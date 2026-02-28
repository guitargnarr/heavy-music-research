#!/usr/bin/env Rscript
# mine_setlistfm.R -- Mine Setlist.fm for concert/festival history
# Requires: SETLISTFM_API_KEY environment variable
# Free key at: https://api.setlist.fm/docs/1.0/index.html
# Also needs MusicBrainz IDs from mine_producers.R output
# Output: data/mined_setlists.json

source("R/utils.R")
library(purrr)

# --- Check API key ---
api_key <- Sys.getenv("SETLISTFM_API_KEY")
if (api_key == "") {
  stop("SETLISTFM_API_KEY not set. Get a free key at https://api.setlist.fm/docs/1.0/index.html")
}

# --- Load artists ---
artists <- read_json_file("artists.json")
log_info("Mining Setlist.fm for ", nrow(artists), " artists")

# --- Load MBIDs from producer mining output (if available) ---
mbid_map <- list()  # name -> mbid

# Try to load from mined_producers.json
producers_path <- file.path(DATA_DIR, "mined_producers.json")
if (file.exists(producers_path)) {
  producers_data <- fromJSON(producers_path, simplifyDataFrame = FALSE)
  for (p in producers_data) {
    if (!is.null(p$mbid) && !is.na(p$mbid) && p$mbid != "") {
      mbid_map[[tolower(p$artist)]] <- p$mbid
    }
  }
  log_info("Loaded ", length(mbid_map), " MBIDs from producer mining output")
}

# Try to load from mined_wikidata.json as fallback
wikidata_path <- file.path(DATA_DIR, "mined_wikidata.json")
if (file.exists(wikidata_path)) {
  wiki_data <- fromJSON(wikidata_path, simplifyDataFrame = FALSE)
  if (!is.null(wiki_data$artists)) {
    for (a in wiki_data$artists) {
      if (!is.null(a$musicbrainz_id) && !is.na(a$musicbrainz_id)) {
        key <- tolower(a$name)
        if (is.null(mbid_map[[key]])) {
          mbid_map[[key]] <- a$musicbrainz_id
        }
      }
    }
    log_info("After Wikidata merge: ", length(mbid_map), " MBIDs total")
  }
}

# --- Setlist.fm API helper ---
setlistfm_request <- function(endpoint, params = list()) {
  rate_limit("setlistfm", 0.15)  # ~7 req/sec, under 16/sec limit
  url <- paste0("https://api.setlist.fm/rest/1.0/", endpoint)

  resp <- tryCatch({
    req <- request(url) |>
      req_url_query(!!!params) |>
      req_headers(
        `x-api-key` = api_key,
        Accept = "application/json",
        `User-Agent` = "MetalcoreIndex/1.0 (matthewdscott7@gmail.com)"
      ) |>
      req_timeout(30) |>
      req_retry(max_tries = 3, backoff = ~2)
    req_perform(req)
  }, error = function(e) {
    log_error("Setlist.fm request failed: ", e$message)
    return(NULL)
  })

  if (is.null(resp)) return(NULL)
  if (resp_status(resp) != 200) {
    log_warn("Setlist.fm returned ", resp_status(resp), " for ", endpoint)
    return(NULL)
  }
  resp_body_json(resp)
}

# --- Search for MBID if not already known ---
find_mbid <- function(artist_name) {
  key <- tolower(artist_name)
  if (!is.null(mbid_map[[key]])) return(mbid_map[[key]])

  # Search MusicBrainz for the MBID
  result <- mb_request("artist/", list(query = paste0("artist:", clean_name(artist_name))))
  if (is.null(result) || length(result$artists) == 0) return(NULL)

  # Match by name
  for (a in result$artists) {
    if (tolower(a$name) == tolower(artist_name) ||
        tolower(a$name) == tolower(clean_name(artist_name))) {
      mbid_map[[key]] <<- a$id
      return(a$id)
    }
  }
  # Take first result if score is high enough
  if (!is.null(result$artists[[1]]$score) && result$artists[[1]]$score >= 90) {
    mbid_map[[key]] <<- result$artists[[1]]$id
    return(result$artists[[1]]$id)
  }
  NULL
}

# --- Mine setlists ---
all_events <- list()
festival_counts <- list()  # festival_name -> list of artists

