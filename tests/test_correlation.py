"""Tests for src/ercot_clustering/clustering/correlation.py."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ercot_clustering.clustering.correlation import build_distance_matrix, to_condensed


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_prices(n_rows: int = 200, n_cols: int = 5, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    data = rng.standard_normal((n_rows, n_cols))
    cols = [f"NODE_{i}" for i in range(n_cols)]
    idx = pd.date_range("2020-01-01", periods=n_rows, freq="15min")
    return pd.DataFrame(data, index=idx, columns=cols)


# ── build_distance_matrix ─────────────────────────────────────────────────────


class TestBuildDistanceMatrix:
    def test_output_shapes(self) -> None:
        prices = _make_prices(n_cols=6)
        corr, dist = build_distance_matrix(prices)
        assert corr.shape == (6, 6)
        assert dist.shape == (6, 6)

    def test_diagonal_is_zero(self) -> None:
        prices = _make_prices(n_cols=5)
        _, dist = build_distance_matrix(prices)
        np.testing.assert_array_almost_equal(np.diag(dist.values), 0.0)

    def test_symmetry(self) -> None:
        prices = _make_prices(n_cols=7)
        corr, dist = build_distance_matrix(prices)
        np.testing.assert_array_almost_equal(corr.values, corr.values.T)
        np.testing.assert_array_almost_equal(dist.values, dist.values.T)

    def test_distance_range(self) -> None:
        prices = _make_prices(n_cols=8)
        _, dist = build_distance_matrix(prices)
        assert dist.values.min() >= -1e-10
        assert dist.values.max() <= 2.0 + 1e-10

    def test_corr_range(self) -> None:
        prices = _make_prices(n_cols=5)
        corr, _ = build_distance_matrix(prices)
        assert corr.values.min() >= -1.0 - 1e-10
        assert corr.values.max() <= 1.0 + 1e-10

    def test_perfect_correlation_gives_zero_distance(self) -> None:
        idx = pd.date_range("2020-01-01", periods=100, freq="15min")
        series = pd.Series(np.linspace(1, 100, 100), index=idx)
        prices = pd.DataFrame({"A": series, "B": series * 2 + 5})
        _, dist = build_distance_matrix(prices)
        assert dist.loc["A", "B"] == pytest.approx(0.0, abs=1e-6)

    def test_anti_correlation_gives_distance_two(self) -> None:
        idx = pd.date_range("2020-01-01", periods=100, freq="15min")
        series = pd.Series(np.linspace(1, 100, 100), index=idx)
        prices = pd.DataFrame({"A": series, "B": -series})
        _, dist = build_distance_matrix(prices)
        assert dist.loc["A", "B"] == pytest.approx(2.0, abs=1e-6)

    def test_index_labels_preserved(self) -> None:
        prices = _make_prices(n_cols=4)
        corr, dist = build_distance_matrix(prices)
        assert list(corr.index) == list(prices.columns)
        assert list(dist.index) == list(prices.columns)
        assert list(dist.columns) == list(prices.columns)

    def test_fewer_than_two_nodes_raises(self) -> None:
        prices = _make_prices(n_cols=1)
        with pytest.raises(ValueError, match="at least 2"):
            build_distance_matrix(prices)

    def test_missing_values_handled(self) -> None:
        prices = _make_prices(n_cols=4)
        prices.iloc[:10, 0] = np.nan  # introduce NaNs
        corr, dist = build_distance_matrix(prices)
        # Should not raise; NaN correlations replaced by 0
        assert not dist.isna().any().any()


# ── to_condensed ──────────────────────────────────────────────────────────────


class TestToCondensed:
    def test_length(self) -> None:
        n = 6
        prices = _make_prices(n_cols=n)
        _, dist = build_distance_matrix(prices)
        condensed = to_condensed(dist)
        expected_len = n * (n - 1) // 2
        assert len(condensed) == expected_len

    def test_values_non_negative(self) -> None:
        prices = _make_prices(n_cols=5)
        _, dist = build_distance_matrix(prices)
        condensed = to_condensed(dist)
        assert (condensed >= 0).all()
