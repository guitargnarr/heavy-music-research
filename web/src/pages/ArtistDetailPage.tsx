import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
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
      <div className="flex items-center justify-center py-20 text-gray-500">
        Loading...
      </div>
    );
  }

  if (error || !artist) {
    return (
      <div className="text-center py-20">
        <p className="text-red-400">{error ?? "Artist not found"}</p>
        <Link to="/" className="text-brand-red-light hover:underline text-sm mt-2 inline-block">
          Back to dashboard
        </Link>
      </div>
    );
  }

  const latestScore = artist.scores[0];

  return (
    <div className="space-y-6">
      <Link
        to="/"
        className="inline-flex items-center gap-1 text-sm text-gray-400 hover:text-gray-200 transition-colors"
      >
        <ArrowLeft size={16} />
        Back to dashboard
      </Link>

      <div className="flex flex-col sm:flex-row items-start gap-4">
        {artist.image_url && (
          <img
            src={artist.image_url}
            alt={artist.name}
            className="w-20 h-20 rounded-xl object-cover"
          />
        )}
        <div className="flex-1">
          <h1 className="text-3xl font-bold">{artist.name}</h1>
          <div className="flex flex-wrap items-center gap-2 mt-2">
            {latestScore && (
              <>
                <GradeBadge grade={latestScore.grade} />
                <SegmentTag tag={latestScore.segment_tag} />
                <span className="text-sm font-mono text-gray-400">
                  Composite: {latestScore.composite.toFixed(1)}
                </span>
              </>
            )}
          </div>
          {artist.genres.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {artist.genres.map((g) => (
                <span
                  key={g}
                  className="text-xs px-2 py-0.5 rounded-md bg-surface-overlay text-gray-400"
                >
                  {g}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {latestScore && (
          <div className="bg-surface-raised border border-surface-border rounded-xl p-5 space-y-3">
            <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
              Score Breakdown
            </h2>
            <ScoreBar label="Trajectory (40%)" value={latestScore.trajectory} />
            <ScoreBar label="Industry Signal (30%)" value={latestScore.industry_signal} />
            <ScoreBar label="Engagement (20%)" value={latestScore.engagement} />
            <ScoreBar label="Release Positioning (10%)" value={latestScore.release_positioning} />
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
        </div>
      </div>

      {artist.snapshots.length > 0 && (
        <div className="bg-surface-raised border border-surface-border rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">
            Latest Snapshot
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
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
              label="YouTube Subscribers"
              value={artist.snapshots[0].youtube_subscribers}
              format="compact"
            />
            <StatCard
              label="YouTube Recent Views"
              value={artist.snapshots[0].youtube_recent_views}
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
    <div className="flex justify-between text-sm">
      <span className="text-gray-500">{label}</span>
      <span className="text-gray-300">{value ?? "Unknown"}</span>
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
      <div className="text-xl font-bold font-mono text-gray-100">{display}</div>
      <div className="text-xs text-gray-500 mt-0.5">{label}</div>
    </div>
  );
}