for (i in seq_len(nrow(artists))) {
  name <- artists$name[i]
  cat(sprintf("[%d/%d] %s", i, nrow(artists), name))

  mbid <- find_mbid(name)
  if (is.null(mbid)) {
    cat(" -- NO MBID, skipping\n")
    next
  }

  # Get pages 1-3 (most recent ~60 shows)
  artist_events <- list()
  for (page in 1:3) {
    result <- setlistfm_request(
      paste0("artist/", mbid, "/setlists"),
      list(p = page)
    )
    if (is.null(result) || is.null(result$setlist) || length(result$setlist) == 0) break

    for (setlist in result$setlist) {
      venue <- setlist$venue
      event_date <- setlist$eventDate  # dd-MM-yyyy format

      # Parse date to ISO format
      iso_date <- tryCatch({
        parts <- strsplit(event_date, "-")[[1]]
        sprintf("%s-%s-%s", parts[3], parts[2], parts[1])
      }, error = function(e) NA)

      # Count songs played
      songs_played <- 0
      if (!is.null(setlist$sets) && !is.null(setlist$sets$set)) {
        for (s in setlist$sets$set) {
          if (!is.null(s$song)) songs_played <- songs_played + length(s$song)
        }
      }

      # Determine if festival
      festival_name <- NULL
      if (!is.null(setlist$tour) && !is.null(setlist$tour$name)) {
        tour_name <- setlist$tour$name
        # Common festival indicators
        if (grepl("fest|festival|download|wacken|hellfest|sonic temple|blue ridge|aftershock|riot fest|slam dunk|reading|leeds|graspop|summer breeze|bloodstock|knotfest|inkcarceration|welcome to rockville|when we were young", tolower(tour_name))) {
          festival_name <- tour_name
        }
      }

      event <- list(
        artist = name,
        event_date = iso_date,
        venue_name = venue$name %||% NA,
        city = venue$city$name %||% NA,
        state = venue$city$stateCode %||% NA,
        country = venue$city$country$code %||% NA,
        tour_name = setlist$tour$name %||% NA,
        festival_name = festival_name,
        songs_played = songs_played
      )

      artist_events[[length(artist_events) + 1]] <- event

      # Track festival appearances
      if (!is.null(festival_name)) {
        fkey <- tolower(festival_name)
        if (is.null(festival_counts[[fkey]])) {
          festival_counts[[fkey]] <- list(name = festival_name, artists = character())
        }
        if (!name %in% festival_counts[[fkey]]$artists) {
          festival_counts[[fkey]]$artists <- c(festival_counts[[fkey]]$artists, name)
        }
      }
    }

    # Check if there are more pages
    total_pages <- ceiling((result$total %||% 0) / (result$itemsPerPage %||% 20))
    if (page >= total_pages) break
  }

  cat(sprintf(" -- %d events (MBID: %s)\n", length(artist_events), substr(mbid, 1, 8)))
  all_events <- c(all_events, artist_events)
}

# --- Summary ---
cat("\n========== SETLIST.FM MINING SUMMARY ==========\n")
cat(sprintf("Total events mined: %d\n", length(all_events)))
cat(sprintf("Artists with events: %d / %d\n",
  length(unique(sapply(all_events, function(e) e$artist))),
  nrow(artists)))

# Festival cross-tabulation
festivals_multi <- Filter(function(f) length(f$artists) >= 2, festival_counts)
festivals_multi <- festivals_multi[order(-sapply(festivals_multi, function(f) length(f$artists)))]

if (length(festivals_multi) > 0) {
  cat(sprintf("\nFestivals with 2+ of our artists (%d):\n", length(festivals_multi)))
  for (f in head(festivals_multi, 15)) {
    cat(sprintf("  %-40s %d artists: %s\n",
      f$name, length(f$artists), paste(f$artists, collapse = ", ")))
  }
}

# Country breakdown
countries <- sapply(all_events, function(e) e$country %||% "Unknown")
country_counts <- sort(table(countries), decreasing = TRUE)
cat("\nEvents by country:\n")
for (cn in names(head(country_counts, 10))) {
  cat(sprintf("  %-5s %d\n", cn, country_counts[cn]))
}

# Date range
dates <- na.omit(sapply(all_events, function(e) e$event_date))
if (length(dates) > 0) {
  cat(sprintf("\nDate range: %s to %s\n", min(dates), max(dates)))
}

# --- Save output ---
output <- list(
  total_events = length(all_events),
  artists_with_events = length(unique(sapply(all_events, function(e) e$artist))),
  events = all_events,
  festivals = map(festivals_multi, function(f) {
    list(name = f$name, artist_count = length(f$artists), artists = f$artists)
  })
)

output_path <- file.path(DATA_DIR, "mined_setlists.json")
write_json(output, output_path, pretty = TRUE, auto_unbox = TRUE, na = "null")
log_info("Wrote ", output_path)

cat("\n========== SETLIST.FM MINING COMPLETE ==========\n")
