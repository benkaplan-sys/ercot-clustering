import type { PriceMatrix } from './types';

/**
 * Pearson correlation between two Float64Array time series.
 * Ignores NaN pairs (pairwise deletion). Returns 0 if insufficient data.
 */
export function pearsonCorrelation(x: Float64Array, y: Float64Array): number {
  const n = Math.min(x.length, y.length);
  const validX: number[] = [];
  const validY: number[] = [];

  for (let i = 0; i < n; i++) {
    if (!isNaN(x[i]) && !isNaN(y[i])) {
      validX.push(x[i]);
      validY.push(y[i]);
    }
  }

  if (validX.length < 10) return 0;

  const m = validX.length;
  let sumX = 0, sumY = 0;
  for (let i = 0; i < m; i++) {
    sumX += validX[i];
    sumY += validY[i];
  }
  const meanX = sumX / m;
  const meanY = sumY / m;

  let num = 0, dX = 0, dY = 0;
  for (let i = 0; i < m; i++) {
    const dx = validX[i] - meanX;
    const dy = validY[i] - meanY;
    num += dx * dy;
    dX += dx * dx;
    dY += dy * dy;
  }

  const denom = Math.sqrt(dX * dY);
  if (denom === 0) return 0;
  return num / denom;
}

/**
 * Build n×n distance matrix: D[i][j] = 1 - clip(corr(i,j), -1, 1).
 * Diagonal is 0. Symmetric.
 */
export function buildDistanceMatrix(values: Float64Array[]): Float64Array[] {
  const n = values.length;
  const dist: Float64Array[] = Array.from({ length: n }, () => new Float64Array(n));

  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      const corr = pearsonCorrelation(values[i], values[j]);
      const clipped = Math.max(-1, Math.min(1, corr));
      const d = 1 - clipped;
      dist[i][j] = d;
      dist[j][i] = d;
    }
    dist[i][i] = 0;
  }

  return dist;
}

/**
 * Convert price matrix to daily averages to reduce computation time.
 * timestamps format: ISO date strings (15-min intervals).
 * Returns a new PriceMatrix with one value per calendar day.
 */
export function downsampleToDaily(matrix: PriceMatrix): PriceMatrix {
  const { nodeIds, timestamps, values } = matrix;

  // Group timestamp indices by date (first 10 chars of ISO string)
  const dateToIndices = new Map<string, number[]>();
  for (let t = 0; t < timestamps.length; t++) {
    const date = timestamps[t].slice(0, 10);
    const existing = dateToIndices.get(date);
    if (existing) {
      existing.push(t);
    } else {
      dateToIndices.set(date, [t]);
    }
  }

  const sortedDates = Array.from(dateToIndices.keys()).sort();
  const numDays = sortedDates.length;

  const newValues: Float64Array[] = values.map(nodeVals => {
    const daily = new Float64Array(numDays);
    for (let d = 0; d < numDays; d++) {
      const indices = dateToIndices.get(sortedDates[d])!;
      let sum = 0;
      let count = 0;
      for (const idx of indices) {
        const v = nodeVals[idx];
        if (!isNaN(v)) {
          sum += v;
          count++;
        }
      }
      daily[d] = count === 0 ? NaN : sum / count;
    }
    return daily;
  });

  return { nodeIds, timestamps: sortedDates, values: newValues };
}

/**
 * Drop nodes where fraction of NaN values exceeds threshold.
 */
export function dropSparseNodes(matrix: PriceMatrix, threshold: number): PriceMatrix {
  const { nodeIds, timestamps, values } = matrix;
  const n = timestamps.length;

  const keepIndices: number[] = [];
  for (let i = 0; i < nodeIds.length; i++) {
    let nanCount = 0;
    for (let t = 0; t < n; t++) {
      if (isNaN(values[i][t])) nanCount++;
    }
    if (nanCount / n <= threshold) {
      keepIndices.push(i);
    }
  }

  return {
    nodeIds: keepIndices.map(i => nodeIds[i]),
    timestamps,
    values: keepIndices.map(i => values[i]),
  };
}
