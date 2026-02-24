import type { SegmentTag as SegmentTagType } from "../../types";

const tagColors: Record<string, string> = {
  "Breakout Candidate": "text-purple-400 border-purple-500/30",
  "Established Ascender": "text-green-400 border-green-500/30",
  "Established Stable": "text-blue-400 border-blue-500/30",
  "Label-Ready": "text-cyan-400 border-cyan-500/30",
  "Producer Bump": "text-orange-400 border-orange-500/30",
  "At Risk": "text-red-400 border-red-500/30",
  "Sleeping Giant": "text-gray-400 border-gray-500/30",
  "Algorithmic Lift": "text-yellow-400 border-yellow-500/30",
};

export function SegmentTag({ tag }: { tag: SegmentTagType }) {
  const color = tagColors[tag] ?? "text-gray-400 border-gray-500/30";
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider border ${color}`}
    >
      {tag}
    </span>
  );
}
