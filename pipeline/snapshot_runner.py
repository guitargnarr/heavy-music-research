"""
Snapshot runner: orchestrates all data collectors and stores snapshots.

This is the cron job entry point for data collection.
Run weekly via Render Cron Job or locally.

Usage:
  cd api && source .venv/bin/activate
  python -m pipeline.snapshot_runner [--simulate]
"""
import json
import logging
import os
import sys
from datetime import date

# Add project paths
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "api"))
sys.path.insert(0, project_root)

from database import Base, engine, SessionLocal  # noqa: E402
from models import Artist, ArtistSnapshot  # noqa: E402
from pipeline.spotify_collector import (  # noqa: E402
    SpotifyCollector,
    simulate_spotify_data,
)
from pipeline.youtube_collector import (  # noqa: E402
    YouTubeCollector,
    simulate_youtube_data,
)
from pipeline.musicbrainz_collector import (  # noqa: E402
    MusicBrainzCollector,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_snapshot(simulate: bool = False):
    """
    Collect data from all sources and store snapshots.

    Args:
        simulate: If True, use simulated data instead of live APIs.
                  Useful for local development and testing.
    """
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    today = date.today()

    try:
        artists = db.query(Artist).filter(Artist.active.is_(True)).all()
        logger.info("Processing %d active artists", len(artists))

        # Initialize collectors
        spotify = SpotifyCollector()
        youtube = YouTubeCollector()
        musicbrainz = MusicBrainzCollector()

        use_spotify = spotify.is_available and not simulate
        use_youtube = youtube.is_available and not simulate
        use_musicbrainz = musicbrainz.is_available and not simulate

        if simulate:
            logger.info("Running in SIMULATION mode")
        else:
            logger.info(
                "API status -- Spotify: %s, YouTube: %s, MusicBrainz: %s",
                "OK" if use_spotify else "OFF",
                "OK" if use_youtube else "OFF",
                "OK" if use_musicbrainz else "OFF",
            )

        created = 0
        skipped = 0

        for artist in artists:
            # Check if snapshot already exists for today
            existing = (
                db.query(ArtistSnapshot)
                .filter(
                    ArtistSnapshot.artist_id == artist.spotify_id,
                    ArtistSnapshot.snapshot_date == today,
                )
                .first()
            )
            if existing:
                skipped += 1
                continue

            # Collect Spotify data
            sp_pop = None
            sp_followers = None
            if use_spotify and not artist.spotify_id.startswith("placeholder_"):
                sp_data = spotify.collect_artist(artist.spotify_id)
                if sp_data:
                    sp_pop = sp_data.popularity
                    sp_followers = sp_data.followers
                    # Update artist record with fresh data
                    if sp_data.image_url:
                        artist.image_url = sp_data.image_url
                    if sp_data.genres:
                        artist.genres = json.dumps(sp_data.genres)
            elif simulate:
                sp_data = simulate_spotify_data(
                    artist.name, artist.spotify_id
                )
                sp_pop = sp_data.popularity
                sp_followers = sp_data.followers

            # Collect YouTube data
            yt_subs = None
            yt_total = None
            yt_recent = None
            yt_comments = None
            if use_youtube and artist.youtube_channel_id:
                yt_data = youtube.collect_channel(artist.youtube_channel_id)
                if yt_data:
                    yt_subs = yt_data.subscriber_count
                    yt_total = yt_data.total_views
                    yt_recent = yt_data.recent_video_views
                    yt_comments = yt_data.recent_comment_count
            elif simulate:
                yt_data = simulate_youtube_data(
                    artist.name, artist.youtube_channel_id or ""
                )
                yt_subs = yt_data.subscriber_count
                yt_total = yt_data.total_views
                yt_recent = yt_data.recent_video_views
                yt_comments = yt_data.recent_comment_count

            # Create snapshot
            snapshot = ArtistSnapshot(
                artist_id=artist.spotify_id,
                snapshot_date=today,
                spotify_popularity=sp_pop,
                spotify_followers=sp_followers,
                youtube_subscribers=yt_subs,
                youtube_total_views=yt_total,
                youtube_recent_views=yt_recent,
                youtube_comment_count=yt_comments,
            )
            db.add(snapshot)
            created += 1

        db.commit()
        logger.info(
            "Snapshot complete: %d created, %d skipped (already exists)",
            created, skipped,
        )

    except Exception as e:
        logger.error("Snapshot runner failed: %s", e)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    simulate = "--simulate" in sys.argv
    run_snapshot(simulate=simulate)
