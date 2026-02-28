#!/usr/bin/env Rscript
# mine_deezer.R -- Deezer fan counts + top track popularity (cross-platform metric)
# No auth required. Deezer API is fully open for public data.
# Output: data/mined_deezer.json

source("R/utils.R")
library(purrr)

# --- Load artists ---
artists <- read_json_file("artists.json")
log_info("Mining Deezer data for ", nrow(artists), " artists")

# --- Deezer helpers ---
deezer_request <- function(path, params = list()) {
  rate_limit("deezer", 0.3)  # ~3 req/sec safe
  url <- paste0("https://api.deezer.com/", path)

  resp <- tryCatch({
    request(url) |>
      req_url_query(!!!params) |>
      req_headers(`User-Agent` = "MetalcoreIndex/1.0") |>
      req_error(is_error = ~ FALSE) |>
      req_perform()
  }, error = function(e) {
    log_error("Deezer request failed: ", e$message)
    NULL
  })

  if (is.null(resp)) return(NULL)
  body <- resp_body_json(resp)
  # Deezer returns errors in-band (no HTTP error codes)
  if (!is.null(body$error)) {
    log_warn("Deezer error: ", body$error$message %||% "unknown")
    return(NULL)
  }
  body
}

search_artist <- function(name) {
  result <- deezer_request("search/artist", list(q = name))
  if (is.null(result) || length(result$data) == 0) return(NULL)

  # Find best match -- exact or closest name
  name_lower <- tolower(name)
  for (item in result$data) {
    if (tolower(item$name) == name_lower) return(item)
  }
  # Fall back to first result if close enough
  first <- result$data[[1]]
  if (agrepl(name_lower, tolower(first$name), max.distance = 0.2)) return(first)
  NULL
}

get_top_tracks <- function(artist_id) {
  result <- deezer_request(paste0("artist/", artist_id, "/top"), list(limit = 10))
  if (is.null(result) || length(result$data) == 0) return(list())

  map(result$data, ~ list(
    title = .x$title,
    rank = .x$rank,  # Deezer popularity score (0-1000000)
    duration = .x$duration
  ))
}

get_related_artists <- function(artist_id) {
  result <- deezer_request(paste0("artist/", artist_id, "/related"), list(limit = 25))
  if (is.null(result) || length(result$data) == 0) return(list())

  map(result$data, ~ list(
    name = .x$name,
    deezer_id = .x$id,
    nb_fan = .x$nb_fan
  ))
}

get_albums <- function(artist_id) {
  result <- deezer_request(paste0("artist/", artist_id, "/albums"), list(limit = 50))
  if (is.null(result) || length(result$data) == 0) return(list())

  map(result$data, ~ list(
    title = .x$title,
    release_date = .x$release_date,
    record_type = .x$record_type  # album, ep, single, compile
  ))
}

# --- Mine each artist ---
results <- list()

for (i in seq_len(nrow(artists))) {
  name <- artists$name[i]
  sid <- artists$spotify_id[i]
  log_info(sprintf("[%d/%d] %s", i, nrow(artists), name))

  artist <- search_artist(name)
  if (is.null(artist)) {
    log_warn("  Not found on Deezer")
    results[[i]] <- list(name = name, spotify_id = sid, found = FALSE)
    next
  }

  deezer_id <- artist$id
  nb_fan <- artist$nb_fan
  nb_album <- artist$nb_album
  log_info(sprintf("  Deezer ID: %s, Fans: %s, Albums: %s", deezer_id, nb_fan, nb_album))

  top <- get_top_tracks(deezer_id)
  avg_rank <- if (length(top) > 0) {
    round(mean(map_dbl(top, ~ .x$rank %||% 0)), 0)
  } else NA_real_
  max_rank <- if (length(top) > 0) {
    max(map_dbl(top, ~ .x$rank %||% 0))
  } else NA_real_

  related <- get_related_artists(deezer_id)
  albums <- get_albums(deezer_id)

  # Cross-reference related artists against our universe
  our_names <- tolower(artists$name)
  internal_related <- keep(related, ~ tolower(.x$name) %in% our_names)

  results[[i]] <- list(
    name = name,
    spotify_id = sid,
    found = TRUE,
    deezer_id = deezer_id,
    nb_fan = nb_fan,
    nb_album = nb_album,
    top_track_avg_rank = avg_rank,
    top_track_max_rank = max_rank,
    top_tracks = top,
    album_count = length(albums),
    albums = albums,
    related_in_universe = map_chr(internal_related, ~ .x$name),
    related_count_total = length(related)
  )
}

# --- Save ---
write_json_file(results, "mined_deezer.json", backup = FALSE)

# --- Summary ---
found <- sum(map_lgl(results, ~ isTRUE(.x$found)))
log_info("Done. Found ", found, "/", nrow(artists), " artists on Deezer")

# Top 10 by fan count
with_fans <- keep(results, ~ isTRUE(.x$found) && !is.null(.x$nb_fan))
with_fans <- with_fans[order(-map_dbl(with_fans, ~ .x$nb_fan))]
log_info("Top 10 by Deezer fans:")
for (r in head(with_fans, 10)) {
  log_info(sprintf("  %s: %s fans, avg track rank: %s",
                   r$name, format(r$nb_fan, big.mark = ","), r$top_track_avg_rank))
}

# Internal connections found via Deezer's "related" API
all_internal <- unique(unlist(map(results, ~ .x$related_in_universe)))
log_info("Found ", length(all_internal), " internal cross-references via Deezer related artists")
