"""Configuration dataclasses for the ERCOT clustering pipeline.

All tunable parameters live here. Pass a ClusteringConfig instance to pipeline
functions rather than using global variables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ClusteringConfig:
    """Parameters controlling the clustering algorithm.

    Attributes:
        start_date: ISO-format date string; data before this date is excluded.
        end_date: ISO-format date string or None (use all available data).
        missing_data_threshold: Nodes with a fraction of missing values above
            this threshold are dropped before clustering.
        method: Linkage method passed to scipy.cluster.hierarchy.linkage.
            Typical values: "ward", "average", "complete", "single".
        criterion: Cluster-cutting strategy.  Either "distance" (cut the tree
            at *distance_threshold*) or "maxclust" (cut to produce exactly
            *max_clusters* flat clusters).
        distance_threshold: Used when criterion="distance".  Nodes whose
            linkage distance exceeds this value are placed in different
            clusters.  Typical range 0.01–0.10.
        max_clusters: Used when criterion="maxclust".  Target number of flat
            clusters returned by fcluster.
        subcluster_k: Number of subclusters to extract from the largest
            first-pass cluster in the second-pass analysis.
        subcluster_criterion: Criterion for the second-pass subcluster step.
            Almost always "maxclust".
    """

    # Date range
    start_date: str = "2020-01-01"
    end_date: str | None = None

    # Data quality
    missing_data_threshold: float = 0.05

    # First-pass clustering
    method: str = "ward"
    criterion: str = "distance"
    distance_threshold: float = 0.025
    max_clusters: int = 8

    # Second-pass subclustering
    subcluster_k: int = 8
    subcluster_criterion: str = "maxclust"


@dataclass
class PathConfig:
    """File-system paths used by the pipeline.

    Attributes:
        prices_dir: Directory containing one or more raw price CSVs.
        metadata_path: Path to the node lat/lon metadata CSV.
        output_dir: Directory where figures and reports are written.
    """

    prices_dir: Path = field(default_factory=lambda: Path("data/raw"))
    metadata_path: Path = field(default_factory=lambda: Path("data/metadata/node_locations.csv"))
    output_dir: Path = field(default_factory=lambda: Path("outputs"))

    def __post_init__(self) -> None:
        """Coerce string inputs to Path objects."""
        self.prices_dir = Path(self.prices_dir)
        self.metadata_path = Path(self.metadata_path)
        self.output_dir = Path(self.output_dir)


def full_history_config() -> ClusteringConfig:
    """Return a ClusteringConfig preset for full history (2020–now).

    Uses distance-threshold cutting, which works well when the full date
    range includes the high-volatility 2022–2023 period.

    Returns:
        ClusteringConfig instance with full-history defaults.
    """
    return ClusteringConfig(
        start_date="2020-01-01",
        end_date=None,
        criterion="distance",
        distance_threshold=0.025,
        max_clusters=8,
        subcluster_k=8,
    )


def recent_history_config() -> ClusteringConfig:
    """Return a ClusteringConfig preset for recent data (2024–now).

    Uses maxclust cutting because the lower-volatility recent period tends
    not to produce strong natural distance-based separation.

    Returns:
        ClusteringConfig instance with recent-history defaults.
    """
    return ClusteringConfig(
        start_date="2024-01-01",
        end_date=None,
        criterion="maxclust",
        max_clusters=8,
        subcluster_k=8,
    )
