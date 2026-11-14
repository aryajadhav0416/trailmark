"""Core web and API routes."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.schemas import HealthResponse

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """Render the placeholder homepage."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": settings.APP_NAME,
        },
    )


@router.get("/healthz", response_model=HealthResponse)
async def healthz() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
