from fastapi import APIRouter, Depends, HTTPException
from app.models.donation import ConfirmDonationRequest, Donation
from app.services.donation_service import donation_service
from app.services.auth_service import CurrentUser, require_role

router = APIRouter(prefix="/api", tags=["donations"])


@router.post("/donations/confirm", response_model=Donation, status_code=201)
def confirm_donation(payload: ConfirmDonationRequest, user: CurrentUser = Depends(require_role("gardener"))) -> Donation:
    try:
        return donation_service.confirm(payload.model_copy(update={"gardener_id": user.id}))
    except KeyError as error:
        raise HTTPException(404, str(error)) from error
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
