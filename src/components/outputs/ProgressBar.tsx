

interface ProgressBarProps {
  message: string;
  pct: number;
}

export function ProgressBar({ message, pct }: ProgressBarProps) {
  return (
    <div className="mt-3">
      <div className="flex justify-between text-xs text-gray-600 mb-1">
        <span>{message}</span>
        <span>{pct}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className="bg-blue-600 h-2 rounded-full transition-all duration-300"
          style={{ width: `${Math.min(100, pct)}%` }}
        />
      </div>
    </div>
  );
}
