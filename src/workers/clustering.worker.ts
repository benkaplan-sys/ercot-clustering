import type { WorkerRequest, WorkerResponse } from '@/core/types';
import { downsampleToDaily, dropSparseNodes } from '@/core/correlation';
import { runHierarchical, findLargestCluster, subcluster } from '@/core/clustering';

function post(msg: WorkerResponse): void {
  self.postMessage(msg);
}

self.onmessage = (event: MessageEvent<WorkerRequest>) => {
  const req = event.data;

  if (req.type !== 'RUN') return;

  try {
    let { priceMatrix } = req;
    const { config } = req;

    // Step 1: Downsample
    if (config.resolution === 'daily') {
      post({ type: 'PROGRESS', message: 'Downsampling to daily averages...', pct: 0 });
      priceMatrix = downsampleToDaily(priceMatrix);
    }

    // Step 2: Drop sparse nodes
    post({ type: 'PROGRESS', message: 'Dropping sparse nodes...', pct: 5 });
    priceMatrix = dropSparseNodes(priceMatrix, config.missingDataThreshold);

    const { nodeIds, values } = priceMatrix;
    const n = nodeIds.length;

    if (n === 0) {
      post({ type: 'ERROR', message: 'No nodes remaining after filtering sparse nodes.' });
      return;
    }

    // Step 3: Compute distance matrix with progress updates
    post({
      type: 'PROGRESS',
      message: 'Computing correlation matrix... (this may take a moment)',
      pct: 10,
    });

    const dist: Float64Array[] = Array.from({ length: n }, () => new Float64Array(n));
    const reportEvery = Math.max(1, Math.floor(n / 10));

    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        let sumX = 0, sumY = 0, sumXX = 0, sumYY = 0, sumXY = 0, count = 0;
        const xi = values[i];
        const xj = values[j];
        const len = xi.length;
        for (let t = 0; t < len; t++) {
          const a = xi[t];
          const b = xj[t];
          if (!isNaN(a) && !isNaN(b)) {
            sumX += a;
            sumY += b;
            sumXX += a * a;
            sumYY += b * b;
            sumXY += a * b;
            count++;
          }
        }
        let d = 1;
        if (count >= 10) {
          const num = sumXY - (sumX * sumY) / count;
          const dX = sumXX - (sumX * sumX) / count;
          const dY = sumYY - (sumY * sumY) / count;
          const denom = Math.sqrt(dX * dY);
          if (denom > 0) {
            const corr = Math.max(-1, Math.min(1, num / denom));
            d = 1 - corr;
          }
        }
        dist[i][j] = d;
        dist[j][i] = d;
      }

      if ((i + 1) % reportEvery === 0) {
        const pct = 10 + Math.round(((i + 1) / n) * 60);
        post({
          type: 'PROGRESS',
          message: `Computing correlation matrix... (${i + 1}/${n} nodes)`,
          pct,
        });
      }
    }

    // Step 4: Hierarchical clustering
    post({ type: 'PROGRESS', message: 'Running hierarchical clustering...', pct: 70 });
    const firstPassLabelsArr = runHierarchical(dist, config);

    const firstPassLabels: Record<string, number> = {};
    for (let i = 0; i < nodeIds.length; i++) {
      firstPassLabels[nodeIds[i]] = firstPassLabelsArr[i];
    }

    const largestClusterId = findLargestCluster(firstPassLabelsArr);
    const largestClusterIndices: number[] = [];
    for (let i = 0; i < firstPassLabelsArr.length; i++) {
      if (firstPassLabelsArr[i] === largestClusterId) {
        largestClusterIndices.push(i);
      }
    }

    // Step 5: Subclustering
    post({ type: 'PROGRESS', message: 'Subclustering largest cluster...', pct: 85 });
    const subLabelsArr = subcluster(
      dist,
      largestClusterIndices,
      config.subcluterK,
      config.linkageMethod
    );

    const subclusterLabels: Record<string, number> = {};
    for (let si = 0; si < largestClusterIndices.length; si++) {
      subclusterLabels[nodeIds[largestClusterIndices[si]]] = subLabelsArr[si];
    }

    const clusterCount = new Set(firstPassLabelsArr).size;
    const subclusterCount = new Set(subLabelsArr).size;

    post({ type: 'PROGRESS', message: 'Done.', pct: 100 });

    post({
      type: 'RESULT',
      result: {
        firstPassLabels,
        subclusterLabels,
        largestClusterId,
        nodeCount: n,
        clusterCount,
        subclusterCount,
      },
    });
  } catch (err) {
    post({
      type: 'ERROR',
      message: err instanceof Error ? err.message : String(err),
    });
  }
};
