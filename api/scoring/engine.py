"""
Scoring engine for the Metalcore Index.

Computes composite scores from 4 dimensions:
- Trajectory (40%): Spotify popularity delta + follower growth + YouTube acceleration
- Industry Signal (30%): Label tier + producer tier + agency tier + management tier
- Engagement (20%): Track popularity distribution + YouTube comment velocity
- Release Positioning (10%): Cycle phase from release dates

Published limitation: Spotify monthly_listeners is NOT available via the official API.
We use the `popularity` score delta as a proxy.
"""
from .weights import (
    DIMENSION_WEIGHTS,
    LABEL_TIERS,
    PRODUCER_TIERS,
    AGENCY_TIERS,
    MANAGEMENT_TIERS,
    GRADE_THRESHOLDS,
    RELEASE_CYCLE_SCORES,
)


def compute_trajectory(
    current_popularity: int | None,
    previous_popularity: int | None,
    current_followers: int | None,
    previous_followers: int | None,
    youtube_recent_views: int | None,
    youtube_previous_views: int | None,
) -> float:
    """Compute trajectory score (0-100) from available data."""
    scores = []
    weights = []

    # Popularity delta (50% of trajectory)
    if current_popularity is not None and previous_popularity is not None:
        delta = current_popularity - previous_popularity
        # Map delta to 0-100: -20 = 0, 0 = 50, +20 = 100
        pop_score = max(0, min(100, 50 + (delta * 2.5)))
        scores.append(pop_score)
        weights.append(0.50)

    # Follower growth rate (30% of trajectory)
    if current_followers and previous_followers and previous_followers > 0:
        growth_rate = (current_followers - previous_followers) / previous_followers
        # Map growth rate: -10% = 0, 0% = 40, +10% = 80, +25% = 100
        follower_score = max(0, min(100, 40 + (growth_rate * 400)))
        scores.append(follower_score)
        weights.append(0.30)

    # YouTube view acceleration (20% of trajectory)
    if youtube_recent_views is not None and youtube_previous_views is not None:
        if youtube_previous_views > 0:
            accel = (youtube_recent_views - youtube_previous_views) / youtube_previous_views
            yt_score = max(0, min(100, 50 + (accel * 200)))
        else:
            yt_score = 50 if youtube_recent_views > 0 else 0
        scores.append(yt_score)
        weights.append(0.20)

    if not scores:
        return 0.0

    # Weighted average, renormalized if some inputs missing
    total_weight = sum(weights)
    return sum(s * w for s, w in zip(scores, weights)) / total_weight


def compute_industry_signal(
    label_name: str | None,
    producer_name: str | None,
    agency_name: str | None,
    management_name: str | None,
) -> float:
    """Compute industry signal score (0-100) from tier lookups."""
    scores = []
    weights = []

    # Label tier (40%)
    if label_name:
        tier = _fuzzy_lookup(label_name, LABEL_TIERS)
        label_score = {1: 100, 2: 70, 3: 40}.get(tier, 20)
        scores.append(label_score)
        weights.append(0.40)
    else:
        scores.append(10)  # Unsigned
        weights.append(0.40)

    # Producer tier (25%)
    if producer_name:
        tier = _fuzzy_lookup(producer_name, PRODUCER_TIERS)
        prod_score = {1: 100, 2: 70}.get(tier, 30)
        scores.append(prod_score)
        weights.append(0.25)

    # Agency tier (20%)
    if agency_name:
        tier = _fuzzy_lookup(agency_name, AGENCY_TIERS)
        agency_score = {1: 100, 2: 70}.get(tier, 30)
        scores.append(agency_score)
        weights.append(0.20)

    # Management tier (15%)
    if management_name:
        tier = _fuzzy_lookup(management_name, MANAGEMENT_TIERS)
        mgmt_score = {1: 100, 2: 70}.get(tier, 30)
        scores.append(mgmt_score)
        weights.append(0.15)

    if not scores:
        return 0.0

    total_weight = sum(weights)
    return sum(s * w for s, w in zip(scores, weights)) / total_weight


