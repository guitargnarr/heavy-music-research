#!/usr/bin/env Rscript
# mine_artist_network.R -- Build artist-artist network from:
#   1. Shared producers (artists who share a producer = related)
#   2. Last.fm similar artists API (free, no key restrictions)
# Output: data/mined_artist_network.json, updates to relationships.json via merge
# Usage: Rscript R/mine_artist_network.R [--commit]

source("R/utils.R")
library(purrr)

args <- commandArgs(trailingOnly = TRUE)
commit <- "--commit" %in% args

if (!commit) {
  log_info("DRY RUN -- pass --commit to write changes")
} else {
  log_info("COMMIT MODE -- will write changes to files")
}

# --- Load data ---
artists <- read_json_file("artists.json")
relationships <- read_json_file("relationships.json")
artist_names <- artists$name

log_info("Artists: ", length(artist_names))
log_info("Existing relationships: ", nrow(relationships))

# ============================================================
# PART 1: Shared Producer Network
# ============================================================
cat("\n========== PART 1: SHARED PRODUCER NETWORK ==========\n")

# Get all produced_by relationships
produced_by <- relationships[relationships$relationship_type == "produced_by", ]
log_info("produced_by edges: ", nrow(produced_by))

# Build producer -> artists mapping
producer_artists <- list()
for (i in seq_len(nrow(produced_by))) {
  producer <- produced_by$target_id[i]
  artist <- produced_by$source_id[i]
  if (is.null(producer_artists[[producer]])) {
    producer_artists[[producer]] <- c()
  }
  producer_artists[[producer]] <- unique(c(producer_artists[[producer]], artist))
}

# Find producers who worked with 2+ of our artists
shared_producers <- keep(producer_artists, ~ length(.x) >= 2)
log_info("Producers shared by 2+ artists: ", length(shared_producers))

# Generate artist-artist edges from shared producers
shared_edges <- list()
existing_rel_keys <- paste(
  relationships$source_id,
  relationships$target_id,
  relationships$relationship_type,
  sep = "|"
)

for (prod_name in names(shared_producers)) {
  artists_list <- shared_producers[[prod_name]]
  # Only artists in our dataset
  internal <- artists_list[artists_list %in% artist_names]
  if (length(internal) < 2) next

  # Generate all pairs
  for (i in seq_len(length(internal) - 1)) {
    for (j in (i + 1):length(internal)) {
      a1 <- internal[i]
      a2 <- internal[j]
      # Alphabetical order to avoid duplicates
      pair <- sort(c(a1, a2))

      key_fwd <- paste(pair[1], pair[2], "shared_producer", sep = "|")
      key_rev <- paste(pair[2], pair[1], "shared_producer", sep = "|")

      if (!key_fwd %in% existing_rel_keys && !key_rev %in% existing_rel_keys) {
        shared_edges[[length(shared_edges) + 1]] <- list(
          source_type = "artist",
          source_id = pair[1],
          target_type = "artist",
          target_id = pair[2],
          relationship_type = "shared_producer"
        )
        existing_rel_keys <- c(existing_rel_keys, key_fwd)
      }
    }
  }
}

cat(sprintf("Shared producer edges to add: %d\n", length(shared_edges)))

if (length(shared_edges) > 0) {
  cat("\nShared producer connections:\n")
  for (e in shared_edges) {
    cat(sprintf("  %s <-> %s\n", e$source_id, e$target_id))
  }
}

# ============================================================
# PART 2: Last.fm Similar Artists
# ============================================================
cat("\n========== PART 2: LAST.FM SIMILAR ARTISTS ==========\n")

# Last.fm API -- free, 5 req/sec, API key required but easy to get
# We'll use the public API key approach
LASTFM_API_KEY <- Sys.getenv("LASTFM_API_KEY", "")

lastfm_request <- function(method, params = list()) {
  rate_limit("lastfm", 0.25)  # 4 req/sec conservative

  params$method <- method
  params$api_key <- LASTFM_API_KEY
  params$format <- "json"

  resp <- tryCatch({
    req <- request("https://ws.audioscrobbler.com/2.0/") |>
      req_url_query(!!!params) |>
      req_retry(max_tries = 3, backoff = ~2)
    req_perform(req)
  }, error = function(e) {
    log_error("Last.fm request failed: ", e$message)
    return(NULL)
  })

  if (is.null(resp)) return(NULL)
  status <- resp_status(resp)
  if (status != 200) {
    log_warn("Last.fm returned ", status)
    return(NULL)
  }
  resp_body_json(resp)
}

