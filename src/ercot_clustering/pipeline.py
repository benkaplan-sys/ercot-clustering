"""End-to-end orchestration for the ERCOT nodal price clustering pipeline.

Typical usage::

    from ercot_clustering import run_pipeline, full_history_config
    from ercot_clustering.config import PathConfig

    result = run_pipeline(
        cfg=full_history_config(),
        paths=PathConfig(),
    )
    print(result.assignments.head())
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from .config import ClusteringConfig, PathConfig
from .clustering.correlation import build_distance_matrix
from .clustering.hierarchical import cut_tree, fit_linkage
from .clustering.subcluster import subcluster_largest
from .data.cleaner import drop_sparse_nodes
from .data.loader import load_metadata, load_prices
from .visualization.scatter_map import plot_scatter_map

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Container for all outputs produced by a clustering pipeline run.

    Attributes:
        assignments: DataFrame with columns [node_id, cluster] — one row per
            node, cluster labels from the first-pass analysis.
        subcluster_assignments: DataFrame with columns [node_id, subcluster] —
            rows only for nodes in the largest first-pass cluster.
        correlation_matrix: Symmetric N×N DataFrame of Pearson correlations.
        distance_matrix: Symmetric N×N DataFrame of 1−ρ distances.
        linkage_matrix: Raw scipy linkage array (shape (N-1, 4)).
        metadata: Node lat/lon DataFrame joined with cluster labels, or None
            if no metadata was available.
        output_paths: List of Path objects for files written to disk.
        config: The ClusteringConfig used for this run.
    """

    assignments: pd.DataFrame
    subcluster_assignments: pd.DataFrame
    correlation_matrix: pd.DataFrame
    distance_matrix: pd.DataFrame
    linkage_matrix: np.ndarray
    metadata: pd.DataFrame | None
    output_paths: list[Path] = field(default_factory=list)
    config: ClusteringConfig = field(default_factory=ClusteringConfig)


