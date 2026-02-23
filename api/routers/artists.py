"""Artist endpoints for the Metalcore Index API."""
import json
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Artist, Score
from schemas import (
    DashboardArtist,
    DashboardResponse,
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

    return {
        "spotify_id": artist.spotify_id,
        "name": artist.name,
        "genres": genres,
        "image_url": artist.image_url,
        "current_label": artist.current_label,
        "current_manager": artist.current_manager,
        "current_management_co": artist.current_management_co,
        "booking_agency": artist.booking_agency,
        "youtube_channel_id": artist.youtube_channel_id,
        "active": artist.active,
        "snapshots": snapshots,
        "scores": scores,
    }
