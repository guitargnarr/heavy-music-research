import type { Grade } from "../../types";

const gradeColor: Record<Grade, string> = {
  A: "#22c55e",
  B: "#3b82f6",
  C: "#f59e0b",
  D: "#ef4444",
};

interface CompositeBarProps {
  value: number;
  grade: Grade;
}

export function CompositeBar({ value, grade }: CompositeBarProps) {
  const pct = Math.min(value, 100);
  return (
    <div className="flex items-center gap-2 min-w-[120px]">
      <div className="flex-1 h-2 bg-surface-border rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{
            width: `${pct}%`,
            backgroundColor: gradeColor[grade],
          }}
        />
      </div>
      <span className="text-xs font-mono text-gray-300 w-8 text-right">
        {value.toFixed(0)}
      </span>
    </div>
  );
}
