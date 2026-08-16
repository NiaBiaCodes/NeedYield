import json
from pathlib import Path
from typing import Optional

from app.models.resource import PublicResource, PublicResourceResponse


CURATED_SOURCE = "Curated from organization-published food donation information"


def load_curated_food_resources(
    limit: int = 40,
    borough: Optional[str] = None,
    donation_only: bool = False,
) -> PublicResourceResponse:
    path = Path(__file__).resolve().parents[1] / "data" / "curated_food_resources.json"
    resources = [PublicResource(**row) for row in json.loads(path.read_text())]
    if borough:
        resources = [resource for resource in resources if resource.borough.lower() == borough.lower()]
    if donation_only:
        resources = [resource for resource in resources if resource.donation_acceptance_verified]
    return PublicResourceResponse(resources=resources[:limit], source=CURATED_SOURCE, dataset_id="curated-food-mutual-aid", fallback=False)
