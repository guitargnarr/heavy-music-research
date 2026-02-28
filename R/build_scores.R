#!/usr/bin/env Rscript
# build_scores.R -- Generate real scores from mined data
# Reads: mined_wikipedia.json, mined_deezer.json, mined_reddit.json,
#        mined_kworb.json, mined_audiodb.json, artists.json, relationships.json
# Writes: scores.json (replaces heuristic scores with real metrics)
# Usage: Rscript R/build_scores.R [--commit]

source("R/utils.R")
library(purrr)
library(dplyr)
library(tidyr)

args <- commandArgs(trailingOnly = TRUE)
commit <- "--commit" %in% args

if (!commit) {
  log_info("DRY RUN -- pass --commit to write changes")
} else {
  log_info("COMMIT MODE -- will write changes to files")
}

# --- Load all data ---
artists <- read_json_file("artists.json")
relationships <- fromJSON(file.path(DATA_DIR, "relationships.json"), simplifyDataFrame = TRUE)

log_info("Loading mined data...")

# Wikipedia pageviews
wiki <- fromJSON(file.path(DATA_DIR, "mined_wikipedia.json"), simplifyDataFrame = FALSE)
wiki_df <- tibble(
  spotify_id = map_chr(wiki, ~ .x$spotify_id),
  wiki_views_90d = map_dbl(wiki, ~ .x$total_views_90d %||% 0),
  wiki_avg_daily = map_dbl(wiki, ~ .x$avg_daily_views %||% 0),
  wiki_trend_7d = map_dbl(wiki, ~ .x$trend_last_7d %||% 0),
  wiki_trend_30d = map_dbl(wiki, ~ .x$trend_last_30d %||% 0)
)
log_info("Wikipedia: ", nrow(wiki_df), " records")

# Deezer
deezer <- fromJSON(file.path(DATA_DIR, "mined_deezer.json"), simplifyDataFrame = FALSE)
deezer_df <- tibble(
  spotify_id = map_chr(deezer, ~ .x$spotify_id),
  deezer_fans = map_dbl(deezer, ~ as.numeric(.x$nb_fan %||% 0)),
  deezer_avg_rank = map_dbl(deezer, ~ as.numeric(.x$top_track_avg_rank %||% 0)),
  deezer_max_rank = map_dbl(deezer, ~ as.numeric(.x$top_track_max_rank %||% 0)),
  deezer_albums = map_dbl(deezer, ~ as.numeric(.x$album_count %||% 0)),
  deezer_related_internal = map_int(deezer, ~ length(.x$related_in_universe %||% list()))
)
log_info("Deezer: ", nrow(deezer_df), " records")

# Reddit
reddit <- fromJSON(file.path(DATA_DIR, "mined_reddit.json"), simplifyDataFrame = FALSE)
reddit_df <- tibble(
  spotify_id = map_chr(reddit, ~ .x$spotify_id),
  reddit_posts = map_dbl(reddit, ~ as.numeric(.x$total_posts %||% 0)),
  reddit_score = map_dbl(reddit, ~ as.numeric(.x$total_score %||% 0)),
  reddit_comments = map_dbl(reddit, ~ as.numeric(.x$total_comments %||% 0)),
  reddit_posts_90d = map_dbl(reddit, ~ as.numeric(.x$posts_last_90d %||% 0)),
  reddit_posts_30d = map_dbl(reddit, ~ as.numeric(.x$posts_last_30d %||% 0))
)
log_info("Reddit: ", nrow(reddit_df), " records")

# Kworb (only 22/75 have data)
kworb <- fromJSON(file.path(DATA_DIR, "mined_kworb.json"), simplifyDataFrame = FALSE)
kworb_df <- tibble(
  spotify_id = map_chr(kworb, ~ .x$spotify_id),
  kworb_streams = map_dbl(kworb, ~ as.numeric(.x$total_streams %||% 0)),
  kworb_found = map_lgl(kworb, ~ isTRUE(.x$found))
)
log_info("Kworb: ", sum(kworb_df$kworb_found), "/", nrow(kworb_df), " with data")

# AudioDB
audiodb <- fromJSON(file.path(DATA_DIR, "mined_audiodb.json"), simplifyDataFrame = FALSE)
audiodb_df <- tibble(
  spotify_id = map_chr(audiodb, ~ .x$spotify_id),
  formed_year = map_dbl(audiodb, ~ {
    y <- .x$formed_year
    if (is.null(y) || length(y) == 0 || !is.numeric(y) || y < 1980 || y > 2025) NA_real_
    else as.numeric(y)
  }),
  country = map_chr(audiodb, ~ {
    c <- .x$country
    if (is.null(c) || length(c) == 0 || !is.character(c)) NA_character_
    else as.character(c)
  })
)

