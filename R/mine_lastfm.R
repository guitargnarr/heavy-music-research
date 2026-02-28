#!/usr/bin/env Rscript
# mine_lastfm.R -- Mine Last.fm for similar artists, listener metrics, and tags
# Requires: LASTFM_API_KEY environment variable
# Free key at: https://www.last.fm/api/account/create
# Output: data/mined_lastfm_metrics.json, data/mined_similar_artists.json, data/expansion_candidates.json

source("R/utils.R")
library(purrr)

# --- Check API key ---
api_key <- Sys.getenv("LASTFM_API_KEY")
if (api_key == "") {
  stop("LASTFM_API_KEY not set. Get a free key at https://www.last.fm/api/account/create")
}

# --- Load artists ---
artists <- read_json_file("artists.json")
log_info("Mining Last.fm for ", nrow(artists), " artists")

# --- Last.fm API helper ---
lastfm_request <- function(method, params = list()) {
  rate_limit("lastfm", 0.25)  # 4 req/sec, under 5/sec limit
  params$method <- method
  params$api_key <- api_key
  params$format <- "json"

  resp <- tryCatch({
    req <- request("https://ws.audioscrobbler.com/2.0/") |>
      req_url_query(!!!params) |>
      req_headers(`User-Agent` = "MetalcoreIndex/1.0 (matthewdscott7@gmail.com)") |>
      req_timeout(30) |>
      req_retry(max_tries = 3, backoff = ~2)
    req_perform(req)
  }, error = function(e) {
    log_error("Last.fm request failed: ", e$message)
    return(NULL)
  })

  if (is.null(resp)) return(NULL)
  if (resp_status(resp) != 200) {
    log_warn("Last.fm returned ", resp_status(resp))
    return(NULL)
  }
  resp_body_json(resp)
}

# --- Mine artist info + similar artists ---
artist_names_lower <- tolower(artists$name)
metrics <- list()
similar_edges <- list()
expansion_counts <- list()  # artists outside our dataset, counted by frequency

for (i in seq_len(nrow(artists))) {
  name <- artists$name[i]
  cat(sprintf("[%d/%d] %s\n", i, nrow(artists), name))

  # 1. Get artist info (listeners, playcount, tags)
  info <- lastfm_request("artist.getinfo", list(artist = name))
  if (is.null(info) || !is.null(info$error)) {
    log_warn("  No info for ", name)
    metrics[[length(metrics) + 1]] <- list(
      name = name, listeners = NA, playcount = NA, tags = list()
    )
  } else {
    a <- info$artist
    tags <- tryCatch({
      sapply(a$tags$tag, function(t) t$name)
    }, error = function(e) character())

    metrics[[length(metrics) + 1]] <- list(
      name = name,
      listeners = as.integer(a$stats$listeners %||% NA),
      playcount = as.integer(a$stats$playcount %||% NA),
      tags = as.list(tags)
    )
    cat(sprintf("  Listeners: %s, Plays: %s\n",
      format(as.integer(a$stats$listeners %||% 0), big.mark = ","),
      format(as.integer(a$stats$playcount %||% 0), big.mark = ",")))
  }

  # 2. Get similar artists
  sim <- lastfm_request("artist.getsimilar", list(artist = name, limit = 25))
  if (is.null(sim) || !is.null(sim$error)) {
    log_warn("  No similar artists for ", name)
    next
  }

  similar_list <- sim$similarartists$artist
  if (is.null(similar_list) || length(similar_list) == 0) next

  for (s in similar_list) {
    target_name <- s$name
    match_score <- as.numeric(s$match %||% 0)
    target_in_dataset <- tolower(target_name) %in% artist_names_lower

    if (target_in_dataset) {
      # Both in our dataset -- create edge
      similar_edges[[length(similar_edges) + 1]] <- list(
        source = name,
        target = target_name,
        match = round(match_score, 4),
        source_in_dataset = TRUE,
        target_in_dataset = TRUE
      )
    } else {
      # Outside our dataset -- count as expansion candidate
      key <- tolower(target_name)
      if (is.null(expansion_counts[[key]])) {
        expansion_counts[[key]] <- list(name = target_name, count = 0, total_match = 0)
      }
      expansion_counts[[key]]$count <- expansion_counts[[key]]$count + 1
      expansion_counts[[key]]$total_match <- expansion_counts[[key]]$total_match + match_score
    }
  }

  internal_matches <- sum(sapply(similar_list, function(s) tolower(s$name) %in% artist_names_lower))
  cat(sprintf("  Similar: %d total, %d in our dataset\n", length(similar_list), internal_matches))
}

# --- Deduplicate similar edges ---
# A->B and B->A are the same edge, keep the one with higher match score
seen_pairs <- list()
deduped_edges <- list()
for (edge in similar_edges) {
  pair_key <- paste(sort(c(tolower(edge$source), tolower(edge$target))), collapse = "|")
  existing <- seen_pairs[[pair_key]]
  if (is.null(existing) || edge$match > existing$match) {
    seen_pairs[[pair_key]] <- edge
  }
}
deduped_edges <- unname(as.list(seen_pairs))

# --- Build expansion candidates (sorted by frequency) ---
expansion <- map(expansion_counts, function(x) {
  list(
    name = x$name,
    recommended_by_count = x$count,
    avg_match = round(x$total_match / x$count, 4)
  )
})
expansion <- expansion[order(-sapply(expansion, function(x) x$recommended_by_count))]
expansion <- head(expansion, 50)  # Top 50 candidates

# --- Summary ---
cat("\n========== LAST.FM MINING SUMMARY ==========\n")
cat(sprintf("Artist metrics collected: %d / %d\n", sum(sapply(metrics, function(m) !is.na(m$listeners))), nrow(artists)))
cat(sprintf("Internal similar-artist edges: %d (deduped from %d)\n", length(deduped_edges), length(similar_edges)))
cat(sprintf("Expansion candidates (outside dataset): %d\n", length(expansion)))

if (length(deduped_edges) > 0) {
  cat("\nTop internal matches:\n")
  sorted <- deduped_edges[order(-sapply(deduped_edges, function(e) e$match))]
  for (e in head(sorted, 15)) {
    cat(sprintf("  %-25s <-> %-25s (%.2f)\n", e$source, e$target, e$match))
  }
}

if (length(expansion) > 0) {
  cat("\nTop expansion candidates (not in our 75):\n")
  for (e in head(expansion, 10)) {
    cat(sprintf("  %-30s recommended by %d artists (avg match: %.2f)\n",
      e$name, e$recommended_by_count, e$avg_match))
  }
}

# --- Save outputs ---
metrics_path <- file.path(DATA_DIR, "mined_lastfm_metrics.json")
write_json(metrics, metrics_path, pretty = TRUE, auto_unbox = TRUE, na = "null")
log_info("Wrote ", metrics_path)

similar_path <- file.path(DATA_DIR, "mined_similar_artists.json")
write_json(deduped_edges, similar_path, pretty = TRUE, auto_unbox = TRUE)
log_info("Wrote ", similar_path)

expansion_path <- file.path(DATA_DIR, "expansion_candidates.json")
write_json(expansion, expansion_path, pretty = TRUE, auto_unbox = TRUE)
log_info("Wrote ", expansion_path)

cat("\n========== LAST.FM MINING COMPLETE ==========\n")
