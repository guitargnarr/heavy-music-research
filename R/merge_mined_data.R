#!/usr/bin/env Rscript
# merge_mined_data.R -- Merge all mined data into seed JSON files
# Reads: data/mined_producers.json, mined_wikidata.json, mined_similar_artists.json,
#        mined_setlists.json, mined_lastfm_metrics.json
# Updates: data/producers.json, data/relationships.json, data/events.json (new)
# Usage: Rscript R/merge_mined_data.R [--commit]
# Default: dry-run (shows changes without writing)

source("R/utils.R")
library(purrr)
library(stringr)

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

# Get existing relationship keys for dedup
existing_rel_keys <- paste(
  existing_relationships$source_id,
  existing_relationships$target_id,
  existing_relationships$relationship_type,
  sep = "|"
)

# Get existing producer names
existing_prod_names <- tolower(existing_producers$name)

new_producers <- list()
new_relationships <- list()
new_events <- list()

# ============================
# SECTION 1: Producer Mining
# ============================
mined_path <- file.path(DATA_DIR, "mined_producers.json")
if (file.exists(mined_path)) {
  mined_producers <- fromJSON(mined_path)
  log_info("Processing mined producers: ", nrow(mined_producers), " records")

  for (i in seq_len(nrow(mined_producers))) {
    row <- mined_producers[i, ]
    artist_name <- row$artist_name

    # Process producer field
    if (!is.null(row$producer) && !is.na(row$producer) && row$producer != "") {
      prod_names <- trimws(unlist(strsplit(row$producer, ",")))

      for (pname in prod_names) {
        pname_clean <- gsub("\\s*\\(\\d+\\)$", "", trimws(pname))
        if (nchar(pname_clean) < 3) next
        if (name_match(pname_clean, artist_name)) next
        # Skip band name fragments
        if (tolower(pname_clean) %in% c("invent", "animate", "saosin")) next
        artist_words <- tolower(unlist(strsplit(artist_name, "\\s+")))
        if (tolower(pname_clean) %in% artist_words && nchar(pname_clean) < 8) next

        # Add to producers list if new
        if (!tolower(pname_clean) %in% existing_prod_names &&
            !tolower(pname_clean) %in% tolower(sapply(new_producers, function(p) p$name))) {
          new_producers[[length(new_producers) + 1]] <- list(
            name = pname_clean,
            credits = list(artist_name)
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

    # Process mixer field as produced_by too (mix engineer is credited as producer in network)
    if (!is.null(row$mixer) && !is.na(row$mixer) && row$mixer != "") {
      mixer_names <- trimws(unlist(strsplit(row$mixer, ",")))
      for (mname in mixer_names) {
        mname_clean <- gsub("\\s*\\(\\d+\\)$", "", trimws(mname))
        if (nchar(mname_clean) < 3) next
        if (name_match(mname_clean, artist_name)) next

        if (!tolower(mname_clean) %in% existing_prod_names &&
            !tolower(mname_clean) %in% tolower(sapply(new_producers, function(p) p$name))) {
          new_producers[[length(new_producers) + 1]] <- list(
            name = mname_clean,
            credits = list(artist_name)
          )
        }

        rel_key <- paste(artist_name, mname_clean, "produced_by", sep = "|")
        if (!rel_key %in% existing_rel_keys) {
          new_relationships[[length(new_relationships) + 1]] <- list(
            source_type = "artist",
            source_id = artist_name,
            target_type = "producer",
            target_id = mname_clean,
            relationship_type = "produced_by"
          )
          existing_rel_keys <- c(existing_rel_keys, rel_key)
        }
      }
    }
  }
} else {
  log_info("No mined_producers.json found, skipping producer merge")
}

# ============================
# SECTION 2: Similar Artists (Last.fm)
# ============================
similar_path <- file.path(DATA_DIR, "mined_similar_artists.json")
similar_count <- 0
if (file.exists(similar_path)) {
  similar_edges <- fromJSON(similar_path, simplifyDataFrame = FALSE)
  log_info("Processing similar artist edges: ", length(similar_edges))

  for (edge in similar_edges) {
    if (!edge$target_in_dataset) next
    if (edge$match < 0.3) next  # Only strong matches

    # Normalize names to match our dataset
    source_name <- edge$source
    target_name <- edge$target

    # Check both directions
    rel_key <- paste(source_name, target_name, "similar_artist", sep = "|")
    rev_key <- paste(target_name, source_name, "similar_artist", sep = "|")
    if (!rel_key %in% existing_rel_keys && !rev_key %in% existing_rel_keys) {
      new_relationships[[length(new_relationships) + 1]] <- list(
        source_type = "artist",
        source_id = source_name,
        target_type = "artist",
        target_id = target_name,
        relationship_type = "similar_artist"
      )
      existing_rel_keys <- c(existing_rel_keys, rel_key)
      similar_count <- similar_count + 1
    }
  }
  log_info("New similar_artist edges: ", similar_count)
} else {
  log_info("No mined_similar_artists.json found, skipping similar artists")
}

# ============================
# SECTION 3: Shared Producer Recompute
# ============================
# Build full produced_by map (existing + new)
produced_by_map <- list()  # producer -> list of artists

# From existing relationships
for (i in seq_len(nrow(existing_relationships))) {
  rel <- existing_relationships[i, ]
  if (rel$relationship_type == "produced_by") {
    prod <- rel$target_id
    art <- rel$source_id
    if (is.null(produced_by_map[[prod]])) produced_by_map[[prod]] <- character()
    produced_by_map[[prod]] <- unique(c(produced_by_map[[prod]], art))
  }
}

# From new relationships
for (rel in new_relationships) {
  if (rel$relationship_type == "produced_by") {
    prod <- rel$target_id
    art <- rel$source_id
    if (is.null(produced_by_map[[prod]])) produced_by_map[[prod]] <- character()
    produced_by_map[[prod]] <- unique(c(produced_by_map[[prod]], art))
  }
}

# Generate shared_producer edges for producers with 2+ artists
shared_count <- 0
for (prod in names(produced_by_map)) {
  arts <- produced_by_map[[prod]]
  if (length(arts) < 2) next

  for (j in 1:(length(arts) - 1)) {
    for (k in (j + 1):length(arts)) {
      rel_key <- paste(arts[j], arts[k], "shared_producer", sep = "|")
      rev_key <- paste(arts[k], arts[j], "shared_producer", sep = "|")
      if (!rel_key %in% existing_rel_keys && !rev_key %in% existing_rel_keys) {
        new_relationships[[length(new_relationships) + 1]] <- list(
          source_type = "artist",
          source_id = arts[j],
          target_type = "artist",
          target_id = arts[k],
          relationship_type = "shared_producer"
        )
        existing_rel_keys <- c(existing_rel_keys, rel_key)
        shared_count <- shared_count + 1
      }
    }
  }
}
log_info("New shared_producer edges: ", shared_count)

# ============================
# SECTION 4: Setlist.fm Events
# ============================
setlist_path <- file.path(DATA_DIR, "mined_setlists.json")
if (file.exists(setlist_path)) {
  setlist_data <- fromJSON(setlist_path, simplifyDataFrame = FALSE)
  if (!is.null(setlist_data$events)) {
    log_info("Processing setlist events: ", length(setlist_data$events))

    # Map artist names to spotify_ids
    name_to_id <- setNames(artists$spotify_id, artists$name)

    for (event in setlist_data$events) {
      artist_id <- name_to_id[[event$artist]]
      if (is.null(artist_id)) next

      new_events[[length(new_events) + 1]] <- list(
        artist_id = artist_id,
        event_name = event$tour_name,
        venue_name = event$venue_name,
        city = event$city,
        region = event$state,
        country = event$country,
        event_date = event$event_date,
        festival_name = event$festival_name,
        ticket_url = NULL,
        source = "setlistfm"
      )
    }
    log_info("Events to add: ", length(new_events))
  }
} else {
  log_info("No mined_setlists.json found, skipping events")
}

# ============================
# SECTION 5: Wikidata Discrepancy Report
# ============================
wiki_path <- file.path(DATA_DIR, "mined_wikidata.json")
if (file.exists(wiki_path)) {
  wiki_data <- fromJSON(wiki_path, simplifyDataFrame = FALSE)
  log_info("Wikidata: ", wiki_data$matched, " matched, ",
           length(wiki_data$not_found), " not found, ",
           length(wiki_data$discrepancies), " discrepancies")

  if (length(wiki_data$discrepancies) > 0) {
    cat("\n--- WIKIDATA LABEL DISCREPANCIES (review manually) ---\n")
    for (d in wiki_data$discrepancies) {
      cat(sprintf("  %-25s Ours: %-30s Wiki: %s\n",
          d$artist, d$our_value, d$wikidata_value))
    }
    cat("(Note: Wikidata often has historical labels; our data = current label)\n")
  }
}

# ============================
# SUMMARY
# ============================
cat("\n========== MERGE SUMMARY ==========\n")

# Count new relationships by type
rel_types <- sapply(new_relationships, function(r) r$relationship_type)
type_counts <- table(rel_types)
cat("New relationships by type:\n")
for (t in names(type_counts)) {
  cat(sprintf("  %-20s %d\n", t, type_counts[t]))
}

cat(sprintf("\nNew producers:                     %d\n", length(new_producers)))
cat(sprintf("Total new relationships:           %d\n", length(new_relationships)))
cat(sprintf("New events:                        %d\n", length(new_events)))
cat(sprintf("\nTotal producers after merge:        %d (was %d)\n",
            nrow(existing_producers) + length(new_producers), nrow(existing_producers)))
cat(sprintf("Total relationships after merge:    %d (was %d)\n",
            nrow(existing_relationships) + length(new_relationships),
            nrow(existing_relationships)))
cat("===================================\n")

if (length(new_producers) > 0) {
  cat("\nNew producers:\n")
  for (p in new_producers) {
    cat(sprintf("  %-30s  credits: %s\n", p$name,
                paste(unlist(p$credits), collapse = ", ")))
  }
}

# --- Write if commit mode ---
if (commit) {
  cat("\n--- WRITING CHANGES ---\n")

  # Merge producers
  if (length(new_producers) > 0) {
    new_prods_list <- lapply(new_producers, function(p) {
      list(
        name = p$name,
        studio_name = NA,
        location = NA,
        credits = unlist(p$credits),
        tier = NA,
        sonic_signature = NA
      )
    })

    existing_raw <- fromJSON(file.path(DATA_DIR, "producers.json"), simplifyDataFrame = FALSE)
    all_producers <- c(existing_raw, new_prods_list)

    bak <- file.path(DATA_DIR, "producers.json.bak")
    file.copy(file.path(DATA_DIR, "producers.json"), bak, overwrite = TRUE)

    write_json(all_producers, file.path(DATA_DIR, "producers.json"),
               pretty = TRUE, auto_unbox = TRUE, na = "null")
    log_info("Updated producers.json (+", length(new_producers), " producers)")
  }

  # Merge relationships
  if (length(new_relationships) > 0) {
    existing_raw <- fromJSON(file.path(DATA_DIR, "relationships.json"), simplifyDataFrame = FALSE)
    all_rels <- c(existing_raw, new_relationships)

    bak <- file.path(DATA_DIR, "relationships.json.bak")
    file.copy(file.path(DATA_DIR, "relationships.json"), bak, overwrite = TRUE)

    write_json(all_rels, file.path(DATA_DIR, "relationships.json"),
               pretty = TRUE, auto_unbox = TRUE)
    log_info("Updated relationships.json (+", length(new_relationships), " relationships)")
  }

  # Write events if any
  if (length(new_events) > 0) {
    events_path <- file.path(DATA_DIR, "events.json")
    write_json(new_events, events_path, pretty = TRUE, auto_unbox = TRUE, na = "null")
    log_info("Wrote events.json (", length(new_events), " events)")
  }

  cat("\nDone! Files updated.\n")
  cat("Next: push to GitHub and deploy.\n")
} else {
  cat("\nDry run complete. Run with --commit to write changes.\n")
}
