"""Tests for src/ercot_clustering/data/cleaner.py."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ercot_clustering.data.cleaner import drop_sparse_nodes


def _make_prices(n_rows: int = 100, n_cols: int = 5) -> pd.DataFrame:
    """Helper: create a simple price DataFrame with no missing values."""
    rng = np.random.default_rng(42)
    data = rng.standard_normal((n_rows, n_cols))
    cols = [f"NODE_{i}" for i in range(n_cols)]
    idx = pd.date_range("2020-01-01", periods=n_rows, freq="15min")
    return pd.DataFrame(data, index=idx, columns=cols)


class TestDropSparseNodes:
    def test_no_missing_keeps_all(self) -> None:
        prices = _make_prices()
        result = drop_sparse_nodes(prices, threshold=0.05)
        assert list(result.columns) == list(prices.columns)

    def test_all_missing_drops_node(self) -> None:
        prices = _make_prices(n_cols=3)
        prices["NODE_0"] = np.nan  # 100% missing
        result = drop_sparse_nodes(prices, threshold=0.05)
        assert "NODE_0" not in result.columns
        assert "NODE_1" in result.columns
        assert "NODE_2" in result.columns

    def test_exactly_at_threshold_keeps(self) -> None:
        prices = _make_prices(n_rows=100, n_cols=2)
        # Introduce exactly 5% missing in NODE_0 (5 of 100 rows)
        prices.iloc[:5, 0] = np.nan
        result = drop_sparse_nodes(prices, threshold=0.05)
        assert "NODE_0" in result.columns

    def test_just_above_threshold_drops(self) -> None:
        prices = _make_prices(n_rows=100, n_cols=2)
        # Introduce 6% missing (6 of 100 rows)
        prices.iloc[:6, 0] = np.nan
        result = drop_sparse_nodes(prices, threshold=0.05)
        assert "NODE_0" not in result.columns
        assert "NODE_1" in result.columns

    def test_original_not_mutated(self) -> None:
        prices = _make_prices()
        prices_copy = prices.copy()
        drop_sparse_nodes(prices, threshold=0.05)
        pd.testing.assert_frame_equal(prices, prices_copy)

    def test_empty_dataframe_returns_copy(self) -> None:
        empty = pd.DataFrame()
        result = drop_sparse_nodes(empty, threshold=0.05)
        assert result.empty

    def test_invalid_threshold_raises(self) -> None:
        prices = _make_prices()
        with pytest.raises(ValueError, match="threshold must be in"):
            drop_sparse_nodes(prices, threshold=1.5)
        with pytest.raises(ValueError, match="threshold must be in"):
            drop_sparse_nodes(prices, threshold=-0.1)

    def test_zero_threshold_drops_any_missing(self) -> None:
        prices = _make_prices(n_rows=100, n_cols=3)
        prices.iloc[0, 0] = np.nan  # 1% missing
        result = drop_sparse_nodes(prices, threshold=0.0)
        assert "NODE_0" not in result.columns

    def test_threshold_one_keeps_all(self) -> None:
        prices = _make_prices(n_cols=3)
        prices["NODE_0"] = np.nan  # 100% missing
        result = drop_sparse_nodes(prices, threshold=1.0)
        assert "NODE_0" in result.columns
