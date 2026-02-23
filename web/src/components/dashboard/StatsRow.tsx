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
      <StatCard label="Universe Size" value={String(total)} />
      <StatCard
        label="Avg Composite"
        value={avgComposite.toFixed(1)}
        sub={`${gradeCount(artists, "A")}A ${gradeCount(artists, "B")}B ${gradeCount(artists, "C")}C ${gradeCount(artists, "D")}D`}
      />
      <StatCard
        label="Top Artist"
        value={topArtist?.name ?? "--"}
        sub={topArtist ? `${topArtist.composite.toFixed(1)} (${topArtist.grade})` : ""}
      />
      <StatCard
        label="Segments"
        value={String(new Set(artists.map((a) => a.segment_tag)).size)}
        sub="active tags"
      />
    </div>
  );
}

function StatCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="bg-surface-raised border border-surface-border rounded-xl px-4 py-3">
      <div className="text-xs text-gray-500 uppercase tracking-wider">
        {label}
      </div>
      <div className="text-lg font-bold text-gray-100 mt-0.5 truncate">
        {value}
      </div>
      {sub && (
        <div className="text-xs text-gray-500 mt-0.5">{sub}</div>
      )}
    </div>
  );
}
