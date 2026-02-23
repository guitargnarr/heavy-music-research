"""
Spotify data collector for the Metalcore Index pipeline.

Uses client credentials flow (server-side, no user OAuth).
Collects per artist:
- popularity (0-100)
- followers total
- top tracks with individual popularity scores (for engagement depth)
- genres
- image URL
- related artists (for universe expansion)

Requires: SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET env vars.
Falls back to simulated data when credentials are absent.
"""
import logging
import os
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SpotifyArtistData:
    spotify_id: str
    name: str
    popularity: int = 0
    followers: int = 0
    genres: list[str] = field(default_factory=list)
    image_url: str | None = None
    top_track_popularities: list[int] = field(default_factory=list)
    related_artist_ids: list[str] = field(default_factory=list)


class SpotifyCollector:
    """Collects artist data from Spotify API."""

    def __init__(self):
        self.sp = None
        self._init_client()

    def _init_client(self):
        client_id = os.getenv("SPOTIPY_CLIENT_ID")
        client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")

        if not client_id or not client_secret:
            logger.warning(
                "Spotify credentials not set. "
                "Set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET."
            )
            return

        try:
            import spotipy
            from spotipy.oauth2 import SpotifyClientCredentials

            self.sp = spotipy.Spotify(
                auth_manager=SpotifyClientCredentials(
                    client_id=client_id,
                    client_secret=client_secret,
                )
            )
            logger.info("Spotify client initialized (client credentials flow)")
        except ImportError:
            logger.warning("spotipy not installed. Run: pip install spotipy")
        except Exception as e:
            logger.error("Failed to init Spotify client: %s", e)

    @property
    def is_available(self) -> bool:
        return self.sp is not None

    def collect_artist(self, spotify_id: str) -> SpotifyArtistData | None:
        """Collect full data for one artist by Spotify ID."""
        if not self.sp:
            return None

        try:
            artist = self.sp.artist(spotify_id)
            time.sleep(0.05)  # Rate limit courtesy

            # Top tracks for engagement depth scoring
            top_tracks = self.sp.artist_top_tracks(spotify_id, country="US")
            track_popularities = [
                t["popularity"] for t in top_tracks.get("tracks", [])
            ]
            time.sleep(0.05)

            return SpotifyArtistData(
                spotify_id=spotify_id,
                name=artist["name"],
                popularity=artist["popularity"],
                followers=artist["followers"]["total"],
                genres=artist.get("genres", []),
                image_url=(
                    artist["images"][0]["url"] if artist.get("images") else None
                ),
                top_track_popularities=track_popularities,
            )

        except Exception as e:
            logger.error("Error collecting %s: %s", spotify_id, e)
            return None

    def collect_related_artists(
        self, spotify_id: str
    ) -> list[dict[str, str]]:
        """Get related artists for universe expansion."""
        if not self.sp:
            return []

        try:
            result = self.sp.artist_related_artists(spotify_id)
            time.sleep(0.05)
            return [
                {"id": a["id"], "name": a["name"]}
                for a in result.get("artists", [])
            ]
        except Exception as e:
            logger.error("Error getting related for %s: %s", spotify_id, e)
            return []

    def collect_batch(
        self, spotify_ids: list[str]
    ) -> list[SpotifyArtistData]:
        """Collect data for multiple artists."""
        results = []
        for i, sid in enumerate(spotify_ids):
            if sid.startswith("placeholder_"):
                logger.debug("Skipping placeholder ID: %s", sid)
                continue

            data = self.collect_artist(sid)
            if data:
                results.append(data)

            if (i + 1) % 50 == 0:
                logger.info("Collected %d/%d artists", i + 1, len(spotify_ids))
                time.sleep(1)  # Batch pause

        return results


def simulate_spotify_data(
    artist_name: str, spotify_id: str
) -> SpotifyArtistData:
    """
    Generate simulated Spotify data for local development.
    Uses deterministic values based on artist name hash for consistency.
    """
    name_hash = sum(ord(c) for c in artist_name)

    # Known bands get realistic-ish values
    known_popularity = {
        "Sleep Token": 78,
        "Knocked Loose": 62,
        "Spiritbox": 65,
        "Lorna Shore": 63,
        "Lamb of God": 68,
        "Periphery": 55,
        "Bad Omens": 70,
        "Turnstile": 66,
        "Gojira": 67,
        "Trivium": 63,
        "Bring Me the Horizon": 80,
        "Architects": 64,
        "A Day To Remember": 67,
        "Motionless In White": 66,
        "Ice Nine Kills": 64,
        "Dayseeker": 58,
        "Bilmuri": 52,
        "Erra": 50,
        "Whitechapel": 51,
        "Born of Osiris": 48,
        "Kublai Khan TX": 47,
        "Thrown": 45,
        "Underoath": 55,
    }

    known_followers = {
        "Sleep Token": 2800000,
        "Knocked Loose": 520000,
        "Spiritbox": 680000,
        "Lorna Shore": 750000,
        "Lamb of God": 2100000,
        "Periphery": 450000,
        "Bad Omens": 1200000,
        "Turnstile": 850000,
        "Gojira": 1500000,
        "Trivium": 1100000,
        "Bring Me the Horizon": 5500000,
        "Architects": 900000,
        "A Day To Remember": 2200000,
        "Motionless In White": 1000000,
        "Ice Nine Kills": 800000,
    }

    pop = known_popularity.get(artist_name, 30 + (name_hash % 40))
    followers = known_followers.get(
        artist_name, 10000 + (name_hash * 137) % 500000
    )

    # Simulate top track popularities (10 tracks)
    base_track_pop = max(10, pop - 15)
    track_pops = [
        min(100, base_track_pop + (i * 3) % 25)
        for i in range(10)
    ]
    track_pops.sort(reverse=True)

    return SpotifyArtistData(
        spotify_id=spotify_id,
        name=artist_name,
        popularity=pop,
        followers=followers,
        top_track_popularities=track_pops,
    )
