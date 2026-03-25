"""Scatter-map visualization: nodes plotted on lat/lon axes, colored by cluster.

The scatter map is the primary diagnostic output of this project.  If clusters
are geographically coherent, nodes of the same color should form spatially
contiguous regions on the plot — without any geographic data having been used
during clustering.
"""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

logger = logging.getLogger(__name__)

# Color palette: up to 20 visually distinct colors
_PALETTE = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    "#aec7e8", "#ffbb78", "#98df8a", "#ff9896", "#c5b0d5",
    "#c49c94", "#f7b6d2", "#c7c7c7", "#dbdb8d", "#9edae5",
]


def plot_scatter_map(
    metadata: pd.DataFrame,
    cluster_col: str = "cluster",
    title: str = "Nodal Clusters",
    output_path: Path | None = None,
    figsize: tuple[float, float] = (12, 8),
) -> plt.Figure:
    """Plot nodes as a scatter map colored by cluster label.

    Args:
        metadata: DataFrame containing at minimum ``latitude``, ``longitude``,
            and the column named by *cluster_col*.  An optional ``node_id``
            column is used for hover labels if present.
        cluster_col: Name of the column containing cluster labels.
        title: Figure title.
        output_path: If provided, save the figure to this path (PNG by
            default; format inferred from suffix).  The parent directory must
            exist.
        figsize: Matplotlib figure size ``(width, height)`` in inches.

    Returns:
        The Matplotlib Figure object (caller can further modify or close it).

    Raises:
        KeyError: If required columns (latitude, longitude, *cluster_col*) are
            missing from *metadata*.
    """
    required = {"latitude", "longitude", cluster_col}
    missing = required - set(metadata.columns)
    if missing:
        raise KeyError(f"metadata is missing required columns: {missing}")

    plot_df = metadata.dropna(subset=["latitude", "longitude", cluster_col]).copy()
    if len(plot_df) == 0:
        logger.warning("No rows remain after dropping NaN lat/lon/cluster — skipping plot.")
        fig, ax = plt.subplots(figsize=figsize)
        ax.set_title(title)
        return fig

    clusters = sorted(plot_df[cluster_col].unique())
    color_map = {c: _PALETTE[i % len(_PALETTE)] for i, c in enumerate(clusters)}

    fig, ax = plt.subplots(figsize=figsize)

    for cluster_id in clusters:
        subset = plot_df[plot_df[cluster_col] == cluster_id]
        ax.scatter(
            subset["longitude"],
            subset["latitude"],
            c=color_map[cluster_id],
            label=f"{cluster_col.capitalize()} {cluster_id}",
            s=40,
            alpha=0.75,
            edgecolors="none",
        )

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.legend(
        loc="best",
        markerscale=1.5,
        fontsize=8,
        framealpha=0.8,
        ncol=max(1, len(clusters) // 8),
    )
    ax.grid(True, alpha=0.3, linestyle="--")
    fig.tight_layout()

    if output_path is not None:
        output_path = Path(output_path)
        logger.info("Saving scatter map to %s", output_path)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")

    return fig
