"""Event endpoints for the Metalcore Index API."""
import logging
import os
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Artist, Event
from schemas import EventResponse, FestivalSummary

router = APIRouter(prefix="/api/events", tags=["events"])
logger = logging.getLogger(__name__)


@router.get("/artist/{spotify_id}", response_model=list[EventResponse])
def get_artist_events(spotify_id: str, db: Session = Depends(get_db)):
    """Get upcoming events for a specific artist."""
    events = (
        db.query(Event)
        .filter(Event.artist_id == spotify_id, Event.event_date >= date.today())
        .order_by(Event.event_date.asc())
        .all()
    )
    return events


@router.get("/upcoming", response_model=list[EventResponse])
def get_upcoming_events(
    days: int = Query(90, ge=1, le=365),
    artist: Optional[str] = Query(None, description="Filter by artist name"),
    festival_only: bool = Query(False),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get all upcoming events, optionally filtered."""
    cutoff = date.today() + timedelta(days=days)
    query = (
        db.query(Event)
        .filter(Event.event_date >= date.today(), Event.event_date <= cutoff)
    )

    if artist:
        query = query.join(Artist).filter(Artist.name.ilike(f"%{artist}%"))

    if festival_only:
        query = query.filter(Event.festival_name.isnot(None))

    events = query.order_by(Event.event_date.asc()).limit(limit).all()
    return events


@router.get("/festivals", response_model=list[FestivalSummary])
def get_festivals(db: Session = Depends(get_db)):
    """Get upcoming festival appearances grouped by festival name."""
    events = (
        db.query(Event, Artist.name)
        .join(Artist, Event.artist_id == Artist.spotify_id)
        .filter(
            Event.festival_name.isnot(None),
            Event.event_date >= date.today(),
        )
        .order_by(Event.event_date.asc())
        .all()
    )

    # Group by festival name
    festivals: dict[str, dict] = {}
    for event, artist_name in events:
        key = event.festival_name
        if key not in festivals:
            festivals[key] = {
                "festival_name": key,
                "start_date": event.event_date,
                "end_date": event.event_date,
                "location": ", ".join(
                    p for p in [event.city, event.region, event.country] if p
                ),
                "artists": [],
            }
        fest = festivals[key]
        if event.event_date < fest["start_date"]:
            fest["start_date"] = event.event_date
        if event.event_date > fest["end_date"]:
            fest["end_date"] = event.event_date
        if artist_name not in fest["artists"]:
            fest["artists"].append(artist_name)

    # Sort by number of artists (most popular festivals first)
    result = sorted(festivals.values(), key=lambda f: -len(f["artists"]))
    return [FestivalSummary(**f) for f in result]


def _verify_secret(x_seed_secret: str = Header(...)):
    expected = os.getenv("SEED_SECRET", "")
    if not expected or x_seed_secret != expected:
        raise HTTPException(status_code=403, detail="Invalid seed secret")


@router.post("/refresh")
def refresh_events(
    db: Session = Depends(get_db),
    _auth=Depends(_verify_secret),
):
    """Collect fresh event data. Uses real APIs if available, simulated otherwise."""
    import traceback

    try:
        from pipeline.bandsintown_collector import (
            BandsintownCollector,
            simulate_bandsintown_events,
        )

        collector = BandsintownCollector()
        artists = db.query(Artist).filter(Artist.active.is_(True)).all()

        # Clear future events (keep historical)
        db.query(Event).filter(
            Event.event_date >= date.today()
        ).delete(synchronize_session="fetch")
        db.flush()

        total_events = 0
        errors = []
        for artist in artists:
            try:
                if collector.is_available:
                    raw_events = collector.get_upcoming_events(artist.name)
                else:
                    raw_events = simulate_bandsintown_events(artist.name)

                for e in raw_events:
                    db.add(Event(
                        artist_id=artist.spotify_id,
                        event_name=e.event_name,
                        venue_name=e.venue_name,
                        city=e.city,
                        region=e.region,
                        country=e.country,
                        event_date=e.event_date,
                        event_type=e.event_type,
                        bandsintown_id=e.bandsintown_id,
                        ticket_url=e.ticket_url,
                        festival_name=e.festival_name,
                    ))
                    total_events += 1
            except Exception as exc:
                db.rollback()
                errors.append(f"{artist.name}: {exc}")
                logger.error("Event error for %s: %s", artist.name, exc)

        db.commit()
        logger.info("Refreshed events: %d events for %d artists", total_events, len(artists))
        return {
            "status": "refreshed",
            "artists_processed": len(artists),
            "events_added": total_events,
            "source": "bandsintown" if collector.is_available else "simulated",
            "errors": errors[:10] if errors else [],
        }
    except Exception as exc:
        tb = traceback.format_exc()
        logger.error("Refresh failed: %s\n%s", exc, tb)
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")
