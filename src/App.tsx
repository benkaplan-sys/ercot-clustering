import { useState, useEffect } from 'react';
import { parsePriceCSVs, parseMetadataCSV } from '@/core/csvParser';
import { DEFAULT_CONFIG } from '@/core/types';
import type { PriceMatrix, NodeRecord, ClusteringConfig } from '@/core/types';
import { useClustering } from '@/hooks/useClustering';
import { FileUpload } from '@/components/inputs/FileUpload';
import { ConfigPanel } from '@/components/inputs/ConfigPanel';
import { ProgressBar } from '@/components/outputs/ProgressBar';
import { ClusterMap } from '@/components/outputs/ClusterMap';
import { ClusterStats } from '@/components/outputs/ClusterStats';

type OutputTab = 'first-pass' | 'subclusters';

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="card text-center">
      <div className="text-2xl font-bold text-blue-700">{value}</div>
      <div className="text-xs text-gray-500 mt-1">{label}</div>
    </div>
  );
}

export default function App() {
  const [priceFiles, setPriceFiles] = useState<File[]>([]);
  const [metadataFile, setMetadataFile] = useState<File | null>(null);
  const [priceMatrix, setPriceMatrix] = useState<PriceMatrix | null>(null);
  const [metadata, setMetadata] = useState<NodeRecord[]>([]);
  const [config, setConfig] = useState<ClusteringConfig>(DEFAULT_CONFIG);
  const [parseError, setParseError] = useState<string | null>(null);
  const [outputTab, setOutputTab] = useState<OutputTab>('first-pass');

  const { state: clusterState, run } = useClustering();

  // Parse price files when they change
  useEffect(() => {
    if (priceFiles.length === 0) {
      setPriceMatrix(null);
      return;
    }
    setParseError(null);
    parsePriceCSVs(priceFiles)
      .then(pm => setPriceMatrix(pm))
      .catch(err => {
        setParseError(err instanceof Error ? err.message : String(err));
        setPriceMatrix(null);
      });
  }, [priceFiles]);

  // Parse metadata file when it changes
  useEffect(() => {
    if (!metadataFile) {
      setMetadata([]);
      return;
    }
    parseMetadataCSV(metadataFile)
      .then(nodes => setMetadata(nodes))
      .catch(err => {
        setParseError(err instanceof Error ? err.message : String(err));
        setMetadata([]);
      });
  }, [metadataFile]);

  function handleRun() {
    if (!priceMatrix || metadata.length === 0) return;
    run(priceMatrix, metadata, config);
  }

  function handleDownload() {
    if (!clusterState.result) return;
    const { firstPassLabels, subclusterLabels } = clusterState.result;

    const metaMap = new Map(metadata.map(m => [m.nodeId, m]));
    const allNodes = Object.keys(firstPassLabels);

    const lines = ['node_id,latitude,longitude,first_pass_cluster,subcluster'];
    for (const nodeId of allNodes.sort()) {
      const meta = metaMap.get(nodeId);
      const lat = meta?.latitude ?? '';
      const lon = meta?.longitude ?? '';
      const fp = firstPassLabels[nodeId] ?? '';
      const sub = subclusterLabels[nodeId] ?? '';
      lines.push(`${nodeId},${lat},${lon},${fp},${sub}`);
    }

    const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'cluster_assignments.csv';
    a.click();
    URL.revokeObjectURL(url);
  }

  const dataStatus = priceMatrix
    ? `${priceMatrix.timestamps.length} timestamps × ${priceMatrix.nodeIds.length} nodes loaded`
    : undefined;

  const canRun = priceMatrix != null && metadata.length > 0 && !clusterState.isRunning;

  // Build label maps filtered to nodes that have metadata
  const metadataNodeIds = new Set(metadata.map(m => m.nodeId));

  const firstPassLabelsFiltered = clusterState.result
    ? Object.fromEntries(
        Object.entries(clusterState.result.firstPassLabels).filter(([id]) => metadataNodeIds.has(id))
      )
    : null;

  const subclusterLabelsFiltered = clusterState.result
    ? Object.fromEntries(
        Object.entries(clusterState.result.subclusterLabels).filter(([id]) => metadataNodeIds.has(id))
      )
    : null;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-blue-900 text-white px-6 py-4 shadow-md">
        <h1 className="text-xl font-bold tracking-tight">ERCOT Nodal Price Clustering</h1>
        <p className="text-blue-300 text-sm mt-0.5">Hierarchical Clustering — Geographic Coherence Analysis</p>
      </header>

      <div className="flex gap-6 p-6 max-w-screen-2xl mx-auto">
        {/* Left sidebar */}
        <aside className="w-80 shrink-0 space-y-4">
          {/* Data card */}
          <div className="card space-y-1">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Data</h2>
            <FileUpload
              label="Price CSV(s) — wide format (timestamp + node columns)"
              accept=".csv"
              multiple
              onFiles={setPriceFiles}
              status={
                parseError
                  ? `Error: ${parseError}`
                  : dataStatus
              }
            />
            <FileUpload
              label="Node Metadata CSV — node_id, latitude, longitude"
              accept=".csv"
              onFiles={files => setMetadataFile(files[0] ?? null)}
              status={metadata.length > 0 ? `${metadata.length} nodes loaded` : undefined}
            />
          </div>

          {/* Config card */}
          <div className="card">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Configuration</h2>
            <ConfigPanel config={config} onChange={setConfig} />
          </div>

          {/* Run button */}
          <button
            className="btn-primary w-full"
            disabled={!canRun}
            onClick={handleRun}
          >
            {clusterState.isRunning ? 'Running...' : 'Run Clustering'}
          </button>

          {/* Progress */}
          {clusterState.isRunning && clusterState.progress && (
            <ProgressBar
              message={clusterState.progress.message}
              pct={clusterState.progress.pct}
            />
          )}

          {/* Error */}
          {clusterState.error && (
            <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-xs text-red-700">
              <strong>Error:</strong> {clusterState.error}
            </div>
          )}
        </aside>

        {/* Main area */}
        <main className="flex-1 min-w-0">
          {!clusterState.result ? (
            <div className="flex flex-col items-center justify-center h-80 text-gray-400">
              <svg
                width="48"
                height="48"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                className="mb-4"
              >
                <circle cx="11" cy="11" r="8" />
                <path d="m21 21-4.35-4.35" />
              </svg>
              <p className="text-sm">Upload data and run analysis to see results</p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Metrics */}
              <div className="grid grid-cols-3 gap-4">
                <MetricCard label="Nodes Clustered" value={clusterState.result.nodeCount} />
                <MetricCard label="First-Pass Clusters" value={clusterState.result.clusterCount} />
                <MetricCard label="Subclusters" value={clusterState.result.subclusterCount} />
              </div>

              {/* Tab buttons */}
              <div className="flex gap-2">
                <button
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    outputTab === 'first-pass'
                      ? 'bg-blue-700 text-white'
                      : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                  }`}
                  onClick={() => setOutputTab('first-pass')}
                >
                  First-Pass Clusters
                </button>
                <button
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    outputTab === 'subclusters'
                      ? 'bg-blue-700 text-white'
                      : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                  }`}
                  onClick={() => setOutputTab('subclusters')}
                >
                  Subclusters
                </button>
                <button
                  className="ml-auto btn-secondary"
                  onClick={handleDownload}
                >
                  Download CSV
                </button>
              </div>

              {/* Tab content */}
              {outputTab === 'first-pass' && firstPassLabelsFiltered && (
                <div className="flex gap-4">
                  <div className="flex-1 card min-w-0">
                    <ClusterMap
                      metadata={metadata}
                      labels={firstPassLabelsFiltered}
                      title="First-Pass Clusters"
                      height={500}
                    />
                  </div>
                  <div className="w-64 card">
                    <ClusterStats
                      labels={firstPassLabelsFiltered}
                      title="Cluster Summary"
                    />
                  </div>
                </div>
              )}

              {outputTab === 'subclusters' && subclusterLabelsFiltered && (
                <div className="flex gap-4">
                  <div className="flex-1 card min-w-0">
                    <ClusterMap
                      metadata={metadata}
                      labels={subclusterLabelsFiltered}
                      title={`Subclusters of Cluster ${clusterState.result.largestClusterId} (largest)`}
                      height={500}
                    />
                  </div>
                  <div className="w-64 card">
                    <ClusterStats
                      labels={subclusterLabelsFiltered}
                      title="Subcluster Summary"
                    />
                  </div>
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
