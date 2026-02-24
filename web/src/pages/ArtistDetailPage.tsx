import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Network, ExternalLink } from "lucide-react";
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
import { ScoreRadar } from "../components/shared/ScoreRadar";
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
      <div className="flex flex-col items-center justify-center py-20 gap-3 text-gray-500">
        <div className="w-6 h-6 border-2 border-gray-600 border-t-brand-red rounded-full animate-spin" />
        Loading artist...
      </div>
    );
  }

  if (error || !artist) {
    return (
      <div className="flex flex-col items-center text-center py-20 gap-3">
        <p className="text-gray-400">
          {error ?? "Artist not found"}
        </p>
        <Link
          to="/"
          className="px-4 py-2 bg-brand-red text-white text-sm font-medium rounded-lg hover:bg-brand-red-dark transition-colors"
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
      <div className="flex items-center gap-3">
        <Link
          to="/"
          className="inline-flex items-center gap-1 text-sm text-gray-400 hover:text-gray-200 transition-colors"
        >
          <ArrowLeft size={16} />
          Dashboard
        </Link>
        <span className="text-gray-600">/</span>
        <span className="text-sm text-gray-300">{artist.name}</span>
      </div>

      <div className="flex flex-col sm:flex-row items-start gap-5">
        {artist.image_url && (
          <img
            src={artist.image_url}
            alt={artist.name}
            className="w-24 h-24 rounded-xl object-cover border border-surface-border"
          />
        )}
        <div className="flex-1">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold">{artist.name}</h1>
              <div className="flex flex-wrap items-center gap-2 mt-2">
                {latestScore && (
                  <>
                    <GradeBadge grade={latestScore.grade} />
                    <SegmentTag tag={latestScore.segment_tag} />
                    <span className="text-sm font-mono text-gray-400">
                      {latestScore.composite.toFixed(1)}
                    </span>
                  </>
                )}
              </div>
            </div>
            <Link
              to={`/network?center=${encodeURIComponent(artist.name)}`}
              className="flex items-center gap-1.5 px-3 py-2 bg-surface-overlay border border-surface-border rounded-lg text-sm text-gray-300 hover:text-white hover:border-gray-500 transition-colors"
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
                  className="text-xs px-2 py-0.5 rounded-md bg-surface-overlay text-gray-400 border border-surface-border"
                >
                  {g}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {latestScore && (
          <div className="bg-surface-raised border border-surface-border rounded-xl p-5 space-y-3">
            <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
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

        {latestScore && (
          <div className="bg-surface-raised border border-surface-border rounded-xl p-5">
            <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-2">
              Score Profile
            </h2>
            <ScoreRadar
              trajectory={latestScore.trajectory}
              industrySignal={latestScore.industry_signal}
              engagement={latestScore.engagement}
              releasePositioning={latestScore.release_positioning}
            />
          </div>
        )}

        <div className="bg-surface-raised border border-surface-border rounded-xl p-5 space-y-3">
          <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
            Industry Info
          </h2>
          <InfoRow label="Label" value={artist.current_label} />
          <InfoRow label="Management" value={artist.current_management_co} />
          <InfoRow label="Manager" value={artist.current_manager} />
          <InfoRow label="Booking" value={artist.booking_agency} />
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

      {scoreHistory.length > 1 && (
        <div className="bg-surface-raised border border-surface-border rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">
            Score History
          </h2>
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
                tick={{ fill: "#6b7280", fontSize: 11 }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fill: "#6b7280", fontSize: 11 }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1a1a1a",
                  border: "1px solid #333",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
                labelStyle={{ color: "#9ca3af" }}
              />
              <Area
                type="monotone"
                dataKey="composite"
                stroke="#dc2626"
                fill="url(#compositeGrad)"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {artist.snapshots.length > 0 && (
        <div className="bg-surface-raised border border-surface-border rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">
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
      <span className="text-gray-500 shrink-0">{label}</span>
      <span className="text-gray-300 text-right truncate">
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
      <div className="text-xl font-bold font-mono text-gray-100">
        {display}
      </div>
      <div className="text-xs text-gray-500 mt-0.5">{label}</div>
    </div>
  );
}
