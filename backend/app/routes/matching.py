from fastapi import APIRouter
from app.models.donation import MatchRequest, MatchResponse
from app.services.location_service import location_service
from app.services.matching_service import match_distribution
from app.services.nyc_open_data import fetch_community_need_scores

router = APIRouter(prefix="/api", tags=["matching"])


@router.post("/match-distribution", response_model=MatchResponse)
async def match(payload: MatchRequest) -> MatchResponse:
    scores, source = await fetch_community_need_scores()
    if scores:
        location_service.update_need_scores(scores, source)
    return match_distribution(payload, location_service.all(), source)

