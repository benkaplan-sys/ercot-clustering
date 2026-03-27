"""Data quality filtering for ERCOT nodal price time series.

The only filter currently applied is dropping nodes that have too many missing
(NaN) values in their price series.  A node with more than *threshold* fraction
of missing values is unlikely to produce reliable correlation estimates and is
dropped before the correlation matrix is computed.
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def drop_sparse_nodes(
    prices: pd.DataFrame,
    threshold: float = 0.05,
) -> pd.DataFrame:
    """Drop columns (nodes) whose missing-data fraction exceeds *threshold*.

    Args:
        prices: Wide-format DataFrame with a DatetimeIndex and one column per
            node.  NaN values represent missing price observations.
        threshold: Maximum allowable fraction of missing values.  Nodes with
            ``nan_fraction > threshold`` are removed.  Must be in [0, 1].

    Returns:
        Filtered DataFrame with sparse nodes removed.  The original DataFrame
        is not modified.

    Raises:
        ValueError: If *threshold* is not in [0, 1].
    """
    if not 0.0 <= threshold <= 1.0:
        raise ValueError(f"threshold must be in [0, 1], got {threshold}")

    n_rows = len(prices)
    if n_rows == 0:
        logger.warning("prices DataFrame is empty — returning as-is.")
        return prices.copy()

    nan_fractions: pd.Series = prices.isna().sum() / n_rows
    keep_mask = nan_fractions <= threshold
    dropped = keep_mask[~keep_mask].index.tolist()

    if dropped:
        logger.info(
            "Dropping %d node(s) with >%.1f%% missing data: %s",
            len(dropped),
            threshold * 100,
            dropped[:10],  # log at most 10 names to keep output readable
        )
    else:
        logger.debug("All %d nodes pass the missing-data threshold.", prices.shape[1])

    return prices.loc[:, keep_mask].copy()
