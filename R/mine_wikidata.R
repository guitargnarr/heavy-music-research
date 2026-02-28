#!/usr/bin/env Rscript
# mine_wikidata.R -- Cross-reference artist data against Wikidata structured data
# No auth required. Uses SPARQL endpoint.
# Output: data/mined_wikidata.json

source("R/utils.R")
library(purrr)

# --- Load artists ---
artists <- read_json_file("artists.json")
log_info("Cross-referencing ", nrow(artists), " artists against Wikidata")

# --- Build SPARQL query ---
# Wikidata properties:
#   P31  = instance of (Q215380 = musical group, Q5 = human)
#   P264 = record label
#   P136 = genre
#   P1902 = MusicBrainz artist ID
#   P434  = MusicBrainz artist ID (older property)
#   P1952 = Discogs artist ID
#   P1953 = Discogs master ID
#   P1559 = Setlist.fm artist ID
#   P137  = operator (sometimes used for management)
#   P127  = owned by
#   P495  = country of origin
#   P571  = inception date

# Build filter string for all artist names
name_filter <- paste0(
  'FILTER(?bandLabel IN (',
  paste(sprintf('"%s"@en', artists$name), collapse = ", "),
  '))'
)

sparql_query <- paste0('
SELECT DISTINCT ?band ?bandLabel ?mbid ?discogsId
  (GROUP_CONCAT(DISTINCT ?labelLabel; SEPARATOR="|") AS ?labels)
  (GROUP_CONCAT(DISTINCT ?genreLabel; SEPARATOR="|") AS ?genres)
  ?countryLabel ?inception
WHERE {
  ?band wdt:P31/wdt:P279* wd:Q2088357 .
  ?band rdfs:label ?bandLabel .
  FILTER(LANG(?bandLabel) = "en")
  ', name_filter, '
  OPTIONAL { ?band wdt:P1902 ?mbid }
  OPTIONAL { ?band wdt:P1952 ?discogsId }
  OPTIONAL {
    ?band wdt:P264 ?label .
    ?label rdfs:label ?labelLabel .
    FILTER(LANG(?labelLabel) = "en")
  }
  OPTIONAL {
    ?band wdt:P136 ?genre .
    ?genre rdfs:label ?genreLabel .
    FILTER(LANG(?genreLabel) = "en")
  }
  OPTIONAL {
    ?band wdt:P495 ?country .
    ?country rdfs:label ?countryLabel .
    FILTER(LANG(?countryLabel) = "en")
  }
  OPTIONAL { ?band wdt:P571 ?inception }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
}
GROUP BY ?band ?bandLabel ?mbid ?discogsId ?countryLabel ?inception
ORDER BY ?bandLabel
')

# Also try Q215380 (musical group) as some bands use that instead
sparql_query_alt <- paste0('
SELECT DISTINCT ?band ?bandLabel ?mbid ?discogsId
  (GROUP_CONCAT(DISTINCT ?labelLabel; SEPARATOR="|") AS ?labels)
  (GROUP_CONCAT(DISTINCT ?genreLabel; SEPARATOR="|") AS ?genres)
  ?countryLabel ?inception
WHERE {
  ?band wdt:P31 wd:Q215380 .
  ?band rdfs:label ?bandLabel .
  FILTER(LANG(?bandLabel) = "en")
  ', name_filter, '
  OPTIONAL { ?band wdt:P1902 ?mbid }
  OPTIONAL { ?band wdt:P1952 ?discogsId }
  OPTIONAL {
    ?band wdt:P264 ?label .
    ?label rdfs:label ?labelLabel .
    FILTER(LANG(?labelLabel) = "en")
  }
  OPTIONAL {
    ?band wdt:P136 ?genre .
    ?genre rdfs:label ?genreLabel .
    FILTER(LANG(?genreLabel) = "en")
  }
  OPTIONAL {
    ?band wdt:P495 ?country .
    ?country rdfs:label ?countryLabel .
    FILTER(LANG(?countryLabel) = "en")
  }
  OPTIONAL { ?band wdt:P571 ?inception }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
}
GROUP BY ?band ?bandLabel ?mbid ?discogsId ?countryLabel ?inception
ORDER BY ?bandLabel
')

# --- Execute SPARQL ---
run_sparql <- function(query) {
  log_info("Executing SPARQL query...")
  resp <- tryCatch({
    req <- request("https://query.wikidata.org/sparql") |>
      req_url_query(query = query, format = "json") |>
      req_headers(
        `User-Agent` = "MetalcoreIndex/1.0 (matthewdscott7@gmail.com)",
        Accept = "application/sparql-results+json"
      ) |>
      req_timeout(60)
    req_perform(req)
  }, error = function(e) {
    log_error("SPARQL query failed: ", e$message)
    return(NULL)
  })

  if (is.null(resp)) return(NULL)
  if (resp_status(resp) != 200) {
    log_warn("Wikidata returned ", resp_status(resp))
    return(NULL)
  }

  body <- resp_body_json(resp)
  bindings <- body$results$bindings
  log_info("Got ", length(bindings), " results from Wikidata")
  bindings
}

# Try both entity types and merge
results1 <- run_sparql(sparql_query)
Sys.sleep(2)
results2 <- run_sparql(sparql_query_alt)

# Merge results, dedup by band URI
all_results <- c(results1 %||% list(), results2 %||% list())
seen_bands <- character()
deduped <- list()
for (r in all_results) {
  band_uri <- r$band$value %||% ""
  if (!band_uri %in% seen_bands) {
    seen_bands <- c(seen_bands, band_uri)
    deduped[[length(deduped) + 1]] <- r
  }
}
log_info("After dedup: ", length(deduped), " unique bands")

# --- Parse results ---
parsed <- map(deduped, function(r) {
  list(
    name = r$bandLabel$value %||% NA,
    wikidata_uri = r$band$value %||% NA,
    musicbrainz_id = r$mbid$value %||% NA,
    discogs_id = r$discogsId$value %||% NA,
    labels = if (!is.null(r$labels$value) && r$labels$value != "")
      strsplit(r$labels$value, "\\|")[[1]] else character(),
    genres = if (!is.null(r$genres$value) && r$genres$value != "")
      strsplit(r$genres$value, "\\|")[[1]] else character(),
    country = r$countryLabel$value %||% NA,
    inception = r$inception$value %||% NA
  )
})

# --- Cross-check against our data ---
cat("\n========== WIKIDATA CROSS-REFERENCE ==========\n")

discrepancies <- list()
matched <- 0
not_found <- character()

for (i in seq_len(nrow(artists))) {
  name <- artists$name[i]
  our_label <- artists$current_label[i]

  # Find in Wikidata results
  wiki <- keep(parsed, ~ !is.na(.x$name) && tolower(.x$name) == tolower(name))

  if (length(wiki) == 0) {
    not_found <- c(not_found, name)
    next
  }

  w <- wiki[[1]]
  matched <- matched + 1

  # Check label discrepancy
  if (length(w$labels) > 0 && !is.null(our_label) && !is.na(our_label)) {
    # Check if any Wikidata label matches our label (partial match for compound labels)
    our_labels_split <- trimws(unlist(strsplit(our_label, "[/,]")))
    wiki_matches <- any(sapply(w$labels, function(wl) {
      any(sapply(our_labels_split, function(ol) {
        grepl(tolower(ol), tolower(wl), fixed = TRUE) ||
          grepl(tolower(wl), tolower(ol), fixed = TRUE)
      }))
    }))

    if (!wiki_matches) {
      discrepancies[[length(discrepancies) + 1]] <- list(
        artist = name,
        field = "label",
        our_value = our_label,
        wikidata_value = paste(w$labels, collapse = " | ")
      )
    }
  }

  # Log MusicBrainz ID if we got one
  if (!is.na(w$musicbrainz_id)) {
    cat(sprintf("  %-30s MBID: %s\n", name, w$musicbrainz_id))
  }
}

cat(sprintf("\nMatched: %d / %d artists\n", matched, nrow(artists)))
cat(sprintf("Not found in Wikidata: %d\n", length(not_found)))
if (length(not_found) > 0) {
  cat("  Missing: ", paste(not_found, collapse = ", "), "\n")
}

if (length(discrepancies) > 0) {
  cat(sprintf("\nLabel discrepancies found: %d\n", length(discrepancies)))
  for (d in discrepancies) {
    cat(sprintf("  %-25s Ours: %-30s Wiki: %s\n", d$artist, d$our_value, d$wikidata_value))
  }
}

# --- Save output ---
output <- list(
  matched = matched,
  not_found = not_found,
  artists = parsed,
  discrepancies = discrepancies
)

output_path <- file.path(DATA_DIR, "mined_wikidata.json")
write_json(output, output_path, pretty = TRUE, auto_unbox = TRUE, na = "null")
log_info("Wrote ", output_path)

cat("\n========== WIKIDATA MINING COMPLETE ==========\n")