lastfm_edges <- list()

if (LASTFM_API_KEY == "") {
  log_warn("LASTFM_API_KEY not set -- skipping Last.fm mining")
  log_info("Get a free key at https://www.last.fm/api/account/create")
} else {
  log_info("Mining Last.fm similar artists for ", length(artist_names), " artists")

  for (i in seq_along(artist_names)) {
    name <- artist_names[i]
    log_info(sprintf("  [%d/%d] %s", i, length(artist_names), name))

    result <- lastfm_request("artist.getsimilar", params = list(
      artist = name,
      limit = 20
    ))

    if (is.null(result) || is.null(result$similarartists) ||
        length(result$similarartists$artist) == 0) {
      log_info("    -> 0 similar artists")
      next
    }

    similar <- result$similarartists$artist
    # similar can be a data.frame or list depending on response
    if (is.data.frame(similar)) {
      similar_names <- similar$name
      similar_matches <- similar$match
    } else {
      similar_names <- sapply(similar, function(s) s$name)
      similar_matches <- sapply(similar, function(s) as.numeric(s$match))
    }

    # Only keep artists in our dataset
    internal_count <- 0
    for (j in seq_along(similar_names)) {
      sim_name <- similar_names[j]
      match_score <- as.numeric(similar_matches[j])

      # Check if this similar artist is in our dataset (fuzzy)
      matched_name <- NULL
      for (an in artist_names) {
        if (name_match(sim_name, an)) {
          matched_name <- an
          break
        }
      }

      if (!is.null(matched_name) && matched_name != name) {
        pair <- sort(c(name, matched_name))
        key_fwd <- paste(pair[1], pair[2], "similar_artist", sep = "|")
        key_rev <- paste(pair[2], pair[1], "similar_artist", sep = "|")

        if (!key_fwd %in% existing_rel_keys && !key_rev %in% existing_rel_keys) {
          lastfm_edges[[length(lastfm_edges) + 1]] <- list(
            source_type = "artist",
            source_id = pair[1],
            target_type = "artist",
            target_id = pair[2],
            relationship_type = "similar_artist"
          )
          existing_rel_keys <- c(existing_rel_keys, key_fwd)
          internal_count <- internal_count + 1
        }
      }
    }

    if (internal_count > 0) {
      log_info("    -> ", internal_count, " internal matches")
    }
  }

  log_info("Last.fm similar artist edges: ", length(lastfm_edges))
}

# ============================================================
# SUMMARY
# ============================================================
all_new <- c(shared_edges, lastfm_edges)

cat("\n========== NETWORK SUMMARY ==========\n")
cat(sprintf("Shared producer edges:        %d\n", length(shared_edges)))
cat(sprintf("Last.fm similar artist edges: %d\n", length(lastfm_edges)))
cat(sprintf("Total new edges:              %d\n", length(all_new)))
cat(sprintf("Total relationships after:    %d (was %d)\n",
            nrow(relationships) + length(all_new), nrow(relationships)))
cat("=====================================\n")

# ============================================================
# WRITE
# ============================================================
if (commit && length(all_new) > 0) {
  cat("\n--- WRITING CHANGES ---\n")

  existing_raw <- fromJSON(file.path(DATA_DIR, "relationships.json"))
  all_rels <- c(
    lapply(seq_len(nrow(existing_raw)), function(i) as.list(existing_raw[i, ])),
    all_new
  )

  write_json(all_rels, file.path(DATA_DIR, "relationships.json"),
             pretty = TRUE, auto_unbox = TRUE)
  log_info("Updated relationships.json")

  # Save raw mined data for reference
  write_json(all_new, file.path(DATA_DIR, "mined_artist_network.json"),
             pretty = TRUE, auto_unbox = TRUE)
  log_info("Wrote mined_artist_network.json")

  cat("Done! Data files updated.\n")
} else if (!commit) {
  cat("\nDry run complete. Run with --commit to write changes.\n")
} else {
  cat("\nNo new edges to add.\n")
}
