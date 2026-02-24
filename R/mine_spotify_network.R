#!/usr/bin/env Rscript
# mine_spotify_network.R -- Mine Spotify related artists to build network graph
# Uses Spotify Web API client credentials flow (httr2, no spotifyr dependency)
# Requires: SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET env vars
# Output: data/mined_spotify_network.json, data/expansion_candidates.json

source("R/utils.R")
library(purrr)
library(igraph)
library(tidyr)

# --- Spotify Auth ---
spotify_get_token <- function() {
  client_id <- Sys.getenv("SPOTIPY_CLIENT_ID")
  client_secret <- Sys.getenv("SPOTIPY_CLIENT_SECRET")

  if (client_id == "" || client_secret == "") {
    stop("Set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET environment variables.")
  }

  resp <- request("https://accounts.spotify.com/api/token") |>
    req_method("POST") |>
    req_body_form(grant_type = "client_credentials") |>
    req_auth_basic(client_id, client_secret) |>
    req_perform()

  token <- resp_body_json(resp)
  log_info("Spotify token acquired (expires in ", token$expires_in, "s)")
  token$access_token
}

# --- Spotify API helpers ---
spotify_request <- function(endpoint, token, params = list()) {
  rate_limit("spotify", 0.1)  # 10 req/sec is safe
  url <- paste0("https://api.spotify.com/v1/", endpoint)

  resp <- tryCatch({
    req <- request(url) |>
      req_url_query(!!!params) |>
      req_auth_bearer_token(token) |>
      req_retry(max_tries = 3, backoff = ~2)
    req_perform(req)
  }, error = function(e) {
    log_error("Spotify request failed: ", e$message)
    return(NULL)
  })

  if (is.null(resp)) return(NULL)
  status <- resp_status(resp)
  if (status == 429) {
    retry_after <- resp_header(resp, "Retry-After") %||% "5"
    log_warn("Rate limited, waiting ", retry_after, "s...")
    Sys.sleep(as.numeric(retry_after))
    return(spotify_request(endpoint, token, params))
  }
  if (status != 200) {
    log_warn("Spotify returned ", status, " for ", endpoint)
    return(NULL)
  }
  resp_body_json(resp)
}

# Search artist by name -> get Spotify ID
spotify_search_artist <- function(name, token) {
  result <- spotify_request("search", token, params = list(q = name, type = "artist", limit = 5))
  if (is.null(result) || length(result$artists$items) == 0) return(NULL)

  items <- result$artists$items
  # Prefer exact match
  for (item in items) {
    if (name_match(item$name, name)) {
      return(list(id = item$id, name = item$name, popularity = item$popularity,
                  followers = item$followers$total))
    }
  }
  # Fallback: first result
  item <- items[[1]]
  list(id = item$id, name = item$name, popularity = item$popularity,
       followers = item$followers$total)
}

# Get related artists for an artist ID
spotify_get_related <- function(artist_id, token) {
  result <- spotify_request(paste0("artists/", artist_id, "/related-artists"), token)
  if (is.null(result) || length(result$artists) == 0) return(list())

  map(result$artists, function(a) {
    list(id = a$id, name = a$name, popularity = a$popularity,
         followers = a$followers$total,
         genres = paste(a$genres, collapse = ", "))
  })
}

# --- Load artists ---
artists <- read_json_file("artists.json")
artist_names <- artists$name
log_info("Building Spotify related artist network for ", length(artist_names), " artists")

# Get token
token <- spotify_get_token()

# --- Step 1: Resolve all artist names to Spotify IDs ---
log_info("Step 1: Resolving artist names to Spotify IDs...")
artist_map <- list()  # name -> {id, name, popularity, followers}

for (i in seq_along(artist_names)) {
  name <- artist_names[i]
  log_info(sprintf("  [%d/%d] %s", i, length(artist_names), name))

  result <- spotify_search_artist(name, token)
  if (!is.null(result)) {
    artist_map[[name]] <- result
    log_info("    -> ", result$name, " (pop:", result$popularity, ", followers:", result$followers, ")")
  } else {
    log_warn("    NOT FOUND on Spotify")
  }
}

log_info("Resolved ", length(artist_map), "/", length(artist_names), " artists")

# --- Step 2: Get related artists for each ---
log_info("Step 2: Fetching related artists...")
edges <- list()
all_related <- list()  # Track all external artists we discover

