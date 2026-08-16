from app.models.donation import MatchRequest
from app.models.produce import ProduceItem
from app.services.inventory_service import get_inventory
from app.services.location_service import LocationService, location_service
from app.services.matching_service import calculate_distance_miles, is_eligible, match_distribution, score_location
from app.services.reservation_service import ReservationService
from app.models.reservation import ReservationCreate, ReservationStatus
from app.models.donation import Allocation, ConfirmDonationRequest
from app.services.donation_service import DonationService
import pytest
from app.services.database_service import SupabasePersistence
from datetime import date, timedelta
from app.models.organization import ApprovalRequest, OrganizationApplicationCreate, WeeklyNeedItem, WeeklyNeedsCreate
from app.services.auth_service import CurrentUser
from app.services.organization_service import OrganizationService
from app.models.rag import RagQuery
from app.services.rag_service import RagService
from app.services.resource_service import load_curated_food_resources


def test_haversine_distance() -> None:
    distance = calculate_distance_miles(40.7128, -74.0060, 40.7580, -73.9855)
    assert 3.0 < distance < 4.0


def test_eligibility_filter() -> None:
    location = LocationService().all()[0]
    assert is_eligible(location, "tomatoes", 1.0, 5.0)
    assert not is_eligible(location, "tomatoes", 6.0, 5.0)
    location.verified_partner = False
    assert not is_eligible(location, "tomatoes", 1.0, 5.0)


def test_preferred_and_surplus_allocation_ranking() -> None:
    locations = LocationService().all()
    request = MatchRequest(
        gardener_latitude=40.79,
        gardener_longitude=-73.95,
        preferred_location_id="east-harlem-harvest-hub",
        preferred_radius_miles=15,
        items=[ProduceItem(name="Tomato", quantity=100), ProduceItem(name="Cucumber", quantity=40)],
    )
    result = match_distribution(request, locations, "test")
    preferred = {item.produce: item.quantity for item in result.preferred_allocations}
    assert preferred == {"tomatoes": 30, "cucumbers": 20}
    assert result.recommended_allocations
    assert sum(a.quantity for a in result.recommended_allocations if a.produce == "tomatoes") <= 70
    tomato_scores = [a.score for a in result.recommended_allocations if a.produce == "tomatoes"]
    assert tomato_scores == sorted(tomato_scores, reverse=True)


def test_inventory_reservation_and_rescue_release() -> None:
    service = ReservationService()
    before = get_inventory("east-harlem-harvest-hub")["tomatoes"]
    reservation = service.create(ReservationCreate(location_id="east-harlem-harvest-hub", produce="tomatoes", quantity=2))
    assert get_inventory("east-harlem-harvest-hub")["tomatoes"] == before - 2
    expired = service.expire(reservation.id, force=True)
    assert expired.status == ReservationStatus.EXPIRED
    assert get_inventory("east-harlem-harvest-hub")["tomatoes"] == before


def test_confirmation_rejects_over_allocation() -> None:
    payload = ConfirmDonationRequest(
        preferred_location_id="east-harlem-harvest-hub",
        preferred_radius_miles=5,
        items=[ProduceItem(name="Tomato", quantity=10)],
        allocations=[Allocation(location_id="east-harlem-harvest-hub", location_name="East Harlem Harvest Hub", produce="tomatoes", quantity=11, score=0.8, distance_miles=1, preferred=True, reasons=[])],
    )
    with pytest.raises(ValueError):
        DonationService().confirm(payload)


def test_supabase_adapter_uses_memory_fallback_without_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    repository = SupabasePersistence()
    assert repository.mode == "memory"
    assert repository.load_locations() == []
    repository.save_inventory("demo-location", "tomatoes", 5)
    assert repository.last_error is None


def test_listing_reservations_expires_due_inventory() -> None:
    service = ReservationService()
    before = get_inventory("east-harlem-harvest-hub")["tomatoes"]
    reservation = service.create(ReservationCreate(location_id="east-harlem-harvest-hub", produce="tomatoes", quantity=1))
    service._items[reservation.id].expires_at = reservation.created_at - timedelta(seconds=1)
    listed = service.all()
    assert listed[0].status == ReservationStatus.EXPIRED
    assert get_inventory("east-harlem-harvest-hub")["tomatoes"] == before


