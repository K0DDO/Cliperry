"""Admin authentication — cookie session + HTTP Basic."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import Settings, get_settings

COOKIE_NAME = "cliperry_admin"
COOKIE_MAX_AGE = 60 * 60 * 12  # 12 hours
_basic = HTTPBasic(auto_error=False)


def verify_password(plain: str, expected: str) -> bool:
    """Constant-time password compare."""
    return secrets.compare_digest(plain.encode("utf-8"), expected.encode("utf-8"))


def credentials_valid(username: str, password: str, settings: Settings) -> bool:
    return secrets.compare_digest(
        username.encode("utf-8"),
        settings.admin_username.encode("utf-8"),
    ) and verify_password(password, settings.admin_password)


def issue_session_token(username: str, settings: Settings) -> str:
    """Signed ``exp:username:sig`` token for admin cookie."""
    exp = int(time.time()) + COOKIE_MAX_AGE
    payload = f"{exp}:{username}"
    sig = hmac.new(
        settings.secret_key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}:{sig}"


def verify_session_token(token: str | None, settings: Settings) -> str | None:
    """Return username if cookie token is valid, else None."""
    if not token:
        return None
    parts = token.split(":")
    if len(parts) != 3:
        return None
    exp_raw, username, sig = parts
    try:
        exp = int(exp_raw)
    except ValueError:
        return None
    if exp < int(time.time()):
        return None
    if not secrets.compare_digest(username, settings.admin_username):
        return None
    payload = f"{exp_raw}:{username}"
    expected = hmac.new(
        settings.secret_key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not secrets.compare_digest(sig, expected):
        return None
    return username


def is_admin_authenticated(request: Request, settings: Settings) -> bool:
    token = request.cookies.get(COOKIE_NAME)
    if verify_session_token(token, settings):
        return True
    return False


async def require_admin(
    request: Request,
    credentials: Annotated[HTTPBasicCredentials | None, Depends(_basic)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> str:
    """
    Protect admin routes.

    Accepts either a signed session cookie or HTTP Basic credentials.
    """
    cookie_user = verify_session_token(request.cookies.get(COOKIE_NAME), settings)
    if cookie_user:
        return cookie_user

    if credentials and credentials_valid(
        credentials.username,
        credentials.password,
        settings,
    ):
        return credentials.username

    # HTML navigations → redirect-friendly 401 with WWW-Authenticate for API clients.
    accept = request.headers.get("accept", "")
    if "text/html" in accept and request.method == "GET":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin login required",
            headers={"X-Admin-Login": "/admin/login"},
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid admin credentials",
        headers={"WWW-Authenticate": "Basic realm=\"Cliperry Admin\""},
    )


AdminUserDep = Annotated[str, Depends(require_admin)]
