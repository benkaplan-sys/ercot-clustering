"""Second-pass subclustering of the largest first-pass cluster.

After the initial clustering identifies broad regional groups, the largest
group often contains hundreds of nodes spanning a wide geographic area.
Subclustering that group with a finer ``maxclust`` cut reveals more detailed
regional structure (e.g., splitting a large "South" cluster into Houston hub,
Corpus Christi area, Rio Grande Valley, etc.).
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from .correlation import build_distance_matrix
from .hierarchical import cut_tree, fit_linkage

logger = logging.getLogger(__name__)


def subcluster_largest(
    assignments: pd.DataFrame,
    prices: pd.DataFrame,
    k: int = 8,
    method: str = "ward",
    criterion: str = "maxclust",
) -> pd.DataFrame:
    """Re-cluster the largest first-pass cluster into *k* subclusters.

    Args:
        assignments: DataFrame with columns ``[node_id, cluster]`` from the
            first-pass analysis.
        prices: Original wide-format price DataFrame used to compute
            correlations within the largest group.
        k: Number of subclusters to extract from the largest cluster.
        method: Linkage method for the second-pass clustering.
        criterion: Cutting criterion for the second pass.  Almost always
            ``"maxclust"``.

    Returns:
        DataFrame with columns ``[node_id, subcluster]`` containing only the
        nodes that belong to the largest first-pass cluster.  Subcluster
        labels are integers starting from 1.

    Raises:
        ValueError: If the largest cluster contains fewer than 2 nodes, which
            would make subclustering impossible.
    """
    # Identify the largest cluster
    cluster_sizes = assignments["cluster"].value_counts()
    largest_cluster_id = cluster_sizes.idxmax()
    largest_nodes = assignments.loc[
        assignments["cluster"] == largest_cluster_id, "node_id"
    ].tolist()

    logger.info(
        "Largest cluster is #%d with %d nodes. Subclustering into %d groups…",
        largest_cluster_id,
        len(largest_nodes),
        k,
    )

    if len(largest_nodes) < 2:
        raise ValueError(
            f"Largest cluster has only {len(largest_nodes)} node(s) — "
            "cannot subcluster with fewer than 2 nodes."
        )

    # Filter prices to nodes in the largest cluster
    valid_nodes = [n for n in largest_nodes if n in prices.columns]
    if len(valid_nodes) < 2:
        raise ValueError(
            f"Only {len(valid_nodes)} of {len(largest_nodes)} nodes in the largest "
            "cluster are present in the prices DataFrame."
        )

    sub_prices = prices[valid_nodes]

    # Build sub-distance matrix and cluster
    _, sub_dist = build_distance_matrix(sub_prices)
    sub_linkage = fit_linkage(sub_dist, method=method)

    # Cap k to the number of available nodes
    effective_k = min(k, len(valid_nodes))
    if effective_k < k:
        logger.warning(
            "Requested k=%d but only %d nodes available; using k=%d",
            k,
            len(valid_nodes),
            effective_k,
        )

    sub_labels = cut_tree(sub_linkage, criterion=criterion, max_clusters=effective_k)

    result = pd.DataFrame({"node_id": valid_nodes, "subcluster": sub_labels})
    logger.info(
        "Subclustering produced %d subclusters from %d nodes",
        result["subcluster"].nunique(),
        len(result),
    )
    return result
