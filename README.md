# ERCOT Nodal Price Clustering

An interactive browser-based tool for hierarchical clustering of ERCOT nodal electricity prices, revealing geographic coherence in price behavior without using location data in the clustering itself.

## What It Does

This tool takes wide-format 15-minute LMP (Locational Marginal Price) data from ERCOT nodes, computes pairwise Pearson correlation distances between nodes, and applies hierarchical agglomerative clustering (Ward's method by default) to discover nodes with similar price behavior.

**Key insight:** Transmission constraints and congestion patterns are strongly reflected in nodal price co-movement. Clusters discovered purely from prices tend to align with physical grid regions (South, North, West, Houston, Waco), validating that congestion drives price separation.

The app also performs a **two-pass clustering**:
1. First pass — broad cluster assignment for all nodes
2. Second pass — re-clusters the largest cluster to reveal finer regional structure

## Quick Start

```bash
npm install
npm run dev
```

Then open http://localhost:5173 in your browser.

## Data Requirements

### Price CSV(s) — Wide Format

One or more CSVs with:
- A `timestamp` column (ISO format: `2024-01-01T00:00:00` or similar)
- One column per node with 15-minute LMP prices

Example:
```
timestamp,HB_NORTH,HB_SOUTH,HB_WEST,...
2024-01-01T00:00:00,25.4,27.1,22.8,...
2024-01-01T00:15:00,24.9,26.8,22.2,...
```

Multiple files are supported and will be inner-joined on timestamps.

### Node Metadata CSV

A CSV with at least three columns (case-insensitive):
- `node_id` — must match column names in the price CSV
- `latitude`
- `longitude`

Example:
```
node_id,latitude,longitude
HB_NORTH,33.5,-97.3
HB_SOUTH,29.8,-95.4
```

## How to Use the UI

1. **Upload price CSV(s)** — drag and drop or click to browse. Multiple files are merged.
2. **Upload metadata CSV** — provides lat/lon for map visualization.
3. **Configure clustering** — choose preset or customize criterion, cluster count, and subclustering.
4. **Click "Run Clustering"** — computation runs in a background Web Worker (no UI freezing).
5. **Explore results** — interactive Plotly scatter maps show nodes colored by cluster on a lat/lon grid. Toggle between first-pass and subcluster views.
6. **Download CSV** — export cluster assignments (node_id, lat, lon, first_pass_cluster, subcluster).

## Configuration Options

| Option | Description |
|---|---|
| **Preset: Full History** | Distance threshold criterion (0.025), good for multi-year data with high volatility |
| **Preset: Recent (2024+)** | Fixed-k criterion with k=6, better for low-volatility recent data |
| **Criterion** | Fixed k: cut tree into exactly k clusters. Distance threshold: cut at a distance level |
| **Max Clusters / Threshold** | Controls first-pass cluster count |
| **Subclusters** | How many subclusters to split the largest first-pass cluster into |
| **Resolution** | Daily (faster, averages 15-min to daily) or Full 15-min |
| **Linkage Method** | Ward (default), Average, Complete, Single |
| **Missing Data Threshold** | Nodes with more than this fraction of NaN prices are dropped |

## Methodology

1. **Preprocessing** — optionally downsample 15-min data to daily averages; drop nodes with excessive missing data
2. **Distance matrix** — pairwise `1 - rho(i, j)` where rho is Pearson correlation (NaN pairs deleted pairwise)
3. **Hierarchical clustering** — agglomerative using Ward's method (or configured linkage); cut by fixed k or distance threshold
4. **Subclustering** — largest cluster re-clustered into k subclusters
5. **Visualization** — Plotly scatter plot with longitude (x) and latitude (y), one color per cluster

All computation runs client-side in a Web Worker — no data leaves your browser.

## Development

```bash
npm run dev      # start dev server
npm run build    # production build
npm run test     # run unit tests
npm run lint     # lint
```

## Python Reference Implementation

The original Python/Streamlit implementation lives in `python/`. It uses `scipy.cluster.hierarchy` and can be run as a Streamlit app:

```bash
cd python
pip install -e ".[ui]"
ercot-cluster-ui
```

See `python/src/` for the Python source and `python/tests/` for Python tests.
