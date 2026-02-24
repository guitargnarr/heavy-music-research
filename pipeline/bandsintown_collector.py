"""
Bandsintown event collector for the Metalcore Index pipeline.

Collects upcoming tour dates per artist via Bandsintown API v3.
Requires: BANDSINTOWN_APP_ID env var (free, register at artists.bandsintown.com).
Falls back to simulated data when credentials are absent.
"""
import logging
import os
import time
import urllib.parse
from dataclasses import dataclass
from datetime import date, timedelta

logger = logging.getLogger(__name__)


@dataclass
class BandsintownEventData:
    artist_name: str
    event_name: str
    venue_name: str | None
    city: str | None
    region: str | None
    country: str | None
    event_date: date
    event_type: str  # concert, festival
    ticket_url: str | None
    festival_name: str | None
    bandsintown_id: str | None


class BandsintownCollector:
    """Collects upcoming events from Bandsintown API v3."""

    BASE_URL = "https://rest.bandsintown.com"

    def __init__(self):
        self.app_id = os.getenv("BANDSINTOWN_APP_ID", "")

    @property
    def is_available(self) -> bool:
        return bool(self.app_id)

    def get_upcoming_events(self, artist_name: str) -> list[BandsintownEventData]:
        """Get upcoming events for an artist."""
        import requests

        encoded = urllib.parse.quote(artist_name)
        url = f"{self.BASE_URL}/artists/{encoded}/events"
        params = {"app_id": self.app_id, "date": "upcoming"}

        try:
            resp = requests.get(url, params=params, timeout=10)
            time.sleep(0.2)  # Rate limit courtesy

            if resp.status_code != 200:
                logger.warning(
                    "Bandsintown %d for %s", resp.status_code, artist_name
                )
                return []

            data = resp.json()
            if isinstance(data, dict) and "errors" in data:
                return []

            return [self._parse_event(artist_name, e) for e in data]

        except Exception as e:
            logger.error("Bandsintown error for %s: %s", artist_name, e)
            return []

    def _parse_event(
        self, artist_name: str, raw: dict
    ) -> BandsintownEventData:
        venue = raw.get("venue", {})
        dt_str = raw.get("datetime", "")[:10]
        try:
            event_date = date.fromisoformat(dt_str)
        except ValueError:
            event_date = date.today()

        # Detect festival from lineup or title
        lineup = raw.get("lineup", [])
        title = raw.get("title", "") or ""
        is_festival = (
            len(lineup) > 3
            or "festival" in title.lower()
            or "fest" in title.lower()
        )

        return BandsintownEventData(
            artist_name=artist_name,
            event_name=title or f"{artist_name} live",
            venue_name=venue.get("name"),
            city=venue.get("city"),
            region=venue.get("region"),
            country=venue.get("country"),
            event_date=event_date,
            event_type="festival" if is_festival else "concert",
            ticket_url=raw.get("url"),
            festival_name=title if is_festival else None,
            bandsintown_id=str(raw.get("id", "")),
        )

    def collect_batch(
        self, artist_names: list[str]
    ) -> dict[str, list[BandsintownEventData]]:
        """Collect events for all artists. Returns dict keyed by name."""
        results = {}
        for i, name in enumerate(artist_names):
            events = self.get_upcoming_events(name)
            if events:
                results[name] = events

            if (i + 1) % 25 == 0:
                logger.info(
                    "Collected events for %d/%d artists", i + 1, len(artist_names)
                )
                time.sleep(1)  # Batch pause

        return results


# --- Simulated data for local development ---

