"""
Pydantic schemas for Metalcore Index API responses.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import date


# --- Artist ---

class ArtistBase(BaseModel):
    spotify_id: str
    name: str
    genres: list[str] = []
    image_url: Optional[str] = None
    current_label: Optional[str] = None
    current_manager: Optional[str] = None
    current_management_co: Optional[str] = None
    booking_agency: Optional[str] = None
    booking_agent: Optional[str] = None
    youtube_channel_id: Optional[str] = None
    active: bool = True


class ArtistResponse(ArtistBase):
    latest_score: Optional["ScoreResponse"] = None

    model_config = {"from_attributes": True}


class ArtistDetail(ArtistBase):
    snapshots: list["SnapshotResponse"] = []
    scores: list["ScoreResponse"] = []
    upcoming_events: list["EventResponse"] = []
    label_contact: Optional["LabelContactInfo"] = None

    model_config = {"from_attributes": True}


# --- Snapshot ---

class SnapshotResponse(BaseModel):
    snapshot_date: date
    spotify_popularity: Optional[int] = None
    spotify_followers: Optional[int] = None
    youtube_subscribers: Optional[int] = None
    youtube_total_views: Optional[int] = None
    youtube_recent_views: Optional[int] = None
    youtube_comment_count: Optional[int] = None
    setlist_count_90d: Optional[int] = None

    model_config = {"from_attributes": True}


# --- Score ---

class ScoreResponse(BaseModel):
    score_date: date
    trajectory: Optional[float] = None
    industry_signal: Optional[float] = None
    engagement: Optional[float] = None
    release_positioning: Optional[float] = None
    composite: Optional[float] = None
    grade: Optional[str] = None
    segment_tag: Optional[str] = None

    model_config = {"from_attributes": True}


# --- Producer ---

class ProducerResponse(BaseModel):
    id: int
    name: str
    studio_name: Optional[str] = None
    location: Optional[str] = None
    credits: list[str] = []
    tier: Optional[int] = None
    sonic_signature: Optional[str] = None

    model_config = {"from_attributes": True}


# --- Network ---

class RelationshipResponse(BaseModel):
    id: int
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    relationship_type: str

    model_config = {"from_attributes": True}


class ProducerCredit(BaseModel):
    name: str
    studio: Optional[str] = None


class RelatedArtistBrief(BaseModel):
    spotify_id: str
    name: str
    image_url: Optional[str] = None
    composite: Optional[float] = None
    grade: Optional[str] = None


class NetworkNode(BaseModel):
    id: str
    label: str
    type: str  # artist, producer, label, management
    score: Optional[float] = None
    spotify_id: Optional[str] = None


class NetworkLink(BaseModel):
    source: str
    target: str
    relationship: str


class NetworkGraph(BaseModel):
    nodes: list[NetworkNode]
    links: list[NetworkLink]


# --- Label ---

class LabelResponse(BaseModel):
    id: int
    name: str
    parent_company: Optional[str] = None
    distribution: Optional[str] = None
    key_contact: Optional[str] = None
    contact_title: Optional[str] = None

    model_config = {"from_attributes": True}


# --- Dashboard ---

class DashboardArtist(BaseModel):
    """Flattened artist + latest score for the dashboard table."""
    spotify_id: str
    name: str
    image_url: Optional[str] = None
    current_label: Optional[str] = None
    grade: Optional[str] = None
    segment_tag: Optional[str] = None
    composite: Optional[float] = None
    trajectory: Optional[float] = None
    industry_signal: Optional[float] = None
    engagement: Optional[float] = None
    release_positioning: Optional[float] = None


class DashboardResponse(BaseModel):
    artists: list[DashboardArtist]
    total: int
    universe_size: int


# --- Events ---

class EventResponse(BaseModel):
    id: int
    event_name: str
    venue_name: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    event_date: date
    event_type: str = "concert"
    ticket_url: Optional[str] = None
    festival_name: Optional[str] = None
    lineup_position: Optional[str] = None

    model_config = {"from_attributes": True}


class FestivalSummary(BaseModel):
    festival_name: str
    start_date: date
    end_date: Optional[date] = None
    location: str
    artists: list[str]


class LabelContactInfo(BaseModel):
    label_name: str
    key_contact: Optional[str] = None
    contact_title: Optional[str] = None


class DashboardParams(BaseModel):
    sort_by: Optional[str] = None
    sort_dir: Optional[str] = None
    grade: Optional[str] = None
    segment: Optional[str] = None
    label: Optional[str] = None
    search: Optional[str] = None
    limit: int = 100
    offset: int = 0
