"""
Extract seed data from heavy-music-industry-landscape-2026.md.
Produces JSON files in data/ for database seeding.

Sources:
- Section 4: Artist-Label Map (14 bands)
- Section 8: Producers & Engineers (21 producers)
- Section 8: Who Produced What (14 band-producer pairs)
- Section 3: Corporate Label Ecosystem (25+ labels)
- Section 5: Management Companies (8 companies)
- Section 6: Booking Agencies (5 agencies)
- Section 2: Genre Taxonomy (additional bands from subgenre map)
"""
import json
import os

# Output directory
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)


def seed_artists():
    """14 bands from Section 4 Artist-Label Map + additional bands from genre tables."""
    artists = [
        {
            "name": "Knocked Loose",
            "current_label": "Pure Noise Records",
            "distribution": "Orchard (Sony) / ADA (Warner)",
            "current_manager": "James Vitalo",
            "current_management_co": "5B Artists + Media",
            "booking_agency": "Wasserman",
            "genres": ["metalcore", "hardcore"],
        },
        {
            "name": "Spiritbox",
            "current_label": "Pale Chord / Rise Records",
            "distribution": "BMG",
            "current_manager": "Jason Mageau",
            "current_management_co": "Culture Wave",
            "booking_agency": "IAG",
            "genres": ["progressive metalcore", "alt-metal"],
        },
        {
            "name": "Sleep Token",
            "current_label": "RCA Records",
            "distribution": "Sony Music",
            "current_manager": "Ryan Richards",
            "current_management_co": "Future History Management",
            "booking_agency": "UTA",
            "genres": ["post-metalcore", "alt-metal"],
        },
        {
            "name": "Periphery",
            "current_label": "3DOT Recordings",
            "distribution": "MNRK / eOne",
            "current_manager": "Wayne Pighini",
            "current_management_co": "Fly South Music Group",
            "booking_agency": "UTA",
            "genres": ["progressive metalcore", "djent"],
        },
        {
            "name": "Lamb of God",
            "current_label": "Epic Records / Nuclear Blast",
            "distribution": "Sony + Believe",
            "current_manager": "Brad Fuhrman",
            "current_management_co": "5B Artists + Media",
            "booking_agency": "Wasserman",
            "genres": ["groove metal"],
        },
        {
            "name": "Erra",
            "current_label": "UNFD",
            "distribution": "FUGA / Downtown Music",
            "current_manager": "Cory Hajde",
            "current_management_co": "Alternate Side / BravoArtist",
            "booking_agency": None,
            "genres": ["progressive metalcore"],
        },
        {
            "name": "Whitechapel",
            "current_label": "Metal Blade Records",
            "distribution": "RED (Sony) / Warner",
            "current_manager": "Steve Davis, Vaughn Lewis",
            "current_management_co": None,
            "booking_agency": None,
            "genres": ["deathcore"],
        },
        {
            "name": "Kublai Khan TX",
            "current_label": "Rise Records",
            "distribution": "BMG",
            "current_manager": None,
            "current_management_co": None,
            "booking_agency": None,
            "genres": ["metalcore", "hardcore"],
        },
        {
            "name": "Born of Osiris",
            "current_label": "Sumerian Records",
            "distribution": "Virgin Music (UMG)",
            "current_manager": "E.J. Shannon",
            "current_management_co": None,
            "booking_agency": "Avocado Booking",
            "genres": ["progressive metalcore", "djent"],
        },
        {
            "name": "Bilmuri",
            "current_label": "Columbia Records",
            "distribution": "Sony Music",
            "current_manager": "Jameson Roper",
            "current_management_co": None,
            "booking_agency": "Wasserman",
            "genres": ["metalcore", "alt-metal"],
        },
        {
            "name": "Thrown",
            "current_label": "Arising Empire",
            "distribution": "Kontor New Media",
            "current_manager": None,
            "current_management_co": None,
            "booking_agency": None,
            "genres": ["nu-metalcore"],
        },
        {
            "name": "Lorna Shore",
            "current_label": "Century Media",
            "distribution": "Sony Music",
            "current_manager": None,
            "current_management_co": None,
            "booking_agency": None,
            "genres": ["deathcore"],
        },
        {
            "name": "Bad Omens",
            "current_label": "Sumerian Records",
            "distribution": "Virgin Music (UMG)",
            "current_manager": None,
            "current_management_co": None,
            "booking_agency": None,
            "genres": ["post-metalcore", "alt-metal"],
        },
        {
            "name": "Turnstile",
            "current_label": "Roadrunner Records",
            "distribution": "Warner Music Group",
            "current_manager": "James Vitalo",
            "current_management_co": "5B Artists + Media",
            "booking_agency": None,
            "genres": ["hardcore"],
        },
        # Additional bands from genre tables and other sections
        {
            "name": "Architects",
            "current_label": "Epitaph Records",
            "distribution": "Epitaph (self-distributed)",
            "current_manager": None,
            "current_management_co": None,
            "booking_agency": None,
            "genres": ["metalcore"],
        },
        {
            "name": "Wage War",
            "current_label": None,
            "distribution": None,
            "current_manager": None,
            "current_management_co": "Fly South Music Group",
            "booking_agency": "UTA",
            "genres": ["metalcore"],
        },
        {
            "name": "Veil of Maya",
            "current_label": None,
            "distribution": None,
            "current_manager": None,
            "current_management_co": "Outerloop Group",
            "booking_agency": None,
            "genres": ["progressive metalcore", "djent"],
        },
        {
            "name": "Animals As Leaders",
            "current_label": "Sumerian Records",
            "distribution": "Virgin Music (UMG)",
            "current_manager": None,
            "current_management_co": None,
            "booking_agency": None,
            "genres": ["progressive metal", "djent"],
        },
        {
            "name": "Dayseeker",
            "current_label": "Spinefarm Records",
            "distribution": "Universal Music Group",
            "current_manager": None,
            "current_management_co": None,
            "booking_agency": None,
            "genres": ["post-metalcore", "alt-metal"],
        },
        {
            "name": "Slaughter to Prevail",
            "current_label": None,
            "distribution": None,
            "current_manager": None,
            "current_management_co": None,
            "booking_agency": None,
            "genres": ["deathcore"],
        },
        {
            "name": "Drain",
            "current_label": None,
            "distribution": None,
            "current_manager": None,
            "current_management_co": None,
            "booking_agency": "Wasserman",
            "genres": ["hardcore"],
        },
        {
            "name": "Fit for an Autopsy",
            "current_label": "MNRK Music Group",
            "distribution": "MNRK",
            "current_manager": None,
            "current_management_co": None,
            "booking_agency": None,
            "genres": ["deathcore"],
        },
        {
            "name": "Counterparts",
            "current_label": None,
            "distribution": None,
            "current_manager": None,
            "current_management_co": None,
            "booking_agency": "Wasserman",
            "genres": ["metalcore", "hardcore"],
        },
        {
            "name": "Ice Nine Kills",
            "current_label": "Fearless Records",
            "distribution": "Concord",
            "current_manager": None,
            "current_management_co": "Outerloop Group",
            "booking_agency": None,
            "genres": ["metalcore"],
        },
        {
            "name": "Motionless In White",
            "current_label": "Roadrunner Records",
            "distribution": "Warner Music Group",
            "current_manager": None,
            "current_management_co": None,
            "booking_agency": None,
            "genres": ["metalcore", "gothic metal"],
        },
        {
            "name": "Gojira",
            "current_label": "Roadrunner Records",
            "distribution": "Warner Music Group",
            "current_manager": None,
            "current_management_co": None,
            "booking_agency": None,
            "genres": ["groove metal", "progressive metal"],
        },
        {
            "name": "Trivium",
            "current_label": "Roadrunner Records",
            "distribution": "Warner Music Group",
            "current_manager": None,
            "current_management_co": None,
            "booking_agency": None,
            "genres": ["metalcore", "thrash metal"],
        },
        {
            "name": "August Burns Red",
            "current_label": None,
            "distribution": None,
            "current_manager": None,
            "current_management_co": None,
            "booking_agency": None,
            "genres": ["metalcore"],
        },
        {
            "name": "Loathe",
            "current_label": None,
            "distribution": None,
            "current_manager": None,
            "current_management_co": "Culture Wave",
            "booking_agency": None,
            "genres": ["nu-metalcore", "alt-metal"],
        },
        {
            "name": "Alpha Wolf",
            "current_label": None,
            "distribution": None,
            "current_manager": None,
            "current_management_co": None,
            "booking_agency": None,
            "genres": ["nu-metalcore"],
        },
        {
            "name": "Invent Animate",
            "current_label": None,
            "distribution": None,
            "current_manager": None,
            "current_management_co": None,
            "booking_agency": None,
            "genres": ["progressive metalcore"],
        },
        {
            "name": "Polaris",
            "current_label": None,
            "distribution": None,
            "current_manager": None,
            "current_management_co": "Culture Wave",
            "booking_agency": None,
            "genres": ["metalcore"],
        },
        {
            "name": "Silent Planet",
            "current_label": None,
            "distribution": None,
            "current_manager": "Cory Hajde",
            "current_management_co": "Alternate Side",
            "booking_agency": None,
            "genres": ["metalcore"],
        },
        {
            "name": "Fit For A King",
            "current_label": None,
            "distribution": None,
            "current_manager": "Cory Hajde",
            "current_management_co": "Alternate Side",
            "booking_agency": None,
            "genres": ["metalcore"],
        },
        {
            "name": "Dance Gavin Dance",
            "current_label": "Rise Records",
            "distribution": "BMG",
            "current_manager": None,
            "current_management_co": None,
            "booking_agency": None,
            "genres": ["post-hardcore", "progressive"],
        },
        {
            "name": "We Came As Romans",
            "current_label": None,
            "distribution": None,
            "current_manager": None,
            "current_management_co": "Culture Wave",
            "booking_agency": "Wasserman",
            "genres": ["metalcore"],
        },
        {
            "name": "After The Burial",
            "current_label": None,
            "distribution": None,
            "current_manager": None,
            "current_management_co": "Culture Wave",
            "booking_agency": None,
            "genres": ["progressive metalcore", "djent"],
        },
        {
            "name": "Brand Of Sacrifice",
            "current_label": None,
            "distribution": None,
            "current_manager": None,
            "current_management_co": "Culture Wave",
            "booking_agency": None,
            "genres": ["deathcore"],
        },
        {
            "name": "Currents",
            "current_label": None,
            "distribution": None,
            "current_manager": None,
            "current_management_co": None,
            "booking_agency": None,
            "genres": ["metalcore"],
        },
        {
            "name": "Like Moths To Flames",
            "current_label": None,
            "distribution": None,
            "current_manager": None,
            "current_management_co": None,
            "booking_agency": None,
            "genres": ["metalcore"],
        },
        {
            "name": "Rivers of Nihil",
            "current_label": None,
            "distribution": None,
            "current_manager": None,
            "current_management_co": None,
            "booking_agency": None,
            "genres": ["progressive metal", "death metal"],
        },
        {
            "name": "Between the Buried and Me",
            "current_label": None,
            "distribution": None,
            "current_manager": None,
            "current_management_co": None,
            "booking_agency": None,
            "genres": ["progressive metal"],
        },
        {
            "name": "A Day To Remember",
            "current_label": None,
            "distribution": None,
            "current_manager": None,
            "current_management_co": "Fly South Music Group",
            "booking_agency": "CAA",
            "genres": ["metalcore", "pop-punk"],
        },
        {
            "name": "Underoath",
            "current_label": "Fearless Records",
            "distribution": "Concord",
            "current_manager": None,
            "current_management_co": None,
            "booking_agency": None,
            "genres": ["metalcore", "post-hardcore"],
        },
        {
            "name": "Northlane",
            "current_label": "UNFD",
            "distribution": "FUGA",
            "current_manager": None,
            "current_management_co": None,
            "booking_agency": None,
            "genres": ["metalcore", "djent"],
        },
        {
            "name": "Bring Me the Horizon",
            "current_label": None,
            "distribution": None,
            "current_manager": None,
            "current_management_co": "Raw Power Management",
            "booking_agency": None,
            "genres": ["metalcore", "alt-metal"],
        },
        {
            "name": "The Ghost Inside",
            "current_label": None,
            "distribution": None,
            "current_manager": None,
            "current_management_co": "Fly South Music Group",
            "booking_agency": None,
            "genres": ["metalcore", "hardcore"],
        },
        {
            "name": "Converge",
            "current_label": None,
            "distribution": None,
            "current_manager": None,
            "current_management_co": None,
            "booking_agency": None,
            "genres": ["mathcore", "hardcore"],
        },
        {
            "name": "Code Orange",
            "current_label": None,
            "distribution": None,
            "current_manager": None,
            "current_management_co": None,
            "booking_agency": None,
            "genres": ["hardcore", "industrial"],
        },
    ]

    # Write with placeholder spotify_ids (will be resolved in seed_spotify_ids.py)
    for i, a in enumerate(artists):
        a["spotify_id"] = f"placeholder_{i:03d}"

    out_path = os.path.join(DATA_DIR, "artists.json")
    with open(out_path, "w") as f:
        json.dump(artists, f, indent=2)
    print(f"Wrote {len(artists)} artists to {out_path}")
    return artists


