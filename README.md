# ERCOT Nodal Price Clustering

Hierarchical clustering of ERCOT nodal electricity prices to discover geographically coherent pricing regions — without using any location data in the clustering process.

## Key Finding

Nodes with similar price behavior cluster together geographically. Congestion and transmission constraints are strongly reflected in nodal price co-movement, producing consistent groupings across **South, North, West, Houston, and Waco** regions.

## Quick Start

```bash
# Install core
pip install -e ".[dev]"

# Install with Streamlit GUI
pip install -e ".[ui,dev]"

# Run the interactive GUI (recommended)
ercot-cluster-ui

# Or run via CLI
ercot-cluster --preset full --prices-dir data/raw --metadata data/metadata/node_locations.csv -v
ercot-cluster --preset recent -v

# Run tests
pytest
```

## Data Requirements

1. **Price CSVs** in `data/raw/`: 15-minute interval LMP prices, wide format with columns `[timestamp, node_1, node_2, ...]`
2. **Node metadata** at `data/metadata/node_locations.csv`: columns `[node_id, latitude, longitude]` (sources: Ascend Analytics, Grid Status)

## Streamlit GUI

The GUI (`ercot-cluster-ui`) provides a fully interactive workflow:

1. **Upload** price CSV(s) and node metadata via drag-and-drop
2. **Configure** using a preset (Full History / Recent) or custom parameters in the sidebar
3. **Run** the full two-pass clustering pipeline with a single click
4. **Explore** results in an interactive Plotly scatter map — hover over nodes to see IDs
5. **Download** cluster assignments as a CSV for further analysis

## Methodology

1. Compute Pearson correlation between all node pairs' price time series
2. Convert to distance: `D = 1 − ρ`
3. Hierarchical agglomerative clustering (Ward's method) with two cutting strategies:
   - **Distance threshold** (0.025) — for high-volatility periods with natural separation
   - **Fixed k** (8 clusters) — for low-volatility periods where natural separation is weak
4. Subcluster the largest first-pass cluster into 8 groups to reveal finer regional structure

## Project Structure

```
src/ercot_clustering/
├── config.py              # All tunable parameters
├── cli.py                 # Command-line interface
├── app.py                 # Streamlit GUI
├── pipeline.py            # End-to-end orchestration
├── data/
│   ├── loader.py          # Load price CSVs and metadata
│   └── cleaner.py         # Drop nodes with >5% missing data
├── clustering/
│   ├── correlation.py     # Correlation → distance matrix
│   ├── hierarchical.py    # Linkage + dendrogram cutting
│   └── subcluster.py      # Re-cluster largest group
└── visualization/
    ├── scatter_map.py      # Lat/lon scatter plots colored by cluster
    └── dendrogram.py       # Dendrogram tree plots
```

See [CLAUDE.md](CLAUDE.md) for full technical guidelines.
