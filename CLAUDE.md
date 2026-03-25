# ERCOT Nodal Price Clustering Project

## Project Overview

This project performs hierarchical clustering on ERCOT nodal electricity prices to discover whether nodes with similar price behavior form geographically coherent clusters — without using any location data in the clustering itself. The answer is yes: congestion and transmission constraints are strongly reflected in nodal price co-movement, producing clusters that align with physical grid regions (South, North, West, Houston, Waco).

## Architecture

```
ercot-clustering/
├── CLAUDE.md                    # This file — project guidelines
├── README.md                    # User-facing documentation
├── pyproject.toml               # Python project config (dependencies, scripts)
├── src/
│   └── ercot_clustering/
│       ├── __init__.py
│       ├── config.py            # All configurable parameters (dates, thresholds, k)
│       ├── app.py               # Streamlit GUI (ercot-cluster-ui entry point)
│       ├── data/
│       │   ├── loader.py        # Load 15-min price CSVs + node lat/lon metadata
│       │   └── cleaner.py       # Missing data filtering (>5% threshold)
│       ├── clustering/
│       │   ├── correlation.py   # Pearson correlation matrix → distance matrix (1 − ρ)
│       │   ├── hierarchical.py  # scipy linkage, dendrogram, fcluster (both modes)
│       │   └── subcluster.py    # Re-cluster the largest cluster into k subclusters
│       └── visualization/
│           ├── scatter_map.py   # Scatter plot of nodes colored by cluster on lat/lon axes
│           └── dendrogram.py    # Optional: dendrogram tree visualization
├── data/
│   ├── raw/                     # Raw 15-min price CSVs (not committed)
│   └── metadata/                # Node lat/lon mapping CSV
├── outputs/                     # Generated plots and reports
├── notebooks/                   # Optional Jupyter exploration
└── tests/
    ├── test_correlation.py
    ├── test_clustering.py
    └── test_cleaner.py
```

## Key Technical Decisions

### Language & Libraries
- **Python 3.11+**
- `pandas` — time series data handling
- `numpy` — numerical operations
- `scipy.cluster.hierarchy` — linkage, fcluster, dendrogram
- `scipy.spatial.distance` — squareform, pdist (correlation distance)
- `matplotlib` — scatter plots with cluster coloring
- `streamlit` — interactive web GUI (optional install: `pip install -e ".[ui]"`)
- `plotly` — interactive scatter maps in the Streamlit GUI
- `pytest` — testing

### Clustering Algorithm
- **Hierarchical agglomerative clustering** with **Ward's method** (or average linkage — see config)
- **Distance metric**: `1 − ρ` where `ρ` = Pearson correlation between each pair of nodes' price time series
- Two cutting strategies, selectable per run:
  1. **`maxclust`** — fixed cluster count `k` (better for low-volatility periods like 2024–2025)
  2. **`distance`** — threshold-based natural cluster formation (better for high-volatility periods like 2022–2023)

### Two-Pass Clustering
1. **First pass**: Cluster all nodes → produces broad groups
2. **Second pass (subclustering)**: Take the largest cluster from pass 1 and re-cluster it with `maxclust` k=8 to reveal finer regional structure

## Configuration Parameters

All tunable parameters live in `src/ercot_clustering/config.py`:

```python
@dataclass
class ClusteringConfig:
    # Date ranges
    start_date: str = "2020-01-01"
    end_date: str | None = None  # None = latest available

    # Data quality
    missing_data_threshold: float = 0.05  # Remove nodes with >5% missing

    # First-pass clustering
    method: str = "ward"                  # Linkage method
    criterion: str = "distance"           # "distance" or "maxclust"
    distance_threshold: float = 0.025     # Used when criterion="distance"
    max_clusters: int = 8                 # Used when criterion="maxclust"

    # Subclustering (second pass on largest cluster)
    subcluster_k: int = 8
    subcluster_criterion: str = "maxclust"
```

## GUI

Run the Streamlit GUI with:
```bash
ercot-cluster-ui
# or
streamlit run src/ercot_clustering/app.py
```

The GUI provides:
- Drag-and-drop CSV upload for price data and node metadata
- Preset configuration (Full History / Recent / Custom)
- Interactive Plotly scatter maps showing geographic clustering
- Cluster statistics table
- CSV download of cluster assignments

## Coding Standards
- Type hints on all function signatures
- Docstrings on all public functions (Google style)
- No global state — pass config objects explicitly
- Functions should be pure where possible (input → output, no side effects)
- Use `pathlib.Path` for all file paths
- Format with `ruff` (line length 100)
- Lint with `ruff check`
