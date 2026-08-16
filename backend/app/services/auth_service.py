import os
from typing import Optional

import httpx
from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel

from app.services.database_service import database_service


class CurrentUser(BaseModel):
    id: str
    email: str = ""
    role: str
    demo: bool = False
    is_admin: bool = False


def _demo_enabled() -> bool:
    return os.getenv("DEMO_MODE_ENABLED", "true").lower() in {"1", "true", "yes"}


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    x_demo_user: Optional[str] = Header(default=None),
    x_demo_role: Optional[str] = Header(default=None),
    x_demo_admin: Optional[str] = Header(default=None),
) -> CurrentUser:
    if authorization and authorization.startswith("Bearer "):
        if not database_service.configured:
            raise HTTPException(503, "Production authentication is not configured")
        token = authorization.removeprefix("Bearer ").strip()
        try:
            response = httpx.get(
                f"{database_service.url}/auth/v1/user",
                headers={"apikey": database_service.service_key, "Authorization": f"Bearer {token}"},
                timeout=5.0,
            )
            response.raise_for_status()
            auth_user = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise HTTPException(401, "Invalid or expired session") from error
        profile = database_service.get_profile(auth_user["id"])
        if not profile:
            raise HTTPException(403, "User profile is unavailable")
        return CurrentUser(id=auth_user["id"], email=auth_user.get("email", ""), role=profile["role"], is_admin=bool(profile.get("is_admin")))

    if _demo_enabled() and x_demo_user and x_demo_role in {"neighbor", "gardener", "organization"}:
        return CurrentUser(id=x_demo_user, email=f"{x_demo_role}@demo.needyield.local", role=x_demo_role, demo=True, is_admin=x_demo_admin == "true")
    raise HTTPException(401, "Sign in or continue with a demo account")


def require_role(*roles: str):
    def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(403, f"This action requires one of these roles: {', '.join(roles)}")
        return user
    return dependency


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not user.is_admin:
        raise HTTPException(403, "Administrator approval is required")
    return user
