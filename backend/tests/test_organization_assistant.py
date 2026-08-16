from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app.models.donation import Allocation, Donation, DonationStatus
from app.models.location import Location
from app.models.organization import ApplicationStatus, OrganizationApplication, WeeklyNeedItem, WeeklyNeeds
from app.models.organization_assistant import OrganizationAssistantIntent
from app.models.produce import ProduceItem
from app.models.reservation import Reservation, ReservationStatus
from app.services.auth_service import CurrentUser
from app.services.organization_assistant_service import OrganizationAssistantService


class FakeOrganizations:
    def __init__(self, needs: WeeklyNeeds | None) -> None:
        self.needs = needs
        self.application = OrganizationApplication(
            id="application-1", user_id="organization-1", email="ops@example.org",
            organization_name="Test Pantry", organization_type="Food pantry",
            address="1 Test Avenue", borough="Manhattan", neighborhood="East Harlem",
            contact_name="Coordinator", phone="212-555-0100",
            accepted_categories=["vegetables"], opening_time="09:00", closing_time="17:00",
            status=ApplicationStatus.APPROVED, created_at=datetime.now(timezone.utc),
            location_id="test-pantry", review_note="Verified",
        )

    def mine(self, user_id: str):
        return self.application if user_id == self.application.user_id else None

    def get_needs(self, user_id: str):
        return self.needs if user_id == self.application.user_id else None


class FakeLocations:
    def __init__(self, inventory: dict[str, int] | None = None) -> None:
        self.location = Location(
            id="test-pantry", name="Test Pantry", address="1 Test Avenue",
            borough="Manhattan", neighborhood="East Harlem", latitude=40.79, longitude=-73.94,
            opening_time="09:00", closing_time="17:00", accepted_categories=["vegetables"],
            saturday_needs={"tomatoes": "high", "kale": "high"},
            requested_quantities={"tomatoes": 25, "kale": 18},
            inventory=inventory if inventory is not None else {"tomatoes": 8, "kale": 4},
            verified_partner=True, participating=True, accepts_saturday=True, demo=True,
            community_need_score=0.8, community_need_source="test",
        )

    def get(self, location_id: str):
        return self.location.model_copy(deep=True) if location_id == self.location.id else None


class FakeDonations:
    def __init__(self, items: list[Donation] | None = None) -> None:
        self.items = items or []

    def for_location(self, location_id: str):
        return self.items


class FakeReservations:
    def __init__(self, items: list[Reservation] | None = None) -> None:
        self.items = items or []

    def for_location(self, location_id: str):
        return self.items


def weekly_needs() -> WeeklyNeeds:
    return WeeklyNeeds(
        distribution_date=date.today() + timedelta(days=2), accepting_donations=True,
        dropoff_start="09:00", dropoff_end="17:00", notes="",
        items=[
            WeeklyNeedItem(produce_name="tomatoes", need_level="high", requested_quantity=25),
            WeeklyNeedItem(produce_name="kale", need_level="high", requested_quantity=18),
        ],
        location_id="test-pantry", submitted_at=datetime.now(timezone.utc),
    )


def confirmed_donation() -> Donation:
    return Donation(
        id="donation-1", gardener_id="gardener-1", timestamp=datetime.now(timezone.utc),
        preferred_location_id="test-pantry", preferred_radius_miles=5,
        items=[ProduceItem(name="tomatoes", quantity=3)],
        allocations=[Allocation(
            location_id="test-pantry", location_name="Test Pantry", produce="tomatoes",
            quantity=3, score=0.9, distance_miles=1.0, preferred=True, reasons=[],
        )],
        status=DonationStatus.CONFIRMED,
    )


def active_reservation() -> Reservation:
    now = datetime.now(timezone.utc)
    return Reservation(
        id="reservation-1", location_id="test-pantry", location_name="Test Pantry",
        location_address="1 Test Avenue", produce="tomatoes", quantity=14,
        created_at=now, expires_at=now + timedelta(hours=4), status=ReservationStatus.RESERVED,
        user_id="neighbor-1",
    )


def service(needs: WeeklyNeeds | None = None, with_activity: bool = True, inventory: dict[str, int] | None = None) -> OrganizationAssistantService:
    return OrganizationAssistantService(
        organizations=FakeOrganizations(needs), locations=FakeLocations(inventory),
        donations=FakeDonations([confirmed_donation()] if with_activity else []),
        reservations=FakeReservations([active_reservation()] if with_activity else []),
    )


USER = CurrentUser(id="organization-1", email="ops@example.org", role="organization")


def test_low_stock_calculation_uses_inventory_and_weekly_targets() -> None:
    response = service(weekly_needs()).query(USER, "What are we low on?")
    assert response.intent == OrganizationAssistantIntent.LOW_STOCK
    shortages = {item.produce_name: item.projected_shortage for item in response.inventory}
    assert shortages == {"kale": 14, "tomatoes": 17}
    assert all(item.unit == "count" for item in response.inventory)


def test_weekly_request_recommendations_are_explainable_actions() -> None:
    response = service(weekly_needs()).query(USER, "What should we request this week?")
    assert response.intent == OrganizationAssistantIntent.RECOMMENDED_REQUESTS
    suggestions = {item.produce_name: item.suggested_quantity for item in response.actions if item.kind == "shortage"}
    assert suggestions == {"tomatoes": 17, "kale": 14}
    assert all("weekly target" in item.detail for item in response.actions if item.kind == "shortage")


def test_incoming_donation_summary_only_reports_recorded_confirmation_data() -> None:
    response = service(weekly_needs()).query(USER, "What donations are coming today?")
    assert response.intent == OrganizationAssistantIntent.INCOMING_DONATIONS
    assert response.today.confirmed_donations == 1
    assert response.donations[0].produce_name == "tomatoes"
    assert response.donations[0].quantity == 3
    assert "does not yet store arrival windows" in response.summary


def test_pending_actions_prioritize_shortages_and_pickups() -> None:
    response = service(weekly_needs()).query(USER, "What needs my attention?")
    assert response.intent == OrganizationAssistantIntent.PENDING_ACTIONS
    assert response.actions[0].kind == "shortage"
    assert any(item.kind == "pickup" for item in response.actions)
    assert response.today.reserved_for_distribution == 14


def test_daily_summary_uses_calculated_status() -> None:
    response = service(weekly_needs()).query(USER, "Give me today's summary")
    assert response.intent == OrganizationAssistantIntent.DAILY_SUMMARY
    assert response.today.confirmed_donations == 1
    assert response.today.low_stock_items == 2
    assert response.today.reserved_for_distribution == 14
    assert "2 low-stock items" in response.summary


def test_missing_weekly_needs_returns_actionable_fallback() -> None:
    response = service(None, with_activity=False, inventory={}).query(USER, "What are we low on?")
    assert response.inventory == []
    assert "have not been set" in response.summary
    attention = service(None, with_activity=False, inventory={}).query(USER, "What needs my attention?")
    assert attention.actions[0].action == "edit_weekly_needs"


def test_gemini_unavailable_does_not_disable_structured_answers(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    response = service(weekly_needs()).query(USER, "Summarize our inventory")
    assert response.intent == OrganizationAssistantIntent.INVENTORY_STATUS
    assert response.inventory
    assert response.generation_mode == "deterministic"
    assert response.fallback is False
