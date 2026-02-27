"""Artist endpoints for the Metalcore Index API."""
import json
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Artist, Label, Producer, Relationship, Score
from schemas import (
    DashboardArtist,
    DashboardResponse,
    EventResponse,
    LabelContactInfo,
    ProducerCredit,
    RelatedArtistBrief,
    ScoreResponse,
    SnapshotResponse,
)

router = APIRouter(prefix="/api/artists", tags=["artists"])


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    grade: Optional[str] = Query(None, description="Filter by grade (A, B, C, D)"),
    segment: Optional[str] = Query(None, description="Filter by segment tag"),
    label: Optional[str] = Query(None, description="Filter by label"),
    search: Optional[str] = Query(None, description="Search by name"),
    sort_by: str = Query("composite", description="Sort field"),
    sort_dir: str = Query("desc", description="Sort direction (asc/desc)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Dashboard endpoint: artists with latest scores, filterable and sortable."""
    # Subquery for latest score per artist
    from sqlalchemy import func

    latest_score_date = (
        db.query(Score.artist_id, func.max(Score.score_date).label("max_date"))
        .group_by(Score.artist_id)
        .subquery()
    )

    query = (
        db.query(Artist, Score)
        .outerjoin(
            latest_score_date, Artist.spotify_id == latest_score_date.c.artist_id
        )
        .outerjoin(
            Score,
            (Score.artist_id == Artist.spotify_id)
            & (Score.score_date == latest_score_date.c.max_date),
        )
        .filter(Artist.active.is_(True))
    )

    # Filters
    if grade:
        query = query.filter(Score.grade == grade.upper())
    if segment:
        query = query.filter(Score.segment_tag == segment)
    if label:
        query = query.filter(Artist.current_label.ilike(f"%{label}%"))
    if search:
        query = query.filter(Artist.name.ilike(f"%{search}%"))

    # Count before pagination
    total = query.count()
    universe_size = db.query(Artist).filter(Artist.active.is_(True)).count()

    # Sort
    sort_column = {
        "composite": Score.composite,
        "trajectory": Score.trajectory,
        "industry_signal": Score.industry_signal,
        "engagement": Score.engagement,
        "release_positioning": Score.release_positioning,
        "name": Artist.name,
    }.get(sort_by, Score.composite)

    if sort_dir == "asc":
        query = query.order_by(sort_column.asc().nullslast())
    else:
        query = query.order_by(sort_column.desc().nullslast())

    results = query.offset(offset).limit(limit).all()

    artists = []
    for artist, score in results:
        artists.append(
            DashboardArtist(
                spotify_id=artist.spotify_id,
                name=artist.name,
                image_url=artist.image_url,
                current_label=artist.current_label,
                grade=score.grade if score else None,
                segment_tag=score.segment_tag if score else None,
                composite=score.composite if score else None,
                trajectory=score.trajectory if score else None,
                industry_signal=score.industry_signal if score else None,
                engagement=score.engagement if score else None,
                release_positioning=score.release_positioning if score else None,
            )
        )

    return DashboardResponse(artists=artists, total=total, universe_size=universe_size)


@router.get("/{spotify_id}")
def get_artist(spotify_id: str, db: Session = Depends(get_db)):
    """Full artist detail with snapshot history and score history."""
    artist = db.query(Artist).filter(Artist.spotify_id == spotify_id).first()
    if not artist:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Artist not found")

    genres = json.loads(artist.genres) if artist.genres else []
    snapshots = [
        SnapshotResponse.model_validate(s)
        for s in sorted(artist.snapshots, key=lambda s: s.snapshot_date)
    ]
    scores = [
        ScoreResponse.model_validate(s)
        for s in sorted(artist.scores, key=lambda s: s.score_date)
    ]

    # Upcoming events
    upcoming_events = [
        EventResponse.model_validate(e)
        for e in sorted(artist.events, key=lambda e: e.event_date)
        if e.event_date >= date.today()
    ]

    # Label contact info (via Relationship + Label tables)
    label_contact = None
    if artist.current_label:
        label = db.query(Label).filter(
            Label.name == artist.current_label
        ).first()
        if not label:
            # Try partial match for compound labels like "Epic Records / Nuclear Blast"
            first_label = artist.current_label.split("/")[0].strip()
            label = db.query(Label).filter(
                Label.name == first_label
            ).first()
        if label and (label.key_contact or label.contact_title):
            label_contact = LabelContactInfo(
                label_name=label.name,
                key_contact=label.key_contact,
                contact_title=label.contact_title,
            )

    # Producer credits from relationships
    producers = []
    prod_rels = db.query(Relationship).filter(
        Relationship.source_id == artist.name,
        Relationship.relationship_type == "produced_by",
    ).all()
    for pr in prod_rels:
        prod = db.query(Producer).filter(Producer.name == pr.target_id).first()
        producers.append(ProducerCredit(
            name=pr.target_id,
            studio=prod.studio_name if prod else None,
        ))

    # Related artists via shared_producer
    related_artists = []
    shared_rels = db.query(Relationship).filter(
        (
            (Relationship.source_id == artist.name)
            | (Relationship.target_id == artist.name)
        ),
        Relationship.relationship_type == "shared_producer",
    ).all()
    seen_related = set()
    for sr in shared_rels:
        other_name = sr.target_id if sr.source_id == artist.name else sr.source_id
        if other_name in seen_related:
            continue
        seen_related.add(other_name)
        target_artist = db.query(Artist).filter(Artist.name == other_name).first()
        if target_artist:
            latest = db.query(Score).filter(
                Score.artist_id == target_artist.spotify_id
            ).order_by(Score.score_date.desc()).first()
            related_artists.append(RelatedArtistBrief(
                spotify_id=target_artist.spotify_id,
                name=target_artist.name,
                image_url=target_artist.image_url,
                composite=latest.composite if latest else None,
                grade=latest.grade if latest else None,
            ))

    return {
        "spotify_id": artist.spotify_id,
        "name": artist.name,
        "genres": genres,
        "image_url": artist.image_url,
        "current_label": artist.current_label,
        "current_manager": artist.current_manager,
        "current_management_co": artist.current_management_co,
        "booking_agency": artist.booking_agency,
        "booking_agent": artist.booking_agent,
        "youtube_channel_id": artist.youtube_channel_id,
        "active": artist.active,
        "snapshots": snapshots,
        "scores": scores,
        "upcoming_events": upcoming_events,
        "label_contact": label_contact,
        "producers": producers,
        "related_artists": related_artists,
    }