# Relationships: count per artist
rel_counts <- relationships %>%
  filter(source_type == "artist") %>%
  group_by(source_id) %>%
  summarise(
    rel_count = n(),
    produced_by_count = sum(relationship_type == "produced_by"),
    .groups = "drop"
  )
# Also count as target (for shared_producer etc)
rel_counts_tgt <- relationships %>%
  filter(target_type == "artist") %>%
  group_by(target_id) %>%
  summarise(
    rel_as_target = n(),
    .groups = "drop"
  )

# --- Merge everything ---
merged <- artists %>%
  select(name, spotify_id, current_label, booking_agency, current_management_co) %>%
  left_join(wiki_df, by = "spotify_id") %>%
  left_join(deezer_df, by = "spotify_id") %>%
  left_join(reddit_df, by = "spotify_id") %>%
  left_join(kworb_df, by = "spotify_id") %>%
  left_join(audiodb_df, by = "spotify_id") %>%
  left_join(rel_counts, by = c("name" = "source_id")) %>%
  left_join(rel_counts_tgt, by = c("name" = "target_id"))

# Replace NAs with 0 for numeric columns
merged <- merged %>%
  mutate(across(where(is.numeric), ~ replace_na(.x, 0)))

log_info("Merged data: ", nrow(merged), " artists with ", ncol(merged), " features")

# =============================================
# SCORING MODEL: Percentile-rank within dataset
# =============================================
# Each dimension maps real data to 0-100 via percentile rank
# This ensures scores spread across the full range

pct_rank <- function(x) {
  # Percent rank: 0 = lowest, 100 = highest
  r <- rank(x, ties.method = "average", na.last = "keep")
  round(100 * (r - 1) / (sum(!is.na(x)) - 1), 2)
}

scored <- merged %>%
  mutate(
    # --- POPULARITY (was "engagement") ---
    # Deezer fans (cross-platform) + Kworb streams (Spotify-specific) + Reddit score
    # Kworb only has 22 artists, so weight it less
    popularity_raw = pct_rank(deezer_fans) * 0.45 +
                     pct_rank(kworb_streams) * 0.15 +
                     pct_rank(reddit_score) * 0.25 +
                     pct_rank(wiki_views_90d) * 0.15,
    popularity = pct_rank(popularity_raw),

    # --- CULTURAL BUZZ (was "trajectory") ---
    # Wikipedia trends (recent vs longer term) + Reddit recency
    # If 7d > 30d avg, artist is trending up
    wiki_velocity = ifelse(wiki_trend_30d > 0,
                           (wiki_trend_7d / wiki_trend_30d) * 100,
                           50),
    buzz_raw = pct_rank(wiki_avg_daily) * 0.35 +
               pct_rank(pmin(wiki_velocity, 200)) * 0.25 +
               pct_rank(reddit_posts_90d) * 0.25 +
               pct_rank(reddit_comments) * 0.15,
    trajectory = pct_rank(buzz_raw),

    # --- INDUSTRY SIGNAL (unchanged concept) ---
    # Relationship count + label tier + agency presence + management presence
    has_major_label = as.numeric(current_label %in% c(
      "RCA Records", "Century Media", "Epic Records", "Columbia Records",
      "Roadrunner Records", "Spinefarm Records", "Rise Records",
      "Nuclear Blast", "Fueled by Ramen", "Warner Records",
      "Capitol Records", "Atlantic Records", "InsideOutMusic"
    )),
    has_strong_indie = as.numeric(current_label %in% c(
      "Pure Noise Records", "Sumerian Records", "Epitaph Records",
      "UNFD", "Metal Blade Records", "Fearless Records", "SharpTone Records",
      "Solid State Records", "MNRK Music Group", "Arising Empire",
      "Blue Grape Music", "Better Noise Music", "Fantasy Records",
      "Hopeless Records", "Solid State"
    )),
    has_top_agency = as.numeric(booking_agency %in% c(
      "Wasserman", "UTA", "CAA", "United Talent Agency"
    )),
    has_management = as.numeric(!is.na(current_management_co) & current_management_co != ""),
    label_score = has_major_label * 100 + has_strong_indie * 70 + (!has_major_label & !has_strong_indie) * 20,
    industry_raw = label_score * 0.35 +
                   pct_rank(rel_count + rel_as_target) * 0.25 +
                   has_top_agency * 100 * 0.20 +
                   has_management * 100 * 0.10 +
                   pct_rank(produced_by_count) * 0.10,
    industry_signal = pct_rank(industry_raw),

    # --- ENGAGEMENT DEPTH (was "release_positioning") ---
    # Track popularity spread (Deezer rank) + Reddit engagement ratio + related artists
    engagement_ratio = ifelse(reddit_posts > 0,
                              reddit_comments / reddit_posts,
                              0),
    engagement_raw = pct_rank(deezer_avg_rank) * 0.35 +
                     pct_rank(deezer_albums) * 0.15 +
                     pct_rank(engagement_ratio) * 0.25 +
                     pct_rank(deezer_related_internal) * 0.25,
    engagement = pct_rank(engagement_raw),

    # --- COMPOSITE ---
    # 35% trajectory + 25% industry + 25% popularity + 15% engagement
    composite = trajectory * 0.35 +
                industry_signal * 0.25 +
                popularity * 0.25 +
                engagement * 0.15
  )

