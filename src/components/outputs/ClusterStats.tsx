

interface ClusterStatsProps {
  labels: Record<string, number>;
  title?: string;
}

export function ClusterStats({ labels, title }: ClusterStatsProps) {
  const counts = new Map<number, number>();
  for (const label of Object.values(labels)) {
    counts.set(label, (counts.get(label) ?? 0) + 1);
  }

  const total = Object.keys(labels).length;

  const rows = Array.from(counts.entries())
    .sort((a, b) => b[1] - a[1]);

  const maxCount = rows[0]?.[1] ?? 0;

  return (
    <div>
      {title && <h3 className="text-sm font-semibold text-gray-700 mb-2">{title}</h3>}
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="text-left py-1 pr-4 text-xs font-medium text-gray-500">Cluster</th>
            <th className="text-right py-1 pr-4 text-xs font-medium text-gray-500">Nodes</th>
            <th className="text-right py-1 text-xs font-medium text-gray-500">% of Total</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([label, count]) => (
            <tr
              key={label}
              className={`border-b border-gray-100 ${
                count === maxCount ? 'bg-blue-50 font-medium' : ''
              }`}
            >
              <td className="py-1 pr-4 text-gray-700">{label}</td>
              <td className="py-1 pr-4 text-right text-gray-700">{count}</td>
              <td className="py-1 text-right text-gray-600">
                {total > 0 ? ((count / total) * 100).toFixed(1) : '0.0'}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