def compute_engagement(
    track_popularity_distribution: list[int] | None,
    youtube_comment_velocity: float | None,
) -> float:
    """
    Compute engagement depth (0-100).
    Track popularity distribution: multiple high-popularity tracks = deeper engagement.
    YouTube comment velocity: comments per 1K views.
    """
    scores = []
    weights = []

    # Track popularity distribution (60%)
    if track_popularity_distribution:
        # Count tracks above various thresholds
        above_50 = sum(1 for p in track_popularity_distribution if p >= 50)
        above_30 = sum(1 for p in track_popularity_distribution if p >= 30)
        avg_popularity = sum(track_popularity_distribution) / len(track_popularity_distribution)

        # Bands with broad popularity across many tracks score higher
        depth_score = min(100, (above_50 * 15) + (above_30 * 5) + avg_popularity)
        scores.append(depth_score)
        weights.append(0.60)

    # YouTube comment velocity (40%)
    if youtube_comment_velocity is not None:
        # Comments per 1K views: 0 = 0, 5 = 50, 15+ = 100
        comment_score = max(0, min(100, youtube_comment_velocity * 6.67))
        scores.append(comment_score)
        weights.append(0.40)

    if not scores:
        return 0.0

    total_weight = sum(weights)
    return sum(s * w for s, w in zip(scores, weights)) / total_weight


def compute_release_positioning(months_since_release: int | None) -> float:
    """Compute release cycle phase score (0-100)."""
    if months_since_release is None:
        return 50.0  # Unknown = mid-cycle assumption

    for (low, high), score in RELEASE_CYCLE_SCORES.items():
        if low <= months_since_release < high:
            return float(score)

    return 20.0


def compute_composite(
    trajectory: float,
    industry_signal: float,
    engagement: float,
    release_positioning: float,
) -> float:
    """Weighted composite score (0-100)."""
    return (
        trajectory * DIMENSION_WEIGHTS["trajectory"]
        + industry_signal * DIMENSION_WEIGHTS["industry_signal"]
        + engagement * DIMENSION_WEIGHTS["engagement"]
        + release_positioning * DIMENSION_WEIGHTS["release_positioning"]
    )


def assign_grade(composite: float) -> str:
    """Map composite score to letter grade."""
    for grade, threshold in sorted(
        GRADE_THRESHOLDS.items(), key=lambda x: x[1], reverse=True
    ):
        if composite >= threshold:
            return grade
    return "D"


def assign_segment_tag(
    composite: float,
    trajectory: float,
    industry_signal: float,
    previous_composite: float | None,
    label_name: str | None,
) -> str:
    """Assign a segment tag based on score patterns."""
    # Breakout Candidate: High trajectory, lower industry signal (not yet signed big)
    if trajectory >= 70 and industry_signal < 50:
        return "Breakout Candidate"

    # Established Ascender: High composite AND rising trajectory
    if composite >= 70 and trajectory >= 65:
        return "Established Ascender"

    # Established Stable: High composite, moderate trajectory
    if composite >= 60 and 40 <= trajectory < 65:
        return "Established Stable"

    # Label-Ready: Good engagement + trajectory, no major label
    if trajectory >= 55 and not label_name:
        return "Label-Ready"

    # Sleeping Giant: Low trajectory but high industry signal
    if trajectory < 35 and industry_signal >= 60:
        return "Sleeping Giant"

    # At Risk: Declining trajectory with previous data
    if previous_composite is not None and composite < previous_composite - 10:
        return "At Risk"

    # Algorithmic Lift: Moderate trajectory spike
    if trajectory >= 60 and composite < 50:
        return "Algorithmic Lift"

    # Default
    if composite >= 40:
        return "Established Stable"
    return "Sleeping Giant"


def _fuzzy_lookup(name: str, lookup: dict[str, int]) -> int | None:
    """Case-insensitive partial match against tier lookup table."""
    name_lower = name.lower().strip()
    for key, tier in lookup.items():
        if key.lower() in name_lower or name_lower in key.lower():
            return tier
    return None
