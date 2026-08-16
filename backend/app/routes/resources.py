from typing import Literal, Optional

from fastapi import APIRouter, Query

from app.models.resource import PublicResourceResponse
from app.services.resource_service import load_curated_food_resources

router = APIRouter(prefix="/api/resources", tags=["resources"])


@router.get("/food-mutual-aid", response_model=PublicResourceResponse)
def food_mutual_aid(
    limit: int = Query(default=80, ge=1, le=200),
    borough: Optional[str] = Query(default=None, max_length=40),
    audience: Literal["neighbor", "gardener"] = "neighbor",
) -> PublicResourceResponse:
    """Neighbors see food access resources; gardeners see donation-confirmed resources."""
    return load_curated_food_resources(limit=limit, borough=borough, donation_only=audience == "gardener")
