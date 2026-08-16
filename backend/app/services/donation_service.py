from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4
from app.models.donation import ConfirmDonationRequest, Donation, DonationStatus
from app.services.inventory_service import add_inventory
from app.services.location_service import location_service
from app.services.matching_service import canonical_produce, capacity_for
from app.services.database_service import database_service


class DonationService:
    def __init__(self) -> None:
        self._items: list[Donation] = []
        self._lock = RLock()

    def confirm(self, payload: ConfirmDonationRequest) -> Donation:
        with self._lock:
            donated = {canonical_produce(item.name): item.quantity for item in payload.items}
            allocated: dict[str, int] = {}
            for allocation in payload.allocations:
                produce = canonical_produce(allocation.produce)
                location = location_service.get(allocation.location_id)
                if not location or not location.verified_partner or not location.participating:
                    raise ValueError("Allocations require a participating verified partner")
                if allocation.quantity > capacity_for(location, produce):
                    raise ValueError(f"Allocation exceeds {location.name}'s stated capacity for {produce}")
                allocated[produce] = allocated.get(produce, 0) + allocation.quantity
                if allocated[produce] > donated.get(produce, 0):
                    raise ValueError(f"Allocated {produce} exceeds the confirmed harvest")
            for allocation in payload.allocations:
                add_inventory(allocation.location_id, canonical_produce(allocation.produce), allocation.quantity)
            donation = Donation(id=str(uuid4()), gardener_id=payload.gardener_id, timestamp=datetime.now(timezone.utc), preferred_location_id=payload.preferred_location_id, preferred_radius_miles=payload.preferred_radius_miles, items=payload.items, allocations=payload.allocations, status=DonationStatus.CONFIRMED)
            self._items.append(donation)
            database_service.save_donation(donation)
            return donation

    def for_location(self, location_id: str) -> list[Donation]:
        with self._lock:
            matches = [
                donation.model_copy(deep=True)
                for donation in self._items
                if any(allocation.location_id == location_id for allocation in donation.allocations)
            ]
        return sorted(matches, key=lambda donation: donation.timestamp, reverse=True)


donation_service = DonationService()