def seed_producers():
    """21 producers from Section 8."""
    producers = [
        # Tier 1: A-List
        {
            "name": "Drew Fulk",
            "studio_name": "Various LA studios",
            "location": "Los Angeles, CA",
            "credits": ["Knocked Loose", "Motionless in White", "BABYMETAL", "Papa Roach", "Whitechapel"],
            "tier": 1,
            "sonic_signature": "Versatile. Dense, radio-ready heaviness. 20+ #1 Billboard Rock Songs",
        },
        {
            "name": "Will Putney",
            "studio_name": "Graphic Nature Audio",
            "location": "Kinnelon, NJ",
            "credits": ["Body Count", "Knocked Loose", "Fit for an Autopsy", "Counterparts", "Gojira"],
            "tier": 1,
            "sonic_signature": "Raw, aggressive, punishing low end",
        },
        {
            "name": "Daniel Braunstein",
            "studio_name": "The Hallway Studios",
            "location": "Los Angeles, CA",
            "credits": ["Spiritbox", "Erra", "Dayseeker", "Invent Animate", "Fit For A King"],
            "tier": 1,
            "sonic_signature": "Clean, expansive, progressive metalcore. The Spiritbox sound",
        },
        {
            "name": "Josh Schroeder",
            "studio_name": "Private studio",
            "location": "Midland, MI",
            "credits": ["Lorna Shore", "Signs of the Swarm", "Tallah"],
            "tier": 1,
            "sonic_signature": "Hyper-produced deathcore. Orchestral, cinematic",
        },
        {
            "name": "Carson Slovak & Grant McFarland",
            "studio_name": "Atrium Audio",
            "location": "Lancaster, PA",
            "credits": ["August Burns Red", "Rivers of Nihil", "Polaris", "Like Moths To Flames"],
            "tier": 1,
            "sonic_signature": "Tight, punchy, technically precise. The ABR sound",
        },
        {
            "name": "Josh Wilbur",
            "studio_name": None,
            "location": "California",
            "credits": ["Lamb of God", "Korn", "Trivium", "Gojira", "Megadeth"],
            "tier": 1,
            "sonic_signature": "Arena-ready groove metal. Big, polished, powerful",
        },
        {
            "name": "Carl Bown",
            "studio_name": "Treehouse Studio",
            "location": "Derbyshire, UK",
            "credits": ["Sleep Token", "Bullet for My Valentine"],
            "tier": 1,
            "sonic_signature": "Dynamic, atmospheric, genre-blending",
        },
        {
            "name": "Adam Getgood",
            "studio_name": None,
            "location": "UK",
            "credits": ["Periphery", "Sleep Token", "Architects", "Animals As Leaders"],
            "tier": 1,
            "sonic_signature": "Pristine prog-metal clarity. Co-founder GetGood Drums",
        },
        # Tier 2: Scene Architects
        {
            "name": "Randy LeBoeuf",
            "studio_name": None,
            "location": "Des Moines area",
            "credits": ["Kublai Khan TX", "The Acacia Strain"],
            "tier": 2,
            "sonic_signature": "Raw, no-frills hardcore",
        },
        {
            "name": "Andrew Wade",
            "studio_name": None,
            "location": None,
            "credits": ["A Day To Remember", "Wage War"],
            "tier": 2,
            "sonic_signature": "Pop-punk meets metalcore polish. 3B+ cumulative streams",
        },
        {
            "name": "Kurt Ballou",
            "studio_name": "GodCity Studio",
            "location": "Salem, MA",
            "credits": ["Converge", "High on Fire", "Nails", "Code Orange"],
            "tier": 2,
            "sonic_signature": "Gold standard for hardcore punk production",
        },
        {
            "name": "Jamie King",
            "studio_name": "Basement Recording",
            "location": "Winston-Salem, NC",
            "credits": ["Between the Buried and Me"],
            "tier": 2,
            "sonic_signature": "Longest-running producer-band relationship in metal",
        },
        {
            "name": "Mark Lewis",
            "studio_name": None,
            "location": "Nashville",
            "credits": ["Whitechapel", "Cannibal Corpse", "Trivium"],
            "tier": 2,
            "sonic_signature": "Florida death metal production modernized",
        },
        {
            "name": "Taylor Larson",
            "studio_name": "Oceanic Recording",
            "location": "Bethesda, MD",
            "credits": ["Periphery", "Veil of Maya"],
            "tier": 2,
            "sonic_signature": None,
        },
        {
            "name": "Zakk Cervini",
            "studio_name": None,
            "location": "Los Angeles",
            "credits": ["Bad Omens", "Poppy", "Dayseeker"],
            "tier": 2,
            "sonic_signature": "Genre-blending pop/metal crossover specialist",
        },
        {
            "name": "Buster Odeholm",
            "studio_name": None,
            "location": "Sweden",
            "credits": ["Thrown", "Humanity's Last Breath", "Vildhjarta"],
            "tier": 2,
            "sonic_signature": "Swedish. Musician-producer model in action",
        },
        {
            "name": "Misha Mansoor",
            "studio_name": None,
            "location": None,
            "credits": ["Periphery", "Animals As Leaders"],
            "tier": 2,
            "sonic_signature": "Godfather of djent. Co-founder GetGood Drums",
        },
        {
            "name": "Matt Goldman",
            "studio_name": None,
            "location": None,
            "credits": ["Underoath", "The Chariot", "As Cities Burn"],
            "tier": 2,
            "sonic_signature": "Raw, organic sound. Defined early 2000s metalcore",
        },
        {
            "name": "Adam Dutkiewicz",
            "studio_name": None,
            "location": None,
            "credits": ["As I Lay Dying", "Underoath", "All That Remains", "Parkway Drive"],
            "tier": 2,
            "sonic_signature": "Killswitch Engage guitarist. Punchy, aggressive. Defined 2000s metalcore",
        },
        {
            "name": "Taylor Young",
            "studio_name": "The Pit Studio",
            "location": "Van Nuys, CA",
            "credits": ["God's Hate", "Nails", "Xibalba"],
            "tier": 2,
            "sonic_signature": "Hardcore/powerviolence specialist",
        },
    ]

    out_path = os.path.join(DATA_DIR, "producers.json")
    with open(out_path, "w") as f:
        json.dump(producers, f, indent=2)
    print(f"Wrote {len(producers)} producers to {out_path}")
    return producers