for (name in names(artist_map)) {
  info <- artist_map[[name]]
  log_info(sprintf("  %s (id:%s)", name, info$id))

  related <- spotify_get_related(info$id, token)
  if (length(related) == 0) {
    log_info("    -> 0 related artists")
    next
  }

  log_info("    -> ", length(related), " related artists")

  for (j in seq_along(related)) {
    rel <- related[[j]]
    # Add edge
    edges[[length(edges) + 1]] <- list(
      source = name,
      source_id = info$id,
      target = rel$name,
      target_id = rel$id,
      weight = j,  # Position in list (1 = most related)
      target_popularity = rel$popularity,
      target_followers = rel$followers,
      target_genres = rel$genres
    )

    # Track external discoveries
    if (!rel$name %in% artist_names) {
      key <- rel$id
      if (is.null(all_related[[key]])) {
        all_related[[key]] <- list(
          name = rel$name,
          id = rel$id,
          popularity = rel$popularity,
          followers = rel$followers,
          genres = rel$genres,
          referred_by = list(name),
          count = 1
        )
      } else {
        all_related[[key]]$referred_by <- c(all_related[[key]]$referred_by, list(name))
        all_related[[key]]$count <- all_related[[key]]$count + 1
      }
    }
  }
}

log_info("Total edges: ", length(edges))
log_info("External artists discovered: ", length(all_related))

# --- Step 3: Identify internal connections ---
internal_edges <- keep(edges, function(e) {
  e$target %in% artist_names
})
log_info("Internal connections (both artists in our dataset): ", length(internal_edges))

# --- Step 4: Network analysis with igraph ---
if (length(internal_edges) > 0) {
  edge_df <- tibble(
    source = sapply(internal_edges, function(e) e$source),
    target = sapply(internal_edges, function(e) e$target),
    weight = sapply(internal_edges, function(e) 21 - e$weight)  # Higher weight = more related
  )

  # Build graph
  g <- graph_from_data_frame(edge_df, directed = FALSE)
  g <- simplify(g)

  # Community detection
  communities <- cluster_louvain(g)
  n_communities <- length(communities)

  # Centrality
  deg <- degree(g)
  betw <- betweenness(g)
  top_central <- sort(deg, decreasing = TRUE)[1:min(10, length(deg))]

  cat("\n========== NETWORK ANALYSIS ==========\n")
  cat(sprintf("Nodes in internal graph:   %d\n", vcount(g)))
  cat(sprintf("Edges in internal graph:   %d\n", ecount(g)))
  cat(sprintf("Communities detected:       %d\n", n_communities))

  cat("\nTop 10 most connected (degree centrality):\n")
  for (nm in names(top_central)) {
    cat(sprintf("  %-30s  degree=%d  community=%d\n", nm, top_central[nm],
                membership(communities)[nm]))
  }

  cat("\nCommunity breakdown:\n")
  for (i in seq_len(n_communities)) {
    members <- names(membership(communities))[membership(communities) == i]
    cat(sprintf("  Community %d (%d members): %s\n", i, length(members),
                paste(head(members, 5), collapse=", "),
                if (length(members) > 5) paste0(", +", length(members) - 5, " more") else ""))
  }
  cat("======================================\n")
}

# --- Step 5: Expansion candidates ---
# Sort external artists by how many of our artists reference them
expansion <- all_related[order(sapply(all_related, function(x) x$count), decreasing = TRUE)]
expansion_top <- expansion[1:min(30, length(expansion))]

cat("\n========== EXPANSION CANDIDATES ==========\n")
cat(sprintf("Top artists NOT in our dataset (by referral count):\n"))
for (ext in expansion_top) {
  refs <- paste(unlist(ext$referred_by), collapse = ", ")
  cat(sprintf("  %-30s  pop=%3d  refs=%d  genres=[%s]\n",
              ext$name, ext$popularity, ext$count,
              substr(ext$genres, 1, 50)))
  cat(sprintf("    referred by: %s\n", refs))
}
cat("==========================================\n")

# --- Save outputs ---

# 1. Full edge list
edge_output <- map(edges, function(e) {
  list(
    source = e$source,
    target = e$target,
    weight = e$weight,
    target_popularity = e$target_popularity,
    target_followers = e$target_followers
  )
})
write_json(edge_output, file.path(DATA_DIR, "mined_spotify_network.json"),
           pretty = TRUE, auto_unbox = TRUE)
log_info("Wrote ", length(edge_output), " edges to mined_spotify_network.json")

# 2. Expansion candidates
expansion_output <- map(expansion_top, function(e) {
  list(
    name = e$name,
    spotify_id = e$id,
    popularity = e$popularity,
    followers = e$followers,
    genres = e$genres,
    referral_count = e$count,
    referred_by = unlist(e$referred_by)
  )
})
write_json(expansion_output, file.path(DATA_DIR, "expansion_candidates.json"),
           pretty = TRUE, auto_unbox = TRUE)
log_info("Wrote ", length(expansion_output), " candidates to expansion_candidates.json")

# 3. Updated Spotify IDs for artists (many may have placeholder IDs)
spotify_id_map <- map(names(artist_map), function(name) {
  info <- artist_map[[name]]
  list(name = name, spotify_id = info$id, popularity = info$popularity,
       followers = info$followers)
})
write_json(spotify_id_map, file.path(DATA_DIR, "spotify_id_updates.json"),
           pretty = TRUE, auto_unbox = TRUE)
log_info("Wrote Spotify ID updates for ", length(spotify_id_map), " artists")

cat("\nDone! Run merge_mined_data.R to integrate results.\n")
