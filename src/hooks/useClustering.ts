import { useState, useRef, useCallback } from 'react';
import type {
  PriceMatrix,
  NodeRecord,
  ClusteringConfig,
  ClusteringResult,
  WorkerResponse,
} from '@/core/types';

export interface ClusteringState {
  isRunning: boolean;
  progress: { message: string; pct: number } | null;
  result: ClusteringResult | null;
  error: string | null;
}

export function useClustering() {
  const [state, setState] = useState<ClusteringState>({
    isRunning: false,
    progress: null,
    result: null,
    error: null,
  });

  const workerRef = useRef<Worker | null>(null);

  const run = useCallback(
    (priceMatrix: PriceMatrix, metadata: NodeRecord[], config: ClusteringConfig) => {
      // Terminate any existing worker
      if (workerRef.current) {
        workerRef.current.terminate();
        workerRef.current = null;
      }

      setState({ isRunning: true, progress: null, result: null, error: null });

      const worker = new Worker(
        new URL('../workers/clustering.worker.ts', import.meta.url),
        { type: 'module' }
      );
      workerRef.current = worker;

      worker.onmessage = (event: MessageEvent<WorkerResponse>) => {
        const msg = event.data;
        if (msg.type === 'PROGRESS') {
          setState(prev => ({
            ...prev,
            progress: { message: msg.message, pct: msg.pct },
          }));
        } else if (msg.type === 'RESULT') {
          setState({
            isRunning: false,
            progress: null,
            result: msg.result,
            error: null,
          });
          worker.terminate();
          workerRef.current = null;
        } else if (msg.type === 'ERROR') {
          setState({
            isRunning: false,
            progress: null,
            result: null,
            error: msg.message,
          });
          worker.terminate();
          workerRef.current = null;
        }
      };

      worker.onerror = (err) => {
        setState({
          isRunning: false,
          progress: null,
          result: null,
          error: err.message,
        });
        worker.terminate();
        workerRef.current = null;
      };

      worker.postMessage({ type: 'RUN', priceMatrix, metadata, config });
    },
    []
  );

  return { state, run };
}
