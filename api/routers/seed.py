"""
Seed endpoint: populate production database on first deploy.
Protected by SEED_SECRET env var. Only runs if DB is empty.
"""
import json
import logging
import os
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from database import get_db, Base, engine
from models import (
    Artist, ArtistSnapshot, Score, Producer, Label, Relationship,
)
from scoring.engine import (
    compute_industry_signal,
    compute_engagement,
    compute_release_positioning,
    compute_composite,
    assign_grade,
    assign_segment_tag,
    _fuzzy_lookup,
)
from scoring.weights import PRODUCER_TIERS
from pipeline.spotify_collector import simulate_spotify_data
from pipeline.musicbrainz_collector import simulate_release_data

router = APIRouter(tags=["seed"])
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
)


def _load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path) as f:
        return json.load(f)


def _verify_secret(x_seed_secret: str = Header(...)):
    expected = os.getenv("SEED_SECRET", "")
    if not expected or x_seed_secret != expected:
        raise HTTPException(status_code=403, detail="Invalid seed secret")


@router.post("/api/seed")
def seed_database(
    db: Session = Depends(get_db),
    _auth=Depends(_verify_secret),
):
    """Seed production DB with artists, producers, labels,
    relationships, snapshots, and scores. Only runs if empty."""
    artist_count = db.query(Artist).count()
    if artist_count > 0:
        return {
            "status": "skipped",
            "message": f"DB already has {artist_count} artists",
        }

    Base.metadata.create_all(bind=engine)
    today = date.today()

    # --- Artists ---
    artists_data = _load_json("artists.json")
    matches_path = os.path.join(DATA_DIR, "spotify_matches.json")
    spotify_map = {}
    if os.path.exists(matches_path):
        for m in _load_json("spotify_matches.json"):
            spotify_map[m["name"]] = m

    for a in artists_data:
        match = spotify_map.get(a["name"])
        spotify_id = match["spotify_id"] if match else a["spotify_id"]
        image_url = match.get("image_url") if match else None
        genres = (
            match.get("genres", a.get("genres", []))
            if match else a.get("genres", [])
        )
        db.add(Artist(
            spotify_id=spotify_id,
            name=a["name"],
            genres=json.dumps(genres),
            image_url=image_url,
            current_label=a.get("current_label"),
            current_manager=a.get("current_manager"),
            current_management_co=a.get("current_management_co"),
            booking_agency=a.get("booking_agency"),
            active=True,
        ))
    db.flush()
    logger.info("Seeded %d artists", len(artists_data))

    # --- Producers ---
    for p in _load_json("producers.json"):
        db.add(Producer(
            name=p["name"],
            studio_name=p.get("studio_name"),
            location=p.get("location"),
            credits=json.dumps(p.get("credits", [])),
            tier=p.get("tier"),
            sonic_signature=p.get("sonic_signature"),
        ))
    db.flush()

    # --- Labels ---
    for lbl in _load_json("labels.json"):
        db.add(Label(
            name=lbl["name"],
            parent_company=lbl.get("parent_company"),
            distribution=lbl.get("distribution"),
            key_contact=lbl.get("key_contact"),
            contact_title=lbl.get("contact_title"),
        ))
    db.flush()

    # --- Relationships ---
    for r in _load_json("relationships.json"):
        db.add(Relationship(
            source_type=r["source_type"],
            source_id=r["source_id"],
            target_type=r["target_type"],
            target_id=r["target_id"],
            relationship_type=r["relationship_type"],
        ))
    db.flush()

    # --- Simulated Snapshots ---
    artists = db.query(Artist).filter(Artist.active.is_(True)).all()
    for artist in artists:
        sp_data = simulate_spotify_data(artist.name, artist.spotify_id)
        yt_data = None
        try:
            from pipeline.youtube_collector import simulate_youtube_data
            yt_data = simulate_youtube_data(
                artist.name, artist.youtube_channel_id or ""
            )
        except Exception:
            pass

        db.add(ArtistSnapshot(
            artist_id=artist.spotify_id,
            snapshot_date=today,
            spotify_popularity=sp_data.popularity,
            spotify_followers=sp_data.followers,
            youtube_subscribers=yt_data.subscriber_count if yt_data else None,
            youtube_total_views=yt_data.total_views if yt_data else None,
            youtube_recent_views=(
                yt_data.recent_video_views if yt_data else None
            ),
            youtube_comment_count=(
                yt_data.recent_comment_count if yt_data else None
            ),
        ))
    db.flush()

    # --- Scores ---
    for artist in artists:
        snapshots = (
            db.query(ArtistSnapshot)
            .filter(ArtistSnapshot.artist_id == artist.spotify_id)
            .order_by(ArtistSnapshot.snapshot_date.desc())
            .limit(2)
            .all()
        )
        current_snap = snapshots[0] if snapshots else None

        # Trajectory from popularity baseline
        pop = current_snap.spotify_popularity or 0 if current_snap else 0
        trajectory = 20 + (pop * 0.75)

        # Industry signal
        producer_name = _get_producer(artist.name, db)
        industry_signal = compute_industry_signal(
            label_name=artist.current_label,
            producer_name=producer_name,
            agency_name=artist.booking_agency,
            management_name=artist.current_management_co,
        )

        # Engagement
        sp_sim = simulate_spotify_data(artist.name, artist.spotify_id)
        track_pops = sp_sim.top_track_popularities
        yt_vel = None
        if current_snap and current_snap.youtube_recent_views:
            views = current_snap.youtube_recent_views
            comments = current_snap.youtube_comment_count or 0
            if views > 0:
                yt_vel = (comments / views) * 1000
        engagement = compute_engagement(
            track_popularity_distribution=track_pops,
            youtube_comment_velocity=yt_vel,
        )

        # Release positioning
        rel_data = simulate_release_data(artist.name)
        release_positioning = compute_release_positioning(
            rel_data.months_since_release
        )

        composite = compute_composite(
            trajectory, industry_signal, engagement, release_positioning
        )
        grade = assign_grade(composite)

        # Determine producer tier for segment tagging
        prod_tier = None
        if producer_name:
            prod_tier = _fuzzy_lookup(producer_name, PRODUCER_TIERS)

        segment_tag = assign_segment_tag(
            composite=composite,
            trajectory=trajectory,
            industry_signal=industry_signal,
            previous_composite=None,
            label_name=artist.current_label,
            producer_tier=prod_tier,
        )

        db.add(Score(
            artist_id=artist.spotify_id,
            score_date=today,
            trajectory=round(trajectory, 2),
            industry_signal=round(industry_signal, 2),
            engagement=round(engagement, 2),
            release_positioning=round(release_positioning, 2),
            composite=round(composite, 2),
            grade=grade,
            segment_tag=segment_tag,
        ))
    db.flush()

    db.commit()

    final_counts = {
        "artists": db.query(Artist).count(),
        "producers": db.query(Producer).count(),
        "labels": db.query(Label).count(),
        "relationships": db.query(Relationship).count(),
        "snapshots": db.query(ArtistSnapshot).count(),
        "scores": db.query(Score).count(),
    }
    logger.info("Seed complete: %s", final_counts)

    return {"status": "seeded", "counts": final_counts}


def _get_producer(artist_name: str, db) -> str | None:
    rel = (
        db.query(Relationship)
        .filter(
            Relationship.source_type == "artist",
            Relationship.source_id == artist_name,
            Relationship.relationship_type == "produced_by",
        )
        .first()
    )
    return rel.target_id if rel else None