# --- Grade + Segment ---
scored <- scored %>%
  mutate(
    grade = case_when(
      composite >= 75 ~ "A",
      composite >= 50 ~ "B",
      composite >= 25 ~ "C",
      TRUE ~ "D"
    ),
    segment_tag = case_when(
      # Breakout: High trajectory, lower industry (underground buzz)
      trajectory >= 70 & industry_signal < 50 ~ "Breakout Candidate",
      # Established Ascender: High composite AND high trajectory
      composite >= 65 & trajectory >= 60 ~ "Established Ascender",
      # Producer Bump: lots of producer connections
      produced_by_count >= 3 & industry_signal >= 60 & composite < 65 ~ "Producer Bump",
      # Established Stable: Solid all-around
      composite >= 45 & trajectory >= 30 & trajectory < 60 ~ "Established Stable",
      # Algorithmic Lift: High popularity but weak industry
      popularity >= 60 & industry_signal < 35 ~ "Algorithmic Lift",
      # Sleeping Giant: Strong industry backing, low current buzz
      industry_signal >= 60 & trajectory < 35 ~ "Sleeping Giant",
      # Default
      composite >= 30 ~ "Established Stable",
      TRUE ~ "Sleeping Giant"
    )
  )

# --- Output scores.json ---
today <- format(Sys.Date(), "%Y-%m-%d")

scores_list <- pmap(scored, function(spotify_id, name, trajectory, industry_signal,
                                      engagement, popularity, composite,
                                      grade, segment_tag, ...) {
  list(
    artist_id = spotify_id,
    score_date = today,
    trajectory = round(trajectory, 2),
    industry_signal = round(industry_signal, 2),
    engagement = round(engagement, 2),
    release_positioning = round(popularity, 2),  # Map popularity to the RP slot in the UI
    composite = round(composite, 2),
    grade = grade,
    segment_tag = segment_tag
  )
})

# --- Summary ---
cat("\n========== SCORING SUMMARY ==========\n")
cat(sprintf("Artists scored: %d\n", nrow(scored)))
cat(sprintf("Score date: %s\n", today))
cat("\nGrade distribution:\n")
grade_tbl <- table(scored$grade)
for (g in names(sort(grade_tbl, decreasing = TRUE))) {
  cat(sprintf("  %s: %d\n", g, grade_tbl[[g]]))
}
cat("\nSegment distribution:\n")
seg_tbl <- table(scored$segment_tag)
for (s in names(sort(seg_tbl, decreasing = TRUE))) {
  cat(sprintf("  %-25s %d\n", s, seg_tbl[[s]]))
}

cat("\nTop 15 by composite:\n")
top <- scored %>% arrange(desc(composite)) %>% head(15)
for (i in seq_len(nrow(top))) {
  r <- top[i, ]
  cat(sprintf("  %2d. %-30s %5.1f  (%s) [%s]\n",
              i, r$name, r$composite, r$grade, r$segment_tag))
}

cat("\nBottom 5 by composite:\n")
bot <- scored %>% arrange(composite) %>% head(5)
for (i in seq_len(nrow(bot))) {
  r <- bot[i, ]
  cat(sprintf("      %-30s %5.1f  (%s)\n", r$name, r$composite, r$grade))
}

