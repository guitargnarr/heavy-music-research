"""
Resolve Spotify artist IDs for seeded bands.

Uses spotipy with client credentials flow (no user OAuth needed).
Requires SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET env vars.

Outputs:
- data/spotify_matches.json (auto-matched artists with confidence)
- data/spotify_review.csv (for manual disambiguation)

Usage:
  export SPOTIPY_CLIENT_ID=your_client_id
  export SPOTIPY_CLIENT_SECRET=your_client_secret
  python scripts/seed_spotify_ids.py
"""
import json
import csv
import os
import time

try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
except ImportError:
    print("spotipy not installed. Run: pip install spotipy")
    print("\nGenerating manual lookup template instead...\n")
    spotipy = None

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def load_artists():
    path = os.path.join(DATA_DIR, "artists.json")
    with open(path) as f:
        return json.load(f)


def resolve_with_spotipy(artists):
    """Use Spotify API to resolve artist names to IDs."""
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials())
    matches = []
    review_rows = []

    for artist in artists:
        name = artist["name"]
        try:
            results = sp.search(q=f"artist:{name}", type="artist", limit=5)
            items = results["artists"]["items"]
        except Exception as e:
            print(f"  ERROR searching '{name}': {e}")
            review_rows.append({
                "name": name,
                "spotify_id": "",
                "spotify_name": "",
                "followers": "",
                "popularity": "",
                "genres": "",
                "confidence": "ERROR",
                "notes": str(e),
            })
            time.sleep(1)
            continue

        if not items:
            print(f"  NO RESULTS: {name}")
            review_rows.append({
                "name": name,
                "spotify_id": "",
                "spotify_name": "",
                "followers": "",
                "popularity": "",
                "genres": "",
                "confidence": "NOT_FOUND",
                "notes": "",
            })
            continue

        # Check for exact name match
        exact = [i for i in items if i["name"].lower() == name.lower()]
        if exact:
            best = exact[0]
            confidence = "HIGH"
        else:
            best = items[0]
            confidence = "LOW"

        match = {
            "name": name,
            "spotify_id": best["id"],
            "spotify_name": best["name"],
            "followers": best["followers"]["total"],
            "popularity": best["popularity"],
            "genres": best.get("genres", []),
            "image_url": best["images"][0]["url"] if best.get("images") else None,
        }
        matches.append(match)

        review_rows.append({
            "name": name,
            "spotify_id": best["id"],
            "spotify_name": best["name"],
            "followers": best["followers"]["total"],
            "popularity": best["popularity"],
            "genres": "; ".join(best.get("genres", [])),
            "confidence": confidence,
            "notes": f"{len(items)} results" if len(items) > 1 else "",
        })

        followers_fmt = f"{best['followers']['total']:,}"
        print(f"  {confidence}: {name} -> {best['name']} "
              f"(pop={best['popularity']}, followers={followers_fmt})")
        time.sleep(0.1)  # Rate limit courtesy

    return matches, review_rows


def generate_manual_template(artists):
    """Generate a CSV template for manual Spotify ID lookup."""
    review_path = os.path.join(DATA_DIR, "spotify_review.csv")
    with open(review_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "name", "spotify_id", "spotify_name", "followers",
            "popularity", "genres", "confidence", "notes",
        ])
        writer.writeheader()
        for artist in artists:
            writer.writerow({
                "name": artist["name"],
                "spotify_id": "",
                "spotify_name": "",
                "followers": "",
                "popularity": "",
                "genres": "; ".join(artist.get("genres", [])),
                "confidence": "MANUAL",
                "notes": "Fill in spotify_id from open.spotify.com",
            })
    print(f"Wrote manual template to {review_path}")
    print("Fill in spotify_id column from https://open.spotify.com/search/")
    print("Artist Spotify ID is in the URL: open.spotify.com/artist/{ID}")


def main():
    artists = load_artists()
    print(f"Loaded {len(artists)} artists\n")

    if spotipy is None or not os.getenv("SPOTIPY_CLIENT_ID"):
        print("No Spotify credentials found.")
        print("Set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET to auto-resolve.")
        print("Generating manual template...\n")
        generate_manual_template(artists)
        return

    print("Resolving Spotify IDs...\n")
    matches, review_rows = resolve_with_spotipy(artists)

    # Save matches
    matches_path = os.path.join(DATA_DIR, "spotify_matches.json")
    with open(matches_path, "w") as f:
        json.dump(matches, f, indent=2)
    print(f"\nWrote {len(matches)} matches to {matches_path}")

    # Save review CSV
    review_path = os.path.join(DATA_DIR, "spotify_review.csv")
    with open(review_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "name", "spotify_id", "spotify_name", "followers",
            "popularity", "genres", "confidence", "notes",
        ])
        writer.writeheader()
        writer.writerows(review_rows)
    print(f"Wrote review CSV to {review_path}")

    # Stats
    high = sum(1 for r in review_rows if r["confidence"] == "HIGH")
    low = sum(1 for r in review_rows if r["confidence"] == "LOW")
    missing = sum(1 for r in review_rows if r["confidence"] in ("NOT_FOUND", "ERROR"))
    print(f"\nConfidence: {high} HIGH, {low} LOW (need review), {missing} MISSING")


if __name__ == "__main__":
    main()