def test_rag_retrieval_is_verified_against_structured_inventory(tmp_path) -> None:
    service = RagService()
    service.path = tmp_path / "chroma"
    assert service.rebuild_index() == 6
    result = service.query(RagQuery(query="Where can I find tomatoes near East Harlem?", latitude=40.7917, longitude=-73.9462))
    assert result.retrieved_count > 0
    assert result.recommendations
    assert all("tomatoes" in item.available_inventory for item in result.recommendations)
    assert result.recommendations[0].distance_miles is not None


def test_radius_filter_excludes_otherwise_eligible_location() -> None:
    location = LocationService().all()[0]
    assert is_eligible(location, "tomatoes", distance=1.0, radius=2.0)
    assert not is_eligible(location, "tomatoes", distance=2.01, radius=2.0)


def test_community_need_increases_score_when_other_factors_match() -> None:
    low, high = [LocationService().all()[0].model_copy(deep=True) for _ in range(2)]
    low.community_need_score = 0.2
    high.community_need_score = 0.9
    low_score, _ = score_location(low, "tomatoes", distance=1.0, radius=5.0)
    high_score, _ = score_location(high, "tomatoes", distance=1.0, radius=5.0)
    assert high_score > low_score


def test_inventory_shortage_increases_score_when_other_factors_match() -> None:
    stocked, scarce = [LocationService().all()[0].model_copy(deep=True) for _ in range(2)]
    stocked.inventory["tomatoes"] = 30
    scarce.inventory["tomatoes"] = 0
    stocked_score, _ = score_location(stocked, "tomatoes", distance=1.0, radius=5.0)
    scarce_score, reasons = score_location(scarce, "tomatoes", distance=1.0, radius=5.0)
    assert scarce_score > stocked_score
    assert "Low current tomatoes inventory" in reasons


def test_approved_organization_weekly_need_enters_matching() -> None:
    service = OrganizationService()
    user = CurrentUser(id="demo-org-test", email="org@example.org", role="organization", demo=True)
    application = service.apply(user, OrganizationApplicationCreate(
        organization_name="Test Community Pantry", organization_type="Food pantry",
        address="1 Test Avenue, New York, NY", borough="Manhattan", neighborhood="East Harlem",
        contact_name="Test Coordinator", phone="212-555-0199", accepted_categories=["vegetables"],
        opening_time="09:00", closing_time="17:00",
    ))
    approved = service.approve(application.id, ApprovalRequest(latitude=40.79, longitude=-73.95), "demo-admin")
    service.submit_needs(user.id, WeeklyNeedsCreate(
        distribution_date=date.today(), dropoff_start="09:00", dropoff_end="17:00",
        items=[WeeklyNeedItem(produce_name="tomatoes", need_level="high", requested_quantity=40)],
    ))
    location = location_service.get(approved.location_id)
    assert location is not None
    assert location.verified_partner
    assert location.saturday_needs["tomatoes"] == "high"
    assert location.requested_quantities["tomatoes"] == 40


def test_curated_resources_only_contain_food_mutual_aid_and_fridges() -> None:
    response = load_curated_food_resources()
    assert response.dataset_id == "curated-food-mutual-aid"
    assert len(response.resources) == 4
    assert all(resource.resource_type in {"mutual_aid", "mutual_aid_pantry", "community_fridge"} for resource in response.resources)
    assert all(resource.verified_partner is False for resource in response.resources)
    assert all(resource.donation_acceptance_verified for resource in response.resources)


def test_sunnyside_woodside_mutual_aid_is_in_curated_resources() -> None:
    resources = load_curated_food_resources(borough="Queens").resources
    swma = next(resource for resource in resources if resource.id == "swma-bliss-plaza")
    assert "Sunnyside & Woodside Mutual Aid" in swma.name
    assert "pop-up pantry" in swma.matched_terms


def test_gardener_destinations_only_include_verified_active_receivers() -> None:
    from app.services.location_service import location_service

    destinations = location_service.donation_destinations()
    assert destinations
    assert all(location.verified_partner for location in destinations)
    assert all(location.participating and location.accepts_saturday for location in destinations)
    assert all(location.accepted_categories for location in destinations)