# Realistic venues for heavy music
_VENUES = [
    ("Mercury Ballroom", "Louisville", "KY", "US"),
    ("The Basement East", "Nashville", "TN", "US"),
    ("House of Blues", "Chicago", "IL", "US"),
    ("The Fillmore", "Philadelphia", "PA", "US"),
    ("Irving Plaza", "New York", "NY", "US"),
    ("The Roxy", "Los Angeles", "CA", "US"),
    ("Marquee Theatre", "Tempe", "AZ", "US"),
    ("The Masquerade", "Atlanta", "GA", "US"),
    ("White Oak Music Hall", "Houston", "TX", "US"),
    ("Summit Music Hall", "Denver", "CO", "US"),
    ("The Palladium", "Worcester", "MA", "US"),
    ("The NorVa", "Norfolk", "VA", "US"),
    ("Ace of Spades", "Sacramento", "CA", "US"),
    ("The Fillmore Silver Spring", "Silver Spring", "MD", "US"),
    ("Jannus Live", "St. Petersburg", "FL", "US"),
    ("Alexandra Palace", "London", None, "GB"),
    ("Columbiahalle", "Berlin", None, "DE"),
    ("Groezrock Festival", "Meerhout", None, "BE"),
    ("Download Festival", "Donington Park", "Derbyshire", "GB"),
    ("Wacken Open Air", "Wacken", "Schleswig-Holstein", "DE"),
]

_FESTIVALS = [
    ("Download Festival", "Donington Park", "Derbyshire", "GB"),
    ("Sonic Temple", "Columbus", "OH", "US"),
    ("Welcome to Rockville", "Daytona Beach", "FL", "US"),
    ("Aftershock Festival", "Sacramento", "CA", "US"),
    ("Blue Ridge Rock Festival", "Alton", "VA", "US"),
    ("Hellfest", "Clisson", "Loire-Atlantique", "FR"),
    ("Wacken Open Air", "Wacken", "Schleswig-Holstein", "DE"),
    ("Heavy Montreal", "Montreal", "QC", "CA"),
    ("Slam Dunk Festival", "Leeds", "West Yorkshire", "GB"),
    ("Impericon Festival", "Leipzig", "Saxony", "DE"),
]


def simulate_bandsintown_events(
    artist_name: str,
) -> list[BandsintownEventData]:
    """Generate deterministic simulated tour dates for local development."""
    name_hash = sum(ord(c) for c in artist_name)

    # Number of upcoming shows (3-10 based on name hash)
    num_shows = 3 + (name_hash % 8)

    # Bigger bands get more shows and festival appearances
    big_bands = {
        "Bring Me the Horizon", "Sleep Token", "Avenged Sevenfold",
        "Lamb of God", "Gojira", "My Chemical Romance", "Trivium",
        "Parkway Drive", "Architects", "Knocked Loose", "Lorna Shore",
        "A Day To Remember", "Halestorm", "Falling in Reverse",
        "Killswitch Engage", "Babymetal", "Motionless In White",
    }
    is_big = artist_name in big_bands
    if is_big:
        num_shows = min(num_shows + 4, 15)

    events = []
    today = date.today()

    for i in range(num_shows):
        # Spread dates over next 6 months
        days_out = 7 + (name_hash * (i + 1) * 7) % 180
        event_date = today + timedelta(days=days_out)

        # Pick venue deterministically
        venue_idx = (name_hash + i * 13) % len(_VENUES)
        venue_name, city, region, country = _VENUES[venue_idx]

        # Some shows are festivals (big bands get more)
        is_festival = (
            (is_big and i % 3 == 0)
            or (not is_big and i == num_shows - 1 and name_hash % 3 == 0)
        )

        if is_festival:
            fest_idx = (name_hash + i) % len(_FESTIVALS)
            fest_name, city, region, country = _FESTIVALS[fest_idx]
            venue_name = fest_name
            event_name = fest_name
        else:
            fest_name = None
            event_name = f"{artist_name} live"

        events.append(BandsintownEventData(
            artist_name=artist_name,
            event_name=event_name,
            venue_name=venue_name,
            city=city,
            region=region,
            country=country,
            event_date=event_date,
            event_type="festival" if is_festival else "concert",
            ticket_url=None,
            festival_name=fest_name,
            bandsintown_id=f"sim_{name_hash}_{i}",
        ))

    # Sort by date
    events.sort(key=lambda e: e.event_date)
    return events
