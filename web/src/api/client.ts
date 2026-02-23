import type {
  DashboardResponse,
  DashboardParams,
  ArtistDetail,
  NetworkGraph,
  ScoreRecord,
} from "../types";

const BASE = import.meta.env.VITE_API_URL ?? "";

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${res.statusText}`);
  }
  return res.json();
}

function toQueryString(params: Record<string, unknown>): string {
  const qs = new URLSearchParams();
  for (const [key, val] of Object.entries(params)) {
    if (val !== undefined && val !== null && val !== "") {
      qs.set(key, String(val));
    }
  }
  const str = qs.toString();
  return str ? `?${str}` : "";
}

export async function getDashboard(
  params: DashboardParams = {}
): Promise<DashboardResponse> {
  return fetchJSON(`/api/artists/dashboard${toQueryString(params as unknown as Record<string, unknown>)}`);
}

export async function getArtistDetail(
  spotifyId: string
): Promise<ArtistDetail> {
  return fetchJSON(`/api/artists/${spotifyId}`);
}

export async function getScoreHistory(
  spotifyId: string
): Promise<ScoreRecord[]> {
  return fetchJSON(`/api/scores/${spotifyId}`);
}

export async function getNetworkGraph(
  center?: string,
  depth?: number
): Promise<NetworkGraph> {
  const params: Record<string, unknown> = {};
  if (center) params.center = center;
  if (depth) params.depth = depth;
  return fetchJSON(`/api/network/graph${toQueryString(params)}`);
}
