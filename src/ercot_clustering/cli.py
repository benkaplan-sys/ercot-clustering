"""Command-line interface for the ERCOT nodal price clustering pipeline.

Usage examples::

    ercot-cluster --preset full --prices-dir data/raw \\
        --metadata data/metadata/node_locations.csv -v

    ercot-cluster --preset recent -v

    ercot-cluster --criterion maxclust --max-clusters 6 \\
        --start-date 2022-01-01 --end-date 2023-12-31 -v
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .config import ClusteringConfig, PathConfig, full_history_config, recent_history_config
from .pipeline import run_pipeline


def _build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="ercot-cluster",
        description="Hierarchical clustering of ERCOT nodal electricity prices.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Preset shortcut
    parser.add_argument(
        "--preset",
        choices=["full", "recent"],
        default=None,
        help="Use a pre-defined configuration preset. Overrides individual flags.",
    )

    # Paths
    parser.add_argument(
        "--prices-dir",
        type=Path,
        default=Path("data/raw"),
        metavar="DIR",
        help="Directory containing raw 15-min price CSVs.",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=Path("data/metadata/node_locations.csv"),
        metavar="FILE",
        help="Node lat/lon metadata CSV (columns: node_id, latitude, longitude).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        metavar="DIR",
        help="Directory where plots and reports are written.",
    )

    # Clustering parameters
    parser.add_argument(
        "--start-date",
        default="2020-01-01",
        metavar="YYYY-MM-DD",
        help="Exclude data before this date.",
    )
    parser.add_argument(
        "--end-date",
        default=None,
        metavar="YYYY-MM-DD",
        help="Exclude data after this date (default: use all available data).",
    )
    parser.add_argument(
        "--criterion",
        choices=["distance", "maxclust"],
        default="distance",
        help="Cluster-cutting criterion.",
    )
    parser.add_argument(
        "--distance-threshold",
        type=float,
        default=0.025,
        metavar="FLOAT",
        help="Distance threshold (used when --criterion=distance).",
    )
    parser.add_argument(
        "--max-clusters",
        type=int,
        default=8,
        metavar="INT",
        help="Target cluster count (used when --criterion=maxclust).",
    )
    parser.add_argument(
        "--method",
        choices=["ward", "average", "complete", "single"],
        default="ward",
        help="Linkage method.",
    )
    parser.add_argument(
        "--missing-threshold",
        type=float,
        default=0.05,
        metavar="FLOAT",
        help="Drop nodes with a missing-data fraction above this value.",
    )
    parser.add_argument(
        "--subcluster-k",
        type=int,
        default=8,
        metavar="INT",
        help="Number of subclusters for the second-pass analysis.",
    )

    # Verbosity
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable INFO-level logging.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ercot-cluster command.

    Args:
        argv: Argument list (defaults to sys.argv if None).

    Returns:
        Exit code (0 = success, 1 = error).
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Configure logging
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logger = logging.getLogger(__name__)

    # Build config from preset or individual flags
    if args.preset == "full":
        cfg = full_history_config()
        logger.info("Using preset: full history (2020–now, distance criterion)")
    elif args.preset == "recent":
        cfg = recent_history_config()
        logger.info("Using preset: recent history (2024–now, maxclust criterion)")
    else:
        cfg = ClusteringConfig(
            start_date=args.start_date,
            end_date=args.end_date,
            missing_data_threshold=args.missing_threshold,
            method=args.method,
            criterion=args.criterion,
            distance_threshold=args.distance_threshold,
            max_clusters=args.max_clusters,
            subcluster_k=args.subcluster_k,
        )

    paths = PathConfig(
        prices_dir=args.prices_dir,
        metadata_path=args.metadata,
        output_dir=args.output_dir,
    )

    try:
        result = run_pipeline(cfg=cfg, paths=paths)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.exception("Pipeline failed")
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    # Summary
    n_first = result.assignments["cluster"].nunique()
    n_sub = result.subcluster_assignments["subcluster"].nunique()
    print(
        f"Done. {len(result.assignments)} nodes → "
        f"{n_first} first-pass clusters, "
        f"{n_sub} subclusters in largest group."
    )
    if result.output_paths:
        print("Outputs written to:")
        for p in result.output_paths:
            print(f"  {p}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
