from fastapi import APIRouter, Depends
from app.models.location import Location
from app.services.auth_service import CurrentUser, require_role
from app.services.location_service import location_service
from app.services.nyc_open_data import fetch_community_need_scores

router = APIRouter(prefix="/api", tags=["locations"])


@router.get("/locations", response_model=list[Location])
async def locations() -> list[Location]:
    scores, source = await fetch_community_need_scores()
    if scores:
        location_service.update_need_scores(scores, source)
    return location_service.all()


@router.get("/locations/donation-destinations", response_model=list[Location])
async def donation_destinations(
    user: CurrentUser = Depends(require_role("gardener")),
) -> list[Location]:
    """Return only verified locations currently accepting gardener donations."""
    scores, source = await fetch_community_need_scores()
    if scores:
        location_service.update_need_scores(scores, source)
    return location_service.donation_destinations()
