import re
from datetime import datetime
from zoneinfo import ZoneInfo

from app.models.organization_assistant import (
    InventoryStatusItem,
    OrganizationActionItem,
    OrganizationAssistantIntent,
    OrganizationAssistantResponse,
    OrganizationDonationSummary,
    OrganizationTodayStatus,
)
from app.models.reservation import ReservationStatus
from app.services.auth_service import CurrentUser
from app.services.donation_service import donation_service
from app.services.location_service import location_service
from app.services.organization_service import organization_service
from app.services.reservation_service import reservation_service

NYC = ZoneInfo("America/New_York")


class OrganizationAssistantService:
    def __init__(
        self,
        organizations=organization_service,
        locations=location_service,
        donations=donation_service,
        reservations=reservation_service,
    ) -> None:
        self.organizations = organizations
        self.locations = locations
        self.donations = donations
        self.reservations = reservations

    @staticmethod
    def detect_intent(query: str) -> OrganizationAssistantIntent:
        value = query.lower().strip()
        if re.search(r"today.?s summary|today at a glance|daily summary|briefing", value):
            return OrganizationAssistantIntent.DAILY_SUMMARY
        if re.search(r"what.*attention|need.*action|outstanding|pending", value):
            return OrganizationAssistantIntent.PENDING_ACTIONS
        if re.search(r"what.*(arriv|coming)|incoming donation", value):
            return OrganizationAssistantIntent.INCOMING_DONATIONS
        if re.search(r"what should we request|recommend.*request|request this week", value):
            return OrganizationAssistantIntent.RECOMMENDED_REQUESTS
        if re.search(r"low on|low stock|run out|shortage", value):
            return OrganizationAssistantIntent.LOW_STOCK
        if re.search(r"weekly need|what.*need this week", value):
            return OrganizationAssistantIntent.WEEKLY_NEEDS
        if re.search(r"pickup|reserved|distribution", value):
            return OrganizationAssistantIntent.PICKUP_STATUS
        if re.search(r"inventory|what.*have|in stock", value):
            return OrganizationAssistantIntent.INVENTORY_STATUS
        return OrganizationAssistantIntent.GENERAL

    def query(self, user: CurrentUser, query: str) -> OrganizationAssistantResponse:
        application = self.organizations.mine(user.id)
        if not application or not application.location_id or application.status.value != "APPROVED":
            raise PermissionError("An approved organization is required to use the operations assistant")
        location = self.locations.get(application.location_id)
        if not location:
            raise KeyError("Organization location not found")

        intent = self.detect_intent(query)
        needs = self.organizations.get_needs(user.id)
        targets = {item.produce_name.lower(): item.requested_quantity for item in needs.items} if needs else {}
        now = datetime.now(NYC)
        donations = self.donations.for_location(location.id)
        today_donations = [item for item in donations if item.timestamp.astimezone(NYC).date() == now.date()]
        reservations = self.reservations.for_location(location.id)
        active_reservations = [item for item in reservations if item.status == ReservationStatus.RESERVED]

        confirmed_by_produce: dict[str, int] = {}
        donation_summaries: list[OrganizationDonationSummary] = []
        for donation in today_donations:
            for allocation in donation.allocations:
                if allocation.location_id != location.id or allocation.quantity <= 0:
                    continue
                produce = allocation.produce.lower()
                confirmed_by_produce[produce] = confirmed_by_produce.get(produce, 0) + allocation.quantity
                donation_summaries.append(OrganizationDonationSummary(
                    donation_id=donation.id, gardener_id=donation.gardener_id,
                    produce_name=produce, quantity=allocation.quantity,
                    confirmed_at=donation.timestamp.astimezone(NYC).isoformat(),
                    status=donation.status.value,
                ))

        reserved_by_produce: dict[str, int] = {}
        for reservation in active_reservations:
            reserved_by_produce[reservation.produce] = reserved_by_produce.get(reservation.produce, 0) + reservation.quantity

        produce_names = sorted(set(location.inventory) | set(targets))
        inventory = [
            InventoryStatusItem(
                produce_name=name,
                available_quantity=location.inventory.get(name, 0),
                weekly_target=targets.get(name) if needs else None,
                confirmed_donation_quantity=confirmed_by_produce.get(name, 0),
                reserved_quantity=reserved_by_produce.get(name, 0),
                projected_shortage=max(0, targets[name] - location.inventory.get(name, 0)) if name in targets else None,
            )
            for name in produce_names
        ]
        low_stock = [item for item in inventory if item.projected_shortage is not None and item.projected_shortage > 0]

        actions: list[OrganizationActionItem] = []
        if not needs:
            actions.append(OrganizationActionItem(
                id="weekly-needs-missing", kind="weekly_needs", title="Add weekly needs",
                detail="Weekly needs have not been set, so shortages cannot be calculated.",
                urgency=5, action="edit_weekly_needs",
            ))
        for item in sorted(low_stock, key=lambda row: row.projected_shortage or 0, reverse=True):
            actions.append(OrganizationActionItem(
                id=f"request-{item.produce_name}", kind="shortage",
                title=f"Request {item.produce_name}",
                detail=f"{item.available_quantity} available against a weekly target of {item.weekly_target}; shortage {item.projected_shortage}.",
                urgency=4, action="add_to_weekly_needs", produce_name=item.produce_name,
                suggested_quantity=item.projected_shortage,
            ))
        if active_reservations:
            reserved_total = sum(item.quantity for item in active_reservations)
            actions.append(OrganizationActionItem(
                id="active-pickups", kind="pickup", title="Prepare reserved produce",
                detail=f"{reserved_total} items are reserved for neighbor pickup.", urgency=3,
                action="view_pickups",
            ))
        actions = sorted(actions, key=lambda item: item.urgency, reverse=True)[:5]

        today = OrganizationTodayStatus(
            confirmed_donations=len(today_donations), low_stock_items=len(low_stock),
            outstanding_actions=len(actions),
            reserved_for_distribution=sum(item.quantity for item in active_reservations),
        )
        summary = self._summary(intent, inventory, low_stock, donation_summaries, actions, today, needs is not None)
        return OrganizationAssistantResponse(
            intent=intent, organization_name=application.organization_name,
            location_id=location.id, demo=location.demo, summary=summary,
            today=today, inventory=self._inventory_for_intent(intent, inventory, low_stock),
            donations=donation_summaries if intent in {OrganizationAssistantIntent.INCOMING_DONATIONS, OrganizationAssistantIntent.DAILY_SUMMARY} else [],
            actions=actions if intent in {OrganizationAssistantIntent.PENDING_ACTIONS, OrganizationAssistantIntent.RECOMMENDED_REQUESTS, OrganizationAssistantIntent.DAILY_SUMMARY, OrganizationAssistantIntent.GENERAL} else [],
        )

    @staticmethod
    def _inventory_for_intent(intent: OrganizationAssistantIntent, inventory: list[InventoryStatusItem], low_stock: list[InventoryStatusItem]) -> list[InventoryStatusItem]:
        if intent in {OrganizationAssistantIntent.LOW_STOCK, OrganizationAssistantIntent.RECOMMENDED_REQUESTS}:
            return low_stock
        if intent in {OrganizationAssistantIntent.INVENTORY_STATUS, OrganizationAssistantIntent.WEEKLY_NEEDS, OrganizationAssistantIntent.DAILY_SUMMARY, OrganizationAssistantIntent.GENERAL}:
            return inventory
        return []

    @staticmethod
    def _summary(intent: OrganizationAssistantIntent, inventory: list[InventoryStatusItem], low_stock: list[InventoryStatusItem], donations: list[OrganizationDonationSummary], actions: list[OrganizationActionItem], today: OrganizationTodayStatus, has_needs: bool) -> str:
        if intent == OrganizationAssistantIntent.LOW_STOCK:
            return f"{len(low_stock)} produce item{'s are' if len(low_stock) != 1 else ' is'} below the current weekly target." if has_needs else "Weekly needs have not been set, so shortages cannot be calculated yet."
        if intent == OrganizationAssistantIntent.RECOMMENDED_REQUESTS:
            return f"Based on current inventory and weekly targets, {len(low_stock)} produce item{'s need' if len(low_stock) != 1 else ' needs'} additional supply." if has_needs else "Add weekly needs before NeedYield calculates request recommendations."
        if intent == OrganizationAssistantIntent.INCOMING_DONATIONS:
            return f"{len(donations)} confirmed allocation{'s were' if len(donations) != 1 else ' was'} recorded for this organization today. NeedYield does not yet store arrival windows."
        if intent == OrganizationAssistantIntent.PENDING_ACTIONS:
            return f"{len(actions)} operational item{'s need' if len(actions) != 1 else ' needs'} attention."
        if intent == OrganizationAssistantIntent.PICKUP_STATUS:
            return f"{today.reserved_for_distribution} items are currently reserved for distribution."
        if intent == OrganizationAssistantIntent.DAILY_SUMMARY:
            return f"Today: {today.confirmed_donations} confirmed donations, {today.low_stock_items} low-stock items, {today.reserved_for_distribution} items reserved, and {today.outstanding_actions} outstanding actions."
        if intent == OrganizationAssistantIntent.WEEKLY_NEEDS:
            return "Current weekly targets and inventory are shown below." if has_needs else "Weekly needs have not been set."
        if intent == OrganizationAssistantIntent.INVENTORY_STATUS:
            return f"Current inventory contains {len(inventory)} tracked produce items."
        return "I can summarize inventory, shortages, confirmed donations, weekly needs, pickups, and outstanding actions using current NeedYield data."


organization_assistant_service = OrganizationAssistantService()
