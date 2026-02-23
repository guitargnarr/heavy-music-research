export type Grade = "A" | "B" | "C" | "D";

export type SegmentTag =
  | "Breakout Candidate"
  | "Established Ascender"
  | "Established Stable"
  | "Label-Ready"
  | "Producer Bump"
  | "At Risk"
  | "Sleeping Giant"
  | "Algorithmic Lift";

export interface DashboardArtist {
  spotify_id: string;
  name: string;
  image_url: string | null;
  current_label: string | null;
  grade: Grade;
  segment_tag: SegmentTag;
  composite: number;
  trajectory: number;
  industry_signal: number;
  engagement: number;
  release_positioning: number;
}

export interface DashboardResponse {
  artists: DashboardArtist[];
  total: number;
  universe_size: number;
}

export interface Snapshot {
  snapshot_date: string;
  spotify_popularity: number | null;
  spotify_followers: number | null;
  youtube_subscribers: number | null;
  youtube_total_views: number | null;
  youtube_recent_views: number | null;
  youtube_comment_count: number | null;
  setlist_count_90d: number | null;
}

export interface ScoreRecord {
  score_date: string;
  trajectory: number;
  industry_signal: number;
  engagement: number;
  release_positioning: number;
  composite: number;
  grade: Grade;
  segment_tag: SegmentTag;
}

export interface ArtistDetail {
  spotify_id: string;
  name: string;
  genres: string[];
  image_url: string | null;
  current_label: string | null;
  current_manager: string | null;
  current_management_co: string | null;
  booking_agency: string | null;
  youtube_channel_id: string | null;
  active: boolean;
  snapshots: Snapshot[];
  scores: ScoreRecord[];
}

export interface NetworkNode {
  id: string;
  label: string;
  type: "artist" | "producer" | "label" | "management" | "agency";
  score: number | null;
}

export interface NetworkLink {
  source: string;
  target: string;
  relationship: string;
}

export interface NetworkGraph {
  nodes: NetworkNode[];
  links: NetworkLink[];
}

export interface DashboardParams {
  sort_by?: string;
  sort_dir?: "asc" | "desc";
  grade?: Grade;
  segment?: string;
  label?: string;
  search?: string;
  limit?: number;
  offset?: number;
}
