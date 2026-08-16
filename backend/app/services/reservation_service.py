from datetime import datetime
from threading import RLock
from uuid import uuid4
from zoneinfo import ZoneInfo
from typing import Optional
from app.models.reservation import Reservation, ReservationCreate, ReservationStatus
from app.services.inventory_service import release_inventory, reserve_inventory
from app.services.location_service import location_service
from app.services.database_service import database_service


class ReservationService:
    def __init__(self) -> None:
        self._items: dict[str, Reservation] = {item.id: item for item in database_service.load_reservations()}
        self._lock = RLock()

    def all(self, user_id: Optional[str] = None) -> list[Reservation]:
        with self._lock:
            now = datetime.now(ZoneInfo("America/New_York"))
            for reservation in list(self._items.values()):
                if reservation.status == ReservationStatus.RESERVED and now >= reservation.expires_at:
                    self.expire(reservation.id)
            items = (item for item in self._items.values() if user_id is None or item.user_id == user_id)
            return sorted((item.model_copy() for item in items), key=lambda item: item.created_at, reverse=True)

    def for_location(self, location_id: str) -> list[Reservation]:
        return [item for item in self.all() if item.location_id == location_id]

    def create(self, payload: ReservationCreate, user_id: Optional[str] = None, demo: bool = False) -> Reservation:
        location = location_service.get(payload.location_id)
        if not location:
            raise KeyError("Location not found")
        with self._lock:
            now = datetime.now(ZoneInfo("America/New_York"))
            deadline = now.replace(hour=17, minute=0, second=0, microsecond=0)
            produce = payload.produce.lower()
            if database_service.configured and user_id and not demo:
                row = database_service.create_reservation_atomic(location.id, produce, payload.quantity, user_id, deadline.isoformat())
                if not row:
                    raise ValueError(database_service.last_error or "Reservation transaction failed")
                reservation = Reservation(id=row["reservation_id"], user_id=user_id, location_id=location.id, location_name=location.name, location_address=location.address, produce=produce, quantity=payload.quantity, created_at=now, expires_at=deadline, status=ReservationStatus.RESERVED)
                location_service.set_inventory_local(location.id, produce, int(row["remaining_quantity"]))
            else:
                reserve_inventory(payload.location_id, produce, payload.quantity)
                reservation = Reservation(id=str(uuid4()), user_id=user_id, location_id=location.id, location_name=location.name, location_address=location.address, produce=produce, quantity=payload.quantity, created_at=now, expires_at=deadline, status=ReservationStatus.RESERVED)
            self._items[reservation.id] = reservation
            if not (database_service.configured and user_id and not demo):
                database_service.save_reservation(reservation, user_id=None if demo else user_id)
            return reservation.model_copy()

    def expire(self, reservation_id: str, force: bool = False) -> Reservation:
        with self._lock:
            reservation = self._items.get(reservation_id)
            if not reservation:
                raise KeyError("Reservation not found")
            now = datetime.now(ZoneInfo("America/New_York"))
            if reservation.status == ReservationStatus.RESERVED and (force or now >= reservation.expires_at):
                reservation.status = ReservationStatus.EXPIRED
                release_inventory(reservation.location_id, reservation.produce, reservation.quantity)
                database_service.save_reservation(reservation)
            return reservation.model_copy()


reservation_service = ReservationService()
