import Papa from 'papaparse';
import type { PriceMatrix, NodeRecord } from './types';

type ParsedRow = Record<string, string | number | null>;

function detectTimestampColumn(headers: string[]): string | null {
  // Look for a column named 'timestamp' (case-insensitive) or the first non-numeric-looking column
  const lower = headers.map(h => h.toLowerCase().trim());
  const tsIdx = lower.findIndex(h => h.includes('timestamp') || h.includes('date') || h.includes('time'));
  if (tsIdx >= 0) return headers[tsIdx];
  return headers[0]; // fallback to first column
}

function parseFile(file: File): Promise<ParsedRow[]> {
  return new Promise((resolve, reject) => {
    Papa.parse<ParsedRow>(file, {
      header: true,
      dynamicTyping: true,
      skipEmptyLines: true,
      complete: result => resolve(result.data),
      error: err => reject(new Error(err.message)),
    });
  });
}

/**
 * Parse one or more wide-format price CSVs.
 * First column = timestamp, remaining columns = node prices.
 * Multiple files are concatenated and deduplicated by timestamp, then sorted.
 * If multiple files, only timestamps present in ALL files are kept (inner join).
 */
export async function parsePriceCSVs(files: File[]): Promise<PriceMatrix> {
  if (files.length === 0) throw new Error('No files provided');

  const parsed = await Promise.all(files.map(parseFile));

  // Detect timestamp column from first file
  const firstHeaders = Object.keys(parsed[0][0] ?? {});
  const tsColumn = detectTimestampColumn(firstHeaders);
  if (!tsColumn) throw new Error('Could not detect timestamp column');

  // For each file, build a map: timestamp -> { nodeId -> value }
  const fileMaps: Map<string, Map<string, number>>[] = parsed.map(rows => {
    const m = new Map<string, Map<string, number>>();
    for (const row of rows) {
      const ts = row[tsColumn];
      if (ts == null || ts === '') continue;
      const tsStr = String(ts);
      const nodeVals = new Map<string, number>();
      for (const [key, val] of Object.entries(row)) {
        if (key === tsColumn) continue;
        nodeVals.set(key, val == null ? NaN : Number(val));
      }
      m.set(tsStr, nodeVals);
    }
    return m;
  });

  // Determine the inner join of timestamps across all files
  let commonTimestamps: Set<string> = new Set(fileMaps[0].keys());
  for (let i = 1; i < fileMaps.length; i++) {
    const fileTs = new Set(fileMaps[i].keys());
    commonTimestamps = new Set([...commonTimestamps].filter(ts => fileTs.has(ts)));
  }

  const sortedTimestamps = Array.from(commonTimestamps).sort();

  // Determine the union of node columns across all files
  const nodeIdSet = new Set<string>();
  for (const fm of fileMaps) {
    for (const nodeVals of fm.values()) {
      for (const k of nodeVals.keys()) nodeIdSet.add(k);
    }
  }
  const nodeIds = Array.from(nodeIdSet).sort();

  // Build merged map: timestamp -> nodeId -> value (last-file wins for duplicates)
  const merged = new Map<string, Map<string, number>>();
  for (const ts of sortedTimestamps) {
    const nodeVals = new Map<string, number>();
    for (const fm of fileMaps) {
      const fv = fm.get(ts);
      if (fv) {
        for (const [nodeId, val] of fv) {
          nodeVals.set(nodeId, val);
        }
      }
    }
    merged.set(ts, nodeVals);
  }

  // Build Float64Array per node
  const values: Float64Array[] = nodeIds.map(nodeId => {
    const arr = new Float64Array(sortedTimestamps.length);
    for (let t = 0; t < sortedTimestamps.length; t++) {
      const ts = sortedTimestamps[t];
      const nodeVals = merged.get(ts);
      const v = nodeVals?.get(nodeId);
      arr[t] = v == null ? NaN : v;
    }
    return arr;
  });

  return { nodeIds, timestamps: sortedTimestamps, values };
}

/**
 * Parse node metadata CSV with columns: node_id, latitude, longitude.
 * Column names are case-insensitive and whitespace-trimmed.
 */
export async function parseMetadataCSV(file: File): Promise<NodeRecord[]> {
  const rows = await parseFile(file);
  if (rows.length === 0) throw new Error('Metadata CSV is empty');

  const rawHeaders = Object.keys(rows[0]);
  const lower = rawHeaders.map(h => h.toLowerCase().trim());

  const nodeCol = rawHeaders[lower.findIndex(h => h.includes('node'))];
  const latCol = rawHeaders[lower.findIndex(h => h.includes('lat'))];
  const lonCol = rawHeaders[lower.findIndex(h => h.includes('lon'))];

  if (!nodeCol) throw new Error('Could not find node_id column in metadata CSV');
  if (!latCol) throw new Error('Could not find latitude column in metadata CSV');
  if (!lonCol) throw new Error('Could not find longitude column in metadata CSV');

  const records: NodeRecord[] = [];
  for (const row of rows) {
    const nodeId = row[nodeCol];
    const lat = row[latCol];
    const lon = row[lonCol];
    if (nodeId == null || lat == null || lon == null) continue;
    records.push({
      nodeId: String(nodeId).trim(),
      latitude: Number(lat),
      longitude: Number(lon),
    });
  }

  return records;
}