def seed_labels():
    """Labels from Section 3."""
    def _label(name, parent, dist, contact=None, title=None):
        return {
            "name": name, "parent_company": parent,
            "distribution": dist, "key_contact": contact,
            "contact_title": title,
        }

    labels = [
        _label("Century Media", "Sony Music", "Sony", "Robert Kampf", "Founder/CEO"),
        _label("RCA Records", "Sony Music", "Sony"),
        _label("Epic Records", "Sony Music", "Sony"),
        _label("Columbia Records", "Sony Music", "Sony"),
        _label("Roadrunner Records", "Warner Music Group", "Warner",
               "Mike Easterlin", "President"),
        _label("Spinefarm Records", "Universal Music Group", "UMG"),
        _label("Rise Records", "BMG", "BMG", "Sean Heydorn", "SVP"),
        _label("Nuclear Blast", "Believe Digital", "Believe",
               "Monte Conner", "Head of A&R"),
        _label("SharpTone Records", "Believe Digital (via Nuclear Blast)",
               "Believe", "Jackie Andersen", "Head of Label"),
        _label("MNRK Music Group", "Blackstone", "MNRK",
               "Scott Givens", "SVP Rock & Metal"),
        _label("Fearless Records", "Concord Music Group", "Concord",
               "Andy Serrao", "President"),
        _label("Sumerian Records", "Independent", "Virgin Music (UMG)",
               "Ash Avildsen", "Founder/CEO"),
        _label("Epitaph Records", "Independent", "Self-distributed",
               "Brett Gurewitz", "Founder/CEO"),
        _label("Pure Noise Records", "Independent", "Orchard/ADA",
               "Jake Round", "Founder/Owner"),
        _label("UNFD", "UNIFIED Music Group", "FUGA",
               "Jaddan Comerford", "CEO"),
        _label("Metal Blade Records", "Independent", "RED (Sony) / Warner",
               "Brian Slagel", "Founder/CEO"),
        _label("Closed Casket Activities", "Independent", "Deathwish",
               "Justin Louden", "Founder"),
        _label("Arising Empire", "Independent", "Kontor New Media"),
        _label("Solid State", "Independent", "RED (Sony)",
               "Greg Johnson", "EVP A&R"),
        _label("3DOT Recordings", "Periphery (self-owned)", "MNRK/eOne"),
        _label("Pale Chord", "Spiritbox imprint", "BMG (via Rise)"),
        _label("Equal Vision", "Independent", "RED (Sony)",
               "Steve Reddy", "Owner"),
    ]

    out_path = os.path.join(DATA_DIR, "labels.json")
    with open(out_path, "w") as f:
        json.dump(labels, f, indent=2)
    print(f"Wrote {len(labels)} labels to {out_path}")
    return labels


