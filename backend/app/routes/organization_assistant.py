from fastapi import APIRouter, Depends, HTTPException

from app.models.organization_assistant import OrganizationAssistantQuery, OrganizationAssistantResponse
from app.services.auth_service import CurrentUser, require_role
from app.services.organization_assistant_service import organization_assistant_service

router = APIRouter(prefix="/api/organizations/assistant", tags=["organization-assistant"])


@router.post("/query", response_model=OrganizationAssistantResponse)
def query_operations(
    payload: OrganizationAssistantQuery,
    user: CurrentUser = Depends(require_role("organization")),
) -> OrganizationAssistantResponse:
    try:
        return organization_assistant_service.query(user, payload.query)
    except PermissionError as error:
        raise HTTPException(403, str(error)) from error
    except KeyError as error:
        raise HTTPException(404, str(error)) from error
