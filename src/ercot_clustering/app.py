"""Streamlit GUI for ERCOT nodal price clustering.

Launch with:
    ercot-cluster-ui
    # or
    streamlit run src/ercot_clustering/app.py
"""

from __future__ import annotations

import io
import logging
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from .config import (
    ClusteringConfig,
    PathConfig,
    full_history_config,
    recent_history_config,
)
from .pipeline import run_pipeline

logger = logging.getLogger(__name__)

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="ERCOT Nodal Price Clustering",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("⚡ ERCOT Clustering")
    st.subheader("Nodal Price Analysis")
    st.divider()

    st.markdown("### Analysis Preset")
    preset = st.radio(
        "Select a preset or configure manually:",
        options=["Full History (2020–now)", "Recent (2024–now)", "Custom"],
        index=0,
        label_visibility="collapsed",
    )

    cfg: ClusteringConfig
    if preset == "Full History (2020–now)":
        cfg = full_history_config()
    elif preset == "Recent (2024–now)":
        cfg = recent_history_config()
    else:
        with st.expander("Custom Parameters", expanded=True):
            start_date = st.text_input("Start date (YYYY-MM-DD)", value="2020-01-01")
            end_date_raw = st.text_input("End date (YYYY-MM-DD, blank = latest)", value="")
            end_date: str | None = end_date_raw.strip() if end_date_raw.strip() else None

            criterion = st.selectbox("Criterion", options=["distance", "maxclust"], index=0)
            if criterion == "distance":
                distance_threshold = st.number_input(
                    "Distance threshold",
                    min_value=0.001,
                    max_value=0.5,
                    value=0.025,
                    step=0.001,
                    format="%.3f",
                )
                max_clusters = 8
            else:
                max_clusters = st.slider("Max clusters", min_value=2, max_value=20, value=8)
                distance_threshold = 0.025

            subcluster_k = st.slider("Subcluster k", min_value=2, max_value=20, value=8)
            linkage_method = st.selectbox(
                "Linkage method",
                options=["ward", "average", "complete", "single"],
                index=0,
            )
            missing_data_threshold = st.slider(
                "Missing data threshold",
                min_value=0.01,
                max_value=0.20,
                value=0.05,
                step=0.01,
            )

        cfg = ClusteringConfig(
            start_date=start_date,
            end_date=end_date,
            criterion=criterion,
            distance_threshold=distance_threshold,
            max_clusters=max_clusters,
            subcluster_k=subcluster_k,
            method=linkage_method,
            missing_data_threshold=missing_data_threshold,
        )

    st.divider()
    with st.expander("About"):
        st.markdown(
            """
            **Methodology**

            1. Compute Pearson correlation between each pair of nodes' 15-min price series.
            2. Convert to distance: `D = 1 − ρ`.
            3. Hierarchical agglomerative clustering (Ward's method by default).
            4. Two cutting strategies: fixed *k* or distance threshold.
            5. Subcluster the largest first-pass group for finer regional structure.

            No geographic data is used during clustering — geographic alignment
            emerges purely from price co-movement.
            """
        )

# ── Status row ────────────────────────────────────────────────────────────────

col_s1, col_s2, col_s3 = st.columns(3)

prices_loaded = "prices_df" in st.session_state
meta_loaded = "metadata_df" in st.session_state
result_ready = "result" in st.session_state

with col_s1:
    if prices_loaded:
        n_price_files = st.session_state.get("n_price_files", 1)
        st.success(f"✅ {n_price_files} price file(s) loaded")
    else:
        st.warning("⚠️ No price data")

with col_s2:
    if meta_loaded:
        st.success("✅ Metadata loaded")
    else:
        st.warning("⚠️ Metadata not loaded")

with col_s3:
    if result_ready:
        st.success("✅ Results ready")
    else:
        st.info("⬜ No results yet")

# ── Main tabs ─────────────────────────────────────────────────────────────────

tab_upload, tab_results = st.tabs(["📂 Data Upload", "📊 Results"])

# ── Upload tab ────────────────────────────────────────────────────────────────

