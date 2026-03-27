import { useState } from 'react';
import type { ClusteringConfig } from '@/core/types';

interface ConfigPanelProps {
  config: ClusteringConfig;
  onChange: (c: ClusteringConfig) => void;
}

const FULL_HISTORY_PRESET: Partial<ClusteringConfig> = {
  criterion: 'distance',
  distanceThreshold: 0.025,
  maxClusters: 8,
  subcluterK: 8,
  resolution: 'daily',
};

const RECENT_PRESET: Partial<ClusteringConfig> = {
  criterion: 'maxclust',
  maxClusters: 6,
  subcluterK: 6,
  resolution: 'daily',
};

function Tooltip({ text }: { text: string }) {
  const [show, setShow] = useState(false);
  return (
    <span className="relative inline-block ml-1">
      <button
        type="button"
        className="text-gray-400 hover:text-gray-600 text-xs"
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
      >
        ⓘ
      </button>
      {show && (
        <div className="absolute z-10 left-full ml-1 top-0 w-48 text-xs bg-gray-800 text-white rounded p-2 shadow-lg">
          {text}
        </div>
      )}
    </span>
  );
}

export function ConfigPanel({ config, onChange }: ConfigPanelProps) {
  const [advancedOpen, setAdvancedOpen] = useState(false);

  function update(partial: Partial<ClusteringConfig>) {
    onChange({ ...config, ...partial });
  }

  return (
    <div className="space-y-4 text-sm">
      {/* Preset buttons */}
      <div>
        <span className="label">Preset</span>
        <div className="flex gap-2">
          <button
            className="btn-secondary flex-1"
            onClick={() => update(FULL_HISTORY_PRESET)}
          >
            Full History
          </button>
          <button
            className="btn-secondary flex-1"
            onClick={() => update(RECENT_PRESET)}
          >
            Recent (2024+)
          </button>
        </div>
      </div>

      {/* Criterion */}
      <div>
        <span className="label flex items-center">
          Criterion
          <Tooltip text="Fixed k cuts the tree into exactly k clusters. Distance threshold forms clusters based on similarity." />
        </span>
        <div className="flex gap-1">
          <button
            className={`flex-1 px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
              config.criterion === 'maxclust'
                ? 'bg-blue-700 text-white border-blue-700'
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
            }`}
            onClick={() => update({ criterion: 'maxclust' })}
          >
            Fixed k
          </button>
          <button
            className={`flex-1 px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
              config.criterion === 'distance'
                ? 'bg-blue-700 text-white border-blue-700'
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
            }`}
            onClick={() => update({ criterion: 'distance' })}
          >
            Distance Threshold
          </button>
        </div>
      </div>

      {/* Criterion-specific controls */}
      {config.criterion === 'maxclust' && (
        <div>
          <label className="label">
            Max Clusters: <strong>{config.maxClusters}</strong>
          </label>
          <input
            type="range"
            min={2}
            max={20}
            value={config.maxClusters}
            onChange={e => update({ maxClusters: Number(e.target.value) })}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-gray-400">
            <span>2</span><span>20</span>
          </div>
        </div>
      )}

      {config.criterion === 'distance' && (
        <div>
          <label className="label">Distance Threshold</label>
          <input
            type="number"
            min={0.001}
            max={0.2}
            step={0.001}
            value={config.distanceThreshold}
            onChange={e => update({ distanceThreshold: Number(e.target.value) })}
            className="input-field"
          />
        </div>
      )}

      {/* Subclusters */}
      <div>
        <label className="label flex items-center">
          Subclusters: <strong className="ml-1">{config.subcluterK}</strong>
          <Tooltip text="After the first-pass clustering, the largest cluster is re-clustered into this many subclusters to reveal finer regional structure." />
        </label>
        <input
          type="range"
          min={2}
          max={20}
          value={config.subcluterK}
          onChange={e => update({ subcluterK: Number(e.target.value) })}
          className="w-full"
        />
        <div className="flex justify-between text-xs text-gray-400">
          <span>2</span><span>20</span>
        </div>
      </div>

      {/* Advanced section */}
      <div>
        <button
          type="button"
          className="flex items-center gap-1 text-xs text-gray-600 hover:text-gray-800 font-medium"
          onClick={() => setAdvancedOpen(o => !o)}
        >
          <span>{advancedOpen ? '▼' : '▶'}</span>
          Advanced
        </button>

        {advancedOpen && (
          <div className="mt-3 space-y-3 pl-2 border-l-2 border-gray-200">
            {/* Resolution */}
            <div>
              <span className="label">Resolution</span>
              <div className="space-y-1">
                {(['daily', 'raw'] as const).map(r => (
                  <label key={r} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="resolution"
                      value={r}
                      checked={config.resolution === r}
                      onChange={() => update({ resolution: r })}
                    />
                    <span className="text-sm text-gray-700">
                      {r === 'daily' ? 'Daily (faster)' : 'Full 15-min'}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            {/* Linkage method */}
            <div>
              <label className="label">Linkage Method</label>
              <select
                value={config.linkageMethod}
                onChange={e => update({ linkageMethod: e.target.value as ClusteringConfig['linkageMethod'] })}
                className="input-field"
              >
                <option value="ward">Ward</option>
                <option value="average">Average</option>
                <option value="complete">Complete</option>
                <option value="single">Single</option>
              </select>
            </div>

            {/* Missing data threshold */}
            <div>
              <label className="label">Missing Data Threshold</label>
              <input
                type="number"
                min={0.01}
                max={0.20}
                step={0.01}
                value={config.missingDataThreshold}
                onChange={e => update({ missingDataThreshold: Number(e.target.value) })}
                className="input-field"
              />
              <p className="text-xs text-gray-400 mt-1">
                Nodes with more than this fraction of missing values are dropped.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
