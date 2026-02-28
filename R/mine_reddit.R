#!/usr/bin/env Rscript
# mine_reddit.R -- Reddit buzz from r/Metalcore, r/Deathcore, r/PostHardcore, r/Hardcore
# No auth required. Uses PullPush.io API (Reddit archive).
# Output: data/mined_reddit.json

source("R/utils.R")
library(purrr)

# --- Load artists ---
artists <- read_json_file("artists.json")
log_info("Mining Reddit buzz for ", nrow(artists), " artists")

# --- PullPush helpers ---
SUBREDDITS <- c("Metalcore", "Deathcore", "PostHardcore", "Hardcore", "progmetal")

pullpush_search <- function(query, subreddit, type = "submission", size = 100) {
  rate_limit("pullpush", 4.5)  # 15 req/min = 4 sec interval

  endpoint <- paste0("https://api.pullpush.io/reddit/search/", type, "/")

  resp <- tryCatch({
    request(endpoint) |>
      req_url_query(
        subreddit = subreddit,
        q = query,
        size = min(size, 100),
        sort = "desc",
        sort_type = "score"
      ) |>
      req_headers(`User-Agent` = "MetalcoreIndex/1.0") |>
      req_timeout(30) |>
      req_error(is_error = ~ FALSE) |>
      req_perform()
  }, error = function(e) {
    log_error("PullPush request failed: ", e$message)
    NULL
  })

  if (is.null(resp) || resp_status(resp) != 200) return(list())
  body <- resp_body_json(resp)
  body$data %||% list()
}

# --- Mine each artist ---
results <- list()

for (i in seq_len(nrow(artists))) {
  name <- artists$name[i]
  sid <- artists$spotify_id[i]
  log_info(sprintf("[%d/%d] %s", i, nrow(artists), name))

  all_posts <- list()
  sub_breakdown <- list()

  for (sub in SUBREDDITS) {
    posts <- pullpush_search(name, sub, type = "submission", size = 100)
    if (length(posts) > 0) {
      all_posts <- c(all_posts, posts)
      safe_num <- function(x) as.numeric(as.character(x %||% 0))
      scores <- map_dbl(posts, ~ safe_num(.x$score))
      comments <- map_dbl(posts, ~ safe_num(.x$num_comments))
      sub_breakdown[[sub]] <- list(
        post_count = length(posts),
        total_score = sum(scores),
        avg_score = round(mean(scores), 1),
        max_score = max(scores),
        total_comments = sum(comments)
      )
      log_info(sprintf("  r/%s: %d posts, total score %d", sub, length(posts), sum(scores)))
    }
  }

  if (length(all_posts) == 0) {
    log_warn("  No Reddit posts found")
    results[[i]] <- list(name = name, spotify_id = sid, found = FALSE, total_posts = 0)
    next
  }

  # Aggregate stats (created_utc may be string or numeric from PullPush)
  safe_num <- function(x) as.numeric(as.character(x %||% 0))
  all_scores <- map_dbl(all_posts, ~ safe_num(.x$score))
  all_comments <- map_dbl(all_posts, ~ safe_num(.x$num_comments))
  all_dates <- map_dbl(all_posts, ~ safe_num(.x$created_utc))

  # Recency: posts in last 90 days
  cutoff_90d <- as.numeric(Sys.time()) - (90 * 86400)
  cutoff_30d <- as.numeric(Sys.time()) - (30 * 86400)
  recent_90d <- keep(all_posts, ~ safe_num(.x$created_utc) > cutoff_90d)
  recent_30d <- keep(all_posts, ~ safe_num(.x$created_utc) > cutoff_30d)

  # Top posts (for context)
  sorted <- all_posts[order(-all_scores)]
  top_posts <- map(head(sorted, 5), ~ list(
    title = .x$title %||% "",
    score = safe_num(.x$score),
    num_comments = safe_num(.x$num_comments),
    subreddit = .x$subreddit %||% "",
    date = as.character(as.POSIXct(safe_num(.x$created_utc), origin = "1970-01-01"))
  ))

  results[[i]] <- list(
    name = name,
    spotify_id = sid,
    found = TRUE,
    total_posts = length(all_posts),
    total_score = sum(all_scores),
    avg_score = round(mean(all_scores), 1),
    max_score = max(all_scores),
    total_comments = sum(all_comments),
    posts_last_90d = length(recent_90d),
    posts_last_30d = length(recent_30d),
    subreddit_breakdown = sub_breakdown,
    top_posts = top_posts
  )
}

# --- Save ---
write_json_file(results, "mined_reddit.json", backup = FALSE)

# --- Summary ---
found <- sum(map_lgl(results, ~ isTRUE(.x$found)))
log_info("Done. Found Reddit presence for ", found, "/", nrow(artists), " artists")

with_posts <- keep(results, ~ isTRUE(.x$found))
with_posts <- with_posts[order(-map_dbl(with_posts, ~ .x$total_score))]
log_info("Top 15 by total Reddit score:")
for (r in head(with_posts, 15)) {
  log_info(sprintf("  %s: %d posts, score %d, %d comments, %d posts in 90d",
                   r$name, r$total_posts, r$total_score, r$total_comments, r$posts_last_90d))
}
