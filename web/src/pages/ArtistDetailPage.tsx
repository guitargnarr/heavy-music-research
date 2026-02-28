import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Network, ExternalLink, MapPin, Ticket, Music2 } from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { getArtistDetail } from "../api/client";
import { GradeBadge } from "../components/shared/GradeBadge";
import { SegmentTag } from "../components/shared/SegmentTag";
import { ScoreBar } from "../components/shared/ScoreBar";
import type { ArtistDetail } from "../types";

export function ArtistDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [artist, setArtist] = useState<ArtistDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getArtistDetail(id)
      .then(setArtist)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3 text-steel">
        <div className="w-6 h-6 border-2 border-surface-border border-t-accent rounded-full animate-spin" />
        Loading artist...
      </div>
    );
  }

  if (error || !artist) {
    return (
      <div className="flex flex-col items-center text-center py-20 gap-3">
        <p className="text-steel">
          {error ?? "Artist not found"}
        </p>
        <Link
          to="/"
          className="px-4 py-2 bg-accent text-white text-sm font-medium rounded-lg hover:bg-brand-red-dark transition-colors"
        >
          Back to dashboard
        </Link>
      </div>
    );
  }

  const latestScore = artist.scores[0];
  const scoreHistory = [...artist.scores].reverse().map((s) => ({
    date: s.score_date,
    composite: s.composite,
    trajectory: s.trajectory,
    industry: s.industry_signal,
    engagement: s.engagement,
    release: s.release_positioning,
  }));

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-3">
        <Link
          to="/"
          className="inline-flex items-center gap-1 text-sm text-steel hover:text-gray-200 transition-colors"
        >
          <ArrowLeft size={16} />
          Dashboard
        </Link>
        <span className="text-surface-border">/</span>
        <span className="text-sm text-gray-300">{artist.name}</span>
      </div>

      {/* Hero */}
      <div className="relative overflow-hidden rounded-xl">
        {artist.image_url && (
          <div
            className="absolute inset-0 opacity-[0.07] blur-3xl scale-125"
            style={{ backgroundImage: `url(${artist.image_url})`, backgroundSize: "cover", backgroundPosition: "center" }}
          />
        )}
        <div className="relative flex flex-col sm:flex-row items-start gap-5 p-1">
          {artist.image_url && (
            <img
              src={artist.image_url}
              alt={artist.name}
              className="w-24 h-24 rounded-lg object-cover border border-surface-border"
            />
          )}
          <div className="flex-1">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h1 className="text-3xl font-display font-bold tracking-tight">{artist.name}</h1>
                <div className="flex flex-wrap items-center gap-2 mt-2">
                  {latestScore && (
                    <>
                      <GradeBadge grade={latestScore.grade} />
                      <SegmentTag tag={latestScore.segment_tag} />
                      <span className="text-sm font-mono text-steel">
                        {latestScore.composite.toFixed(1)}
                      </span>
                    </>
                  )}
                </div>
              </div>
              <Link
                to={`/network?center=${encodeURIComponent(artist.name)}`}
                className="flex items-center gap-1.5 px-3 py-2 bg-surface-raised border border-surface-border rounded-lg text-sm text-steel hover:text-white transition-colors"
              >
                <Network size={14} />
                Network
              </Link>
            </div>

            {artist.genres.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-3">
                {artist.genres.map((g) => (
                  <span
                    key={g}
                    className="text-[10px] px-2 py-0.5 rounded border border-surface-border text-steel uppercase tracking-wider"
                  >
                    {g}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Cards grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {latestScore && (
          <div className="card p-5 space-y-3">
            <h2 className="text-[10px] font-medium text-steel uppercase tracking-widest">
              Score Breakdown
            </h2>
            <ScoreBar label="Trajectory (40%)" value={latestScore.trajectory} />
            <ScoreBar
              label="Industry Signal (30%)"
              value={latestScore.industry_signal}
            />
            <ScoreBar
              label="Engagement (20%)"
              value={latestScore.engagement}
            />
            <ScoreBar
              label="Release Positioning (10%)"
              value={latestScore.release_positioning}
            />
          </div>
        )}

        <div className="card p-5 space-y-3">
          <h2 className="text-[10px] font-medium text-steel uppercase tracking-widest">
            Producer Credits
          </h2>
          {(!artist.producers || artist.producers.length === 0) ? (
            <p className="text-xs text-steel italic">No producer data yet</p>
          ) : (
            artist.producers.map((p) => (
              <div key={p.name} className="flex items-start gap-2">
                <Music2 size={12} className="text-blue-400 mt-0.5 shrink-0" />
                <div>
                  <div className="text-sm font-medium text-gray-200">{p.name}</div>
                  {p.studio && (
                    <div className="text-xs text-steel font-mono">{p.studio}</div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        <div className="card p-5 space-y-3">
          <h2 className="text-[10px] font-medium text-steel uppercase tracking-widest">
            Industry Info
          </h2>
          <InfoRow label="Label" value={artist.current_label} />
          {artist.label_contact && (
            <>
              {artist.label_contact.key_contact && (
                <InfoRow
                  label="A&R Contact"
                  value={`${artist.label_contact.key_contact}${artist.label_contact.contact_title ? ` (${artist.label_contact.contact_title})` : ""}`}
                />
              )}
            </>
          )}
          <InfoRow label="Management" value={artist.current_management_co} />
          <InfoRow label="Manager" value={artist.current_manager} />
          <InfoRow label="Booking Agency" value={artist.booking_agency} />
          <InfoRow label="Booking Agent" value={artist.booking_agent} />
          {artist.spotify_id && !artist.spotify_id.startsWith("placeholder") && (
            <a
              href={`https://open.spotify.com/artist/${artist.spotify_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-green-400 hover:text-green-300 mt-2"
            >
              <ExternalLink size={12} />
              Spotify
            </a>
          )}
        </div>
      </div>

      {/* Related Artists (shared producers) */}
      {artist.related_artists && artist.related_artists.length > 0 && (
        <div className="card p-5">
          <h2 className="text-[10px] font-medium text-steel uppercase tracking-widest mb-3">
            Related Artists <span className="text-steel/50 normal-case">(shared producers)</span>
          </h2>
          <div className="flex flex-wrap gap-2">
            {artist.related_artists.map((ra) => (
              <Link
                key={ra.spotify_id}
                to={`/artist/${ra.spotify_id}`}
                className="flex items-center gap-2 px-3 py-2 rounded-lg bg-surface-overlay border border-surface-border hover:border-accent/30 transition-colors group"
              >
                {ra.image_url ? (
                  <img src={ra.image_url} alt="" className="w-6 h-6 rounded-full object-cover" />
                ) : (
                  <div className="w-6 h-6 rounded-full bg-surface-border" />
                )}
                <span className="text-sm text-gray-300 group-hover:text-white transition-colors">{ra.name}</span>
                {ra.composite != null && (
                  <span className="text-xs font-mono text-steel">{ra.composite.toFixed(0)}</span>
                )}
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Score history */}
      {scoreHistory.length > 1 && (
        <div className="card p-5">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mb-4">
            <h2 className="text-[10px] font-medium text-steel uppercase tracking-widest">
              Score History
            </h2>
            <div className="flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-steel ml-auto">
              <span className="flex items-center gap-1"><span className="inline-block w-3 h-0.5 bg-red-600 rounded" /> Composite</span>
              <span className="flex items-center gap-1"><span className="inline-block w-3 h-0.5 bg-green-500 rounded opacity-60" /> Trajectory</span>
              <span className="flex items-center gap-1"><span className="inline-block w-3 h-0.5 bg-blue-500 rounded opacity-60" /> Industry</span>
              <span className="flex items-center gap-1"><span className="inline-block w-3 h-0.5 bg-amber-500 rounded opacity-60" /> Engagement</span>
              <span className="flex items-center gap-1"><span className="inline-block w-3 h-0.5 bg-purple-500 rounded opacity-60" /> Release</span>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={scoreHistory}>
              <defs>
                <linearGradient id="compositeGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#dc2626" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#dc2626" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="date"
                tick={{ fill: "#8a8f98", fontSize: 11, fontFamily: "IBM Plex Mono" }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fill: "#8a8f98", fontSize: 11, fontFamily: "IBM Plex Mono" }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#0d0e10",
                  border: "1px solid #1e2024",
                  borderRadius: "8px",
                  fontSize: "12px",
                  fontFamily: "IBM Plex Mono",
                }}
                labelStyle={{ color: "#8a8f98" }}
              />
              <Area type="monotone" dataKey="trajectory" stroke="#22c55e" fill="none" strokeWidth={1} strokeDasharray="4 2" dot={false} />
              <Area type="monotone" dataKey="industry" stroke="#3b82f6" fill="none" strokeWidth={1} strokeDasharray="4 2" dot={false} />
              <Area type="monotone" dataKey="engagement" stroke="#f59e0b" fill="none" strokeWidth={1} strokeDasharray="4 2" dot={false} />
              <Area type="monotone" dataKey="release" stroke="#a855f7" fill="none" strokeWidth={1} strokeDasharray="4 2" dot={false} />
              <Area
                type="monotone"
                dataKey="composite"
                stroke="#dc2626"
                fill="url(#compositeGrad)"
                strokeWidth={1.5}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Snapshots */}
      {artist.snapshots.length > 0 && (
        <div className="card p-5">
          <h2 className="text-[10px] font-medium text-steel uppercase tracking-widest mb-3">
            Latest Snapshot
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            <StatCard
              label="Spotify Popularity"
              value={artist.snapshots[0].spotify_popularity}
            />
            <StatCard
              label="Spotify Followers"
              value={artist.snapshots[0].spotify_followers}
              format="compact"
            />
            <StatCard
              label="YouTube Subs"
              value={artist.snapshots[0].youtube_subscribers}
              format="compact"
            />
            <StatCard
              label="YouTube Views (total)"
              value={artist.snapshots[0].youtube_total_views}
              format="compact"
            />
            <StatCard
              label="YouTube Views (recent)"
              value={artist.snapshots[0].youtube_recent_views}
              format="compact"
            />
            <StatCard
              label="YouTube Comments"
              value={artist.snapshots[0].youtube_comment_count}
              format="compact"
            />
          </div>
        </div>
      )}

      {/* Upcoming Shows */}
      {artist.upcoming_events && artist.upcoming_events.length > 0 && (
        <div className="card p-5">
          <h2 className="text-[10px] font-medium text-steel uppercase tracking-widest mb-4">
            Upcoming Shows ({artist.upcoming_events.length})
          </h2>
          <div className="relative pl-6 border-l border-surface-border space-y-0">
            {artist.upcoming_events.map((event) => (
              <div
                key={event.id}
                className="relative flex items-center justify-between gap-3 py-3 group"
              >
                {/* Timeline dot */}
                <div className="absolute -left-[25px] w-2 h-2 rounded-full bg-surface-border group-hover:bg-accent transition-colors" />

                <div className="flex items-center gap-4 min-w-0">
                  <div className="text-center shrink-0 w-12">
                    <div className="text-[10px] text-steel uppercase tracking-wider font-mono">
                      {new Date(event.event_date + "T00:00:00").toLocaleDateString("en-US", { month: "short" })}
                    </div>
                    <div className="text-lg font-mono font-semibold text-gray-200 leading-tight">
                      {new Date(event.event_date + "T00:00:00").getDate()}
                    </div>
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-200 truncate">
                        {event.venue_name ?? event.event_name}
                      </span>
                      {event.festival_name && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded border border-accent/30 text-accent shrink-0 uppercase tracking-wider">
                          Festival
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-1 text-xs text-steel mt-0.5">
                      <MapPin size={10} />
                      {[event.city, event.region, event.country].filter(Boolean).join(", ")}
                    </div>
                  </div>
                </div>
                {event.ticket_url && (
                  <a
                    href={event.ticket_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-xs text-accent hover:text-white shrink-0"
                  >
                    <Ticket size={12} />
                    Tickets
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function InfoRow({
  label,
  value,
}: {
  label: string;
  value: string | null;
}) {
  return (
    <div className="flex justify-between text-sm gap-2">
      <span className="text-steel shrink-0">{label}</span>
      <span className="text-gray-300 text-right truncate font-mono text-xs">
        {value ?? "Unknown"}
      </span>
    </div>
  );
}

function StatCard({
  label,
  value,
  format,
}: {
  label: string;
  value: number | null;
  format?: "compact";
}) {
  const display =
    value === null
      ? "--"
      : format === "compact"
        ? Intl.NumberFormat("en", { notation: "compact" }).format(value)
        : value.toLocaleString();

  return (
    <div className="text-center">
      <div className="text-xl font-semibold font-mono text-gray-100">
        {display}
      </div>
      <div className="text-[10px] text-steel mt-0.5 uppercase tracking-wider">{label}</div>
    </div>
  );
}
