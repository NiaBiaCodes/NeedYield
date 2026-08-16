from fastapi import APIRouter, Depends, HTTPException
from app.models.reservation import Reservation, ReservationCreate
from app.services.reservation_service import reservation_service
from app.services.auth_service import CurrentUser, require_role

router = APIRouter(prefix="/api", tags=["reservations"])


@router.get("/reservations", response_model=list[Reservation])
def list_reservations(user: CurrentUser = Depends(require_role("neighbor"))) -> list[Reservation]:
    return reservation_service.all(user.id)


@router.post("/reservations", response_model=Reservation, status_code=201)
def create_reservation(payload: ReservationCreate, user: CurrentUser = Depends(require_role("neighbor"))) -> Reservation:
    try:
        return reservation_service.create(payload, user.id, user.demo)
    except KeyError as error:
        raise HTTPException(404, str(error)) from error
    except ValueError as error:
        raise HTTPException(409, str(error)) from error


@router.post("/demo/expire-reservation/{reservation_id}", response_model=Reservation)
def demo_expire(reservation_id: str, user: CurrentUser = Depends(require_role("neighbor"))) -> Reservation:
    if not user.demo:
        raise HTTPException(404, "Not found")
    try:
        return reservation_service.expire(reservation_id, force=True)
    except KeyError as error:
        raise HTTPException(404, str(error)) from error
