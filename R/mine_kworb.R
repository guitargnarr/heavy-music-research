#!/usr/bin/env Rscript
# mine_kworb.R -- Scrape actual Spotify stream counts from Kworb.net
# No auth required. Static HTML pages, be respectful with rate limiting.
# Output: data/mined_kworb.json

source("R/utils.R")
library(purrr)
library(rvest)

# --- Load artists ---
artists <- read_json_file("artists.json")
log_info("Mining Kworb.net stream data for ", nrow(artists), " artists")

# --- Kworb helpers ---
get_kworb_streams <- function(spotify_id) {
  rate_limit("kworb", 3)  # Be very respectful -- 1 req per 3 sec
  url <- paste0("https://kworb.net/spotify/artist/", spotify_id, ".html")

  page <- tryCatch({
    read_html(url)
  }, error = function(e) {
    NULL
  })

  if (is.null(page)) return(NULL)

  # Kworb pages have a table with track data
  tables <- tryCatch({
    html_table(page, fill = TRUE)
  }, error = function(e) {
    list()
  })

  if (length(tables) == 0) return(NULL)

  # The main table typically has columns like: #, Title, Streams, Daily
  tbl <- tables[[1]]
  if (nrow(tbl) == 0) return(NULL)

  # Column names vary -- try to find streams column
  cols <- tolower(names(tbl))
  stream_col <- which(grepl("stream|total", cols))[1]
  daily_col <- which(grepl("daily|change", cols))[1]
  title_col <- which(grepl("title|track|name", cols))[1]

  if (is.na(title_col)) title_col <- 2  # Fallback: second column is usually title
  if (is.na(stream_col)) stream_col <- 3  # Fallback: third is usually streams

  # Parse stream counts (remove commas, convert to numeric)
  parse_count <- function(x) {
    x <- gsub("[^0-9]", "", as.character(x))
    as.numeric(x)
  }

  tracks <- list()
  total_streams <- 0

  for (j in seq_len(min(nrow(tbl), 20))) {
    title <- as.character(tbl[j, title_col])
    streams <- parse_count(tbl[j, stream_col])
    daily <- if (!is.na(daily_col)) parse_count(tbl[j, daily_col]) else NA_real_

    if (!is.na(streams) && streams > 0) {
      total_streams <- total_streams + streams
      tracks[[length(tracks) + 1]] <- list(
        title = title,
        streams = streams,
        daily = daily
      )
    }
  }

  if (length(tracks) == 0) return(NULL)

  list(
    tracks = tracks,
    total_streams = total_streams,
    track_count = length(tracks),
    top_track_streams = tracks[[1]]$streams,
    top_track = tracks[[1]]$title,
    avg_daily = if (any(!is.na(map_dbl(tracks, ~ .x$daily %||% NA_real_)))) {
      round(sum(map_dbl(tracks, ~ .x$daily %||% 0), na.rm = TRUE), 0)
    } else NA_real_
  )
}

# --- Mine each artist ---
results <- list()

for (i in seq_len(nrow(artists))) {
  name <- artists$name[i]
  sid <- artists$spotify_id[i]
  log_info(sprintf("[%d/%d] %s (spotify: %s)", i, nrow(artists), name, sid))

  kworb <- get_kworb_streams(sid)

  if (is.null(kworb)) {
    log_warn("  No Kworb data (may not be indexed)")
    results[[i]] <- list(name = name, spotify_id = sid, found = FALSE)
    next
  }

  log_info(sprintf("  Total streams: %s, Top track: %s (%s streams)",
                   format(kworb$total_streams, big.mark = ","),
                   kworb$top_track,
                   format(kworb$top_track_streams, big.mark = ",")))

  results[[i]] <- list(
    name = name,
    spotify_id = sid,
    found = TRUE,
    total_streams = kworb$total_streams,
    track_count = kworb$track_count,
    top_track = kworb$top_track,
    top_track_streams = kworb$top_track_streams,
    avg_daily_total = kworb$avg_daily,
    tracks = kworb$tracks
  )
}

# --- Save ---
write_json_file(results, "mined_kworb.json", backup = FALSE)

# --- Summary ---
found <- sum(map_lgl(results, ~ isTRUE(.x$found)))
log_info("Done. Found ", found, "/", nrow(artists), " on Kworb")

with_streams <- keep(results, ~ isTRUE(.x$found))
with_streams <- with_streams[order(-map_dbl(with_streams, ~ .x$total_streams))]
log_info("Top 15 by total Spotify streams:")
for (r in head(with_streams, 15)) {
  log_info(sprintf("  %s: %s total streams, top track: %s",
                   r$name,
                   format(r$total_streams, big.mark = ","),
                   r$top_track))
}
