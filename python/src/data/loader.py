"""Load raw ERCOT price CSVs and node metadata.

Expected formats
----------------
Price CSVs (wide format)::

    timestamp,NODE_A,NODE_B,...
    2020-01-01 00:00,25.3,24.8,...
    2020-01-01 00:15,26.1,25.0,...
    ...

Metadata CSV::

    node_id,latitude,longitude
    NODE_A,29.74,-95.37
    NODE_B,32.89,-97.02
    ...
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def load_prices(
    prices_dir: Path,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    """Load and concatenate all price CSVs from a directory.

    CSVs are expected to be in wide format with a timestamp column as the
    index (or first column).  Files are concatenated along the time axis and
    duplicate timestamps are deduplicated (first occurrence kept).

    Args:
        prices_dir: Directory containing one or more ``.csv`` price files.
        start_date: ISO-format date string; rows before this date are dropped.
        end_date: ISO-format date string; rows after this date are dropped.

    Returns:
        DataFrame with a DatetimeIndex and one column per node.

    Raises:
        FileNotFoundError: If *prices_dir* contains no CSV files.
    """
    prices_dir = Path(prices_dir)
    csv_files = sorted(prices_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {prices_dir}")

    logger.debug("Found %d price file(s): %s", len(csv_files), [f.name for f in csv_files])

    dfs: list[pd.DataFrame] = []
    for csv_path in csv_files:
        logger.debug("Reading %s", csv_path.name)
        df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
        dfs.append(df)

    combined: pd.DataFrame = pd.concat(dfs, axis=0)
    combined.sort_index(inplace=True)
    combined = combined.loc[~combined.index.duplicated(keep="first")]

    # Date filtering
    if start_date is not None:
        combined = combined.loc[combined.index >= pd.Timestamp(start_date)]
    if end_date is not None:
        combined = combined.loc[combined.index <= pd.Timestamp(end_date)]

    logger.info(
        "Loaded %d timestamps × %d nodes (date range %s → %s)",
        len(combined),
        combined.shape[1],
        combined.index.min().date() if len(combined) else "N/A",
        combined.index.max().date() if len(combined) else "N/A",
    )
    return combined


def load_metadata(metadata_path: Path) -> pd.DataFrame:
    """Load node lat/lon metadata from a CSV file.

    Args:
        metadata_path: Path to the metadata CSV.  Expected columns:
            ``node_id``, ``latitude``, ``longitude``.

    Returns:
        DataFrame with columns [node_id, latitude, longitude].

    Raises:
        FileNotFoundError: If *metadata_path* does not exist.
        KeyError: If required columns are missing from the CSV.
    """
    metadata_path = Path(metadata_path)
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")

    meta = pd.read_csv(metadata_path)

    required = {"node_id", "latitude", "longitude"}
    missing_cols = required - set(meta.columns)
    if missing_cols:
        raise KeyError(
            f"Metadata CSV is missing required columns: {missing_cols}. "
            f"Found: {list(meta.columns)}"
        )

    logger.info("Loaded metadata for %d nodes from %s", len(meta), metadata_path.name)
    return meta[["node_id", "latitude", "longitude"]].copy()
