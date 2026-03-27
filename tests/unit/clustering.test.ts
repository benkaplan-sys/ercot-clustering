import { describe, it, expect } from 'vitest';
import { runHierarchical, findLargestCluster, subcluster } from '@/core/clustering';
import { buildDistanceMatrix } from '@/core/correlation';
import type { ClusteringConfig } from '@/core/types';

/** Build a synthetic dataset: 2 groups of nodes with high internal correlation */
function makeSyntheticDistMatrix(): Float64Array[] {
  const n = 6;
  const T = 100;

  // Group 1: nodes 0,1,2 follow similar sinusoidal pattern
  // Group 2: nodes 3,4,5 follow opposite pattern
  const values: Float64Array[] = Array.from({ length: n }, (_, i) => {
    const arr = new Float64Array(T);
    for (let t = 0; t < T; t++) {
      const base = i < 3 ? Math.sin(t * 0.3) : -Math.sin(t * 0.3);
      arr[t] = base + (Math.random() * 0.01 - 0.005); // tiny noise
    }
    return arr;
  });

  return buildDistanceMatrix(values);
}

const baseConfig: Pick<ClusteringConfig, 'linkageMethod' | 'criterion' | 'distanceThreshold' | 'maxClusters'> = {
  linkageMethod: 'ward',
  criterion: 'maxclust',
  distanceThreshold: 0.025,
  maxClusters: 2,
};

describe('runHierarchical', () => {
  it('with maxclust: returns exactly k labels for n > k nodes', () => {
    const dist = makeSyntheticDistMatrix();
    const labels = runHierarchical(dist, { ...baseConfig, criterion: 'maxclust', maxClusters: 2 });
    expect(labels).toHaveLength(6);
    const unique = new Set(labels);
    expect(unique.size).toBe(2);
  });

  it('with maxclust k=1 returns all label 1', () => {
    const dist = makeSyntheticDistMatrix();
    const labels = runHierarchical(dist, { ...baseConfig, criterion: 'maxclust', maxClusters: 1 });
    expect(labels.every(l => l === 1)).toBe(true);
  });

  it('with distance criterion returns >= 1 cluster', () => {
    const dist = makeSyntheticDistMatrix();
    const labels = runHierarchical(dist, { ...baseConfig, criterion: 'distance', distanceThreshold: 0.5 });
    expect(labels).toHaveLength(6);
    const unique = new Set(labels);
    expect(unique.size).toBeGreaterThanOrEqual(1);
  });

  it('all labels are positive integers', () => {
    const dist = makeSyntheticDistMatrix();
    const labels = runHierarchical(dist, baseConfig);
    for (const l of labels) {
      expect(l).toBeGreaterThan(0);
      expect(Number.isInteger(l)).toBe(true);
    }
  });

  it('handles single node', () => {
    const dist = [new Float64Array([0])];
    const labels = runHierarchical(dist, baseConfig);
    expect(labels).toEqual([1]);
  });
});

describe('findLargestCluster', () => {
  it('returns the label with the most members', () => {
    const labels = [1, 1, 1, 2, 2, 3];
    expect(findLargestCluster(labels)).toBe(1);
  });

  it('returns correct label when cluster 2 is largest', () => {
    const labels = [1, 2, 2, 2, 3];
    expect(findLargestCluster(labels)).toBe(2);
  });

  it('handles tie by returning first encountered', () => {
    const labels = [1, 2];
    // Both have count 1; either is acceptable
    const result = findLargestCluster(labels);
    expect([1, 2]).toContain(result);
  });
});

describe('subcluster', () => {
  it('returns correct number of labels for subset', () => {
    const dist = makeSyntheticDistMatrix();
    // Use all 6 nodes as the "subset"
    const nodeIndices = [0, 1, 2, 3, 4, 5];
    const sublabels = subcluster(dist, nodeIndices, 3, 'ward');
    expect(sublabels).toHaveLength(6);
    const unique = new Set(sublabels);
    expect(unique.size).toBe(3);
  });

  it('handles subset of 1 node', () => {
    const dist = makeSyntheticDistMatrix();
    const sublabels = subcluster(dist, [2], 3, 'ward');
    expect(sublabels).toEqual([1]);
  });

  it('clamps k to subset size', () => {
    const dist = makeSyntheticDistMatrix();
    // k=10 but only 3 nodes in subset → should return 3 or fewer clusters
    const sublabels = subcluster(dist, [0, 1, 2], 10, 'ward');
    expect(sublabels).toHaveLength(3);
    const unique = new Set(sublabels);
    expect(unique.size).toBeLessThanOrEqual(3);
  });

  it('all labels are positive integers', () => {
    const dist = makeSyntheticDistMatrix();
    const sublabels = subcluster(dist, [0, 1, 2, 3], 2, 'ward');
    for (const l of sublabels) {
      expect(l).toBeGreaterThan(0);
      expect(Number.isInteger(l)).toBe(true);
    }
  });
});
