"""
Score runner: computes scores from stored snapshots.

Reads the latest + previous snapshots, computes all 4 scoring dimensions,
assigns grades and segment tags, and stores in the scores table.

Usage:
  cd api && source .venv/bin/activate
  python -m pipeline.score_runner [--simulate]
"""
import logging
import os
import sys
from datetime import date

# Add project paths
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "api"))
sys.path.insert(0, project_root)

from database import Base, engine, SessionLocal  # noqa: E402
from models import Artist, ArtistSnapshot, Score  # noqa: E402
from scoring.engine import (  # noqa: E402
    compute_trajectory,
    compute_industry_signal,
    compute_engagement,
    compute_release_positioning,
    compute_composite,
    assign_grade,
    assign_segment_tag,
)
from pipeline.spotify_collector import simulate_spotify_data  # noqa: E402
from pipeline.musicbrainz_collector import simulate_release_data  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_scores(simulate: bool = False):
    """
    Compute scores for all active artists.

    Uses the two most recent snapshots for delta calculations.
    When simulate=True, generates simulated supplemental data
    (track popularities, release dates) that isn't in snapshots.
    """
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    today = date.today()

    try:
        artists = db.query(Artist).filter(Artist.active.is_(True)).all()
        logger.info("Scoring %d active artists", len(artists))

        created = 0
        skipped = 0

        for artist in artists:
            # Check if score already exists for today
            existing = (
                db.query(Score)
                .filter(
                    Score.artist_id == artist.spotify_id,
                    Score.score_date == today,
                )
                .first()
            )
            if existing:
                skipped += 1
                continue

            # Get two most recent snapshots for delta computation
            snapshots = (
                db.query(ArtistSnapshot)
                .filter(ArtistSnapshot.artist_id == artist.spotify_id)
                .order_by(ArtistSnapshot.snapshot_date.desc())
                .limit(2)
                .all()
            )

            current_snap = snapshots[0] if snapshots else None
            previous_snap = snapshots[1] if len(snapshots) > 1 else None

            # --- Trajectory (40%) ---
            trajectory = compute_trajectory(
                current_popularity=(
                    current_snap.spotify_popularity if current_snap else None
                ),
                previous_popularity=(
                    previous_snap.spotify_popularity if previous_snap else None
                ),
                current_followers=(
                    current_snap.spotify_followers if current_snap else None
                ),
                previous_followers=(
                    previous_snap.spotify_followers if previous_snap else None
                ),
                youtube_recent_views=(
                    current_snap.youtube_recent_views if current_snap else None
                ),
                youtube_previous_views=(
                    previous_snap.youtube_recent_views
                    if previous_snap else None
                ),
            )

            # First snapshot with no previous: use popularity as baseline
            if current_snap and not previous_snap:
                pop = current_snap.spotify_popularity or 0
                # Map raw popularity to trajectory: 0=20, 50=57.5, 80=80
                trajectory = 20 + (pop * 0.75)

            # --- Industry Signal (30%) ---
            # Get producer from relationships
            producer_name = _get_producer_name(artist.name, db)

            industry_signal = compute_industry_signal(
                label_name=artist.current_label,
                producer_name=producer_name,
                agency_name=artist.booking_agency,
                management_name=artist.current_management_co,
            )

            # --- Engagement (20%) ---
            track_pops = None
            yt_comment_velocity = None

            if simulate:
                sp_sim = simulate_spotify_data(
                    artist.name, artist.spotify_id
                )
                track_pops = sp_sim.top_track_popularities

            if current_snap and current_snap.youtube_recent_views:
                views = current_snap.youtube_recent_views
                comments = current_snap.youtube_comment_count or 0
                if views > 0:
                    yt_comment_velocity = (comments / views) * 1000

            engagement = compute_engagement(
                track_popularity_distribution=track_pops,
                youtube_comment_velocity=yt_comment_velocity,
            )

            # --- Release Positioning (10%) ---
            months_since = None
            if simulate:
                rel_data = simulate_release_data(artist.name)
                months_since = rel_data.months_since_release

            release_positioning = compute_release_positioning(months_since)

            # --- Composite ---
            composite = compute_composite(
                trajectory, industry_signal, engagement, release_positioning
            )
            grade = assign_grade(composite)

            # Previous composite for segment tag
            prev_score = (
                db.query(Score)
                .filter(Score.artist_id == artist.spotify_id)
                .order_by(Score.score_date.desc())
                .first()
            )
            prev_composite = prev_score.composite if prev_score else None

            segment_tag = assign_segment_tag(
                composite=composite,
                trajectory=trajectory,
                industry_signal=industry_signal,
                previous_composite=prev_composite,
                label_name=artist.current_label,
            )

            score = Score(
                artist_id=artist.spotify_id,
                score_date=today,
                trajectory=round(trajectory, 2),
                industry_signal=round(industry_signal, 2),
                engagement=round(engagement, 2),
                release_positioning=round(release_positioning, 2),
                composite=round(composite, 2),
                grade=grade,
                segment_tag=segment_tag,
            )
            db.add(score)
            created += 1

            logger.debug(
                "%s: T=%.0f IS=%.0f E=%.0f RP=%.0f -> %.0f (%s) [%s]",
                artist.name, trajectory, industry_signal, engagement,
                release_positioning, composite, grade, segment_tag,
            )

        db.commit()
        logger.info(
            "Scoring complete: %d created, %d skipped", created, skipped
        )

        # Print top 10 by composite
        top_scores = (
            db.query(Score, Artist)
            .join(Artist, Score.artist_id == Artist.spotify_id)
            .filter(Score.score_date == today)
            .order_by(Score.composite.desc())
            .limit(10)
            .all()
        )

        if top_scores:
            logger.info("\n=== Top 10 by Composite ===")
            for score, art in top_scores:
                logger.info(
                    "  %s: %.1f (%s) [%s] -- T=%.0f IS=%.0f E=%.0f RP=%.0f",
                    art.name, score.composite, score.grade,
                    score.segment_tag, score.trajectory,
                    score.industry_signal, score.engagement,
                    score.release_positioning,
                )

    except Exception as e:
        logger.error("Score runner failed: %s", e)
        db.rollback()
        raise
    finally:
        db.close()


def _get_producer_name(artist_name: str, db) -> str | None:
    """Look up producer from relationships table."""
    from models import Relationship

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


if __name__ == "__main__":
    simulate = "--simulate" in sys.argv
    run_scores(simulate=simulate)
