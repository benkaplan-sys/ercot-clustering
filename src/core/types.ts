export interface NodeRecord {
  nodeId: string;
  latitude: number;
  longitude: number;
}

export interface PriceMatrix {
  nodeIds: string[];
  /** timestamps[i] is the ISO string for row i */
  timestamps: string[];
  /** values[nodeIndex][timestampIndex] */
  values: Float64Array[];
}

export interface ClusteringConfig {
  linkageMethod: 'ward' | 'average' | 'complete' | 'single';
  criterion: 'distance' | 'maxclust';
  distanceThreshold: number;   // used when criterion='distance'
  maxClusters: number;         // used when criterion='maxclust'
  subcluterK: number;
  missingDataThreshold: number;
  /** 'raw' = use all timestamps; 'daily' = average to daily first */
  resolution: 'raw' | 'daily';
}

export const DEFAULT_CONFIG: ClusteringConfig = {
  linkageMethod: 'ward',
  criterion: 'maxclust',
  distanceThreshold: 0.025,
  maxClusters: 8,
  subcluterK: 8,
  missingDataThreshold: 0.05,
  resolution: 'daily',
};

export interface ClusteringResult {
  /** First-pass label per node (1-indexed) */
  firstPassLabels: Record<string, number>;
  /** Subcluster label per node (only nodes in largest cluster) */
  subclusterLabels: Record<string, number>;
  largestClusterId: number;
  /** Distance matrix dimensions (for reference) */
  nodeCount: number;
  clusterCount: number;
  subclusterCount: number;
}

export type WorkerRequest =
  | { type: 'RUN'; priceMatrix: PriceMatrix; metadata: NodeRecord[]; config: ClusteringConfig }

export type WorkerResponse =
  | { type: 'PROGRESS'; message: string; pct: number }
  | { type: 'RESULT'; result: ClusteringResult }
  | { type: 'ERROR'; message: string }
