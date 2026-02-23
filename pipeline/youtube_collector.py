"""
YouTube data collector for the Metalcore Index pipeline.

Strategy (from Ultrathink):
- NEVER use Search endpoint (100 units/call, 10K daily quota)
- Seed channel IDs manually in the artists table
- Use Channels endpoint (1 unit) and Videos endpoint (1 unit) for ongoing data
- Cache 7+ days

Collects per artist:
- subscriber count
- total view count
- recent video views (last 90 days)
- comment count on recent videos

Requires: YOUTUBE_API_KEY env var.
Falls back to simulated data when credentials are absent.
"""
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class YouTubeChannelData:
    channel_id: str
    subscriber_count: int = 0
    total_views: int = 0
    recent_video_views: int = 0
    recent_comment_count: int = 0
    video_count: int = 0


class YouTubeCollector:
    """Collects channel and video data from YouTube Data API v3."""

    def __init__(self):
        self.youtube = None
        self._init_client()

    def _init_client(self):
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            logger.warning(
                "YOUTUBE_API_KEY not set. YouTube collection disabled."
            )
            return

        try:
            from googleapiclient.discovery import build

            self.youtube = build("youtube", "v3", developerKey=api_key)
            logger.info("YouTube client initialized")
        except ImportError:
            logger.warning(
                "google-api-python-client not installed. "
                "Run: pip install google-api-python-client"
            )
        except Exception as e:
            logger.error("Failed to init YouTube client: %s", e)

    @property
    def is_available(self) -> bool:
        return self.youtube is not None

    def collect_channel(self, channel_id: str) -> YouTubeChannelData | None:
        """Collect channel statistics. Costs 1 quota unit."""
        if not self.youtube:
            return None

        try:
            response = (
                self.youtube.channels()
                .list(part="statistics", id=channel_id)
                .execute()
            )
            time.sleep(0.1)

            items = response.get("items", [])
            if not items:
                logger.warning("No channel found for ID: %s", channel_id)
                return None

            stats = items[0]["statistics"]
            data = YouTubeChannelData(
                channel_id=channel_id,
                subscriber_count=int(stats.get("subscriberCount", 0)),
                total_views=int(stats.get("viewCount", 0)),
                video_count=int(stats.get("videoCount", 0)),
            )

            # Get recent videos for view acceleration + comments
            recent = self._get_recent_video_stats(channel_id)
            data.recent_video_views = recent["views"]
            data.recent_comment_count = recent["comments"]

            return data

        except Exception as e:
            logger.error("Error collecting channel %s: %s", channel_id, e)
            return None

    def _get_recent_video_stats(
        self, channel_id: str, days: int = 90
    ) -> dict[str, int]:
        """
        Get aggregate stats for videos published in the last N days.
        Uses playlistItems (1 unit) + videos (1 unit per batch of 50).
        """
        result = {"views": 0, "comments": 0}
        if not self.youtube:
            return result

        try:
            # Get uploads playlist ID (channel ID with UC -> UU)
            uploads_id = "UU" + channel_id[2:]
            cutoff = datetime.utcnow() - timedelta(days=days)
            cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

            # Get recent video IDs from uploads playlist
            response = (
                self.youtube.playlistItems()
                .list(
                    part="contentDetails",
                    playlistId=uploads_id,
                    maxResults=20,
                )
                .execute()
            )
            time.sleep(0.1)

            video_ids = []
            for item in response.get("items", []):
                published = item["contentDetails"].get("videoPublishedAt", "")
                if published >= cutoff_str:
                    video_ids.append(item["contentDetails"]["videoId"])

            if not video_ids:
                return result

            # Batch fetch video stats (50 per request, 1 unit)
            for i in range(0, len(video_ids), 50):
                batch = video_ids[i: i + 50]
                vid_response = (
                    self.youtube.videos()
                    .list(
                        part="statistics",
                        id=",".join(batch),
                    )
                    .execute()
                )
                time.sleep(0.1)

                for vid in vid_response.get("items", []):
                    stats = vid.get("statistics", {})
                    result["views"] += int(stats.get("viewCount", 0))
                    result["comments"] += int(stats.get("commentCount", 0))

            return result

        except Exception as e:
            logger.error(
                "Error getting recent videos for %s: %s", channel_id, e
            )
            return result

    def collect_batch(
        self, channel_ids: list[str]
    ) -> list[YouTubeChannelData]:
        """Collect data for multiple channels."""
        results = []
        for i, cid in enumerate(channel_ids):
            if not cid:
                continue
            data = self.collect_channel(cid)
            if data:
                results.append(data)
            if (i + 1) % 20 == 0:
                logger.info(
                    "Collected %d/%d channels", i + 1, len(channel_ids)
                )
                time.sleep(0.5)
        return results


def simulate_youtube_data(
    artist_name: str, channel_id: str
) -> YouTubeChannelData:
    """Generate simulated YouTube data for local development."""
    name_hash = sum(ord(c) for c in artist_name)

    known_subs = {
        "Sleep Token": 850000,
        "Knocked Loose": 280000,
        "Spiritbox": 420000,
        "Lorna Shore": 650000,
        "Lamb of God": 1200000,
        "Periphery": 550000,
        "Bad Omens": 500000,
        "Gojira": 900000,
        "Trivium": 800000,
        "Bring Me the Horizon": 3200000,
        "Turnstile": 350000,
        "Architects": 600000,
    }

    subs = known_subs.get(artist_name, 5000 + (name_hash * 97) % 300000)
    total_views = subs * (15 + name_hash % 30)
    recent_views = int(total_views * (0.02 + (name_hash % 10) * 0.005))
    comments = int(recent_views * (0.005 + (name_hash % 5) * 0.001))

    return YouTubeChannelData(
        channel_id=channel_id or f"sim_{artist_name[:10]}",
        subscriber_count=subs,
        total_views=total_views,
        recent_video_views=recent_views,
        recent_comment_count=comments,
    )
