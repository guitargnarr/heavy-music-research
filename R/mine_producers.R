#!/usr/bin/env Rscript
# mine_producers.R -- Mine producer/engineer credits from MusicBrainz + Discogs
# v2: Check recording-level rels on MB, actual releases on Discogs
# Output: data/mined_producers.json

source("R/utils.R")
library(purrr)

# --- Load artists ---
artists <- read_json_file("artists.json")
log_info("Mining producer credits for ", nrow(artists), " artists")

# --- MusicBrainz: Search artist -> get MBID ---
mb_search_artist <- function(name) {
  clean <- clean_name(name)
  result <- mb_request("artist/", params = list(query = paste0('artist:"', clean, '"'), limit = 5))
  if (is.null(result) || length(result$artists) == 0) return(NULL)

  candidates <- result$artists
  for (cand in candidates) {
    if (name_match(cand$name, name)) {
      return(list(id = cand$id, name = cand$name))
    }
  }
  if (length(candidates) > 0 && !is.null(candidates[[1]]$score) && candidates[[1]]$score > 90) {
    return(list(id = candidates[[1]]$id, name = candidates[[1]]$name))
  }
  NULL
}

# --- MusicBrainz: Get recent albums ---
mb_get_albums <- function(artist_mbid) {
  result <- mb_request(
    "release-group/",
    params = list(artist = artist_mbid, type = "album", limit = 10)
  )
  if (is.null(result) || length(result$`release-groups`) == 0) return(NULL)

  rgs <- result$`release-groups`
  albums <- keep(rgs, ~ !is.null(.x$`primary-type`) && .x$`primary-type` == "Album")
  if (length(albums) == 0) return(NULL)

  albums <- albums[order(sapply(albums, function(a) {
    d <- a$`first-release-date`
    if (is.null(d) || d == "") return("0000")
    d
  }), decreasing = TRUE)]
  albums
}

# --- MusicBrainz: Get release with BOTH artist-rels AND recording-level-rels ---
mb_get_release_credits <- function(release_group_id) {
  # Get releases in this release group
  result <- mb_request(
    "release/",
    params = list(`release-group` = release_group_id, limit = 5)
  )
  if (is.null(result) || length(result$releases) == 0) return(NULL)

  release_id <- result$releases[[1]]$id

  # Get release with artist-rels (release-level credits)
  detail <- mb_request(
    paste0("release/", release_id),
    params = list(inc = "artist-rels+recording-rels+recordings")
  )
  if (is.null(detail)) return(NULL)

  credits <- list()
  producer_roles <- c("producer", "co-producer")
  engineer_roles <- c("engineer", "audio", "sound engineer", "recording", "vocal producer")
  mix_roles <- c("mix", "mixer", "mixing")
  master_roles <- c("mastering")

  # Helper to categorize a role
  categorize_role <- function(rel_type) {
    rt <- tolower(rel_type)
    if (rt %in% producer_roles) return("producer")
    if (rt %in% engineer_roles) return("engineer")
    if (rt %in% mix_roles) return("mix")
    if (rt %in% master_roles) return("mastering")
    NULL
  }

  # Extract from release-level relations
  if (!is.null(detail$relations) && length(detail$relations) > 0) {
    for (rel in detail$relations) {
      role <- categorize_role(rel$type %||% "")
      if (!is.null(role) && !is.null(rel$artist$name)) {
        credits[[length(credits) + 1]] <- list(name = rel$artist$name, role = role)
      }
    }
  }

  # Extract from recording-level relations (often where producers are!)
  if (!is.null(detail$media) && length(detail$media) > 0) {
    for (medium in detail$media) {
      tracks <- medium$tracks
      if (is.null(tracks)) next
      for (track in tracks) {
        recording <- track$recording
        if (is.null(recording) || is.null(recording$relations)) next
        for (rel in recording$relations) {
          role <- categorize_role(rel$type %||% "")
          if (!is.null(role) && !is.null(rel$artist$name)) {
            # Only add if not already found
            existing <- sapply(credits, function(c) paste(c$name, c$role))
            key <- paste(rel$artist$name, role)
            if (!key %in% existing) {
              credits[[length(credits) + 1]] <- list(name = rel$artist$name, role = role)
            }
          }
        }
        # Only check first 3 tracks -- producer is usually the same across all
        if (!is.null(track$position) && track$position >= 3) break
      }
      break  # Only first medium
    }
  }

  credits
}

