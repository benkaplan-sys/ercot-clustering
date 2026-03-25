"""Hierarchical agglomerative clustering using scipy.

This module wraps scipy's linkage and fcluster functions to provide a clean
interface for the two cutting strategies used in this project:

- ``"distance"`` — cut the tree at a fixed distance threshold.
- ``"maxclust"`` — cut to produce a fixed number of flat clusters.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

logger = logging.getLogger(__name__)


def fit_linkage(
    dist_df: pd.DataFrame,
    method: str = "ward",
) -> np.ndarray:
    """Fit a hierarchical agglomerative clustering linkage.

    Args:
        dist_df: Symmetric N×N distance DataFrame (1−ρ values, diagonal = 0).
        method: Linkage algorithm.  One of ``"ward"``, ``"average"``,
            ``"complete"``, ``"single"``.  Ward's method minimises within-
            cluster variance and is the recommended default.

    Returns:
        Linkage matrix of shape ``(N-1, 4)`` as returned by
        ``scipy.cluster.hierarchy.linkage``.

    Raises:
        ValueError: If *dist_df* is not square or has fewer than 2 rows.
    """
    n = dist_df.shape[0]
    if dist_df.shape[1] != n:
        raise ValueError(f"dist_df must be square, got shape {dist_df.shape}")
    if n < 2:
        raise ValueError(f"Need at least 2 nodes, got {n}")

    condensed = squareform(dist_df.values, checks=False)
    logger.debug("Fitting linkage (method=%s, n=%d)…", method, n)
    Z = linkage(condensed, method=method)
    logger.debug("Linkage complete. Shape: %s", Z.shape)
    return Z


def cut_tree(
    linkage_matrix: np.ndarray,
    criterion: str = "distance",
    threshold: float = 0.025,
    max_clusters: int = 8,
) -> np.ndarray:
    """Cut the linkage tree into flat clusters.

    Args:
        linkage_matrix: Linkage array as returned by :func:`fit_linkage`.
        criterion: Cutting strategy.  Either ``"distance"`` (cut at
            *threshold*) or ``"maxclust"`` (produce exactly *max_clusters*
            flat clusters).
        threshold: Distance threshold used when ``criterion="distance"``.
        max_clusters: Target cluster count used when ``criterion="maxclust"``.

    Returns:
        1-D integer array of length N with flat cluster labels (1-indexed).

    Raises:
        ValueError: If *criterion* is not one of the supported values.
    """
    if criterion == "distance":
        logger.debug("Cutting tree at distance threshold %.4f", threshold)
        labels = fcluster(linkage_matrix, t=threshold, criterion="distance")
    elif criterion == "maxclust":
        logger.debug("Cutting tree to %d clusters", max_clusters)
        labels = fcluster(linkage_matrix, t=max_clusters, criterion="maxclust")
    else:
        raise ValueError(
            f"Unsupported criterion '{criterion}'. Use 'distance' or 'maxclust'."
        )

    n_clusters = len(np.unique(labels))
    logger.info("Tree cut produced %d cluster(s)", n_clusters)
    return labels