def seed_relationships(artists, producers):
    """Build relationships from the Who Produced What table and Artist-Label Map."""
    relationships = []

    # Band -> Producer (from Section 8: Who Produced What)
    production_pairs = [
        ("Knocked Loose", "Drew Fulk"),
        ("Lorna Shore", "Josh Schroeder"),
        ("Spiritbox", "Daniel Braunstein"),
        ("Erra", "Daniel Braunstein"),
        ("Sleep Token", "Carl Bown"),
        ("Sleep Token", "Adam Getgood"),
        ("Lamb of God", "Josh Wilbur"),
        ("Whitechapel", "Drew Fulk"),
        ("Thrown", "Buster Odeholm"),
        ("Kublai Khan TX", "Randy LeBoeuf"),
        ("Dayseeker", "Daniel Braunstein"),
        ("Fit For A King", "Daniel Braunstein"),
        ("Between the Buried and Me", "Jamie King"),
        ("A Day To Remember", "Andrew Wade"),
        ("August Burns Red", "Carson Slovak & Grant McFarland"),
        ("Periphery", "Adam Getgood"),
        ("Periphery", "Misha Mansoor"),
        ("Bad Omens", "Zakk Cervini"),
    ]

    for band, producer in production_pairs:
        relationships.append({
            "source_type": "artist",
            "source_id": band,
            "target_type": "producer",
            "target_id": producer,
            "relationship_type": "produced_by",
        })

    # Band -> Label (from artist data)
    for a in artists:
        if a["current_label"]:
            # Handle compound labels like "Pale Chord / Rise Records"
            for label in a["current_label"].split(" / "):
                label = label.strip()
                relationships.append({
                    "source_type": "artist",
                    "source_id": a["name"],
                    "target_type": "label",
                    "target_id": label,
                    "relationship_type": "signed_to",
                })

    # Band -> Management (from artist data)
    for a in artists:
        if a["current_management_co"]:
            for mgmt in a["current_management_co"].split(" / "):
                mgmt = mgmt.strip()
                relationships.append({
                    "source_type": "artist",
                    "source_id": a["name"],
                    "target_type": "management",
                    "target_id": mgmt,
                    "relationship_type": "managed_by",
                })

    # Band -> Agency (from artist data)
    for a in artists:
        if a["booking_agency"]:
            relationships.append({
                "source_type": "artist",
                "source_id": a["name"],
                "target_type": "agency",
                "target_id": a["booking_agency"],
                "relationship_type": "booked_by",
            })

    # Deduplicate
    seen = set()
    unique = []
    for r in relationships:
        key = (r["source_type"], r["source_id"], r["target_type"], r["target_id"], r["relationship_type"])
        if key not in seen:
            seen.add(key)
            unique.append(r)

    out_path = os.path.join(DATA_DIR, "relationships.json")
    with open(out_path, "w") as f:
        json.dump(unique, f, indent=2)
    print(f"Wrote {len(unique)} relationships to {out_path}")
    return unique


def main():
    print("=== Metalcore Index: Seed Data Extraction ===\n")

    artists = seed_artists()
    producers = seed_producers()
    labels = seed_labels()
    relationships = seed_relationships(artists, producers)

    print("\n=== Summary ===")
    print(f"Artists:       {len(artists)}")
    print(f"Producers:     {len(producers)}")
    print(f"Labels:        {len(labels)}")
    print(f"Relationships: {len(relationships)}")
    print(f"\nFiles written to: {DATA_DIR}/")

    # Validation: Knocked Loose should map to Pure Noise + Drew Fulk + 5B + Wasserman
    kl_rels = [r for r in relationships if r["source_id"] == "Knocked Loose"]
    print("\n=== Validation: Knocked Loose connections ===")
    for r in kl_rels:
        print(f"  {r['relationship_type']}: {r['target_id']}")


if __name__ == "__main__":
    main()
