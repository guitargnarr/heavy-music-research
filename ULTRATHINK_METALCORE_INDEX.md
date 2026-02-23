# ULTRATHINK: Metalcore Index -- Architecture Reality Check

**Triggered by:** Architectural decision, cross-project methodology transfer, 5+ files affected
**Date:** 2026-02-23
**Scope:** Can the V2 plan actually be built as specified?

---

## 1. THE HARD BLOCKERS

### Monthly Listeners Does Not Exist in the Spotify API

The entire V2 scoring model is built on "monthly listener velocity" as the primary metric in the Trajectory dimension (40% weight). **Spotify does not expose monthly listeners through their Web API.** This is not a rate limit issue -- the field simply does not exist in any endpoint response.

What Spotify DOES provide per artist:
- `followers.total` (integer)
- `popularity` (0-100, proprietary algorithm based on recent play counts)
- `genres` (array, marked deprecated)
- Top tracks with play counts
- Related artists (up to 20)

What this means: The V2 plan's core formula -- "% change in monthly listeners over trailing 90 days, smoothed for release spikes" -- cannot be computed from official API data. The plan must be redesigned around available metrics or accept scraping risk.

**Options:**
1. **Use `popularity` score as the velocity proxy.** Snapshot weekly, compute delta. It reflects recent play behavior and updates continuously. Imperfect (it's a black box algorithm) but official, stable, and defensible. This is the recommended path.
2. **Use `followers.total` delta.** More transparent than popularity but slower-moving -- followers grow incrementally, not in response to single releases. Better as a supporting signal than a primary metric.
3. **Use third-party scrapers (RapidAPI, Chartmetric, Soundcharts).** Monthly listeners available but: TOS risk, reliability risk, cost ($50-500/mo for commercial data providers). Not appropriate for an open-data MVP.
4. **Scrape Spotify artist pages directly.** Monthly listeners are displayed on the web page. Technically possible via headless browser. Violates Spotify TOS. Will get blocked at scale. Not viable.

**Decision:** Redesign Trajectory dimension around `popularity` delta + `followers` delta + YouTube view acceleration. Document the monthly_listeners gap as a published limitation (fits the V2 philosophy perfectly). If a commercial data provider becomes viable later, add it as a premium data source.

### Spotify API Requires Organization Registration (May 2025 Policy)

As of May 2025, new Spotify developer apps require organizational (not individual) registration. Project Lavos LLC qualifies as an organization, so this is solvable but requires:
- Registering the app under Project Lavos LLC
- Maintaining an active Spotify Premium subscription on the owner account
- Development mode limits the app to 5 test users until extended quota mode is approved

**Impact on MVP:** The 5-user development mode limit means the Index cannot be publicly deployed with Spotify OAuth flows. However, the Index's architecture should use **server-side API calls** (client credentials flow), not user-facing OAuth. The data pipeline fetches artist data on a cron schedule and serves pre-computed scores via REST API. Users never authenticate with Spotify directly. This sidesteps the 5-user limit entirely.

### YouTube API Quota is the Tightest Constraint

Default: 10,000 units/day. Search costs 100 units per request.

If tracking 1,000 bands: searching for each band's YouTube channel = 100,000 units = **10x the daily quota.** This is a hard constraint.

**Solution:** Never use YouTube Search in the pipeline. Instead:
1. Seed the database with YouTube channel IDs manually for the initial 50 bands
2. Use the Channels endpoint (1 unit) and Videos endpoint (1 unit) for ongoing data
3. For new bands entering the universe, add YouTube channel IDs as part of the manual curation step
4. Cache all YouTube data for 7 days minimum

With this approach, tracking 1,000 bands costs ~2,000-3,000 units/day (channel stats + recent video stats), well within the 10K quota.

---

## 2. SCORING MODEL REDESIGN

The V2 plan's four dimensions survive, but the specific input metrics must change.

### Trajectory (40% weight) -- REVISED

| Input Metric | Source | Calculation | Replaces |
|-------------|--------|-------------|----------|
| Popularity Velocity | Spotify API | Delta in `popularity` score over trailing 90-day snapshots | Monthly listener velocity |
| Follower Growth Rate | Spotify API | % change in `followers.total` over 90 days | (new, supplementary) |
| YouTube View Acceleration | YouTube Data API | Avg views/day on videos from past 90 days vs. prior catalog | Unchanged |
| Social Follower Growth | Manual / API | Composite % growth across platforms | Unchanged (but fragile) |

The `popularity` score is the best available proxy for listener engagement velocity. It's influenced by recent play counts, which correlates with what monthly listeners measures. It's not identical, but it's the only official, stable, rate-limit-friendly metric that reflects current momentum.

### Industry Signal (30% weight) -- UNCHANGED
All inputs (label attachment, producer attachment, booking agency tier, festival slots, PR coverage) come from MusicBrainz, news scraping, and manual curation. No API constraints affect this dimension.

### Engagement Depth (20% weight) -- PARTIALLY REVISED

| Input Metric | Source | Feasibility |
|-------------|--------|-------------|
| Spotify Save-to-Listen Ratio | Spotify API | NOT AVAILABLE. Spotify does not expose save counts per artist. DROP this metric. |
| YouTube Comment Velocity | YouTube Data API | AVAILABLE. Comments per 1K views. Keep. |
| Social Engagement Rate | IG/TikTok/X | FRAGILE. All three platforms resist scraping. Design for graceful degradation. |
| Reddit/Discord Activity | Reddit API / manual | AVAILABLE but manual. Reddit API has rate limits (100 req/min with OAuth). |
| Tour Attendance Signals | Songkick / Bandsintown | PARTIALLY AVAILABLE. Event data yes, sellout signals no. |

Replace Save-to-Listen with: **Track Popularity Distribution** -- Spotify provides `popularity` per track. A band where multiple tracks have high popularity (wide distribution) has deeper engagement than a band with one viral track and the rest near zero. This is available, computable, and a genuine signal of fanbase depth vs. single-hit dependency.

### Release Positioning (10% weight) -- UNCHANGED
All inputs (cycle phase detection from release dates, studio activity signals) come from MusicBrainz release data and news scraping. No API constraints.

---

## 3. ARCHITECTURE DECISIONS

### Data Pipeline: Python + Cron, Not Real-Time

The V2 plan says "updated weekly." This is correct. Given rate limits, the pipeline should:
1. Run nightly via cron (or scheduled GitHub Action, or Render cron job)
2. Process bands in batches to respect rate limits
3. Store snapshots in PostgreSQL with timestamps for time-series analysis
4. Compute scores from stored snapshots, not live API calls
5. Serve pre-computed scores via REST API (fast, no rate limit concerns for users)

### Database: PostgreSQL on Render (Proven Stack)

The client-cms pattern (`/Users/matthewscott/Projects/client-sites/client-cms/api/main.py`) provides the exact template:
- FastAPI + SQLAlchemy + pg8000
- Render deployment with managed PostgreSQL
- JWT auth (needed for any future premium tier)
- Health check endpoints

Schema needs:
- `artists` table (spotify_id PK, name, genres, current_label, current_manager, etc.)
- `artist_snapshots` table (artist_id FK, snapshot_date, popularity, followers, youtube_subs, youtube_views, etc.)
- `scores` table (artist_id FK, score_date, trajectory, industry_signal, engagement, release_position, composite, grade, segment_tag)
- `producers` table (name, credits array, studio, location)
- `relationships` table (source_type, source_id, target_type, target_id, relationship_type) -- for the network graph
- `news` table (title, source, url, published_date, tagged_entities) -- for the aggregator

### Frontend: React + Vite + TailwindCSS v3

No D3.js code exists in any current project. Two options:
1. **D3.js directly** -- Maximum control, but steep learning curve for force-directed graphs. No existing code to reference.
2. **React Flow or vis-network** -- Higher-level network visualization libraries. Less control but faster to ship.

Recommendation: Use **react-force-graph** (thin React wrapper around d3-force) for the network visualizer. It handles the force simulation, zoom/pan, and node rendering. Use **Recharts** (already familiar from plan) for the momentum dashboard charts.

### Deployment: Vercel (frontend) + Render (backend + db + cron)

This is the proven stack. No reason to deviate.

---

## 4. MVP SCOPE -- WHAT ACTUALLY SHIPS IN 6 WEEKS

Cut to two features, not three. The news aggregator is maintenance-heavy and doesn't leverage the scoring methodology.

**Feature 1: Artist Momentum Dashboard**
- Searchable, filterable table of all bands in the universe
- Columns: name, grade (A-D), segment tag, composite score, sparkline trend, label, producer
- Filter by: grade, segment, genre, label
- Sort by: any scoring dimension
- Click-through to detail page with full breakdown
- Data source: pre-computed scores from Python pipeline

**Feature 2: Network Visualizer**
- Force-directed graph: bands, producers, labels, management companies as nodes
- Click a node to highlight connections
- Color-code by type (band = one color, producer = another, etc.)
- Size nodes by composite score
- Data source: relationships table seeded from the research report's existing data

**Deferred to Phase 2:**
- News aggregator (scraping maintenance burden)
- Touring/festival database (Songkick/Bandsintown rate limits need investigation)
- Predictive signals (requires 90+ days of historical data)
- Exportable reports

---

## 5. COLD START: SEEDING THE UNIVERSE

The research report already contains the seed data:
- **14 bands** in the Artist-Label Map (Section 4) with label, distribution, manager, management co.
- **8 Tier 1 producers** and **13 Tier 2 producers** with full discography links
- **19 A&R contacts** with titles and labels
- **All label-band-producer relationships** documented throughout

Step 1: Extract the 14 mapped bands + their 1-hop network (every band mentioned in the producer discography table, every band on the labels listed). This gets to ~50-80 bands immediately.

Step 2: Use Spotify's Related Artists endpoint (20 related artists per call) to expand from those 50-80 to 200+. Filter by the inclusion criteria (genre tag match, 10K+ listeners, active release).

Step 3: Manual curation pass -- add Louisville scene bands, add bands from the festival lineups listed in Section 7, add any bands from the consumer personas that aren't already captured.

Target: 200 bands by week 3, 500 by month 2. The scoring model becomes statistically meaningful at ~200 (percentile normalization works).

---

## 6. WHAT THE PLAN GETS RIGHT

1. **The flywheel is real.** Index -> content -> relationships -> opportunities -> better Index. This compounding loop is the strategic thesis and it holds up.

2. **Segment tags are the product, not the scores.** "Label-Ready" and "Breakout Candidate" are what make people bookmark the Index. The composite score is supporting evidence. V2 nails this.

3. **Published limitations as conversation starters.** This is the strongest idea in either document. Every limitation invites an insider to fill the gap. The monthly_listeners gap is itself a published limitation now -- "we use Spotify's popularity score as a proxy because monthly listeners are not available via the official API." That transparency builds more credibility than pretending you have data you don't.

4. **Open-data ethos.** Correct for the scene. Metal/hardcore rewards generosity and punishes gatekeeping.

5. **The RMM methodology transfer.** The four-layer architecture (universe, merge, score, limitations) is genuinely domain-agnostic. Applying it to music after proving it in pharmacy analytics is a powerful portfolio story.

---

## 7. EXECUTION ORDER

1. **Day 1-2:** Register Spotify developer app under Project Lavos LLC. Confirm client credentials flow works. Test YouTube Data API quota. Verify Setlist.fm API access.
2. **Day 3-5:** Build database schema. Seed 50 bands from the research report. Write Python pipeline for Spotify + YouTube data collection. First snapshot.
3. **Week 2:** Build scoring engine. Compute first scores. Validate against intuition (does Knocked Loose score higher than a random local band? Does Sleep Token show as "Established Ascender"?). Calibrate weights.
4. **Week 3-4:** Build React frontend -- momentum dashboard with table, filters, detail pages. Connect to API.
5. **Week 5:** Build network visualizer. Seed relationship data from report.
6. **Week 6:** Polish, deploy, expand universe to 200+. Soft launch.

---

## 8. RISKS

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Spotify org registration rejected | Low | Critical | Apply immediately. Project Lavos LLC is a real entity with EIN. |
| YouTube quota insufficient at scale | Medium | High | Cache aggressively. Never use Search endpoint. Manual channel ID seeding. |
| Social scraping breaks | High | Medium | Design scoring to degrade gracefully. Social dimension is 20% weight, not primary. |
| Popularity score doesn't correlate with actual momentum | Medium | High | Validate against known cases (Sleep Token, Knocked Loose trajectory). If correlation is weak, shift to follower growth rate as primary. |
| Cold start scores look arbitrary with <100 bands | Medium | Medium | Don't publish scores until universe reaches 200. Show raw data first, scores second. |
| Spotify deprecates genres/followers fields | Low | Medium | They're already marked deprecated. Build fallback to MusicBrainz genre data. |

---

## DECISION SUMMARY

| Question | Decision | Rationale |
|----------|----------|-----------|
| Monthly listeners? | Use `popularity` delta as proxy | Not available via API. Popularity is the closest official metric. |
| MVP features? | 2 (momentum dashboard + network viz) | News aggregator deferred. Two strong > three mediocre. |
| Backend stack? | FastAPI + pg8000 + PostgreSQL on Render | Proven pattern from client-cms. No reason to deviate. |
| Frontend stack? | React + Vite + TailwindCSS v3 + Recharts + react-force-graph | Familiar tooling. react-force-graph for network viz. |
| Spotify auth flow? | Client credentials (server-side) | Sidesteps 5-user dev mode limit. Users never auth with Spotify. |
| YouTube strategy? | Manual channel ID seeding + aggressive caching | Search endpoint too expensive. Cache 7+ days. |
| Cold start? | Seed from research report + Related Artists expansion | 14 mapped bands -> 50-80 via network -> 200+ via Related Artists API |
| Timeline? | 6 weeks to MVP (2 features) | Realistic with parallel worktrees. |
| Social scraping? | Design for graceful degradation | High probability of breakage. Score redistributes weight when unavailable. |
