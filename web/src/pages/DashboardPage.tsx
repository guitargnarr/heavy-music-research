import { useEffect, useState, useCallback, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  Search,
  ArrowUpDown,
  ChevronUp,
  ChevronDown,
  Filter,
} from "lucide-react";
import { getDashboard } from "../api/client";
import { GradeBadge } from "../components/shared/GradeBadge";
import { SegmentTag } from "../components/shared/SegmentTag";
import { CompositeBar } from "../components/shared/CompositeBar";
import { FilterChip } from "../components/shared/FilterChip";
import { StatsRow } from "../components/dashboard/StatsRow";
import type { DashboardArtist, Grade, SegmentTag as SegType } from "../types";

type SortField =
  | "composite"
  | "trajectory"
  | "industry_signal"
  | "engagement"
  | "release_positioning"
  | "name";
type SortDir = "asc" | "desc";

const grades: Grade[] = ["A", "B", "C", "D"];
const segments: SegType[] = [
  "Breakout Candidate",
  "Established Ascender",
  "Established Stable",
  "Label-Ready",
  "Producer Bump",
  "At Risk",
  "Sleeping Giant",
  "Algorithmic Lift",
];

export function DashboardPage() {
  const [allArtists, setAllArtists] = useState<DashboardArtist[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [gradeFilter, setGradeFilter] = useState<Grade | "">("");
  const [segmentFilter, setSegmentFilter] = useState<SegType | "">("");
  const [labelFilter, setLabelFilter] = useState("");
  const [sortBy, setSortBy] = useState<SortField>("composite");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [showFilters, setShowFilters] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getDashboard({
        sort_by: sortBy,
        sort_dir: sortDir,
        grade: gradeFilter || undefined,
        segment: segmentFilter || undefined,
        label: labelFilter || undefined,
        search: search || undefined,
        limit: 100,
      });
      setAllArtists(data.artists);
      setTotal(data.total);
    } catch (err) {
      console.error("Failed to fetch dashboard:", err);
      setError(
        "Could not reach the API. The server may be waking up from a cold start -- try refreshing in a few seconds."
      );
    } finally {
      setLoading(false);
    }
  }, [sortBy, sortDir, gradeFilter, segmentFilter, labelFilter, search]);

  useEffect(() => {
    const timer = setTimeout(fetchData, search ? 300 : 0);
    return () => clearTimeout(timer);
  }, [fetchData, search]);

  const uniqueLabels = useMemo(() => {
    const labels = new Set<string>();
    allArtists.forEach((a) => {
      if (a.current_label) labels.add(a.current_label);
    });
    return Array.from(labels).sort();
  }, [allArtists]);

  const activeFilterCount =
    (gradeFilter ? 1 : 0) +
    (segmentFilter ? 1 : 0) +
    (labelFilter ? 1 : 0);

  const toggleSort = (field: SortField) => {
    if (sortBy === field) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    } else {
      setSortBy(field);
      setSortDir("desc");
    }
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortBy !== field)
      return <ArrowUpDown size={12} className="text-gray-600" />;
    return sortDir === "desc" ? (
      <ChevronDown size={12} className="text-brand-red-light" />
    ) : (
      <ChevronUp size={12} className="text-brand-red-light" />
    );
  };

  return (
    <div className="space-y-4">
      <StatsRow artists={allArtists} total={total} />

      <div className="flex flex-col gap-3">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <h1 className="text-2xl font-bold">Momentum Dashboard</h1>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            <div className="relative flex-1 sm:w-64">
              <Search
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500"
              />
              <input
                type="text"
                placeholder="Search artists..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-3 py-2 bg-surface-raised border border-surface-border rounded-lg text-sm text-gray-200 placeholder:text-gray-500 focus:outline-none focus:ring-1 focus:ring-brand-red/50 focus:border-brand-red/50"
              />
            </div>
            <button
              onClick={() => setShowFilters((f) => !f)}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${
                showFilters || activeFilterCount > 0
                  ? "bg-brand-red/10 text-brand-red-light border-brand-red/30"
                  : "bg-surface-raised text-gray-400 border-surface-border hover:text-gray-200"
              }`}
            >
              <Filter size={14} />
              Filters
              {activeFilterCount > 0 && (
                <span className="bg-brand-red text-white text-xs w-4 h-4 rounded-full flex items-center justify-center">
                  {activeFilterCount}
                </span>
              )}
            </button>
          </div>
        </div>

        {showFilters && (
          <div className="flex flex-wrap items-center gap-2 bg-surface-raised border border-surface-border rounded-xl px-4 py-3">
            <select
              value={gradeFilter}
              onChange={(e) => setGradeFilter(e.target.value as Grade | "")}
              className="bg-surface-overlay border border-surface-border rounded-lg px-3 py-1.5 text-sm text-gray-300 focus:outline-none focus:ring-1 focus:ring-brand-red/50"
            >
              <option value="">All Grades</option>
              {grades.map((g) => (
                <option key={g} value={g}>
                  Grade {g}
                </option>
              ))}
            </select>
            <select
              value={segmentFilter}
              onChange={(e) => setSegmentFilter(e.target.value as SegType | "")}
              className="bg-surface-overlay border border-surface-border rounded-lg px-3 py-1.5 text-sm text-gray-300 focus:outline-none focus:ring-1 focus:ring-brand-red/50"
            >
              <option value="">All Segments</option>
              {segments.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            <select
              value={labelFilter}
              onChange={(e) => setLabelFilter(e.target.value)}
              className="bg-surface-overlay border border-surface-border rounded-lg px-3 py-1.5 text-sm text-gray-300 focus:outline-none focus:ring-1 focus:ring-brand-red/50"
            >
              <option value="">All Labels</option>
              {uniqueLabels.map((l) => (
                <option key={l} value={l}>
                  {l}
                </option>
              ))}
            </select>
            {activeFilterCount > 0 && (
              <button
                onClick={() => {
                  setGradeFilter("");
                  setSegmentFilter("");
                  setLabelFilter("");
                }}
                className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
              >
                Clear all
              </button>
            )}
          </div>
        )}

        {activeFilterCount > 0 && (
          <div className="flex flex-wrap gap-2">
            {gradeFilter && (
              <FilterChip
                label={`Grade ${gradeFilter}`}
                onRemove={() => setGradeFilter("")}
              />
            )}
            {segmentFilter && (
              <FilterChip
                label={segmentFilter}
                onRemove={() => setSegmentFilter("")}
              />
            )}
            {labelFilter && (
              <FilterChip
                label={labelFilter}
                onRemove={() => setLabelFilter("")}
              />
            )}
          </div>
        )}
      </div>

      <div className="bg-surface-raised border border-surface-border rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-border text-gray-400">
                <th className="text-left px-4 py-3 font-medium w-8 text-gray-500">
                  #
                </th>
                <th className="text-left px-3 py-3 font-medium">
                  <button
                    onClick={() => toggleSort("name")}
                    className="flex items-center gap-1 hover:text-gray-200"
                  >
                    Artist <SortIcon field="name" />
                  </button>
                </th>
                <th className="text-center px-3 py-3 font-medium">Grade</th>
                <th className="text-left px-3 py-3 font-medium">Segment</th>
                <th className="text-left px-3 py-3 font-medium min-w-[140px]">
                  <button
                    onClick={() => toggleSort("composite")}
                    className="flex items-center gap-1 hover:text-gray-200"
                  >
                    Composite <SortIcon field="composite" />
                  </button>
                </th>
                <th className="text-right px-3 py-3 font-medium hidden md:table-cell">
                  <button
                    onClick={() => toggleSort("trajectory")}
                    className="flex items-center gap-1 ml-auto hover:text-gray-200"
                  >
                    Traj <SortIcon field="trajectory" />
                  </button>
                </th>
                <th className="text-right px-3 py-3 font-medium hidden md:table-cell">
                  <button
                    onClick={() => toggleSort("industry_signal")}
                    className="flex items-center gap-1 ml-auto hover:text-gray-200"
                  >
                    IS <SortIcon field="industry_signal" />
                  </button>
                </th>
                <th className="text-right px-3 py-3 font-medium hidden lg:table-cell">
                  <button
                    onClick={() => toggleSort("engagement")}
                    className="flex items-center gap-1 ml-auto hover:text-gray-200"
                  >
                    Eng <SortIcon field="engagement" />
                  </button>
                </th>
                <th className="text-right px-3 py-3 font-medium hidden lg:table-cell">
                  <button
                    onClick={() => toggleSort("release_positioning")}
                    className="flex items-center gap-1 ml-auto hover:text-gray-200"
                  >
                    RP <SortIcon field="release_positioning" />
                  </button>
                </th>
                <th className="text-left px-3 py-3 font-medium hidden xl:table-cell">
                  Label
                </th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td
                    colSpan={10}
                    className="px-4 py-12 text-center text-gray-500"
                  >
                    <div className="flex flex-col items-center gap-2">
                      <div className="w-5 h-5 border-2 border-gray-600 border-t-brand-red rounded-full animate-spin" />
                      <span>Loading dashboard...</span>
                    </div>
                  </td>
                </tr>
              ) : error ? (
                <tr>
                  <td
                    colSpan={10}
                    className="px-4 py-12 text-center"
                  >
                    <div className="flex flex-col items-center gap-3">
                      <p className="text-gray-400">{error}</p>
                      <button
                        onClick={fetchData}
                        className="px-4 py-2 bg-brand-red text-white text-sm font-medium rounded-lg hover:bg-brand-red-dark transition-colors"
                      >
                        Retry
                      </button>
                    </div>
                  </td>
                </tr>
              ) : allArtists.length === 0 ? (
                <tr>
                  <td
                    colSpan={10}
                    className="px-4 py-12 text-center text-gray-500"
                  >
                    No artists found
                  </td>
                </tr>
              ) : (
                allArtists.map((a, idx) => (
                  <tr
                    key={a.spotify_id}
                    className="border-b border-surface-border/50 hover:bg-surface-overlay/50 transition-colors"
                  >
                    <td className="px-4 py-3 text-gray-600 font-mono text-xs">
                      {idx + 1}
                    </td>
                    <td className="px-3 py-3">
                      <Link
                        to={`/artist/${a.spotify_id}`}
                        className="font-medium text-gray-100 hover:text-white hover:underline"
                      >
                        {a.name}
                      </Link>
                    </td>
                    <td className="px-3 py-3 text-center">
                      <GradeBadge grade={a.grade} />
                    </td>
                    <td className="px-3 py-3">
                      <SegmentTag tag={a.segment_tag} />
                    </td>
                    <td className="px-3 py-3">
                      <CompositeBar value={a.composite} grade={a.grade} />
                    </td>
                    <td className="px-3 py-3 text-right font-mono text-gray-400 hidden md:table-cell">
                      {a.trajectory?.toFixed(0) ?? "—"}
                    </td>
                    <td className="px-3 py-3 text-right font-mono text-gray-400 hidden md:table-cell">
                      {a.industry_signal?.toFixed(0) ?? "—"}
                    </td>
                    <td className="px-3 py-3 text-right font-mono text-gray-400 hidden lg:table-cell">
                      {a.engagement?.toFixed(0) ?? "—"}
                    </td>
                    <td className="px-3 py-3 text-right font-mono text-gray-400 hidden lg:table-cell">
                      {a.release_positioning?.toFixed(0) ?? "—"}
                    </td>
                    <td className="px-3 py-3 text-gray-500 text-xs hidden xl:table-cell max-w-[150px] truncate">
                      {a.current_label ?? "Unsigned"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
