#!/usr/bin/env Rscript
# merge_mined_data.R -- Merge mined data into seed JSON files
# Reads: data/mined_producers.json (and data/mined_spotify_network.json if exists)
# Updates: data/producers.json, data/relationships.json
# Usage: Rscript R/merge_mined_data.R [--commit]
# Default: dry-run (shows changes without writing)

source("R/utils.R")
library(purrr)

args <- commandArgs(trailingOnly = TRUE)
commit <- "--commit" %in% args

if (!commit) {
  log_info("DRY RUN -- pass --commit to write changes")
} else {
  log_info("COMMIT MODE -- will write changes to files")
}

# --- Load existing data ---
existing_producers <- read_json_file("producers.json")
existing_relationships <- read_json_file("relationships.json")
artists <- read_json_file("artists.json")

log_info("Existing: ", nrow(existing_producers), " producers, ",
         nrow(existing_relationships), " relationships, ",
         nrow(artists), " artists")

# --- Load mined producer data ---
mined_path <- file.path(DATA_DIR, "mined_producers.json")
if (!file.exists(mined_path)) {
  stop("mined_producers.json not found. Run mine_producers.R first.")
}
mined_producers <- fromJSON(mined_path)
log_info("Mined producer records: ", nrow(mined_producers))

# --- Extract unique producers from mined data ---
# Parse producer names (comma-separated) and create individual entries
new_producers <- list()
new_relationships <- list()

# Get existing producer names for dedup
existing_prod_names <- tolower(existing_producers$name)
# Get existing relationship keys for dedup
existing_rel_keys <- paste(
  existing_relationships$source_id,
  existing_relationships$target_id,
  existing_relationships$relationship_type,
  sep = "|"
)

for (i in seq_len(nrow(mined_producers))) {
  row <- mined_producers[i, ]
  artist_name <- row$artist_name

  # Process producer field
  if (!is.null(row$producer) && !is.na(row$producer) && row$producer != "") {
    prod_names <- trimws(unlist(strsplit(row$producer, ",")))

    for (pname in prod_names) {
      # Skip numbering artifacts like "(2)" or "(3)"
      pname_clean <- gsub("\\s*\\(\\d+\\)$", "", trimws(pname))
      if (nchar(pname_clean) < 3) next
      # Skip the band name itself (self-produced) -- fuzzy check
      if (name_match(pname_clean, artist_name)) next
      # Skip partial band names (e.g., "Invent" from "Invent, Animate")
      if (tolower(pname_clean) %in% c("invent", "animate", "saosin")) next
      # Skip band members self-producing (check if the name IS the artist name)
      # Band names as producers are fine (e.g., "Lamb Of God" producing themselves is still noise)
      artist_words <- tolower(unlist(strsplit(artist_name, "\\s+")))
      if (tolower(pname_clean) %in% artist_words && nchar(pname_clean) < 8) next

      # Add to producers list if new
      if (!tolower(pname_clean) %in% existing_prod_names &&
          !tolower(pname_clean) %in% tolower(sapply(new_producers, function(p) p$name))) {
        new_producers[[length(new_producers) + 1]] <- list(
          name = pname_clean,
          studio_name = NA,
          location = NA,
          credits = list(artist_name),
          tier = NA,
          sonic_signature = NA
        )
      } else {
        # Update credits for existing new producer
        for (j in seq_along(new_producers)) {
          if (tolower(new_producers[[j]]$name) == tolower(pname_clean)) {
            if (!artist_name %in% new_producers[[j]]$credits) {
              new_producers[[j]]$credits <- c(new_producers[[j]]$credits, list(artist_name))
            }
            break
          }
        }
      }

      # Add produced_by relationship if new
      rel_key <- paste(artist_name, pname_clean, "produced_by", sep = "|")
      if (!rel_key %in% existing_rel_keys) {
        new_relationships[[length(new_relationships) + 1]] <- list(
          source_type = "artist",
          source_id = artist_name,
          target_type = "producer",
          target_id = pname_clean,
          relationship_type = "produced_by"
        )
        existing_rel_keys <- c(existing_rel_keys, rel_key)
      }
    }
  }

  # Process mixer field (add as relationships too)
  if (!is.null(row$mixer) && !is.na(row$mixer) && row$mixer != "") {
    mixer_names <- trimws(unlist(strsplit(row$mixer, ",")))
    for (mname in mixer_names) {
      mname_clean <- gsub("\\s*\\(\\d+\\)$", "", trimws(mname))
      if (nchar(mname_clean) < 3) next
      if (name_match(mname_clean, artist_name)) next

      # Add mixer as producer if not already there
      if (!tolower(mname_clean) %in% existing_prod_names &&
          !tolower(mname_clean) %in% tolower(sapply(new_producers, function(p) p$name))) {
        new_producers[[length(new_producers) + 1]] <- list(
          name = mname_clean,
          studio_name = NA,
          location = NA,
          credits = list(artist_name),
          tier = NA,
          sonic_signature = paste0("Mixer (", artist_name, ")")
        )
      }
    }
  }
}

