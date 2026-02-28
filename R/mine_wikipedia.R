#!/usr/bin/env Rscript
# mine_wikipedia.R -- Wikipedia pageview data for cultural buzz signal
# No auth required. Wikimedia Pageviews API.
# Output: data/mined_wikipedia.json

source("R/utils.R")
library(purrr)
library(tidyr)

# --- Load artists ---
artists <- read_json_file("artists.json")
log_info("Mining Wikipedia pageviews for ", nrow(artists), " artists")

# --- Wikipedia article name mapping ---
# Wikipedia titles use underscores, disambiguation may be needed
# We'll search and resolve each artist

resolve_wiki_title <- function(name) {
  rate_limit("wikipedia", 0.2)  # 5 req/sec is safe

  # Try the exact name first, then with "(band)" suffix
  candidates <- c(
    gsub(" ", "_", name),
    paste0(gsub(" ", "_", name), "_(band)")
  )

  for (title in candidates) {
    resp <- tryCatch({
      request("https://en.wikipedia.org/api/rest_v1/page/summary") |>
        req_url_path_append(URLencode(title, reserved = TRUE)) |>
        req_headers(`User-Agent` = "MetalcoreIndex/1.0 (matthewdscott7@gmail.com)") |>
        req_error(is_error = ~ FALSE) |>
        req_perform()
    }, error = function(e) NULL)

    if (!is.null(resp) && resp_status(resp) == 200) {
      body <- resp_body_json(resp)
      # Verify it's about a band/musician, not something else
      desc <- tolower(body$description %||% "")
      extract <- tolower(body$extract %||% "")
      if (grepl("band|music|metal|rock|hardcore|singer|group|artist", paste(desc, extract)))
        return(body$title)
    }
  }
  return(NA_character_)
}

get_pageviews <- function(title, days = 90) {
  if (is.na(title)) return(NULL)
  rate_limit("wikipedia", 0.2)

  end_date <- format(Sys.Date() - 1, "%Y%m%d")
  start_date <- format(Sys.Date() - days, "%Y%m%d")

  resp <- tryCatch({
    request("https://wikimedia.org/api/rest_v1") |>
      req_url_path_append(
        "metrics", "pageviews", "per-article",
        "en.wikipedia", "all-access", "user",
        URLencode(gsub(" ", "_", title), reserved = TRUE),
        "daily", start_date, end_date
      ) |>
      req_headers(`User-Agent` = "MetalcoreIndex/1.0 (matthewdscott7@gmail.com)") |>
      req_error(is_error = ~ FALSE) |>
      req_perform()
  }, error = function(e) NULL)

  if (is.null(resp) || resp_status(resp) != 200) return(NULL)

  body <- resp_body_json(resp)
  items <- body$items
  if (length(items) == 0) return(NULL)

  views <- map_int(items, ~ .x$views)
  dates <- map_chr(items, ~ .x$timestamp)

  list(
    daily_views = views,
    dates = dates,
    total_views = sum(views),
    avg_daily = round(mean(views), 1),
    max_daily = max(views),
    min_daily = min(views),
    trend_last_7d = if (length(views) >= 7) round(mean(tail(views, 7)), 1) else NA_real_,
    trend_last_30d = if (length(views) >= 30) round(mean(tail(views, 30)), 1) else NA_real_
  )
}

# --- Mine each artist ---
results <- list()

for (i in seq_len(nrow(artists))) {
  name <- artists$name[i]
  sid <- artists$spotify_id[i]
  log_info(sprintf("[%d/%d] %s", i, nrow(artists), name))

  title <- resolve_wiki_title(name)
  if (is.na(title)) {
    log_warn("  No Wikipedia article found for: ", name)
    results[[i]] <- list(
      name = name,
      spotify_id = sid,
      wiki_title = NA_character_,
      found = FALSE
    )
    next
  }

  log_info("  Resolved to: ", title)
  pv <- get_pageviews(title, days = 90)

  if (is.null(pv)) {
    log_warn("  No pageview data for: ", title)
    results[[i]] <- list(
      name = name,
      spotify_id = sid,
      wiki_title = title,
      found = TRUE,
      total_views_90d = 0
    )
    next
  }

  results[[i]] <- list(
    name = name,
    spotify_id = sid,
    wiki_title = title,
    found = TRUE,
    total_views_90d = pv$total_views,
    avg_daily_views = pv$avg_daily,
    max_daily_views = pv$max_daily,
    trend_last_7d = pv$trend_last_7d,
    trend_last_30d = pv$trend_last_30d
  )

  log_info(sprintf("  90d total: %s, avg/day: %s, 7d avg: %s",
                   pv$total_views, pv$avg_daily, pv$trend_last_7d))
}

# --- Save results ---
write_json_file(results, "mined_wikipedia.json", backup = FALSE)

# --- Summary ---
found <- sum(map_lgl(results, ~ isTRUE(.x$found)))
log_info("Done. Found Wikipedia articles for ", found, "/", nrow(artists), " artists")

# Top 10 by pageviews
with_views <- keep(results, ~ !is.null(.x$total_views_90d) && .x$total_views_90d > 0)
with_views <- with_views[order(-map_dbl(with_views, ~ .x$total_views_90d))]
log_info("Top 10 by 90-day pageviews:")
for (r in head(with_views, 10)) {
  log_info(sprintf("  %s: %s views (avg %s/day)", r$name, r$total_views_90d, r$avg_daily_views))
}
