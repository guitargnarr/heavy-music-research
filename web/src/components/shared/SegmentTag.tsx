import type { SegmentTag as SegmentTagType } from "../../types";

const tagColors: Record<string, string> = {
  "Breakout Candidate": "bg-purple-600/20 text-purple-300 border-purple-600/30",
  "Established Ascender": "bg-green-600/20 text-green-300 border-green-600/30",
  "Established Stable": "bg-blue-600/20 text-blue-300 border-blue-600/30",
  "Label-Ready": "bg-cyan-600/20 text-cyan-300 border-cyan-600/30",
  "Producer Bump": "bg-orange-600/20 text-orange-300 border-orange-600/30",
  "At Risk": "bg-red-600/20 text-red-300 border-red-600/30",
  "Sleeping Giant": "bg-gray-600/20 text-gray-300 border-gray-600/30",
  "Algorithmic Lift": "bg-yellow-600/20 text-yellow-300 border-yellow-600/30",
};

export function SegmentTag({ tag }: { tag: SegmentTagType }) {
  const color = tagColors[tag] ?? "bg-gray-600/20 text-gray-300 border-gray-600/30";
  return (
    <span
      className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-medium border ${color}`}
    >
      {tag}
    </span>
  );
}
