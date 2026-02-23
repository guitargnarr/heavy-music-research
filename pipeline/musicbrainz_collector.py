"""
MusicBrainz collector for the Metalcore Index pipeline.

Collects release dates for the Release Positioning dimension.
Maps months since last release to cycle phase score.

MusicBrainz API: free, no key needed, 1 req/sec rate limit.
Requires: musicbrainzngs library.
"""
import logging
import time
from dataclasses import dataclass
from datetime import date

logger = logging.getLogger(__name__)


@dataclass
class ReleaseData:
    artist_name: str
    latest_release_title: str | None = None
    latest_release_date: date | None = None
    months_since_release: int | None = None


class MusicBrainzCollector:
    """Collects release date data from MusicBrainz."""

    def __init__(self):
        self.mb = None
        self._init_client()

    def _init_client(self):
        try:
            import musicbrainzngs

            musicbrainzngs.set_useragent(
                "MetalcoreIndex",
                "0.1.0",
                "https://github.com/guitargnarr/heavy-music-research",
            )
            self.mb = musicbrainzngs
            logger.info("MusicBrainz client initialized")
        except ImportError:
            logger.warning(
                "musicbrainzngs not installed. "
                "Run: pip install musicbrainzngs"
            )

    @property
    def is_available(self) -> bool:
        return self.mb is not None

    def get_latest_release(self, artist_name: str) -> ReleaseData | None:
        """Find the most recent album/EP release for an artist."""
        if not self.mb:
            return None

        try:
            # Search for artist
            result = self.mb.search_artists(artist=artist_name, limit=5)
            time.sleep(1.1)  # MusicBrainz rate limit: 1 req/sec

            artists = result.get("artist-list", [])
            if not artists:
                logger.warning("No MusicBrainz results for: %s", artist_name)
                return ReleaseData(artist_name=artist_name)

            # Find best match (exact name preferred)
            mb_artist = None
            for a in artists:
                if a["name"].lower() == artist_name.lower():
                    mb_artist = a
                    break
            if not mb_artist:
                mb_artist = artists[0]

            mb_id = mb_artist["id"]

            # Get release groups (albums + EPs)
            rg_result = self.mb.browse_release_groups(
                artist=mb_id,
                release_type=["album", "ep"],
                limit=10,
            )
            time.sleep(1.1)

            release_groups = rg_result.get("release-group-list", [])
            if not release_groups:
                return ReleaseData(artist_name=artist_name)

            # Find most recent release with a valid date
            latest = None
            latest_date = None
            for rg in release_groups:
                fd = rg.get("first-release-date", "")
                if not fd or len(fd) < 4:
                    continue
                try:
                    if len(fd) == 4:
                        rd = date(int(fd), 1, 1)
                    elif len(fd) == 7:
                        parts = fd.split("-")
                        rd = date(int(parts[0]), int(parts[1]), 1)
                    else:
                        parts = fd.split("-")
                        rd = date(int(parts[0]), int(parts[1]), int(parts[2]))

                    if latest_date is None or rd > latest_date:
                        latest_date = rd
                        latest = rg
                except (ValueError, IndexError):
                    continue

            if not latest or not latest_date:
                return ReleaseData(artist_name=artist_name)

            today = date.today()
            months = (
                (today.year - latest_date.year) * 12
                + today.month - latest_date.month
            )

            return ReleaseData(
                artist_name=artist_name,
                latest_release_title=latest.get("title"),
                latest_release_date=latest_date,
                months_since_release=max(0, months),
            )

        except Exception as e:
            logger.error(
                "Error getting releases for %s: %s", artist_name, e
            )
            return ReleaseData(artist_name=artist_name)

    def collect_batch(self, artist_names: list[str]) -> list[ReleaseData]:
        """Collect release data for multiple artists."""
        results = []
        for i, name in enumerate(artist_names):
            data = self.get_latest_release(name)
            if data:
                results.append(data)
            if (i + 1) % 10 == 0:
                logger.info(
                    "Collected %d/%d release dates", i + 1, len(artist_names)
                )
        return results


def simulate_release_data(artist_name: str) -> ReleaseData:
    """Generate simulated release data for local development."""
    known_releases = {
        "Knocked Loose": ("You Won't Go Before You're Supposed To", 2024, 5),
        "Spiritbox": ("Tsunami Sea", 2025, 1),
        "Sleep Token": ("Even in Arcadia", 2025, 5),
        "Lorna Shore": ("I Feel The Everblack Festering Within Me", 2025, 9),
        "Periphery": ("Periphery V", 2023, 6),
        "Lamb of God": ("New album", 2025, 3),
        "Erra": ("Cure", 2024, 6),
        "Bad Omens": ("THE DEATH OF PEACE OF MIND", 2022, 2),
        "Whitechapel": ("Hymns in Dissonance", 2025, 4),
        "Thrown": ("Excessive Guilt", 2024, 8),
        "Kublai Khan TX": ("Absolute", 2024, 3),
        "Turnstile": ("GLOW ON", 2021, 8),
        "Dayseeker": ("Creature In The Black Night", 2025, 6),
        "Between the Buried and Me": ("The Blue Nowhere", 2025, 2),
        "A Day To Remember": ("Big Ole Album Vol. 1", 2025, 1),
        "Gojira": ("Fortitude", 2021, 4),
        "Trivium": ("In the Court of the Dragon", 2021, 10),
        "Architects": ("The Classic Symptoms of a Broken Spirit", 2022, 11),
        "Bilmuri": ("AMERICAN TRASH", 2023, 7),
        "Born of Osiris": ("Through Shadows", 2025, 3),
    }

    if artist_name in known_releases:
        title, year, month = known_releases[artist_name]
        rel_date = date(year, month, 1)
        today = date.today()
        months = (
            (today.year - rel_date.year) * 12
            + today.month - rel_date.month
        )
        return ReleaseData(
            artist_name=artist_name,
            latest_release_title=title,
            latest_release_date=rel_date,
            months_since_release=max(0, months),
        )

    # Unknown bands: random-ish months since release
    name_hash = sum(ord(c) for c in artist_name)
    months = 3 + (name_hash % 30)
    return ReleaseData(
        artist_name=artist_name,
        months_since_release=months,
    )