# --- Check for Spotify network data ---
spotify_net_path <- file.path(DATA_DIR, "mined_spotify_network.json")
spotify_relationships <- list()
if (file.exists(spotify_net_path)) {
  log_info("Found mined_spotify_network.json, processing...")
  spotify_edges <- fromJSON(spotify_net_path)
  artist_names <- artists$name

  # Only internal edges (both artists in our dataset)
  for (i in seq_len(nrow(spotify_edges))) {
    edge <- spotify_edges[i, ]
    if (edge$source %in% artist_names && edge$target %in% artist_names) {
      rel_key <- paste(edge$source, edge$target, "related_artist", sep = "|")
      rev_key <- paste(edge$target, edge$source, "related_artist", sep = "|")
      if (!rel_key %in% existing_rel_keys && !rev_key %in% existing_rel_keys) {
        spotify_relationships[[length(spotify_relationships) + 1]] <- list(
          source_type = "artist",
          source_id = edge$source,
          target_type = "artist",
          target_id = edge$target,
          relationship_type = "related_artist"
        )
        existing_rel_keys <- c(existing_rel_keys, rel_key)
      }
    }
  }
  log_info("Spotify internal edges to add: ", length(spotify_relationships))
} else {
  log_info("No mined_spotify_network.json found, skipping Spotify data")
}

# --- Summary ---
cat("\n========== MERGE SUMMARY ==========\n")
cat(sprintf("New producers to add:              %d\n", length(new_producers)))
cat(sprintf("New produced_by relationships:     %d\n", length(new_relationships)))
cat(sprintf("New related_artist relationships:  %d\n", length(spotify_relationships)))
cat(sprintf("\nTotal producers after merge:        %d (was %d)\n",
            nrow(existing_producers) + length(new_producers), nrow(existing_producers)))
cat(sprintf("Total relationships after merge:    %d (was %d)\n",
            nrow(existing_relationships) + length(new_relationships) + length(spotify_relationships),
            nrow(existing_relationships)))
cat("===================================\n")

if (length(new_producers) > 0) {
  cat("\nNew producers:\n")
  for (p in new_producers) {
    cat(sprintf("  %-30s  credits: %s\n", p$name,
                paste(unlist(p$credits), collapse = ", ")))
  }
}

if (length(new_relationships) > 0) {
  cat("\nNew produced_by relationships:\n")
  for (r in new_relationships) {
    cat(sprintf("  %s -> %s\n", r$source_id, r$target_id))
  }
}

# --- Write if commit mode ---
if (commit) {
  cat("\n--- WRITING CHANGES ---\n")

  # Merge producers
  if (length(new_producers) > 0) {
    # Convert new_producers to data frame format matching existing
    new_prods_df <- tibble(
      name = sapply(new_producers, function(p) p$name),
      studio_name = sapply(new_producers, function(p) p$studio_name %||% NA_character_),
      location = sapply(new_producers, function(p) p$location %||% NA_character_),
      credits = lapply(new_producers, function(p) unlist(p$credits)),
      tier = sapply(new_producers, function(p) p$tier %||% NA_integer_),
      sonic_signature = sapply(new_producers, function(p) p$sonic_signature %||% NA_character_)
    )

    # Read raw JSON, append, write
    existing_raw <- fromJSON(file.path(DATA_DIR, "producers.json"))
    # Convert to list of lists for clean JSON
    all_producers <- c(
      lapply(seq_len(nrow(existing_raw)), function(i) as.list(existing_raw[i, ])),
      lapply(seq_len(nrow(new_prods_df)), function(i) {
        row <- as.list(new_prods_df[i, ])
        # Ensure credits is a vector
        row$credits <- unlist(row$credits)
        # Remove NAs for cleaner JSON
        row <- row[!sapply(row, function(x) length(x) == 1 && is.na(x))]
        row
      })
    )

    write_json(all_producers, file.path(DATA_DIR, "producers.json"),
               pretty = TRUE, auto_unbox = TRUE, na = "null")
    log_info("Updated producers.json")
  }

  # Merge relationships
  all_new_rels <- c(new_relationships, spotify_relationships)
  if (length(all_new_rels) > 0) {
    existing_raw <- fromJSON(file.path(DATA_DIR, "relationships.json"))
    all_rels <- c(
      lapply(seq_len(nrow(existing_raw)), function(i) as.list(existing_raw[i, ])),
      all_new_rels
    )

    write_json(all_rels, file.path(DATA_DIR, "relationships.json"),
               pretty = TRUE, auto_unbox = TRUE)
    log_info("Updated relationships.json")
  }

  cat("\nDone! Data files updated.\n")
  cat("Next: re-seed the database with:\n")
  cat("  curl -X POST https://metalcore-index-api.onrender.com/api/seed -H 'X-Seed-Secret: metalcore-seed-2026'\n")
} else {
  cat("\nDry run complete. Run with --commit to write changes.\n")
}
