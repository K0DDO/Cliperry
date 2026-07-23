"""Built-in Cliperry admin panel — HTML + JSON API under ``/admin``."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.auth import (
    COOKIE_MAX_AGE,
    COOKIE_NAME,
    AdminUserDep,
    credentials_valid,
    is_admin_authenticated,
    issue_session_token,
)
from app.admin.schemas import (
    AdminTaskListResponse,
    AdminUserItem,
    AdminUserListResponse,
    DashboardResponse,
)
from app.admin.service import AdminService
from app.config import Settings, get_settings
from app.database.session import get_db

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(prefix="/admin", tags=["admin"])
DbDep = Annotated[AsyncSession, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def _service(session: AsyncSession) -> AdminService:
    return AdminService(session)


async def require_admin_html(
    request: Request,
    settings: SettingsDep,
) -> str | RedirectResponse:
    """Cookie-only guard for HTML pages; redirects to login when missing."""
    from app.admin.auth import verify_session_token

    user = verify_session_token(request.cookies.get(COOKIE_NAME), settings)
    if user:
        return user
    next_url = quote(str(request.url.path), safe="/")
    return RedirectResponse(
        url=f"/admin/login?next={next_url}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


# ---------------------------------------------------------------------------
# Auth pages
# ---------------------------------------------------------------------------


@router.get("/login", response_class=HTMLResponse, response_model=None)
async def login_page(
    request: Request,
    settings: SettingsDep,
    next: str = "/admin",
) -> HTMLResponse | RedirectResponse:
    if is_admin_authenticated(request, settings):
        return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "title": "Admin login",
            "next": next or "/admin",
            "error": None,
            "app_name": settings.app_name,
        },
    )


@router.post("/login", response_model=None)
async def login_submit(
    request: Request,
    settings: SettingsDep,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    next: Annotated[str, Form()] = "/admin",
) -> RedirectResponse | HTMLResponse:
    # Brute-force protection on admin login.
    try:
        from app.auth.rate_limit import RateLimiter, client_ip
        from app.database.redis import get_redis

        redis = get_redis()
        limiter = RateLimiter(redis, settings)
        ip = client_ip(request, trust_proxy=settings.trust_proxy_headers)
        await limiter.check(
            key=f"admin_login:{ip}",
            limit=settings.rate_limit_admin_login,
        )
    except Exception as exc:  # noqa: BLE001
        from app.errors import AppError

        if isinstance(exc, AppError) and exc.code == "rate_limit_exceeded":
            return templates.TemplateResponse(
                request,
                "login.html",
                {
                    "title": "Admin login",
                    "next": "/admin",
                    "error": "Слишком много попыток. Подождите минуту.",
                    "app_name": settings.app_name,
                },
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        # If Redis is down, fail closed for login in production.
        if settings.is_production:
            return templates.TemplateResponse(
                request,
                "login.html",
                {
                    "title": "Admin login",
                    "next": "/admin",
                    "error": "Вход временно недоступен",
                    "app_name": settings.app_name,
                },
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    if not credentials_valid(username, password, settings):
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "title": "Admin login",
                "next": next if _safe_admin_next(next) else "/admin",
                "error": "Неверный логин или пароль",
                "app_name": settings.app_name,
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    target = next if _safe_admin_next(next) else "/admin"
    response = RedirectResponse(url=target, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=COOKIE_NAME,
        value=issue_session_token(username, settings),
        httponly=True,
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
        secure=settings.is_production,
        path="/admin",
    )
    return response


@router.post("/logout")
async def logout() -> RedirectResponse:
    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(COOKIE_NAME, path="/admin")
    return response


def _safe_admin_next(value: str | None) -> bool:
    """Allow only relative /admin paths (no open redirects)."""
    if not value:
        return False
    if not value.startswith("/admin"):
        return False
    if value.startswith("//") or "://" in value or "\\" in value:
        return False
    return True


# ---------------------------------------------------------------------------
# HTML pages
# ---------------------------------------------------------------------------


@router.get("/", response_class=HTMLResponse, response_model=None)
async def dashboard_page(
    request: Request,
    session: DbDep,
    settings: SettingsDep,
    admin: Annotated[str | RedirectResponse, Depends(require_admin_html)],
) -> HTMLResponse | RedirectResponse:
    if isinstance(admin, RedirectResponse):
        return admin
    data = await _service(session).dashboard()
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "title": "Dashboard",
            "admin": admin,
            "app_name": settings.app_name,
            "stats": data.stats,
            "recent_errors": data.recent_errors,
            "nav": "dashboard",
        },
    )


@router.get("/users", response_class=HTMLResponse, response_model=None)
async def users_page(
    request: Request,
    session: DbDep,
    settings: SettingsDep,
    admin: Annotated[str | RedirectResponse, Depends(require_admin_html)],
    page: int = Query(default=1, ge=1),
) -> HTMLResponse | RedirectResponse:
    if isinstance(admin, RedirectResponse):
        return admin
    data = await _service(session).list_users(page=page, page_size=20)
    return templates.TemplateResponse(
        request,
        "users.html",
        {
            "title": "Users",
            "admin": admin,
            "app_name": settings.app_name,
            "data": data,
            "nav": "users",
        },
    )


@router.post("/users/{user_id}/block", response_model=None)
async def block_user_form(
    user_id: uuid.UUID,
    session: DbDep,
    admin: Annotated[str | RedirectResponse, Depends(require_admin_html)],
    blocked: Annotated[str, Form()] = "1",
) -> RedirectResponse:
    if isinstance(admin, RedirectResponse):
        return admin
    try:
        await _service(session).set_user_blocked(user_id, blocked=blocked == "1")
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RedirectResponse(url="/admin/users", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/tasks", response_class=HTMLResponse, response_model=None)
async def tasks_page(
    request: Request,
    session: DbDep,
    settings: SettingsDep,
    admin: Annotated[str | RedirectResponse, Depends(require_admin_html)],
    page: int = Query(default=1, ge=1),
    status_filter: str | None = Query(default=None, alias="status"),
) -> HTMLResponse | RedirectResponse:
    if isinstance(admin, RedirectResponse):
        return admin
    try:
        data = await _service(session).list_tasks(
            page=page,
            page_size=20,
            status_filter=status_filter or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return templates.TemplateResponse(
        request,
        "tasks.html",
        {
            "title": "Tasks",
            "admin": admin,
            "app_name": settings.app_name,
            "data": data,
            "nav": "tasks",
            "status_filter": status_filter or "",
        },
    )


# ---------------------------------------------------------------------------
# JSON API (Basic auth or cookie)
# ---------------------------------------------------------------------------


@router.get("/api/dashboard", response_model=DashboardResponse)
async def api_dashboard(
    session: DbDep,
    _admin: AdminUserDep,
) -> DashboardResponse:
    return await _service(session).dashboard()


@router.get("/api/users", response_model=AdminUserListResponse)
async def api_users(
    session: DbDep,
    _admin: AdminUserDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> AdminUserListResponse:
    return await _service(session).list_users(page=page, page_size=page_size)


@router.post("/api/users/{user_id}/block", response_model=AdminUserItem)
async def api_block_user(
    user_id: uuid.UUID,
    session: DbDep,
    _admin: AdminUserDep,
    blocked: bool = Query(default=True),
) -> AdminUserItem:
    try:
        return await _service(session).set_user_blocked(user_id, blocked=blocked)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/tasks", response_model=AdminTaskListResponse)
async def api_tasks(
    session: DbDep,
    _admin: AdminUserDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
) -> AdminTaskListResponse:
    try:
        return await _service(session).list_tasks(
            page=page,
            page_size=page_size,
            status_filter=status_filter,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/health")
async def admin_health(_admin: AdminUserDep) -> JSONResponse:
    return JSONResponse({"status": "ok", "scope": "admin"})
