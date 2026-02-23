"""Score endpoints for the Metalcore Index API."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Score
from schemas import ScoreResponse

router = APIRouter(prefix="/api/scores", tags=["scores"])


@router.get("/{artist_id}", response_model=list[ScoreResponse])
def get_artist_scores(artist_id: str, db: Session = Depends(get_db)):
    """Get score history for an artist."""
    scores = (
        db.query(Score)
        .filter(Score.artist_id == artist_id)
        .order_by(Score.score_date.desc())
        .all()
    )
    return [ScoreResponse.model_validate(s) for s in scores]
