import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { Search, ArrowUpDown, ChevronUp, ChevronDown } from "lucide-react";
import { getDashboard } from "../api/client";
import { GradeBadge } from "../components/shared/GradeBadge";
import { SegmentTag } from "../components/shared/SegmentTag";
import type { DashboardArtist, Grade } from "../types";

type SortField = "composite" | "trajectory" | "industry_signal" | "engagement" | "name";
type SortDir = "asc" | "desc";

const grades: Grade[] = ["A", "B", "C", "D"];

export function DashboardPage() {
  const [artists, setArtists] = useState<DashboardArtist[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [gradeFilter, setGradeFilter] = useState<Grade | "">("");
  const [sortBy, setSortBy] = useState<SortField>("composite");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getDashboard({
        sort_by: sortBy,
        sort_dir: sortDir,
        grade: gradeFilter || undefined,
        search: search || undefined,
        limit: 50,
      });
      setArtists(data.artists);
      setTotal(data.total);
    } catch (err) {
      console.error("Failed to fetch dashboard:", err);
    } finally {
      setLoading(false);
    }
  }, [sortBy, sortDir, gradeFilter, search]);

  useEffect(() => {
    const timer = setTimeout(fetchData, search ? 300 : 0);
    return () => clearTimeout(timer);
  }, [fetchData, search]);

  const toggleSort = (field: SortField) => {
    if (sortBy === field) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    } else {
      setSortBy(field);
      setSortDir("desc");
    }
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortBy !== field) return <ArrowUpDown size={12} className="text-gray-600" />;
    return sortDir === "desc" ? (
      <ChevronDown size={12} className="text-brand-red-light" />
    ) : (
      <ChevronUp size={12} className="text-brand-red-light" />
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Momentum Dashboard</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {total} artists tracked
          </p>
        </div>

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
          <select
            value={gradeFilter}
            onChange={(e) => setGradeFilter(e.target.value as Grade | "")}
            className="bg-surface-raised border border-surface-border rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:ring-1 focus:ring-brand-red/50"
          >
            <option value="">All Grades</option>
            {grades.map((g) => (
              <option key={g} value={g}>
                Grade {g}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="bg-surface-raised border border-surface-border rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-border text-gray-400">
                <th className="text-left px-4 py-3 font-medium">
                  <button
                    onClick={() => toggleSort("name")}
                    className="flex items-center gap-1 hover:text-gray-200"
                  >
                    Artist <SortIcon field="name" />
                  </button>
                </th>
                <th className="text-center px-3 py-3 font-medium">Grade</th>
                <th className="text-left px-3 py-3 font-medium">Segment</th>
                <th className="text-right px-3 py-3 font-medium">
                  <button
                    onClick={() => toggleSort("composite")}
                    className="flex items-center gap-1 ml-auto hover:text-gray-200"
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
                <th className="text-left px-3 py-3 font-medium hidden lg:table-cell">
                  Label
                </th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-gray-500">
                    Loading...
                  </td>
                </tr>
              ) : artists.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-gray-500">
                    No artists found
                  </td>
                </tr>
              ) : (
                artists.map((a) => (
                  <tr
                    key={a.spotify_id}
                    className="border-b border-surface-border/50 hover:bg-surface-overlay/50 transition-colors"
                  >
                    <td className="px-4 py-3">
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
                    <td className="px-3 py-3 text-right font-mono text-gray-200">
                      {a.composite.toFixed(1)}
                    </td>
                    <td className="px-3 py-3 text-right font-mono text-gray-400 hidden md:table-cell">
                      {a.trajectory.toFixed(0)}
                    </td>
                    <td className="px-3 py-3 text-right font-mono text-gray-400 hidden md:table-cell">
                      {a.industry_signal.toFixed(0)}
                    </td>
                    <td className="px-3 py-3 text-right font-mono text-gray-400 hidden lg:table-cell">
                      {a.engagement.toFixed(0)}
                    </td>
                    <td className="px-3 py-3 text-gray-500 text-xs hidden lg:table-cell max-w-[150px] truncate">
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
