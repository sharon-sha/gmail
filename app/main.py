import asyncio
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_app_settings
from app.database import init_db
from app.routers import gmail, pages
from app.services.worker import run_worker_cycle

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
settings = get_app_settings()
scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        init_db()
    except Exception:
        logger.exception("Database initialization failed")
        raise

    scheduler.add_job(
        run_worker_cycle,
        "interval",
        seconds=settings.poll_interval_seconds,
        id="email-worker",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("%s started on %s", settings.app_name, settings.app_url)
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(pages.router)
app.include_router(gmail.router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        accept = request.headers.get("accept", "")
        wants_html = "text/html" in accept or request.url.path.startswith("/dashboard")
        if wants_html:
            return RedirectResponse("/login?notice=Please+log+in+to+continue", status_code=303)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
