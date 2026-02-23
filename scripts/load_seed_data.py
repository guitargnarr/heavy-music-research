"""
Load seed data JSON files into the database.
Run from the api/ directory (or set DATABASE_URL).

Usage:
  cd api && source .venv/bin/activate
  python ../scripts/load_seed_data.py
"""
import json
import os
import sys

# Add api/ to path so we can import database/models
api_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "api")
sys.path.insert(0, api_dir)

from database import Base, engine, SessionLocal  # noqa: E402
from models import Artist, Producer, Label, Relationship  # noqa: E402

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path) as f:
        return json.load(f)


def seed_artists(db):
    artists_data = load_json("artists.json")

    # Check for spotify_matches.json for resolved IDs
    matches_path = os.path.join(DATA_DIR, "spotify_matches.json")
    spotify_map = {}
    if os.path.exists(matches_path):
        matches = load_json("spotify_matches.json")
        for m in matches:
            spotify_map[m["name"]] = m

    count = 0
    for a in artists_data:
        match = spotify_map.get(a["name"])
        spotify_id = match["spotify_id"] if match else a["spotify_id"]
        image_url = match.get("image_url") if match else None
        genres = match.get("genres", a.get("genres", [])) if match else a.get("genres", [])

        existing = db.query(Artist).filter(Artist.spotify_id == spotify_id).first()
        if existing:
            continue

        artist = Artist(
            spotify_id=spotify_id,
            name=a["name"],
            genres=json.dumps(genres),
            image_url=image_url,
            current_label=a.get("current_label"),
            current_manager=a.get("current_manager"),
            current_management_co=a.get("current_management_co"),
            booking_agency=a.get("booking_agency"),
            active=True,
        )
        db.add(artist)
        count += 1

    db.commit()
    print(f"Loaded {count} artists")


def seed_producers(db):
    producers_data = load_json("producers.json")
    count = 0
    for p in producers_data:
        existing = db.query(Producer).filter(Producer.name == p["name"]).first()
        if existing:
            continue

        producer = Producer(
            name=p["name"],
            studio_name=p.get("studio_name"),
            location=p.get("location"),
            credits=json.dumps(p.get("credits", [])),
            tier=p.get("tier"),
            sonic_signature=p.get("sonic_signature"),
        )
        db.add(producer)
        count += 1

    db.commit()
    print(f"Loaded {count} producers")


def seed_labels(db):
    labels_data = load_json("labels.json")
    count = 0
    for lbl in labels_data:
        existing = db.query(Label).filter(Label.name == lbl["name"]).first()
        if existing:
            continue

        label = Label(
            name=lbl["name"],
            parent_company=lbl.get("parent_company"),
            distribution=lbl.get("distribution"),
            key_contact=lbl.get("key_contact"),
            contact_title=lbl.get("contact_title"),
        )
        db.add(label)
        count += 1

    db.commit()
    print(f"Loaded {count} labels")


def seed_relationships(db):
    rels_data = load_json("relationships.json")
    count = 0
    for r in rels_data:
        existing = (
            db.query(Relationship)
            .filter(
                Relationship.source_type == r["source_type"],
                Relationship.source_id == r["source_id"],
                Relationship.target_type == r["target_type"],
                Relationship.target_id == r["target_id"],
                Relationship.relationship_type == r["relationship_type"],
            )
            .first()
        )
        if existing:
            continue

        rel = Relationship(
            source_type=r["source_type"],
            source_id=r["source_id"],
            target_type=r["target_type"],
            target_id=r["target_id"],
            relationship_type=r["relationship_type"],
        )
        db.add(rel)
        count += 1

    db.commit()
    print(f"Loaded {count} relationships")


def main():
    print("=== Loading seed data into database ===\n")

    # Create tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        seed_artists(db)
        seed_producers(db)
        seed_labels(db)
        seed_relationships(db)

        # Stats
        print("\n=== Database Stats ===")
        print(f"Artists:       {db.query(Artist).count()}")
        print(f"Producers:     {db.query(Producer).count()}")
        print(f"Labels:        {db.query(Label).count()}")
        print(f"Relationships: {db.query(Relationship).count()}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
