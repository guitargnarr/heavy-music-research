import type { Grade } from "../../types";

const gradeClass: Record<Grade, string> = {
  A: "grade-a",
  B: "grade-b",
  C: "grade-c",
  D: "grade-d",
};

export function GradeBadge({ grade }: { grade: Grade }) {
  return (
    <span
      className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-mono font-semibold ${gradeClass[grade]}`}
    >
      {grade}
    </span>
  );
}
