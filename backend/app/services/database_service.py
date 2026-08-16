import os
from typing import Any, Optional
from uuid import UUID

import httpx

from app.models.donation import Donation
from app.models.location import Location
from app.models.reservation import Reservation


class SupabasePersistence:
    """Server-side Supabase adapter with a no-throw demo fallback contract."""

    def __init__(self) -> None:
        self.url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        self.configured = bool(self.url and self.service_key)
        self.last_error: Optional[str] = None

    @property
    def mode(self) -> str:
        return "supabase" if self.configured and not self.last_error else "memory"

    def _headers(self, prefer: Optional[str] = None) -> dict[str, str]:
        headers = {"apikey": self.service_key, "Authorization": f"Bearer {self.service_key}", "Content-Type": "application/json"}
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        if not self.configured:
            return None
        try:
            response = httpx.request(method, f"{self.url}/rest/v1/{path}", headers=self._headers(kwargs.pop("prefer", None)), timeout=5.0, **kwargs)
            response.raise_for_status()
            self.last_error = None
            return response.json() if response.content else None
        except (httpx.HTTPError, ValueError) as error:
            self.last_error = str(error)
            return None

    def load_locations(self) -> list[Location]:
        rows = self._request("GET", "locations?select=*")
        if not isinstance(rows, list) or not rows:
            return []
        inventory_rows = self._request("GET", "inventory?select=location_id,produce_name,quantity") or []
        need_rows = self._request("GET", "organization_needs?select=location_id,produce_name,need_level,requested_quantity") or []
        inventory_by_location: dict[str, dict[str, int]] = {}
        needs_by_location: dict[str, dict[str, str]] = {}
        quantities_by_location: dict[str, dict[str, int]] = {}
        for item in inventory_rows:
            inventory_by_location.setdefault(item["location_id"], {})[item["produce_name"]] = item["quantity"]
        for item in need_rows:
            needs_by_location.setdefault(item["location_id"], {})[item["produce_name"]] = item["need_level"]
            if item.get("requested_quantity") is not None:
                quantities_by_location.setdefault(item["location_id"], {})[item["produce_name"]] = item["requested_quantity"]
        locations = []
        for row in rows:
            payload = dict(row)
            payload.update({
                "accepted_categories": row.get("accepted_categories") or ["vegetables", "fruit", "herbs"],
                "saturday_needs": needs_by_location.get(row["id"], {}),
                "requested_quantities": quantities_by_location.get(row["id"], {}),
                "inventory": inventory_by_location.get(row["id"], {}),
                "participating": row.get("participating", True), "accepts_saturday": row.get("accepts_saturday", True),
                "community_need_score": float(row.get("community_need_score", 0.5)),
                "community_need_source": row.get("community_need_source", "Supabase"),
            })
            locations.append(Location(**payload))
        return locations

    def seed_locations(self, locations: list[Location]) -> None:
        if not self.configured:
            return
        location_rows = [{
            "id": item.id, "name": item.name, "address": item.address, "borough": item.borough,
            "neighborhood": item.neighborhood, "latitude": item.latitude, "longitude": item.longitude,
            "opening_time": item.opening_time, "closing_time": item.closing_time,
            "accepted_categories": item.accepted_categories, "verified_partner": item.verified_partner,
            "participating": item.participating, "accepts_saturday": item.accepts_saturday,
            "demo": item.demo, "community_need_score": item.community_need_score,
            "community_need_source": item.community_need_source,
        } for item in locations]
        self._request("POST", "locations?on_conflict=id", json=location_rows, prefer="resolution=merge-duplicates")
        inventory_rows = [{"location_id": item.id, "produce_name": produce, "quantity": quantity, "unit": "count"} for item in locations for produce, quantity in item.inventory.items()]
        need_rows = [{"location_id": item.id, "produce_name": produce, "need_level": level, "requested_quantity": item.requested_quantities.get(produce)} for item in locations for produce, level in item.saturday_needs.items()]
        self._request("POST", "inventory?on_conflict=location_id,produce_name", json=inventory_rows, prefer="resolution=merge-duplicates")
        self._request("POST", "organization_needs?on_conflict=location_id,produce_name,distribution_date", json=need_rows, prefer="resolution=merge-duplicates")

    def save_inventory(self, location_id: str, produce: str, quantity: int) -> None:
        self._request("POST", "inventory?on_conflict=location_id,produce_name", json={"location_id": location_id, "produce_name": produce, "quantity": quantity, "unit": "count"}, prefer="resolution=merge-duplicates")

    def save_location(self, item: Location) -> None:
        self._request("POST", "locations?on_conflict=id", json={
            "id": item.id, "name": item.name, "address": item.address, "borough": item.borough,
            "neighborhood": item.neighborhood, "latitude": item.latitude, "longitude": item.longitude,
            "opening_time": item.opening_time, "closing_time": item.closing_time,
            "accepted_categories": item.accepted_categories, "verified_partner": item.verified_partner,
            "participating": item.participating, "accepts_saturday": item.accepts_saturday,
            "demo": item.demo, "community_need_score": item.community_need_score,
            "community_need_source": item.community_need_source,
        }, prefer="resolution=merge-duplicates")

    def save_organization_needs(self, location: Location, distribution_date: str) -> None:
        rows = [{"location_id": location.id, "produce_name": produce, "need_level": level,
                 "requested_quantity": location.requested_quantities.get(produce), "distribution_date": distribution_date}
                for produce, level in location.saturday_needs.items()]
        if rows:
            self._request("POST", "organization_needs?on_conflict=location_id,produce_name,distribution_date", json=rows, prefer="resolution=merge-duplicates")

    def get_profile(self, user_id: str) -> Optional[dict[str, Any]]:
        rows = self._request("GET", f"profiles?id=eq.{user_id}&select=id,role,display_name,is_admin")
        return rows[0] if isinstance(rows, list) and rows else None

    def load_reservations(self) -> list[Reservation]:
        rows = self._request("GET", "reservations?select=*,locations(name,address)&order=created_at.desc")
        if not isinstance(rows, list):
            return []
        result = []
        for source in rows:
            row = dict(source)
            location = row.pop("locations", {}) or {}
            row["produce"] = row.pop("produce_name")
            result.append(Reservation(location_name=location.get("name", "Unknown location"), location_address=location.get("address", ""), **row))
        return result

    def save_reservation(self, reservation: Reservation, user_id: Optional[str] = None) -> None:
        self._request("POST", "reservations?on_conflict=id", json={
            "id": reservation.id, "user_id": user_id or reservation.user_id, "location_id": reservation.location_id,
            "produce_name": reservation.produce, "quantity": reservation.quantity,
            "created_at": reservation.created_at.isoformat(), "expires_at": reservation.expires_at.isoformat(),
            "status": reservation.status.value,
        }, prefer="resolution=merge-duplicates")

    def create_reservation_atomic(self, location_id: str, produce: str, quantity: int, user_id: str, expires_at: str) -> Optional[dict[str, Any]]:
        rows = self._request("POST", "rpc/reserve_inventory_atomic", json={"p_location_id": location_id, "p_produce": produce, "p_quantity": quantity, "p_user_id": user_id, "p_expires_at": expires_at})
        if isinstance(rows, list) and rows:
            return rows[0]
        if isinstance(rows, dict):
            return rows
        return None

    def save_donation(self, donation: Donation) -> None:
        gardener_uuid = donation.gardener_id if self._is_uuid(donation.gardener_id) else None
        self._request("POST", "donations?on_conflict=id", json={
            "id": donation.id, "gardener_id": gardener_uuid, "demo_gardener_id": None if gardener_uuid else donation.gardener_id,
            "preferred_location_id": donation.preferred_location_id, "radius_miles": donation.preferred_radius_miles,
            "status": donation.status.value, "created_at": donation.timestamp.isoformat(),
        }, prefer="resolution=merge-duplicates")
        self._request("POST", "donation_items", json=[{"donation_id": donation.id, "produce_name": item.name.lower(), "quantity": item.quantity, "unit": item.unit} for item in donation.items])
        self._request("POST", "allocations", json=[{
            "donation_id": donation.id, "location_id": item.location_id, "produce_name": item.produce,
            "quantity": item.quantity, "score": item.score, "confirmed": True,
        } for item in donation.allocations])

    @staticmethod
    def _is_uuid(value: str) -> bool:
        try:
            UUID(value)
            return True
        except ValueError:
            return False


database_service = SupabasePersistence()
