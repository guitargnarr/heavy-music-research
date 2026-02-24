"""
Tier lookup tables and scoring weights for the Metalcore Index.
Populated from the heavy-music-industry-landscape-2026.md research report.
"""

# --- Dimension Weights ---
DIMENSION_WEIGHTS = {
    "trajectory": 0.40,
    "industry_signal": 0.30,
    "engagement": 0.20,
    "release_positioning": 0.10,
}

# --- Trajectory Sub-Weights ---
TRAJECTORY_WEIGHTS = {
    "popularity_delta": 0.50,
    "follower_growth": 0.30,
    "youtube_acceleration": 0.20,
}

# --- Industry Signal Sub-Weights ---
INDUSTRY_SIGNAL_WEIGHTS = {
    "label_tier": 0.40,
    "producer_tier": 0.25,
    "agency_tier": 0.20,
    "management_tier": 0.15,
}

# --- Label Tiers (from Section 3: Corporate Label Ecosystem) ---
# Tier 1: Major-affiliated or major-distributed with proven breakout track record
# Tier 2: Strong independent with distribution deal
# Tier 3: Independent / self-released
LABEL_TIERS: dict[str, int] = {
    # Major-affiliated (Tier 1)
    "RCA Records": 1,
    "Century Media": 1,
    "Epic Records": 1,
    "Columbia Records": 1,
    "Roadrunner Records": 1,
    "Spinefarm Records": 1,
    "Rise Records": 1,
    "Nuclear Blast": 1,
    "Fueled by Ramen": 1,
    "InsideOutMusic": 1,  # Sony Music prog label
    "Warner Records": 1,
    "Capitol Records": 1,
    "Atlantic Records": 1,
    # Strong independent (Tier 2)
    "Pure Noise Records": 2,
    "Sumerian Records": 2,
    "Epitaph Records": 2,
    "UNFD": 2,
    "Metal Blade Records": 2,
    "Fearless Records": 2,
    "SharpTone Records": 2,
    "Solid State": 2,
    "MNRK Music Group": 2,
    "Arising Empire": 2,
    "Equal Vision": 2,
    # Independent / self-released (Tier 3)
    "Closed Casket Activities": 3,
    "3DOT Recordings": 3,
    "Pale Chord": 2,  # Imprint but Rise/BMG distributed
    "Blue Grape Music": 2,  # Ex-Roadrunner execs, ADA/Warner distributed
    "Solid State Records": 2,  # Alias for Solid State
    "Better Noise Music": 2,
    "Fantasy Records": 2,  # Concord distributed
    "Hopeless Records": 2,
    # Independent / small (Tier 3)
    "Thriller Records": 3,
    "Out of Line Music": 3,
    "Cleopatra Records": 3,
    "Anger Music Group": 3,
}

# --- Producer Tiers (from Section 8: Producers & Engineers) ---
# Tier 1: A-list producers from the report
# Tier 2: Scene architects from the report
PRODUCER_TIERS: dict[str, int] = {
    # Tier 1: A-List
    "Drew Fulk": 1,
    "Will Putney": 1,
    "Daniel Braunstein": 1,
    "Josh Schroeder": 1,
    "Carson Slovak & Grant McFarland": 1,
    "Josh Wilbur": 1,
    "Carl Bown": 1,
    "Adam Getgood": 1,
    # Tier 2: Scene Architects
    "Randy LeBoeuf": 2,
    "Andrew Wade": 2,
    "Kurt Ballou": 2,
    "Jamie King": 2,
    "Mark Lewis": 2,
    "Taylor Larson": 2,
    "Zakk Cervini": 2,
    "Buster Odeholm": 2,
    "Misha Mansoor": 2,
    "Matt Goldman": 2,
    "Adam Dutkiewicz": 2,
    "Taylor Young": 2,
}

# --- Agency Tiers (from Section 6: Booking Agencies) ---
# Tier 1: Big 4 agencies
# Tier 2: Specialized agencies
AGENCY_TIERS: dict[str, int] = {
    "Wasserman": 1,
    "UTA": 1,
    "CAA": 1,
    "IAG": 2,
    "Avocado Booking": 2,
    "Heavy Talent": 2,
    "District 19": 2,
    "Distilled Entertainment": 2,
}

# --- Management Tiers (from Section 5: Management Companies) ---
# Tier 1: Power management with proven arena-level acts
# Tier 2: Established with solid roster
MANAGEMENT_TIERS: dict[str, int] = {
    "5B Artists + Media": 1,
    "Culture Wave": 1,
    "Fly South Music Group": 1,
    "Future History Management": 1,
    "Raw Power Management": 1,
    "Outerloop Group": 2,
    "10th Street Entertainment": 2,
    "Alternate Side": 2,
    "BravoArtist": 2,
    "Intromental Management": 2,
    "Velvet Hammer": 1,  # A7X, major-tier management
    "Opera Ghost Management": 2,
    "Destroy All Lines": 2,  # AU/NZ powerhouse
    "Big Noise": 2,
    "5B Artist Management": 1,  # Alias for 5B Artists + Media
}

# --- Grade Thresholds ---
GRADE_THRESHOLDS = {
    "A": 80,
    "B": 60,
    "C": 40,
    "D": 0,
}

# --- Segment Tag Definitions ---
SEGMENT_TAGS = [
    "Breakout Candidate",
    "Established Ascender",
    "Established Stable",
    "Label-Ready",
    "Producer Bump",
    "At Risk",  # internal only
    "Sleeping Giant",
    "Algorithmic Lift",
]

# --- Release Cycle Phase Scoring ---
# Months since last release -> score (0-100)
RELEASE_CYCLE_SCORES = {
    (0, 3): 100,    # Just released: peak cycle
    (3, 6): 85,     # Post-release touring
    (6, 12): 65,    # Mid-cycle
    (12, 18): 50,   # Late cycle
    (18, 24): 35,   # Overdue
    (24, 999): 20,  # Dormant
}
