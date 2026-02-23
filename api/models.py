"""
SQLAlchemy models for Metalcore Index.
6 tables: artists, artist_snapshots, scores, producers, relationships, labels
"""
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    Date,
    Text,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database import Base


class Artist(Base):
    __tablename__ = "artists"

    spotify_id = Column(String(50), primary_key=True)
    name = Column(String(200), nullable=False, index=True)
    genres = Column(Text, default="[]")  # JSON array
    image_url = Column(String(500), nullable=True)
    current_label = Column(String(200), nullable=True)
    current_manager = Column(String(200), nullable=True)
    current_management_co = Column(String(200), nullable=True)
    booking_agency = Column(String(200), nullable=True)
    youtube_channel_id = Column(String(50), nullable=True)
    active = Column(Boolean, default=True)

    snapshots = relationship("ArtistSnapshot", back_populates="artist")
    scores = relationship("Score", back_populates="artist")


class ArtistSnapshot(Base):
    __tablename__ = "artist_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    artist_id = Column(String(50), ForeignKey("artists.spotify_id"), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    spotify_popularity = Column(Integer, nullable=True)
    spotify_followers = Column(Integer, nullable=True)
    youtube_subscribers = Column(Integer, nullable=True)
    youtube_total_views = Column(Integer, nullable=True)
    youtube_recent_views = Column(Integer, nullable=True)
    youtube_comment_count = Column(Integer, nullable=True)
    setlist_count_90d = Column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint("artist_id", "snapshot_date", name="uq_artist_snapshot_date"),
    )

    artist = relationship("Artist", back_populates="snapshots")


class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    artist_id = Column(String(50), ForeignKey("artists.spotify_id"), nullable=False)
    score_date = Column(Date, nullable=False)
    trajectory = Column(Float, nullable=True)
    industry_signal = Column(Float, nullable=True)
    engagement = Column(Float, nullable=True)
    release_positioning = Column(Float, nullable=True)
    composite = Column(Float, nullable=True)
    grade = Column(String(1), nullable=True)  # A, B, C, D
    segment_tag = Column(String(50), nullable=True)

    __table_args__ = (
        UniqueConstraint("artist_id", "score_date", name="uq_artist_score_date"),
    )

    artist = relationship("Artist", back_populates="scores")


class Producer(Base):
    __tablename__ = "producers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, unique=True)
    studio_name = Column(String(200), nullable=True)
    location = Column(String(200), nullable=True)
    credits = Column(Text, default="[]")  # JSON array of band names
    tier = Column(Integer, nullable=True)  # 1 or 2
    sonic_signature = Column(Text, nullable=True)


class Relationship(Base):
    __tablename__ = "relationships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_type = Column(String(50), nullable=False)  # artist, producer, label, management
    source_id = Column(String(200), nullable=False)
    target_type = Column(String(50), nullable=False)
    target_id = Column(String(200), nullable=False)
    # signed_to, produced_by, managed_by, booked_by
    relationship_type = Column(String(100), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "source_type",
            "source_id",
            "target_type",
            "target_id",
            "relationship_type",
            name="uq_relationship",
        ),
    )


class Label(Base):
    __tablename__ = "labels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, unique=True)
    parent_company = Column(String(200), nullable=True)
    distribution = Column(String(200), nullable=True)
    key_contact = Column(String(200), nullable=True)
    contact_title = Column(String(200), nullable=True)
