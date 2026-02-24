# utils.R -- Shared helpers for Metalcore Index data mining
# Rate limiter, JSON I/O, logging, API helpers

library(httr2)
library(jsonlite)
library(dplyr)
library(stringr)

# --- Paths ---
PROJECT_ROOT <- normalizePath(file.path(dirname(sys.frame(1)$ofile), ".."))
DATA_DIR <- file.path(PROJECT_ROOT, "data")

# --- Logging ---
log_info <- function(...) {
  msg <- paste0(...)
  cat(sprintf("[%s] %s\n", format(Sys.time(), "%H:%M:%S"), msg))
}

log_warn <- function(...) {
  msg <- paste0(...)
  cat(sprintf("[%s] WARN: %s\n", format(Sys.time(), "%H:%M:%S"), msg))
}

log_error <- function(...) {
  msg <- paste0(...)
  cat(sprintf("[%s] ERROR: %s\n", format(Sys.time(), "%H:%M:%S"), msg))
}

# --- Rate Limiter ---
# Simple rate limiter: tracks last request time per domain
.rate_state <- new.env(parent = emptyenv())

rate_limit <- function(domain, min_interval_sec) {
  last_time <- .rate_state[[domain]]
  if (!is.null(last_time)) {
    elapsed <- as.numeric(Sys.time() - last_time, units = "secs")
    if (elapsed < min_interval_sec) {
      wait <- min_interval_sec - elapsed
      Sys.sleep(wait)
    }
  }
  .rate_state[[domain]] <- Sys.time()
}

# --- JSON I/O ---
read_json_file <- function(filename) {
  path <- file.path(DATA_DIR, filename)
  if (!file.exists(path)) {
    stop(sprintf("File not found: %s", path))
  }
  fromJSON(path, simplifyDataFrame = TRUE)
}

write_json_file <- function(data, filename, backup = TRUE) {
  path <- file.path(DATA_DIR, filename)
  if (backup && file.exists(path)) {
    bak <- paste0(path, ".bak")
    file.copy(path, bak, overwrite = TRUE)
    log_info("Backup created: ", basename(bak))
  }
  write_json(data, path, pretty = TRUE, auto_unbox = TRUE)
  log_info("Wrote ", basename(path), " (", file.size(path), " bytes)")
}

# --- API Helpers ---

# MusicBrainz: free, no key, 1 req/sec, User-Agent required
mb_request <- function(endpoint, params = list()) {
  rate_limit("musicbrainz", 1.1)
  url <- paste0("https://musicbrainz.org/ws/2/", endpoint)
  params$fmt <- "json"

  resp <- tryCatch({
    req <- request(url) |>
      req_url_query(!!!params) |>
      req_headers(`User-Agent` = "MetalcoreIndex/1.0 (matthewdscott7@gmail.com)") |>
      req_retry(max_tries = 3, backoff = ~2)
    req_perform(req)
  }, error = function(e) {
    log_error("MusicBrainz request failed: ", e$message)
    return(NULL)
  })

  if (is.null(resp)) return(NULL)
  if (resp_status(resp) != 200) {
    log_warn("MusicBrainz returned ", resp_status(resp), " for ", endpoint)
    return(NULL)
  }
  resp_body_json(resp)
}

# Discogs: free unauthenticated, 25 req/min
discogs_request <- function(endpoint, params = list()) {
  rate_limit("discogs", 2.5)
  url <- paste0("https://api.discogs.com/", endpoint)

  resp <- tryCatch({
    req <- request(url) |>
      req_url_query(!!!params) |>
      req_headers(`User-Agent` = "MetalcoreIndex/1.0") |>
      req_retry(max_tries = 3, backoff = ~2)
    req_perform(req)
  }, error = function(e) {
    log_error("Discogs request failed: ", e$message)
    return(NULL)
  })

  if (is.null(resp)) return(NULL)
  if (resp_status(resp) != 200) {
    log_warn("Discogs returned ", resp_status(resp), " for ", endpoint)
    return(NULL)
  }
  resp_body_json(resp)
}

# --- String Matching ---
# Fuzzy match artist names (handles slight variations)
name_match <- function(a, b) {
  a_clean <- str_to_lower(str_trim(a))
  b_clean <- str_to_lower(str_trim(b))
  a_clean == b_clean
}

# Clean artist name for API queries
clean_name <- function(name) {
  # Remove common suffixes that confuse search
  name |>
    str_replace_all("\\s*\\(.*?\\)", "") |>  # Remove parentheticals
    str_trim()
}

log_info("utils.R loaded. PROJECT_ROOT=", PROJECT_ROOT)
log_info("DATA_DIR=", DATA_DIR)
