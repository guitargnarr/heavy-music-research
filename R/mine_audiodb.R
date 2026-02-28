#!/usr/bin/env Rscript
# mine_audiodb.R -- TheAudioDB metadata enrichment (social links, genre, mood, country, year)
# No real auth needed. Free test key = "2"
# Output: data/mined_audiodb.json

source("R/utils.R")
library(purrr)

# --- Load artists ---
artists <- read_json_file("artists.json")
log_info("Mining TheAudioDB for ", nrow(artists), " artists")

AUDIODB_KEY <- "2"  # Free test key

# --- TheAudioDB helpers ---
audiodb_request <- function(endpoint, params = list()) {
  rate_limit("audiodb", 1.1)  # 2 req/sec on free key, be safe
  url <- paste0("https://www.theaudiodb.com/api/v1/json/", AUDIODB_KEY, "/", endpoint)

  resp <- tryCatch({
    request(url) |>
      req_url_query(!!!params) |>
      req_headers(`User-Agent` = "MetalcoreIndex/1.0") |>
      req_error(is_error = ~ FALSE) |>
      req_perform()
  }, error = function(e) {
    log_error("AudioDB request failed: ", e$message)
    NULL
  })

  if (is.null(resp) || resp_status(resp) != 200) return(NULL)
  resp_body_json(resp)
}

search_artist <- function(name) {
  result <- audiodb_request("search.php", list(s = name))
  if (is.null(result) || is.null(result$artists)) return(NULL)
  # Find best match
  name_lower <- tolower(name)
  for (item in result$artists) {
    if (tolower(item$strArtist %||% "") == name_lower) return(item)
  }
  # First result if only one
  if (length(result$artists) == 1) return(result$artists[[1]])
  NULL
}

get_discography <- function(artist_id) {
  # Use MBID if available, otherwise search by name
  result <- audiodb_request("discography.php", list(s = artist_id))
  if (is.null(result) || is.null(result$album)) return(list())
  map(result$album, ~ list(
    album = .x$strAlbum,
    year = .x$intYearReleased
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
    log_warn("  Not found on TheAudioDB")
    results[[i]] <- list(name = name, spotify_id = sid, found = FALSE)
    next
  }

  # Extract useful fields
  audiodb_id <- artist$idArtist
  log_info(sprintf("  Found: %s (ID: %s)", artist$strArtist, audiodb_id))

  results[[i]] <- list(
    name = name,
    spotify_id = sid,
    found = TRUE,
    audiodb_id = audiodb_id,
    genre = artist$strGenre,
    style = artist$strStyle,
    mood = artist$strMood,
    country = artist$strCountry,
    formed_year = artist$intFormedYear,
    members = artist$intMembers,
    mbid = artist$strMusicBrainzID,
    # Social links
    website = artist$strWebsite,
    facebook = artist$strFacebook,
    twitter = artist$strTwitter,
    instagram = if (!is.null(artist$strInstagram) && artist$strInstagram != "") artist$strInstagram else NA_character_,
    # Metadata
    biography_excerpt = if (!is.null(artist$strBiographyEN)) {
      substr(artist$strBiographyEN, 1, 300)
    } else NA_character_,
    charted = artist$intCharted,
    banner_url = artist$strArtistBanner,
    logo_url = artist$strArtistLogo,
    fanart_url = artist$strArtistFanart
  )

  log_info(sprintf("  Genre: %s, Style: %s, Country: %s, Formed: %s",
                   artist$strGenre %||% "?",
                   artist$strStyle %||% "?",
                   artist$strCountry %||% "?",
                   artist$intFormedYear %||% "?"))
  if (!is.null(artist$strFacebook) && artist$strFacebook != "") {
    log_info("  Facebook: ", artist$strFacebook)
  }
  if (!is.null(artist$strTwitter) && artist$strTwitter != "") {
    log_info("  Twitter: ", artist$strTwitter)
  }
}

# --- Save ---
write_json_file(results, "mined_audiodb.json", backup = FALSE)

# --- Summary ---
found <- sum(map_lgl(results, ~ isTRUE(.x$found)))
log_info("Done. Found ", found, "/", nrow(artists), " on TheAudioDB")

with_social <- keep(results, ~ isTRUE(.x$found) && (!is.na(.x$facebook) || !is.na(.x$twitter)))
log_info("Artists with social links: ", length(with_social))

# Genre distribution
genres <- map_chr(keep(results, ~ isTRUE(.x$found)), ~ .x$genre %||% "Unknown")
genre_table <- sort(table(genres), decreasing = TRUE)
log_info("Genre distribution:")
for (g in names(genre_table)) {
  log_info(sprintf("  %s: %d", g, genre_table[[g]]))
}
