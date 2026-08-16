from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app.models.organization import ApprovalRequest, OrganizationApplication, OrganizationApplicationCreate, RejectionRequest, WeeklyNeeds, WeeklyNeedsCreate
from app.services.auth_service import CurrentUser, require_admin, require_role
from app.services.organization_service import organization_service

router = APIRouter(prefix="/api", tags=["organizations"])


@router.post("/organizations/applications", response_model=OrganizationApplication)
def apply(payload: OrganizationApplicationCreate, user: CurrentUser = Depends(require_role("organization"))):
    return organization_service.apply(user, payload)


@router.get("/organizations/application", response_model=Optional[OrganizationApplication])
def my_application(user: CurrentUser = Depends(require_role("organization"))):
    return organization_service.mine(user.id)


@router.get("/admin/organization-applications", response_model=list[OrganizationApplication])
def applications(_: CurrentUser = Depends(require_admin)):
    return organization_service.all()


@router.post("/admin/organization-applications/{application_id}/approve", response_model=OrganizationApplication)
def approve(application_id: str, payload: ApprovalRequest, user: CurrentUser = Depends(require_admin)):
    try:
        return organization_service.approve(application_id, payload, user.id)
    except KeyError as error:
        raise HTTPException(404, str(error)) from error


@router.post("/admin/organization-applications/{application_id}/reject", response_model=OrganizationApplication)
def reject(application_id: str, payload: RejectionRequest, _: CurrentUser = Depends(require_admin)):
    try:
        return organization_service.reject(application_id, payload.review_note)
    except KeyError as error:
        raise HTTPException(404, str(error)) from error


@router.post("/organizations/weekly-needs", response_model=WeeklyNeeds)
def weekly_needs(payload: WeeklyNeedsCreate, user: CurrentUser = Depends(require_role("organization"))):
    try:
        return organization_service.submit_needs(user.id, payload)
    except (PermissionError, KeyError) as error:
        raise HTTPException(403, str(error)) from error


@router.get("/organizations/weekly-needs", response_model=Optional[WeeklyNeeds])
def get_weekly_needs(user: CurrentUser = Depends(require_role("organization"))):
    return organization_service.get_needs(user.id)
