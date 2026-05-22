from datetime import datetime, timedelta
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password, verify_password
from app.config import get_app_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import ActivityLog, Integration, ProcessedEmail, User
from app.services.telegram import send_telegram_message, verify_telegram_bot_token, verify_telegram_chat

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
settings = get_app_settings()


def _cookie_options() -> dict:
    secure = get_app_settings().app_url.startswith("https://")
    return {
        "httponly": True,
        "max_age": 7 * 24 * 3600,
        "samesite": "lax",
        "secure": secure,
    }


def _mask_bot_token(token: str | None) -> str | None:
    if not token or len(token) < 12:
        return None
    return f"{token[:10]}...{token[-4:]}"


def _render(request: Request, template: str, context: dict | None = None):
    payload = {"app_name": settings.app_name}
    if context:
        payload.update(context)
    return templates.TemplateResponse(request, template, payload)


@router.get("/", response_class=HTMLResponse)
def landing(request: Request):
    return _render(request, "landing.html")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return _render(
        request,
        "login.html",
        {
            "error": request.query_params.get("error"),
            "notice": request.query_params.get("notice"),
        },
    )


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return _render(request, "register.html", {"error": request.query_params.get("error")})


@router.post("/register")
def register(
    email: str = Form(...),
    name: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    email = email.strip().lower()
    if db.scalar(select(User).where(User.email == email)):
        return RedirectResponse(
            "/register?error=Email+already+registered",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    user = User(
        email=email,
        name=name.strip() or email.split("@")[0],
        password_hash=hash_password(password),
        plan="free",
    )
    db.add(user)
    db.flush()
    db.add(Integration(user_id=user.id))
    db.commit()

    token = create_access_token(user.id, user.email)
    response = RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie("access_token", token, **_cookie_options())
    return response


@router.post("/login")
def login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if not user or not verify_password(password, user.password_hash):
        return RedirectResponse(
            "/login?error=Invalid+email+or+password",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    token = create_access_token(user.id, user.email)
    response = RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie("access_token", token, **_cookie_options())
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    return response


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    integration = user.integration or Integration(user_id=user.id)
    if not user.integration:
        db.add(integration)
        db.commit()

    flash_error = request.query_params.get("error")
    flash_success = request.query_params.get("saved")

    start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_usage = db.scalar(
        select(func.count())
        .select_from(ProcessedEmail)
        .where(
            ProcessedEmail.user_id == user.id,
            ProcessedEmail.created_at >= start_of_month,
        )
    ) or 0

    recent_emails = db.scalars(
        select(ProcessedEmail)
        .where(ProcessedEmail.user_id == user.id)
        .order_by(ProcessedEmail.created_at.desc())
        .limit(8)
    ).all()

    activity = db.scalars(
        select(ActivityLog)
        .where(ActivityLog.user_id == user.id)
        .order_by(ActivityLog.created_at.desc())
        .limit(8)
    ).all()

    return _render(
        request,
        "dashboard.html",
        {
            "user": user,
            "integration": integration,
            "monthly_usage": monthly_usage,
            "monthly_limit": settings.free_plan_monthly_limit,
            "recent_emails": recent_emails,
            "activity": activity,
            "flash_error": flash_error,
            "flash_success": flash_success,
            "masked_bot_token": _mask_bot_token(integration.telegram_bot_token),
        },
    )


@router.post("/dashboard/settings")
def update_settings(
    telegram_bot_token: str = Form(""),
    telegram_chat_id: str = Form(""),
    gmail_query: str = Form(""),
    automation_enabled: str | None = Form(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    integration = user.integration
    if not integration:
        integration = Integration(user_id=user.id)
        db.add(integration)

    bot_token = telegram_bot_token.strip()
    chat_id = telegram_chat_id.strip() or integration.telegram_chat_id
    previous_bot_token = integration.telegram_bot_token
    bot_token_changed = bool(bot_token and bot_token != previous_bot_token)

    if bot_token:
        try:
            integration.telegram_bot_username = verify_telegram_bot_token(bot_token)
        except RuntimeError as exc:
            message = quote(f"Invalid Telegram bot token. Create one with @BotFather. ({exc})")
            return RedirectResponse(f"/dashboard?error={message}", status_code=status.HTTP_303_SEE_OTHER)
        integration.telegram_bot_token = bot_token

    effective_bot_token = integration.telegram_bot_token
    if not effective_bot_token:
        message = quote("Paste your Telegram bot token to switch bots. The .env token is not used by the SaaS app.")
        return RedirectResponse(f"/dashboard?error={message}", status_code=status.HTTP_303_SEE_OTHER)

    if chat_id:
        try:
            verify_telegram_chat(chat_id, effective_bot_token)
        except RuntimeError as exc:
            bot_name = integration.telegram_bot_username or "your_bot"
            message = quote(
                f"Message @{bot_name} on Telegram first, then save again. ({exc})"
            )
            return RedirectResponse(f"/dashboard?error={message}", status_code=status.HTTP_303_SEE_OTHER)
    elif automation_enabled == "on":
        message = quote("Add your Telegram chat ID before enabling automation.")
        return RedirectResponse(f"/dashboard?error={message}", status_code=status.HTTP_303_SEE_OTHER)

    integration.telegram_chat_id = chat_id
    integration.gmail_query = gmail_query.strip()
    integration.automation_enabled = automation_enabled == "on"
    integration.last_error = None
    db.commit()

    if bot_token_changed and chat_id:
        try:
            send_telegram_message(
                effective_bot_token,
                chat_id,
                f"{settings.app_name} is now connected to @{integration.telegram_bot_username}.",
            )
        except RuntimeError as exc:
            message = quote(f"Bot token saved but test message failed: {exc}")
            return RedirectResponse(f"/dashboard?error={message}", status_code=status.HTTP_303_SEE_OTHER)

    return RedirectResponse("/dashboard?saved=1", status_code=status.HTTP_303_SEE_OTHER)
