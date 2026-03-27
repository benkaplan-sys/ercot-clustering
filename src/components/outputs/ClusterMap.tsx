
import Plot from 'react-plotly.js';
import type { NodeRecord } from '@/core/types';

interface ClusterMapProps {
  metadata: NodeRecord[];
  labels: Record<string, number>;
  title: string;
  height?: number;
}

const CLUSTER_COLORS = [
  '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
  '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
];

const OUTLIER_COLOR = '#cccccc';

export function ClusterMap({ metadata, labels, title, height = 500 }: ClusterMapProps) {
  // Group nodes by cluster label
  const clusterMap = new Map<number, NodeRecord[]>();
  for (const node of metadata) {
    const label = labels[node.nodeId];
    if (label == null) continue;
    const existing = clusterMap.get(label);
    if (existing) {
      existing.push(node);
    } else {
      clusterMap.set(label, [node]);
    }
  }

  const sortedLabels = Array.from(clusterMap.keys()).sort((a, b) => a - b);

  // Determine singleton clusters (only 1 node) — treated as outliers
  const singletonLabels = new Set(
    sortedLabels.filter(l => (clusterMap.get(l)?.length ?? 0) === 1)
  );

  const traces = sortedLabels.map(label => {
    const nodes = clusterMap.get(label)!;
    const isSingleton = singletonLabels.has(label);
    const colorIdx = (label - 1) % CLUSTER_COLORS.length;
    const color = isSingleton ? OUTLIER_COLOR : CLUSTER_COLORS[colorIdx];

    return {
      type: 'scatter' as const,
      x: nodes.map(n => n.longitude),
      y: nodes.map(n => n.latitude),
      mode: 'markers' as const,
      name: isSingleton ? `Outlier (${nodes[0].nodeId})` : `Cluster ${label} (${nodes.length} nodes)`,
      showlegend: !isSingleton,
      text: nodes.map(n => n.nodeId),
      hovertemplate: '<b>%{text}</b><br>Lat: %{y:.4f}<br>Lon: %{x:.4f}<extra></extra>',
      marker: {
        size: 8,
        color,
        opacity: 0.85,
      },
    };
  });

  return (
    <Plot
      data={traces}
      layout={{
        title: { text: title, font: { size: 14 } },
        xaxis: { title: { text: 'Longitude' }, gridcolor: '#f0f0f0' },
        yaxis: { title: { text: 'Latitude' }, gridcolor: '#f0f0f0' },
        plot_bgcolor: '#ffffff',
        paper_bgcolor: '#ffffff',
        legend: { orientation: 'v', x: 1.02, y: 1, xanchor: 'left' },
        height,
        margin: { l: 60, r: 20, t: 50, b: 50 },
      }}
      config={{ displayModeBar: true, responsive: true }}
      style={{ width: '100%' }}
    />
  );
}
