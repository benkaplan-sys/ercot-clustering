"""Compute Pearson correlation and convert to a distance matrix.

The distance metric used throughout this project is::

    D(i, j) = 1 − ρ(i, j)

where ρ(i, j) is the Pearson correlation coefficient between the price time
series of nodes i and j.  This maps:

- perfectly correlated nodes (ρ = 1)  → D = 0 (same cluster)
- uncorrelated nodes (ρ = 0)          → D = 1
- anti-correlated nodes (ρ = −1)      → D = 2

Values are clipped to [0, 2] to handle floating-point rounding near ±1.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from scipy.spatial.distance import squareform

logger = logging.getLogger(__name__)


def build_distance_matrix(
    prices: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compute the Pearson correlation and 1−ρ distance matrices.

    Missing values (NaN) are handled by pandas' pairwise correlation, which
    uses only the overlapping non-NaN observations for each pair of nodes.

    Args:
        prices: Wide-format DataFrame with a DatetimeIndex and one column per
            node.  Each column is a price time series.

    Returns:
        A 2-tuple ``(corr_df, dist_df)`` where:

        - ``corr_df``: Symmetric N×N DataFrame of Pearson correlations,
          indexed and columned by node names.
        - ``dist_df``: Symmetric N×N DataFrame of 1−ρ distances, clipped
          to [0, 2].

    Raises:
        ValueError: If *prices* has fewer than 2 columns.
    """
    n_nodes = prices.shape[1]
    if n_nodes < 2:
        raise ValueError(f"Need at least 2 nodes to build a distance matrix, got {n_nodes}.")

    logger.debug("Computing %d×%d Pearson correlation matrix…", n_nodes, n_nodes)
    corr: pd.DataFrame = prices.corr(method="pearson", min_periods=10)

    # Fill any NaN pairs (e.g. constant series) with 0 correlation
    corr_filled = corr.fillna(0.0)

    # Clip to [-1, 1] to guard against floating-point drift
    corr_clipped = corr_filled.clip(lower=-1.0, upper=1.0)

    # Distance matrix: D = 1 − ρ, clipped to [0, 2]
    dist_values = (1.0 - corr_clipped).clip(lower=0.0, upper=2.0)
    dist_df = pd.DataFrame(dist_values.values, index=corr.index, columns=corr.columns)

    # Ensure the diagonal is exactly 0 (self-distance)
    np.fill_diagonal(dist_df.values, 0.0)

    logger.debug("Distance matrix complete. Range: [%.4f, %.4f]", dist_df.values.min(), dist_df.values.max())

    return corr_clipped, dist_df


def to_condensed(dist_df: pd.DataFrame) -> np.ndarray:
    """Convert a square distance DataFrame to a condensed 1-D array.

    scipy's linkage functions expect a condensed distance vector as produced
    by ``scipy.spatial.distance.pdist``.

    Args:
        dist_df: Symmetric square distance DataFrame (diagonal = 0).

    Returns:
        1-D condensed distance array suitable for ``scipy.cluster.hierarchy.linkage``.
    """
    return squareform(dist_df.values, checks=False)