cat("\nDimension ranges:\n")
cat(sprintf("  Trajectory:      %.1f - %.1f (mean %.1f)\n",
            min(scored$trajectory), max(scored$trajectory), mean(scored$trajectory)))
cat(sprintf("  Industry Signal: %.1f - %.1f (mean %.1f)\n",
            min(scored$industry_signal), max(scored$industry_signal), mean(scored$industry_signal)))
cat(sprintf("  Engagement:      %.1f - %.1f (mean %.1f)\n",
            min(scored$engagement), max(scored$engagement), mean(scored$engagement)))
cat(sprintf("  Popularity:      %.1f - %.1f (mean %.1f)\n",
            min(scored$popularity), max(scored$popularity), mean(scored$popularity)))
cat(sprintf("  Composite:       %.1f - %.1f (mean %.1f)\n",
            min(scored$composite), max(scored$composite), mean(scored$composite)))
cat("=====================================\n")

# --- Deezer similar_to relationships ---
new_rels <- list()
existing_rel_keys <- paste(
  relationships$source_id,
  relationships$target_id,
  relationships$relationship_type,
  sep = "|"
)

for (d in deezer) {
  if (!isTRUE(d$found)) next
  artist_name <- d$name
  related <- d$related_in_universe
  if (is.null(related) || length(related) == 0) next

  for (rel_name in related) {
    # Deduplicate (check both directions)
    key1 <- paste(artist_name, rel_name, "similar_to", sep = "|")
    key2 <- paste(rel_name, artist_name, "similar_to", sep = "|")
    if (!key1 %in% existing_rel_keys && !key2 %in% existing_rel_keys) {
      new_rels[[length(new_rels) + 1]] <- list(
        source_type = "artist",
        source_id = artist_name,
        target_type = "artist",
        target_id = rel_name,
        relationship_type = "similar_to"
      )
      existing_rel_keys <- c(existing_rel_keys, key1)
    }
  }
}
cat(sprintf("\nNew similar_to relationships from Deezer: %d\n", length(new_rels)))

# --- Write ---
if (commit) {
  # Write scores
  write_json_file(scores_list, "scores.json", backup = TRUE)
  log_info("Wrote scores.json with ", length(scores_list), " scores")

  # Merge new relationships
  if (length(new_rels) > 0) {
    existing_raw <- fromJSON(file.path(DATA_DIR, "relationships.json"), simplifyDataFrame = FALSE)
    all_rels <- c(existing_raw, new_rels)
    bak <- file.path(DATA_DIR, "relationships.json.bak")
    file.copy(file.path(DATA_DIR, "relationships.json"), bak, overwrite = TRUE)
    write_json(all_rels, file.path(DATA_DIR, "relationships.json"),
               pretty = TRUE, auto_unbox = TRUE)
    log_info("Updated relationships.json (+", length(new_rels), " similar_to edges)")
  }

  # Enrich artists.json with AudioDB metadata
  enriched_count <- 0
  artists_raw <- fromJSON(file.path(DATA_DIR, "artists.json"), simplifyDataFrame = FALSE)
  for (i in seq_along(artists_raw)) {
    adb <- keep(audiodb, ~ .x$spotify_id == artists_raw[[i]]$spotify_id && isTRUE(.x$found))
    if (length(adb) > 0) {
      a <- adb[[1]]
      if (!is.null(a$country) && is.character(a$country) && a$country != "" &&
          is.null(artists_raw[[i]]$country)) {
        artists_raw[[i]]$country <- a$country
        enriched_count <- enriched_count + 1
      }
      if (!is.null(a$formed_year) && is.numeric(a$formed_year) && a$formed_year > 1980 &&
          is.null(artists_raw[[i]]$formed_year)) {
        artists_raw[[i]]$formed_year <- a$formed_year
      }
      if (!is.null(a$website) && is.character(a$website) && a$website != "" &&
          is.null(artists_raw[[i]]$website)) {
        artists_raw[[i]]$website <- a$website
      }
    }
  }
  if (enriched_count > 0) {
    bak <- file.path(DATA_DIR, "artists.json.bak")
    file.copy(file.path(DATA_DIR, "artists.json"), bak, overwrite = TRUE)
    write_json(artists_raw, file.path(DATA_DIR, "artists.json"),
               pretty = TRUE, auto_unbox = TRUE)
    log_info("Enriched artists.json with AudioDB metadata (", enriched_count, " artists)")
  }

  cat("\nDone! Files updated. Next: push to GitHub and deploy.\n")
} else {
  cat("\nDry run complete. Run with --commit to write changes.\n")
}
