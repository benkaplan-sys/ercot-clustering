import { describe, it, expect } from 'vitest';
import { pearsonCorrelation, buildDistanceMatrix, downsampleToDaily } from '@/core/correlation';
import type { PriceMatrix } from '@/core/types';

describe('pearsonCorrelation', () => {
  it('returns 1.0 for perfectly correlated series', () => {
    const n = 50;
    const x = new Float64Array(n).map((_, i) => i);
    const y = new Float64Array(n).map((_, i) => 2 * i + 3);
    expect(pearsonCorrelation(x, y)).toBeCloseTo(1.0, 5);
  });

  it('returns -1.0 for perfectly anti-correlated series', () => {
    const n = 50;
    const x = new Float64Array(n).map((_, i) => i);
    const y = new Float64Array(n).map((_, i) => -i + 100);
    expect(pearsonCorrelation(x, y)).toBeCloseTo(-1.0, 5);
  });

  it('returns near 0 for independent constant series', () => {
    const n = 50;
    const x = new Float64Array(n).fill(5);
    const y = new Float64Array(n).fill(10);
    // constant series → denom = 0 → returns 0
    expect(pearsonCorrelation(x, y)).toBe(0);
  });

  it('handles NaN pairs by pairwise deletion', () => {
    const n = 30;
    const x = new Float64Array(n).map((_, i) => i);
    const y = new Float64Array(n).map((_, i) => i);
    // Corrupt first 5 y values
    for (let i = 0; i < 5; i++) y[i] = NaN;
    // Still perfectly correlated on valid pairs
    expect(pearsonCorrelation(x, y)).toBeCloseTo(1.0, 4);
  });

  it('returns 0 when fewer than 10 valid pairs', () => {
    const x = new Float64Array(20).map((_, i) => i);
    const y = new Float64Array(20).map((_, i) => i);
    // Set all but 5 to NaN
    for (let i = 5; i < 20; i++) { x[i] = NaN; y[i] = NaN; }
    expect(pearsonCorrelation(x, y)).toBe(0);
  });
});

describe('buildDistanceMatrix', () => {
  function makeValues(n: number, m: number): Float64Array[] {
    return Array.from({ length: n }, (_, i) =>
      new Float64Array(m).map((_, t) => Math.sin(i * t * 0.1))
    );
  }

  it('diagonal is 0', () => {
    const vals = makeValues(4, 50);
    const dist = buildDistanceMatrix(vals);
    for (let i = 0; i < 4; i++) {
      expect(dist[i][i]).toBe(0);
    }
  });

  it('is symmetric', () => {
    const vals = makeValues(4, 50);
    const dist = buildDistanceMatrix(vals);
    for (let i = 0; i < 4; i++) {
      for (let j = 0; j < 4; j++) {
        expect(dist[i][j]).toBeCloseTo(dist[j][i], 10);
      }
    }
  });

  it('values are in [0, 2]', () => {
    const vals = makeValues(5, 50);
    const dist = buildDistanceMatrix(vals);
    for (let i = 0; i < 5; i++) {
      for (let j = 0; j < 5; j++) {
        expect(dist[i][j]).toBeGreaterThanOrEqual(0);
        expect(dist[i][j]).toBeLessThanOrEqual(2);
      }
    }
  });
});

describe('downsampleToDaily', () => {
  function makeMatrix(): PriceMatrix {
    // 4 timestamps per day, 3 days = 12 rows, 3 nodes
    const timestamps: string[] = [];
    for (let d = 1; d <= 3; d++) {
      for (let h = 0; h < 4; h++) {
        timestamps.push(`2024-01-0${d}T${String(h * 6).padStart(2, '0')}:00:00`);
      }
    }
    const nodeIds = ['A', 'B', 'C'];
    const values: Float64Array[] = [
      new Float64Array(12).fill(10),
      new Float64Array(12).fill(20),
      new Float64Array(12).fill(30),
    ];
    return { nodeIds, timestamps, values };
  }

  it('reduces to one value per calendar day', () => {
    const mat = makeMatrix();
    const daily = downsampleToDaily(mat);
    expect(daily.timestamps).toHaveLength(3);
    expect(daily.timestamps[0]).toBe('2024-01-01');
  });

  it('preserves node count', () => {
    const mat = makeMatrix();
    const daily = downsampleToDaily(mat);
    expect(daily.nodeIds).toHaveLength(3);
  });

  it('averages correctly for uniform values', () => {
    const mat = makeMatrix();
    const daily = downsampleToDaily(mat);
    // Each node has uniform values, so daily average = that value
    expect(daily.values[0][0]).toBeCloseTo(10, 5);
    expect(daily.values[1][0]).toBeCloseTo(20, 5);
    expect(daily.values[2][0]).toBeCloseTo(30, 5);
  });
});
