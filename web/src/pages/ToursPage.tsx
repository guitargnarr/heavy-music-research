import { useEffect, useState, useMemo } from "react";
import { Search, MapPin, Calendar, Ticket } from "lucide-react";
import { getUpcomingEvents, getFestivals } from "../api/client";
import type { EventRecord, FestivalSummary } from "../types";

export function ToursPage() {
  const [events, setEvents] = useState<EventRecord[]>([]);
  const [festivals, setFestivals] = useState<FestivalSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [festivalOnly, setFestivalOnly] = useState(false);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getUpcomingEvents({ days: 180, limit: 500 }),
      getFestivals(),
    ])
      .then(([evts, fests]) => {
        setEvents(evts);
        setFestivals(fests);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const filteredEvents = useMemo(() => {
    let filtered = events;
    if (festivalOnly) {
      filtered = filtered.filter((e) => e.festival_name);
    }
    if (search) {
      const q = search.toLowerCase();
      filtered = filtered.filter(
        (e) =>
          e.event_name.toLowerCase().includes(q) ||
          (e.venue_name?.toLowerCase().includes(q) ?? false) ||
          (e.city?.toLowerCase().includes(q) ?? false) ||
          (e.festival_name?.toLowerCase().includes(q) ?? false)
      );
    }
    return filtered;
  }, [events, search, festivalOnly]);

  const groupedByMonth = useMemo(() => {
    const groups: Record<string, EventRecord[]> = {};
    for (const event of filteredEvents) {
      const d = new Date(event.event_date + "T00:00:00");
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
      if (!groups[key]) groups[key] = [];
      groups[key].push(event);
    }
    return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b));
  }, [filteredEvents]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3 text-gray-500">
        <div className="w-6 h-6 border-2 border-gray-600 border-t-brand-red rounded-full animate-spin" />
        Loading tour data...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center text-center py-20 gap-3">
        <p className="text-gray-400">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Tours & Festivals</h1>
          <p className="text-sm text-gray-500 mt-1">
            {events.length} upcoming shows across {new Set(events.map((e) => e.event_name)).size} events
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
              placeholder="Search events, venues, cities..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-surface-raised border border-surface-border rounded-lg text-sm text-gray-200 placeholder:text-gray-500 focus:outline-none focus:ring-1 focus:ring-brand-red/50 focus:border-brand-red/50"
            />
          </div>
          <button
            onClick={() => setFestivalOnly((f) => !f)}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${
              festivalOnly
                ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                : "bg-surface-raised text-gray-400 border-surface-border hover:text-gray-200"
            }`}
          >
            <Calendar size={14} />
            Festivals
          </button>
        </div>
      </div>

      {festivals.length > 0 && !search && !festivalOnly && (
        <div>
          <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">
            Festival Appearances
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {festivals.slice(0, 6).map((f) => (
              <div
                key={f.festival_name}
                className="bg-surface-raised border border-surface-border rounded-xl p-4 space-y-2"
              >
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-semibold text-gray-200 text-sm">
                    {f.festival_name}
                  </h3>
                  <span className="text-xs px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-400 border border-amber-500/20 shrink-0">
                    {f.artists.length} artists
                  </span>
                </div>
                <div className="flex items-center gap-1 text-xs text-gray-500">
                  <MapPin size={10} />
                  {f.location}
                </div>
                <div className="flex items-center gap-1 text-xs text-gray-500">
                  <Calendar size={10} />
                  {new Date(f.start_date + "T00:00:00").toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                  })}
                  {f.end_date && f.end_date !== f.start_date && (
                    <>
                      {" - "}
                      {new Date(f.end_date + "T00:00:00").toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                      })}
                    </>
                  )}
                </div>
                <div className="flex flex-wrap gap-1 pt-1">
                  {f.artists.slice(0, 5).map((name) => (
                    <span
                      key={name}
                      className="text-xs px-1.5 py-0.5 rounded bg-surface-overlay text-gray-400 border border-surface-border"
                    >
                      {name}
                    </span>
                  ))}
                  {f.artists.length > 5 && (
                    <span className="text-xs text-gray-600">
                      +{f.artists.length - 5} more
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div>
        {groupedByMonth.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            No events found
          </div>
        ) : (
          groupedByMonth.map(([monthKey, monthEvents]) => {
            const [year, month] = monthKey.split("-");
            const monthLabel = new Date(
              parseInt(year),
              parseInt(month) - 1
            ).toLocaleDateString("en-US", { month: "long", year: "numeric" });

            return (
              <div key={monthKey} className="mb-6">
                <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2 sticky top-14 bg-surface-base/95 backdrop-blur-sm py-2 z-10">
                  {monthLabel}
                  <span className="text-gray-600 ml-2 font-normal">
                    ({monthEvents.length} shows)
                  </span>
                </h2>
                <div className="bg-surface-raised border border-surface-border rounded-xl overflow-hidden">
                  {monthEvents.map((event, idx) => (
                    <div
                      key={event.id}
                      className={`flex items-center justify-between gap-3 px-4 py-3 ${
                        idx !== monthEvents.length - 1
                          ? "border-b border-surface-border/50"
                          : ""
                      } hover:bg-surface-overlay/50 transition-colors`}
                    >
                      <div className="flex items-center gap-4 min-w-0">
                        <div className="text-center shrink-0 w-10">
                          <div className="text-xs text-gray-500">
                            {new Date(event.event_date + "T00:00:00").toLocaleDateString("en-US", {
                              weekday: "short",
                            })}
                          </div>
                          <div className="text-lg font-bold text-gray-200 leading-tight">
                            {new Date(event.event_date + "T00:00:00").getDate()}
                          </div>
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-gray-200 truncate">
                              {event.event_name}
                            </span>
                            {event.festival_name && (
                              <span className="text-xs px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-400 border border-amber-500/20 shrink-0">
                                Festival
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-3 text-xs text-gray-500 mt-0.5">
                            {event.venue_name && (
                              <span>{event.venue_name}</span>
                            )}
                            <span className="flex items-center gap-1">
                              <MapPin size={10} />
                              {[event.city, event.region, event.country]
                                .filter(Boolean)
                                .join(", ")}
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 shrink-0">
                        {event.ticket_url && (
                          <a
                            href={event.ticket_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-1 text-xs text-brand-red-light hover:text-white"
                          >
                            <Ticket size={12} />
                            Tickets
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
