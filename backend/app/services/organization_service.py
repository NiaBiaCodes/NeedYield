from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

from app.models.location import Location
from app.models.organization import (
    ApplicationStatus,
    ApprovalRequest,
    OrganizationApplication,
    OrganizationApplicationCreate,
    WeeklyNeeds,
    WeeklyNeedsCreate,
)
from app.services.auth_service import CurrentUser
from app.services.location_service import location_service


class OrganizationService:
    """Organization workflow with a reliable in-memory demo path.

    Supabase tables and RLS are defined in migration 004; the REST adapter can
    replace this store without changing the API or UI contracts.
    """

    def __init__(self) -> None:
        self._applications: dict[str, OrganizationApplication] = {}
        self._weekly_needs: dict[str, WeeklyNeeds] = {}
        self._lock = RLock()

    def apply(self, user: CurrentUser, payload: OrganizationApplicationCreate) -> OrganizationApplication:
        with self._lock:
            existing = next((item for item in self._applications.values() if item.user_id == user.id), None)
            if existing:
                return existing.model_copy(deep=True)
            application = OrganizationApplication(
                **payload.model_dump(), id=str(uuid4()), user_id=user.id, email=user.email,
                status=ApplicationStatus.PENDING, created_at=datetime.now(timezone.utc),
            )
            self._applications[application.id] = application
            return application.model_copy(deep=True)

    def mine(self, user_id: str) -> OrganizationApplication | None:
        with self._lock:
            item = next((item for item in self._applications.values() if item.user_id == user_id), None)
            if item:
                return item.model_copy(deep=True)
            if user_id == "demo-organization":
                location = location_service.get("east-harlem-harvest-hub")
                if location:
                    return OrganizationApplication(
                        id="demo-organization-application", user_id=user_id,
                        email="organization@demo.needyield.local", organization_name=location.name,
                        organization_type="Demo food pantry", address=location.address,
                        borough=location.borough, neighborhood=location.neighborhood,
                        contact_name="Demo Coordinator", phone="212-555-0100",
                        accepted_categories=location.accepted_categories,
                        opening_time=location.opening_time, closing_time=location.closing_time,
                        notes="Demo organization linked to structured NeedYield data.",
                        status=ApplicationStatus.APPROVED,
                        created_at=datetime.now(timezone.utc), location_id=location.id,
                        review_note="Demo organization",
                    )
            return None

    def all(self) -> list[OrganizationApplication]:
        with self._lock:
            return [item.model_copy(deep=True) for item in sorted(self._applications.values(), key=lambda row: row.created_at, reverse=True)]

    def approve(self, application_id: str, approval: ApprovalRequest, reviewer_id: str) -> OrganizationApplication:
        del reviewer_id
        with self._lock:
            application = self._applications.get(application_id)
            if not application:
                raise KeyError("Application not found")
            location_id = application.location_id or f"org-{application.id[:8]}"
            location_service.add_location(Location(
                id=location_id, name=application.organization_name, address=application.address,
                borough=application.borough, neighborhood=application.neighborhood,
                latitude=approval.latitude, longitude=approval.longitude,
                opening_time=application.opening_time, closing_time=application.closing_time,
                accepted_categories=application.accepted_categories, saturday_needs={},
                requested_quantities={}, inventory={}, verified_partner=True, participating=True,
                accepts_saturday=True, demo=application.user_id.startswith("demo-"),
                community_need_score=0.5, community_need_source="Awaiting NYC Open Data refresh",
            ))
            application.status = ApplicationStatus.APPROVED
            application.location_id = location_id
            application.review_note = approval.review_note
            return application.model_copy(deep=True)

    def reject(self, application_id: str, note: str) -> OrganizationApplication:
        with self._lock:
            application = self._applications.get(application_id)
            if not application:
                raise KeyError("Application not found")
            application.status = ApplicationStatus.REJECTED
            application.review_note = note
            return application.model_copy(deep=True)

    def submit_needs(self, user_id: str, payload: WeeklyNeedsCreate) -> WeeklyNeeds:
        application = self.mine(user_id)
        if not application or application.status != ApplicationStatus.APPROVED or not application.location_id:
            raise PermissionError("Organization approval is required before submitting weekly needs")
        needs = WeeklyNeeds(**payload.model_dump(), location_id=application.location_id, submitted_at=datetime.now(timezone.utc))
        location_service.update_organization_needs(application.location_id, needs)
        with self._lock:
            self._weekly_needs[user_id] = needs
        return needs.model_copy(deep=True)

    def get_needs(self, user_id: str) -> WeeklyNeeds | None:
        with self._lock:
            needs = self._weekly_needs.get(user_id)
            if needs:
                return needs.model_copy(deep=True)
        if user_id == "demo-organization":
            application = self.mine(user_id)
            location = location_service.get(application.location_id) if application and application.location_id else None
            if location and location.saturday_needs:
                from datetime import date, timedelta
                from app.models.organization import WeeklyNeedItem
                return WeeklyNeeds(
                    distribution_date=date.today() + timedelta(days=(5 - date.today().weekday()) % 7),
                    accepting_donations=location.participating,
                    dropoff_start=location.opening_time, dropoff_end=location.closing_time,
                    notes="Demo weekly needs derived from the linked location.",
                    items=[WeeklyNeedItem(produce_name=name, need_level=level, requested_quantity=location.requested_quantities.get(name, 0)) for name, level in location.saturday_needs.items()],
                    location_id=location.id, submitted_at=datetime.now(timezone.utc),
                )
        return None


organization_service = OrganizationService()
