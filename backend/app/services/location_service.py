import json
from pathlib import Path
from threading import RLock
from typing import Optional
from app.models.location import Location
from app.models.organization import WeeklyNeeds
from app.services.database_service import database_service


class LocationService:
    def __init__(self) -> None:
        path = Path(__file__).resolve().parents[1] / "data" / "demo_locations.json"
        seeded_locations = [Location(**item) for item in json.loads(path.read_text())]
        persisted_locations = database_service.load_locations()
        active_locations = persisted_locations or seeded_locations
        self._locations = {item.id: item for item in active_locations}
        if database_service.configured and not persisted_locations:
            database_service.seed_locations(seeded_locations)
        self._lock = RLock()

    def all(self) -> list[Location]:
        with self._lock:
            return [location.model_copy(deep=True) for location in self._locations.values()]

    def donation_destinations(self) -> list[Location]:
        """Locations currently verified and operationally able to receive produce."""
        with self._lock:
            return [
                location.model_copy(deep=True)
                for location in self._locations.values()
                if location.verified_partner
                and location.participating
                and location.accepts_saturday
                and bool(location.accepted_categories)
            ]

    def get(self, location_id: str) -> Optional[Location]:
        with self._lock:
            location = self._locations.get(location_id)
            return location.model_copy(deep=True) if location else None

    def add_location(self, location: Location) -> None:
        with self._lock:
            self._locations[location.id] = location.model_copy(deep=True)
            database_service.save_location(location)

    def update_organization_needs(self, location_id: str, needs: WeeklyNeeds) -> None:
        with self._lock:
            location = self._locations.get(location_id)
            if not location:
                raise KeyError("Approved location not found")
            location.participating = needs.accepting_donations
            location.accepts_saturday = needs.accepting_donations
            location.opening_time = needs.dropoff_start
            location.closing_time = needs.dropoff_end
            location.saturday_needs = {item.produce_name.strip().lower(): item.need_level for item in needs.items}
            location.requested_quantities = {item.produce_name.strip().lower(): item.requested_quantity for item in needs.items}
            database_service.save_organization_needs(location, needs.distribution_date.isoformat())

    def update_need_scores(self, scores: dict[str, float], source: str) -> None:
        with self._lock:
            for location in self._locations.values():
                score = scores.get(location.neighborhood.lower()) or scores.get(location.borough.lower())
                if score is not None:
                    location.community_need_score = score
                    location.community_need_source = source

    def mutate_inventory(self, location_id: str, produce: str, delta: int) -> int:
        with self._lock:
            location = self._locations.get(location_id)
            if not location:
                raise KeyError("Location not found")
            key = produce.lower()
            current = location.inventory.get(key, 0)
            next_quantity = current + delta
            if next_quantity < 0:
                raise ValueError("Insufficient inventory")
            location.inventory[key] = next_quantity
            database_service.save_inventory(location_id, key, next_quantity)
            return next_quantity

    def set_inventory_local(self, location_id: str, produce: str, quantity: int) -> None:
        with self._lock:
            location = self._locations.get(location_id)
            if location:
                location.inventory[produce.lower()] = quantity


location_service = LocationService()
