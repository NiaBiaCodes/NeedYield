from math import asin, cos, radians, sin, sqrt
from app.models.donation import Allocation, MatchRequest, MatchResponse
from app.models.location import Location

# Gardener preference is applied before scoring. Within eligible alternatives,
# an organization's current explicit need is the strongest signal.
WEIGHTS = {"produce_need": 0.35, "community_need": 0.30, "inventory_shortage": 0.20, "proximity": 0.10, "hours": 0.05}
NEED_SCORES = {"none": 0.0, "low": 0.25, "medium": 0.60, "high": 1.0}
DEFAULT_CAPACITY = {"none": 0, "low": 8, "medium": 18, "high": 30}


def canonical_produce(name: str) -> str:
    value = name.strip().lower()
    return {"tomato": "tomatoes", "cucumber": "cucumbers", "pepper": "peppers", "carrot": "carrots", "herb": "herbs"}.get(value, value)


def calculate_distance_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_miles = 3958.8
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    value = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return earth_radius_miles * 2 * asin(sqrt(value))


def is_eligible(location: Location, produce: str, distance: float, radius: float) -> bool:
    return (
        location.verified_partner and location.participating and location.accepts_saturday
        and "vegetables" in location.accepted_categories
        and distance <= radius
        and NEED_SCORES.get(location.saturday_needs.get(produce, "none"), 0) > 0
    )


def score_location(location: Location, produce: str, distance: float, radius: float) -> tuple[float, list[str]]:
    need_level = location.saturday_needs.get(produce, "none")
    need = NEED_SCORES.get(need_level, 0)
    proximity = max(0.0, 1 - distance / radius)
    inventory = location.inventory.get(produce, 0)
    shortage = max(0.0, 1 - inventory / 30)
    score = (
        location.community_need_score * WEIGHTS["community_need"]
        + need * WEIGHTS["produce_need"]
        + proximity * WEIGHTS["proximity"]
        + shortage * WEIGHTS["inventory_shortage"]
        + WEIGHTS["hours"]
    )
    reasons = [f"{need_level.title()} {produce} need"]
    if location.community_need_score >= 0.75:
        reasons.append("High community need signal")
    if inventory < 12:
        reasons.append(f"Low current {produce} inventory")
    reasons.extend([f"{distance:.1f} miles away", "Accepting Saturday produce"])
    return round(score, 3), reasons


def capacity_for(location: Location, produce: str) -> int:
    explicit = location.requested_quantities.get(produce)
    if explicit is not None:
        return max(0, explicit)
    return DEFAULT_CAPACITY[location.saturday_needs.get(produce, "none")]


def match_distribution(request: MatchRequest, locations: list[Location], data_source: str) -> MatchResponse:
    preferred = next((loc for loc in locations if loc.id == request.preferred_location_id), None)
    preferred_allocations: list[Allocation] = []
    alternatives: list[Allocation] = []
    remaining: dict[str, int] = {}
    for item in request.items:
        produce = canonical_produce(item.name)
        available = item.quantity
        if preferred:
            distance = calculate_distance_miles(request.gardener_latitude, request.gardener_longitude, preferred.latitude, preferred.longitude)
            if is_eligible(preferred, produce, distance, request.preferred_radius_miles):
                quantity = min(available, capacity_for(preferred, produce))
                if quantity:
                    score, reasons = score_location(preferred, produce, distance, request.preferred_radius_miles)
                    preferred_allocations.append(Allocation(location_id=preferred.id, location_name=preferred.name, produce=produce, quantity=quantity, score=score, distance_miles=round(distance, 2), preferred=True, reasons=["Your preferred organization", *reasons]))
                    available -= quantity
        candidates = []
        for location in locations:
            if location.id == request.preferred_location_id:
                continue
            distance = calculate_distance_miles(request.gardener_latitude, request.gardener_longitude, location.latitude, location.longitude)
            if is_eligible(location, produce, distance, request.preferred_radius_miles):
                score, reasons = score_location(location, produce, distance, request.preferred_radius_miles)
                candidates.append((score, location, distance, reasons))
        for score, location, distance, reasons in sorted(candidates, key=lambda row: row[0], reverse=True):
            if available <= 0:
                break
            quantity = min(available, capacity_for(location, produce))
            if quantity:
                alternatives.append(Allocation(location_id=location.id, location_name=location.name, produce=produce, quantity=quantity, score=score, distance_miles=round(distance, 2), reasons=reasons))
                available -= quantity
        remaining[produce] = available
    return MatchResponse(preferred_allocations=preferred_allocations, recommended_allocations=alternatives, remaining_surplus=remaining, surplus_alert=any(remaining.values()), data_source=data_source)