# --- Discogs: Search artist ---
discogs_search_artist <- function(name) {
  clean <- clean_name(name)
  result <- discogs_request("database/search", params = list(q = clean, type = "artist"))
  if (is.null(result) || length(result$results) == 0) return(NULL)

  for (r in result$results) {
    if (name_match(r$title, name)) {
      return(list(id = r$id, name = r$title))
    }
  }
  if (length(result$results) > 0) {
    return(list(id = result$results[[1]]$id, name = result$results[[1]]$title))
  }
  NULL
}

# --- Discogs: Get most recent album and its credits (v2 -- check actual releases) ---
discogs_get_producer_credits <- function(artist_id) {
  result <- discogs_request(
    paste0("artists/", artist_id, "/releases"),
    params = list(sort = "year", sort_order = "desc", per_page = 30)
  )
  if (is.null(result) || length(result$releases) == 0) return(NULL)

  releases <- result$releases

  # Try to find an album release (not single/compilation)
  for (r in releases) {
    role <- r$role %||% "Main"
    if (role != "Main") next
    rtype <- r$type %||% ""

    # Prefer master releases
    release_id <- r$id
    is_master <- (rtype == "master")

    if (is_master) {
      # Get the master to find the main release
      master_detail <- discogs_request(paste0("masters/", release_id))
      if (!is.null(master_detail) && !is.null(master_detail$main_release)) {
        release_id <- master_detail$main_release
      } else {
        next
      }
    }

    # Get the actual release (not master) -- this has extraartists
    detail <- discogs_request(paste0("releases/", release_id))
    if (is.null(detail)) next

    # Check extraartists
    credits <- list()
    extra <- detail$extraartists
    if (!is.null(extra) && length(extra) > 0) {
      for (ea in extra) {
        role_str <- tolower(ea$role %||% "")
        if (str_detect(role_str, "produc")) {
          credits[[length(credits) + 1]] <- list(name = ea$name, role = "producer")
        } else if (str_detect(role_str, "mix(?!master)")) {
          credits[[length(credits) + 1]] <- list(name = ea$name, role = "mix")
        } else if (str_detect(role_str, "master")) {
          credits[[length(credits) + 1]] <- list(name = ea$name, role = "mastering")
        } else if (str_detect(role_str, "engineer|record")) {
          credits[[length(credits) + 1]] <- list(name = ea$name, role = "engineer")
        }
      }
    }

    if (length(credits) > 0) {
      return(list(
        album = detail$title %||% r$title,
        year = detail$year %||% r$year,
        credits = credits
      ))
    }
    # If no credits found on this release, try next one (up to 5)
  }
  NULL
}

# --- Main Mining Loop ---
results <- list()
mb_found <- 0
discogs_found <- 0
no_data <- 0