with tab_upload:
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### Price Data")
        price_files = st.file_uploader(
            "Upload one or more price CSVs",
            accept_multiple_files=True,
            type=["csv"],
            key="price_uploader",
        )
        if price_files:
            dfs: list[pd.DataFrame] = []
            for f in price_files:
                dfs.append(pd.read_csv(f, index_col=0, parse_dates=True))
            combined = pd.concat(dfs).sort_index()
            combined = combined.loc[~combined.index.duplicated(keep="first")]
            st.session_state["prices_df"] = combined
            st.session_state["n_price_files"] = len(price_files)
            st.caption(
                f"{len(combined):,} timestamps × {combined.shape[1]:,} nodes"
            )
            st.dataframe(combined.iloc[:5, :5], use_container_width=True)

    with col_right:
        st.markdown("#### Node Metadata")
        meta_file = st.file_uploader(
            "Upload node_locations.csv (node_id, latitude, longitude)",
            type=["csv"],
            key="meta_uploader",
        )
        if meta_file:
            meta_df = pd.read_csv(meta_file)
            st.session_state["metadata_df"] = meta_df
            st.caption(f"{len(meta_df):,} nodes with location data")
            st.dataframe(meta_df.head(), use_container_width=True)

    st.divider()

    # Run button
    can_run = "prices_df" in st.session_state
    if st.button(
        "▶ Run Clustering Analysis",
        type="primary",
        disabled=not can_run,
        use_container_width=True,
    ):
        with st.spinner("Running clustering pipeline…"):
            try:
                # Write uploaded data to a temp directory so pipeline can read files
                if "tmpdir" not in st.session_state:
                    tmpdir_obj = tempfile.TemporaryDirectory()
                    st.session_state["tmpdir"] = tmpdir_obj
                else:
                    tmpdir_obj = st.session_state["tmpdir"]

                tmpdir = Path(tmpdir_obj.name)
                prices_dir = tmpdir / "raw"
                prices_dir.mkdir(exist_ok=True)
                metadata_dir = tmpdir / "metadata"
                metadata_dir.mkdir(exist_ok=True)

                # Write price CSV
                prices_path = prices_dir / "prices.csv"
                st.session_state["prices_df"].to_csv(prices_path)

                # Write metadata CSV (if provided)
                if "metadata_df" in st.session_state:
                    meta_path = metadata_dir / "node_locations.csv"
                    st.session_state["metadata_df"].to_csv(meta_path, index=False)
                else:
                    meta_path = metadata_dir / "node_locations.csv"  # won't exist

                paths = PathConfig(
                    prices_dir=prices_dir,
                    metadata_path=meta_path,
                    output_dir=tmpdir / "outputs",
                )

                result = run_pipeline(cfg=cfg, paths=paths, save_plots=False)
                st.session_state["result"] = result
                st.success("Clustering complete! Switch to the 📊 Results tab.")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Pipeline error: {exc}")

# ── Results tab ───────────────────────────────────────────────────────────────

with tab_results:
    if "result" not in st.session_state:
        st.info("Run the clustering pipeline in the 📂 Data Upload tab to see results here.")
    else:
        result = st.session_state["result"]

        # Metrics row
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Nodes Analysed", len(result.assignments))
        with m2:
            st.metric("First-Pass Clusters", result.assignments["cluster"].nunique())
        with m3:
            st.metric(
                "Subclusters in Largest",
                result.subcluster_assignments["subcluster"].nunique(),
            )

        st.divider()

        # Scatter maps using Plotly (requires plotly installed)
        try:
            import plotly.express as px  # noqa: PLC0415

            if result.metadata is not None and len(result.metadata) > 0:
                map_col1, map_col2 = st.columns(2)

                with map_col1:
                    st.markdown("##### First-Pass Clusters")
                    plot_df_fp = result.metadata.dropna(subset=["latitude", "longitude", "cluster"]).copy()
                    plot_df_fp["cluster_label"] = "Cluster " + plot_df_fp["cluster"].astype(str)
                    fig_fp = px.scatter(
                        plot_df_fp,
                        x="longitude",
                        y="latitude",
                        color="cluster_label",
                        hover_data=["node_id"],
                        title="First-Pass Clusters",
                        color_discrete_sequence=px.colors.qualitative.Plotly,
                        height=450,
                    )
                    fig_fp.update_layout(legend_title_text="Cluster")
                    st.plotly_chart(fig_fp, use_container_width=True)

                with map_col2:
                    st.markdown("##### Subclusters (Largest Group)")
                    plot_df_sub = result.metadata.dropna(
                        subset=["latitude", "longitude", "subcluster"]
                    ).copy()
                    if len(plot_df_sub) > 0:
                        plot_df_sub["subcluster_label"] = (
                            "Sub " + plot_df_sub["subcluster"].astype(str)
                        )
                        fig_sub = px.scatter(
                            plot_df_sub,
                            x="longitude",
                            y="latitude",
                            color="subcluster_label",
                            hover_data=["node_id"],
                            title="Subclusters (Largest First-Pass Group)",
                            color_discrete_sequence=px.colors.qualitative.Safe,
                            height=450,
                        )
                        fig_sub.update_layout(legend_title_text="Subcluster")
                        st.plotly_chart(fig_sub, use_container_width=True)
                    else:
                        st.info("No subcluster location data available.")
            else:
                st.info(
                    "No node metadata was provided, so geographic scatter maps are unavailable. "
                    "Upload a node_locations.csv in the Data Upload tab and re-run."
                )

        except ImportError:
            st.warning(
                "Plotly is not installed. Install with `pip install -e \".[ui]\"` "
                "to enable interactive scatter maps."
            )

        st.divider()

        # Cluster statistics table
        st.markdown("#### Cluster Statistics")
        stats = (
            result.assignments.groupby("cluster")
            .size()
            .reset_index(name="node_count")
            .sort_values("node_count", ascending=False)
        )
        stats.index = range(1, len(stats) + 1)
        st.dataframe(stats, use_container_width=True)

        st.divider()

        # Download section
        st.markdown("#### Download Results")

        # Merge assignments + subclusters for download
        download_df = result.assignments.merge(
            result.subcluster_assignments, on="node_id", how="left"
        )
        if result.metadata is not None:
            download_df = download_df.merge(
                result.metadata[["node_id", "latitude", "longitude"]],
                on="node_id",
                how="left",
            )

        csv_bytes = download_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇ Download cluster_assignments.csv",
            data=csv_bytes,
            file_name="cluster_assignments.csv",
            mime="text/csv",
        )


# ── Entry point ───────────────────────────────────────────────────────────────


def launch() -> None:
    """Entry point for ercot-cluster-ui command."""
    app_path = Path(__file__).resolve()
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(app_path)],
        check=False,
    )
