import type { DashboardArtist, Grade } from "../../types";

interface StatsRowProps {
  artists: DashboardArtist[];
  total: number;
}

function gradeCount(artists: DashboardArtist[], grade: Grade): number {
  return artists.filter((a) => a.grade === grade).length;
}

export function StatsRow({ artists, total }: StatsRowProps) {
  const avgComposite =
    artists.length > 0
      ? artists.reduce((s, a) => s + a.composite, 0) / artists.length
      : 0;

  const topArtist = artists.length > 0 ? artists[0] : null;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <StatCard label="Universe Size" value={String(total)} accent="red" />
      <StatCard
        label="Avg Composite"
        value={avgComposite.toFixed(1)}
        sub={`${gradeCount(artists, "A")}A  ${gradeCount(artists, "B")}B  ${gradeCount(artists, "C")}C  ${gradeCount(artists, "D")}D`}
        accent="blue"
      />
      <StatCard
        label="Top Artist"
        value={topArtist?.name ?? "--"}
        sub={topArtist ? `${topArtist.composite.toFixed(1)} (${topArtist.grade})` : ""}
        accent="green"
      />
      <StatCard
        label="Segments"
        value={String(new Set(artists.map((a) => a.segment_tag)).size)}
        sub="active tags"
        accent="amber"
      />
    </div>
  );
}

const accentColors: Record<string, string> = {
  red: "border-l-red-500",
  blue: "border-l-blue-500",
  green: "border-l-green-500",
  amber: "border-l-amber-500",
};

function StatCard({
  label,
  value,
  sub,
  accent = "red",
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: string;
}) {
  return (
    <div className={`card px-4 py-3 border-l-[3px] ${accentColors[accent]}`}>
      <div className="text-[10px] text-steel uppercase tracking-widest font-semibold">
        {label}
      </div>
      <div className="text-xl font-mono font-bold text-white mt-1 truncate">
        {value}
      </div>
      {sub && (
        <div className="text-xs text-steel mt-0.5 font-mono">{sub}</div>
      )}
    </div>
  );
}
