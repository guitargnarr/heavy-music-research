interface ScoreBarProps {
  label: string;
  value: number;
  max?: number;
}

const barColor = (value: number): string => {
  if (value >= 80) return "bg-green-500";
  if (value >= 60) return "bg-blue-500";
  if (value >= 40) return "bg-amber-500";
  return "bg-red-500";
};

export function ScoreBar({ label, value, max = 100 }: ScoreBarProps) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-steel">{label}</span>
        <span className="font-mono font-medium text-gray-300">{value.toFixed(0)}</span>
      </div>
      <div className="h-1.5 bg-surface-border rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full animate-bar-fill origin-left ${barColor(value)}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