for (i in seq_len(nrow(artists))) {
  name <- artists$name[i]
  log_info(sprintf("[%d/%d] %s", i, nrow(artists), name))

  # Try MusicBrainz first
  mb_artist <- mb_search_artist(name)
  mb_credits <- NULL
  album_title <- NULL
  album_year <- NULL

  if (!is.null(mb_artist)) {
    log_info("  MB: ", mb_artist$name, " (", mb_artist$id, ")")
    albums <- mb_get_albums(mb_artist$id)

    if (!is.null(albums) && length(albums) > 0) {
      for (album in albums[1:min(3, length(albums))]) {
        credits <- mb_get_release_credits(album$id)
        if (!is.null(credits) && length(credits) > 0) {
          album_title <- album$title
          album_year <- substr(album$`first-release-date`, 1, 4)
          mb_credits <- credits
          break
        }
      }
    }
  }

  if (!is.null(mb_credits) && length(mb_credits) > 0) {
    producer_names <- unique(sapply(keep(mb_credits, ~ .x$role == "producer"), function(c) c$name))
    engineer_names <- unique(sapply(keep(mb_credits, ~ .x$role == "engineer"), function(c) c$name))
    mixer_names <- unique(sapply(keep(mb_credits, ~ .x$role == "mix"), function(c) c$name))

    results[[length(results) + 1]] <- list(
      artist_name = name,
      album = album_title,
      year = as.integer(album_year),
      producer = if (length(producer_names) > 0) paste(producer_names, collapse = ", ") else NA,
      engineer = if (length(engineer_names) > 0) paste(engineer_names, collapse = ", ") else NA,
      mixer = if (length(mixer_names) > 0) paste(mixer_names, collapse = ", ") else NA,
      source = "musicbrainz"
    )
    mb_found <- mb_found + 1
    log_info("  -> MB HIT: ", album_title, " (", album_year, ") -- ",
             length(mb_credits), " credits [",
             paste(unique(sapply(mb_credits, function(c) c$role)), collapse=", "), "]")
    next
  }

  # Fallback to Discogs
  log_info("  MB miss, trying Discogs...")
  discogs_artist <- discogs_search_artist(name)

  if (!is.null(discogs_artist)) {
    log_info("  Discogs: ", discogs_artist$name, " (", discogs_artist$id, ")")
    discogs_result <- discogs_get_producer_credits(discogs_artist$id)

    if (!is.null(discogs_result) && length(discogs_result$credits) > 0) {
      producer_names <- unique(sapply(keep(discogs_result$credits, ~ .x$role == "producer"), function(c) c$name))
      engineer_names <- unique(sapply(keep(discogs_result$credits, ~ .x$role == "engineer"), function(c) c$name))
      mixer_names <- unique(sapply(keep(discogs_result$credits, ~ .x$role == "mix"), function(c) c$name))

      results[[length(results) + 1]] <- list(
        artist_name = name,
        album = discogs_result$album,
        year = discogs_result$year,
        producer = if (length(producer_names) > 0) paste(producer_names, collapse = ", ") else NA,
        engineer = if (length(engineer_names) > 0) paste(engineer_names, collapse = ", ") else NA,
        mixer = if (length(mixer_names) > 0) paste(mixer_names, collapse = ", ") else NA,
        source = "discogs"
      )
      discogs_found <- discogs_found + 1
      log_info("  -> DISCOGS HIT: ", discogs_result$album, " -- ",
               length(discogs_result$credits), " credits")
      next
    }
  }

  log_warn("  NO DATA for ", name)
  no_data <- no_data + 1
}

# --- Save results ---
output <- map(results, function(r) {
  list(
    artist_name = r$artist_name,
    album = r$album,
    year = r$year,
    producer = r$producer,
    engineer = r$engineer,
    mixer = r$mixer,
    source = r$source
  )
})

output_path <- file.path(DATA_DIR, "mined_producers.json")
write_json(output, output_path, pretty = TRUE, auto_unbox = TRUE, na = "null")
log_info("Wrote ", length(output), " records to ", output_path)

# --- Summary ---
cat("\n========== MINING SUMMARY ==========\n")
cat(sprintf("Total artists:       %d\n", nrow(artists)))
cat(sprintf("MusicBrainz hits:    %d\n", mb_found))
cat(sprintf("Discogs hits:        %d\n", discogs_found))
cat(sprintf("No data:             %d\n", no_data))
cat(sprintf("Coverage:            %.0f%%\n", (mb_found + discogs_found) / nrow(artists) * 100))
cat("====================================\n")

# Show all results with producer names
if (length(output) > 0) {
  cat("\nResults:\n")
  for (r in output) {
    prod <- if (!is.null(r$producer) && !is.na(r$producer)) r$producer else "(credits found, no producer role)"
    cat(sprintf("  %-30s | %-40s | %s [%s]\n", r$artist_name, r$album, prod, r$source))
  }
}
