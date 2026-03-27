"""Tests for hierarchical clustering and subclustering modules."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ercot_clustering.clustering.hierarchical import cut_tree, fit_linkage
from ercot_clustering.clustering.subcluster import subcluster_largest


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_distance_df(n: int = 10, seed: int = 0) -> pd.DataFrame:
    """Create a random symmetric distance matrix with zero diagonal."""
    rng = np.random.default_rng(seed)
    raw = rng.uniform(0, 1, (n, n))
    sym = (raw + raw.T) / 2
    np.fill_diagonal(sym, 0.0)
    nodes = [f"NODE_{i}" for i in range(n)]
    return pd.DataFrame(sym, index=nodes, columns=nodes)


def _make_prices_with_clusters(n_nodes: int = 20, n_ts: int = 200) -> pd.DataFrame:
    """Create a price DataFrame with two synthetic clusters."""
    rng = np.random.default_rng(99)
    idx = pd.date_range("2022-01-01", periods=n_ts, freq="15min")
    base_a = rng.standard_normal(n_ts)
    base_b = rng.standard_normal(n_ts)
    cols = {}
    for i in range(n_nodes):
        base = base_a if i < n_nodes // 2 else base_b
        cols[f"NODE_{i}"] = base + rng.normal(0, 0.05, n_ts)
    return pd.DataFrame(cols, index=idx)


# ── fit_linkage ───────────────────────────────────────────────────────────────


class TestFitLinkage:
    def test_output_shape(self) -> None:
        dist = _make_distance_df(n=10)
        Z = fit_linkage(dist, method="ward")
        assert Z.shape == (9, 4)  # (N-1, 4)

    def test_non_square_raises(self) -> None:
        bad = pd.DataFrame(np.ones((3, 4)))
        with pytest.raises(ValueError, match="square"):
            fit_linkage(bad)

    def test_too_few_nodes_raises(self) -> None:
        tiny = pd.DataFrame([[0.0]], index=["A"], columns=["A"])
        with pytest.raises(ValueError, match="at least 2"):
            fit_linkage(tiny)

    @pytest.mark.parametrize("method", ["ward", "average", "complete", "single"])
    def test_all_methods_run(self, method: str) -> None:
        dist = _make_distance_df(n=8)
        Z = fit_linkage(dist, method=method)
        assert Z.shape[0] == 7


# ── cut_tree ──────────────────────────────────────────────────────────────────


class TestCutTree:
    def _linkage(self, n: int = 12) -> np.ndarray:
        dist = _make_distance_df(n=n)
        return fit_linkage(dist, method="ward")

    def test_maxclust_gives_right_k(self) -> None:
        Z = self._linkage(n=15)
        labels = cut_tree(Z, criterion="maxclust", max_clusters=4)
        assert len(np.unique(labels)) == 4

    def test_distance_criterion_runs(self) -> None:
        Z = self._linkage(n=15)
        labels = cut_tree(Z, criterion="distance", threshold=0.5)
        assert len(labels) == 15
        assert labels.min() >= 1  # fcluster labels are 1-indexed

    def test_invalid_criterion_raises(self) -> None:
        Z = self._linkage()
        with pytest.raises(ValueError, match="Unsupported criterion"):
            cut_tree(Z, criterion="bogus")

    def test_labels_length_matches_n(self) -> None:
        n = 20
        Z = self._linkage(n=n)
        labels = cut_tree(Z, criterion="maxclust", max_clusters=5)
        assert len(labels) == n


# ── subcluster_largest ────────────────────────────────────────────────────────


class TestSubclusterLargest:
    def _setup(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        prices = _make_prices_with_clusters(n_nodes=20)
        nodes = list(prices.columns)
        # Assign first 15 nodes to cluster 1, remaining 5 to cluster 2
        cluster_labels = [1] * 15 + [2] * 5
        assignments = pd.DataFrame({"node_id": nodes, "cluster": cluster_labels})
        return assignments, prices

    def test_returns_only_largest_cluster_nodes(self) -> None:
        assignments, prices = self._setup()
        result = subcluster_largest(assignments, prices, k=3)
        # Largest cluster has 15 nodes (cluster 1)
        assert len(result) == 15

    def test_subcluster_column_present(self) -> None:
        assignments, prices = self._setup()
        result = subcluster_largest(assignments, prices, k=3)
        assert "subcluster" in result.columns
        assert "node_id" in result.columns

    def test_subcluster_count_respects_k(self) -> None:
        assignments, prices = self._setup()
        result = subcluster_largest(assignments, prices, k=3)
        assert result["subcluster"].nunique() == 3

    def test_too_small_largest_cluster_raises(self) -> None:
        prices = _make_prices_with_clusters(n_nodes=4)
        nodes = list(prices.columns)
        assignments = pd.DataFrame({"node_id": nodes, "cluster": [1, 1, 2, 3]})
        # Largest is cluster 1 with 2 nodes; k=3 → cap to 2 (no raise expected)
        result = subcluster_largest(assignments, prices, k=3)
        assert len(result) == 2

    def test_single_node_largest_raises(self) -> None:
        prices = _make_prices_with_clusters(n_nodes=3)
        nodes = list(prices.columns)
        assignments = pd.DataFrame({"node_id": nodes, "cluster": [1, 2, 3]})
        with pytest.raises(ValueError, match="fewer than 2"):
            subcluster_largest(assignments, prices, k=2)
