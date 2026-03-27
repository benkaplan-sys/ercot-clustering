# ERCOT Nodal Price Clustering — Project Guidelines

## Overview

This repo contains both a **React/TypeScript/Vite browser app** (project root) and a **Python reference implementation** (`python/`).

The browser app clusters ERCOT nodal electricity prices hierarchically, revealing geographic coherence in price behavior without using location data.

---

## Frontend Architecture (React/TypeScript/Vite)

### Stack
- **React 19** + **TypeScript** (strict mode)
- **Vite 8** — bundler and dev server
- **Tailwind CSS v4** — utility-first styling (uses `@import "tailwindcss"` in CSS, no config file required, uses `@tailwindcss/vite` plugin)
- **react-plotly.js** — interactive scatter maps
- **papaparse** — CSV parsing in the browser
- **ml-hclust** — hierarchical clustering (`agnes` function)
- **Vitest** — unit testing

### Commands
```bash
npm run dev      # start dev server at http://localhost:5173
npm run build    # production build (tsc + vite build)
npm run test     # run unit tests with Vitest
npm run lint     # ESLint
```

### Project Layout

```
ercot-clustering/
├── src/
│   ├── core/
│   │   ├── types.ts          # Shared TypeScript types and DEFAULT_CONFIG
│   │   ├── csvParser.ts      # Parse wide-format price CSVs and metadata CSVs
│   │   ├── correlation.ts    # Pearson correlation, distance matrix, downsampling
│   │   └── clustering.ts     # Hierarchical clustering using ml-hclust (agnes)
│   ├── workers/
│   │   └── clustering.worker.ts   # Web Worker: full pipeline (downsample → dist → cluster)
│   ├── hooks/
│   │   └── useClustering.ts  # React hook managing Worker lifecycle
│   ├── components/
│   │   ├── inputs/
│   │   │   ├── FileUpload.tsx    # Drag-and-drop file input
│   │   │   └── ConfigPanel.tsx   # Clustering configuration UI
│   │   └── outputs/
│   │       ├── ClusterMap.tsx    # Plotly scatter map colored by cluster
│   │       ├── ClusterStats.tsx  # Summary table (cluster ID, node count, %)
│   │       └── ProgressBar.tsx   # Animated progress during clustering
│   ├── App.tsx               # Root component — layout and state management
│   ├── main.tsx              # React entry point
│   └── index.css             # Tailwind import + custom component classes
├── tests/
│   ├── setup.ts
│   └── unit/
│       ├── correlation.test.ts
│       └── clustering.test.ts
├── python/                   # Python reference implementation (see python/CLAUDE.md)
└── ...config files...
```

### Web Worker Pipeline

The clustering computation runs entirely in a Web Worker (`src/workers/clustering.worker.ts`) to avoid blocking the UI:

1. **Downsample** — if `resolution='daily'`, average 15-min prices to daily values
2. **Drop sparse nodes** — remove nodes exceeding `missingDataThreshold` fraction of NaN
3. **Distance matrix** — compute n×n pairwise `1 - pearson_corr` matrix with inline progress updates
4. **Hierarchical clustering** — `agnes` from `ml-hclust` with Ward linkage; cut by fixed k or distance threshold
5. **Subclustering** — re-cluster the largest cluster into k subclusters
6. Post `RESULT` message back to main thread

### ml-hclust API Notes

- `agnes(data, {method, distanceFunction})` — data is an array of items (we pass integer indices)
- `tree.group(k)` returns the root tree node itself (NOT an array); its `.children` property contains k cluster subtrees
- Each subtree node has `{isLeaf, index, children}` — walk recursively to collect leaf indices
- `tree.cut(distance)` returns an array of cluster subtree nodes (same structure as individual children)

### TypeScript Conventions

- Strict mode (`noUnusedLocals`, `noUnusedParameters`, `strict`)
- No `any` types
- `Float64Array` used for time-series node values (memory-efficient)
- Path alias `@/*` maps to `src/*`
- Worker created via `new Worker(new URL('../workers/clustering.worker.ts', import.meta.url), {type: 'module'})`

### Tailwind v4 Notes

Tailwind v4 does not have a CLI or `tailwind.config.js`. Instead:
- Import in CSS: `@import "tailwindcss";`
- Add plugin in `vite.config.ts`: `import tailwindcss from '@tailwindcss/vite'`
- Custom component classes go in `@layer components { }` in `src/index.css`

---

## Python Reference Implementation

See `python/CLAUDE.md` for the Python architecture. The Python code uses:
- `scipy.cluster.hierarchy` for clustering
- `streamlit` for the GUI
- `pandas` + `numpy` for data handling

Run the Python GUI:
```bash
cd python
pip install -e ".[ui]"
ercot-cluster-ui
```
