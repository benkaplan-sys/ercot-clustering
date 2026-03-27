import { agnes } from 'ml-hclust';
import type { ClusteringConfig, ClusteringResult } from './types';

/** Recursively collect all leaf indices from a cluster tree node. */
function collectLeaves(node: { isLeaf: boolean; index: number; children: typeof node[] }): number[] {
  if (node.isLeaf) return [node.index];
  return node.children.flatMap(collectLeaves);
}

/**
 * Run hierarchical clustering on a precomputed distance matrix.
 * Returns flat cluster labels (1-indexed) as number[].
 */
export function runHierarchical(
  distMatrix: Float64Array[],
  config: Pick<ClusteringConfig, 'linkageMethod' | 'criterion' | 'distanceThreshold' | 'maxClusters'>
): number[] {
  const n = distMatrix.length;
  if (n === 0) return [];
  if (n === 1) return [1];

  const indices = Array.from({ length: n }, (_, i) => i);

  const tree = agnes(indices, {
    method: config.linkageMethod,
    distanceFunction: (i: number, j: number) => distMatrix[i][j],
  });

  const labels = new Array<number>(n).fill(0);

  if (config.criterion === 'maxclust') {
    const k = Math.min(config.maxClusters, n);
    // group(k) returns the tree root itself with children representing k clusters
    const grouped = tree.group(k);
    const clusters: typeof grouped.children = grouped.children ?? [grouped];
    for (let ci = 0; ci < clusters.length; ci++) {
      const leaves = collectLeaves(clusters[ci]);
      for (const idx of leaves) {
        labels[idx] = ci + 1;
      }
    }
  } else {
    // cut(distance) returns array of cluster tree nodes
    const clusters = tree.cut(config.distanceThreshold);
    for (let ci = 0; ci < clusters.length; ci++) {
      const leaves = collectLeaves(clusters[ci]);
      for (const idx of leaves) {
        labels[idx] = ci + 1;
      }
    }
  }

  return labels;
}

/** Identify the label of the largest cluster (most members). */
export function findLargestCluster(labels: number[]): number {
  const counts = new Map<number, number>();
  for (const label of labels) {
    counts.set(label, (counts.get(label) ?? 0) + 1);
  }
  let maxCount = -1;
  let maxLabel = 1;
  for (const [label, count] of counts) {
    if (count > maxCount) {
      maxCount = count;
      maxLabel = label;
    }
  }
  return maxLabel;
}

/**
 * Re-cluster the subset of nodes in the largest cluster into k subclusters.
 * nodeIndices: indices of the subset in the original distMatrix.
 * Returns subcluster labels (1-indexed) for the subset only.
 */
export function subcluster(
  distMatrix: Float64Array[],
  nodeIndices: number[],
  k: number,
  linkageMethod: ClusteringConfig['linkageMethod']
): number[] {
  const m = nodeIndices.length;
  if (m === 0) return [];
  if (m === 1) return [1];

  const effectiveK = Math.min(k, m);

  // Build a local distance matrix for the subset
  const subDist: Float64Array[] = Array.from({ length: m }, (_, si) => {
    const row = new Float64Array(m);
    for (let sj = 0; sj < m; sj++) {
      row[sj] = distMatrix[nodeIndices[si]][nodeIndices[sj]];
    }
    return row;
  });

  const subIndices = Array.from({ length: m }, (_, i) => i);

  const tree = agnes(subIndices, {
    method: linkageMethod,
    distanceFunction: (i: number, j: number) => subDist[i][j],
  });

  const labels = new Array<number>(m).fill(0);
  const grouped = tree.group(effectiveK);
  const clusters: typeof grouped.children = grouped.children ?? [grouped];
  for (let ci = 0; ci < clusters.length; ci++) {
    const leaves = collectLeaves(clusters[ci]);
    for (const idx of leaves) {
      labels[idx] = ci + 1;
    }
  }

  return labels;
}

/**
 * Build the full ClusteringResult from distance matrix and node IDs.
 */
export function buildClusteringResult(
  distMatrix: Float64Array[],
  nodeIds: string[],
  config: ClusteringConfig
): ClusteringResult {
  const firstPassLabelsArr = runHierarchical(distMatrix, config);

  const firstPassLabels: Record<string, number> = {};
  for (let i = 0; i < nodeIds.length; i++) {
    firstPassLabels[nodeIds[i]] = firstPassLabelsArr[i];
  }

  const largestClusterId = findLargestCluster(firstPassLabelsArr);

  // Find indices of nodes in the largest cluster
  const largestClusterIndices: number[] = [];
  for (let i = 0; i < firstPassLabelsArr.length; i++) {
    if (firstPassLabelsArr[i] === largestClusterId) {
      largestClusterIndices.push(i);
    }
  }

  const subLabelsArr = subcluster(
    distMatrix,
    largestClusterIndices,
    config.subcluterK,
    config.linkageMethod
  );

  const subclusterLabels: Record<string, number> = {};
  for (let si = 0; si < largestClusterIndices.length; si++) {
    const origIdx = largestClusterIndices[si];
    subclusterLabels[nodeIds[origIdx]] = subLabelsArr[si];
  }

  const clusterCount = new Set(firstPassLabelsArr).size;
  const subclusterCount = new Set(subLabelsArr).size;

  return {
    firstPassLabels,
    subclusterLabels,
    largestClusterId,
    nodeCount: nodeIds.length,
    clusterCount,
    subclusterCount,
  };
}
