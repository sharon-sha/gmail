from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import get_app_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Integration, User
from app.services.gmail_oauth import create_gmail_auth_url, exchange_gmail_code
from app.services.gmail_service import get_gmail_profile

router = APIRouter(prefix="/auth/gmail", tags=["gmail"])
templates = Jinja2Templates(directory="app/templates")
settings = get_app_settings()


@router.get("/connect")
def connect_gmail(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        auth_url = create_gmail_auth_url(db, user.id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return RedirectResponse(auth_url)


@router.get("/callback")
def gmail_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if error:
        return templates.TemplateResponse(
            request,
            "oauth_result.html",
            {
                "app_name": settings.app_name,
                "success": False,
                "message": f"Google authorization failed: {error}",
            },
        )

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing OAuth code or state")

    try:
        token_json = exchange_gmail_code(db, code, state, user.id)
        gmail_email = get_gmail_profile(token_json)
    except Exception as exc:
        return templates.TemplateResponse(
            request,
            "oauth_result.html",
            {
                "app_name": settings.app_name,
                "success": False,
                "message": str(exc),
            },
        )

    integration = user.integration
    if not integration:
        integration = Integration(user_id=user.id)
        db.add(integration)

    integration.gmail_token_json = token_json
    integration.gmail_email = gmail_email
    integration.last_error = None
    db.commit()

    return templates.TemplateResponse(
        request,
        "oauth_result.html",
        {
            "app_name": settings.app_name,
            "success": True,
            "message": f"Gmail connected as {gmail_email}",
        },
    )