def run_pipeline(
    cfg: ClusteringConfig,
    paths: PathConfig,
    *,
    save_plots: bool = True,
) -> PipelineResult:
    """Run the full two-pass clustering pipeline.

    Steps:
        1. Load raw price CSVs from *paths.prices_dir*.
        2. Filter to the date range in *cfg*.
        3. Drop nodes that exceed *cfg.missing_data_threshold*.
        4. Compute Pearson correlation → distance matrix.
        5. Fit hierarchical linkage and cut to flat clusters (first pass).
        6. Subcluster the largest first-pass cluster (second pass).
        7. Optionally load node metadata and produce scatter-map figures.

    Args:
        cfg: Clustering configuration parameters.
        paths: File-system paths for inputs and outputs.
        save_plots: If True, write PNG scatter maps to *paths.output_dir*.

    Returns:
        PipelineResult with all intermediate and final outputs.

    Raises:
        FileNotFoundError: If *paths.prices_dir* contains no CSV files.
        ValueError: If fewer than 2 nodes remain after quality filtering.
    """
    logger.info("=== ERCOT Clustering Pipeline ===")
    logger.info("Config: %s", cfg)
    logger.info("Paths:  %s", paths)

    # ── 1. Load prices ────────────────────────────────────────────────────────
    logger.info("Loading prices from %s", paths.prices_dir)
    prices: pd.DataFrame = load_prices(
        prices_dir=paths.prices_dir,
        start_date=cfg.start_date,
        end_date=cfg.end_date,
    )
    logger.info("Loaded %d timestamps × %d nodes", len(prices), prices.shape[1])

    # ── 2. Clean ──────────────────────────────────────────────────────────────
    logger.info("Dropping nodes with >%.0f%% missing data", cfg.missing_data_threshold * 100)
    prices = drop_sparse_nodes(prices, threshold=cfg.missing_data_threshold)
    logger.info("%d nodes remain after quality filter", prices.shape[1])

    if prices.shape[1] < 2:
        raise ValueError(
            f"Only {prices.shape[1]} node(s) remain after quality filtering — "
            "need at least 2 to cluster."
        )

    # ── 3. Correlation → distance ─────────────────────────────────────────────
    logger.info("Computing correlation matrix (%d×%d)…", prices.shape[1], prices.shape[1])
    corr_df, dist_df = build_distance_matrix(prices)
    logger.info("Correlation matrix complete.")

    # ── 4. First-pass linkage & cut ───────────────────────────────────────────
    logger.info("Fitting linkage (method=%s)…", cfg.method)
    linkage_matrix = fit_linkage(dist_df, method=cfg.method)

    logger.info("Cutting tree (criterion=%s)…", cfg.criterion)
    labels: np.ndarray = cut_tree(
        linkage_matrix,
        criterion=cfg.criterion,
        threshold=cfg.distance_threshold,
        max_clusters=cfg.max_clusters,
    )

    assignments = pd.DataFrame(
        {"node_id": dist_df.index.tolist(), "cluster": labels}
    )
    n_clusters = assignments["cluster"].nunique()
    logger.info("First pass: %d clusters from %d nodes", n_clusters, len(assignments))

    # ── 5. Subclustering ──────────────────────────────────────────────────────
    logger.info(
        "Subclustering largest cluster into %d groups (criterion=%s)…",
        cfg.subcluster_k,
        cfg.subcluster_criterion,
    )
    subcluster_assignments = subcluster_largest(
        assignments=assignments,
        prices=prices,
        k=cfg.subcluster_k,
        method=cfg.method,
        criterion=cfg.subcluster_criterion,
    )
    logger.info(
        "Second pass: %d subclusters", subcluster_assignments["subcluster"].nunique()
    )

    # ── 6. Load metadata (optional) ───────────────────────────────────────────
    metadata: pd.DataFrame | None = None
    if paths.metadata_path.exists():
        logger.info("Loading node metadata from %s", paths.metadata_path)
        meta_raw = load_metadata(paths.metadata_path)
        # Join cluster labels onto metadata
        metadata = meta_raw.merge(assignments, on="node_id", how="inner")
        # Also join subclusters
        metadata = metadata.merge(subcluster_assignments, on="node_id", how="left")
        logger.info(
            "Metadata joined: %d of %d nodes have location data",
            len(metadata),
            len(assignments),
        )
    else:
        logger.warning(
            "Metadata file not found at %s — skipping geographic plots", paths.metadata_path
        )

    # ── 7. Save plots ─────────────────────────────────────────────────────────
    output_paths: list[Path] = []
    if save_plots and metadata is not None:
        paths.output_dir.mkdir(parents=True, exist_ok=True)

        # First-pass scatter map
        fp_out = paths.output_dir / "scatter_first_pass.png"
        logger.info("Saving first-pass scatter map → %s", fp_out)
        plot_scatter_map(
            metadata=metadata,
            cluster_col="cluster",
            title="First-Pass Clusters",
            output_path=fp_out,
        )
        output_paths.append(fp_out)

        # Subcluster scatter map (only nodes that were subclustered)
        sub_meta = metadata.dropna(subset=["subcluster"])
        if len(sub_meta) > 0:
            sub_out = paths.output_dir / "scatter_subclusters.png"
            logger.info("Saving subcluster scatter map → %s", sub_out)
            plot_scatter_map(
                metadata=sub_meta,
                cluster_col="subcluster",
                title="Subclusters (Largest First-Pass Group)",
                output_path=sub_out,
            )
            output_paths.append(sub_out)

    logger.info("Pipeline complete.")
    return PipelineResult(
        assignments=assignments,
        subcluster_assignments=subcluster_assignments,
        correlation_matrix=corr_df,
        distance_matrix=dist_df,
        linkage_matrix=linkage_matrix,
        metadata=metadata,
        output_paths=output_paths,
        config=cfg,
    )
