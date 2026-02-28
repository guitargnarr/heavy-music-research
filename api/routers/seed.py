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

# Import simulators only for initial seed (not rescore)
try:
    from pipeline.spotify_collector import simulate_spotify_data
    from pipeline.musicbrainz_collector import simulate_release_data
except ImportError:
    simulate_spotify_data = None
    simulate_release_data = None

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


@router.post("/api/rescore")
def rescore_all(
    db: Session = Depends(get_db),
    _auth=Depends(_verify_secret),
):
    """Reload all data from JSON files: artists, producers, relationships, scores.
    Uses pre-computed scores from scores.json (built by R/build_scores.R from
    real mined data: Wikipedia pageviews, Deezer fans, Reddit buzz, Kworb streams)."""
    artists = db.query(Artist).all()

    # Refresh artist metadata and insert new artists from data files
    artists_data = _load_json("artists.json")
    name_to_data = {a["name"]: a for a in artists_data}
    existing_names = {a.name for a in artists}
    metadata_updated = 0
    artists_added = 0

    # Update existing artist metadata
    for artist in artists:
        src = name_to_data.get(artist.name)
        if not src:
            continue
        changed = False
        for field in ["current_label", "booking_agency", "current_management_co",
                      "current_manager", "booking_agent"]:
            if src.get(field) and getattr(artist, field, None) != src[field]:
                setattr(artist, field, src[field])
                changed = True
        if changed:
            metadata_updated += 1

    # Insert new artists not yet in DB
    for a in artists_data:
        if a["name"] in existing_names:
            continue
        db.add(Artist(
            spotify_id=a["spotify_id"],
            name=a["name"],
            genres=json.dumps(a.get("genres", [])),
            image_url=None,
            current_label=a.get("current_label"),
            current_manager=a.get("current_manager"),
            current_management_co=a.get("current_management_co"),
            booking_agency=a.get("booking_agency"),
            booking_agent=a.get("booking_agent"),
            active=True,
        ))
        artists_added += 1
    db.flush()

    # Refresh producers from data file
    producers_data = _load_json("producers.json")
    existing_producers = {p.name for p in db.query(Producer).all()}
    producers_added = 0
    for p in producers_data:
        if p["name"] not in existing_producers:
            db.add(Producer(
                name=p["name"],
                studio_name=p.get("studio_name"),
                location=p.get("location"),
                credits=json.dumps(p.get("credits", [])),
                tier=p.get("tier"),
                sonic_signature=p.get("sonic_signature"),
            ))
            producers_added += 1
    db.flush()

    # Refresh relationships from data file
    rels_data = _load_json("relationships.json")
    existing_rels = {
        (r.source_id, r.target_id, r.relationship_type)
        for r in db.query(Relationship).all()
    }
    rels_added = 0
    for r in rels_data:
        key = (r["source_id"], r["target_id"], r["relationship_type"])
        if key not in existing_rels:
            db.add(Relationship(
                source_type=r["source_type"],
                source_id=r["source_id"],
                target_type=r["target_type"],
                target_id=r["target_id"],
                relationship_type=r["relationship_type"],
            ))
            rels_added += 1
    db.flush()

    # Load pre-computed scores from scores.json
    scores_data = _load_json("scores.json")
    scores_by_artist = {s["artist_id"]: s for s in scores_data}
    today = date.today()
    updated = 0

    # Re-query to include newly added artists
    artists = db.query(Artist).all()

    for artist in artists:
        score_src = scores_by_artist.get(artist.spotify_id)
        if not score_src:
            logger.warning("No pre-computed score for %s", artist.name)
            continue

        trajectory = score_src.get("trajectory", 0)
        industry_signal = score_src.get("industry_signal", 0)
        engagement = score_src.get("engagement", 0)
        release_positioning = score_src.get("release_positioning", 0)
        composite = score_src.get("composite", 0)
        grade = score_src.get("grade", "D")
        segment_tag = score_src.get("segment_tag", "Established Stable")

        # Update existing score or create new one
        existing = (
            db.query(Score)
            .filter(Score.artist_id == artist.spotify_id)
            .order_by(Score.score_date.desc())
            .first()
        )
        if existing:
            existing.trajectory = round(trajectory, 2)
            existing.industry_signal = round(industry_signal, 2)
            existing.engagement = round(engagement, 2)
            existing.release_positioning = round(release_positioning, 2)
            existing.composite = round(composite, 2)
            existing.grade = grade
            existing.segment_tag = segment_tag
            existing.score_date = today
        else:
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
        updated += 1

    db.commit()
    logger.info("Rescore complete: %d scored, %d metadata refreshed, %d new artists, %d producers, %d rels",
                updated, metadata_updated, artists_added, producers_added, rels_added)
    return {
        "status": "rescored",
        "artists_updated": updated,
        "metadata_refreshed": metadata_updated,
        "artists_added": artists_added,
        "producers_added": producers_added,
        "relationships_added": rels_added,
    }


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
