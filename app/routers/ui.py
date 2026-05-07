from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.services.url_service import URLService
from app.schemas.url import URLCreate
from app.config import get_settings

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the home page."""
    return templates.TemplateResponse(request, "home.html")


@router.post("/shorten", response_class=HTMLResponse)
async def shorten_url(
    request: Request,
    url: str = Form(...),
    custom_alias: str = Form(None),
):
    """Handle URL shortening form submission."""
    from app.database import async_session_maker

    async with async_session_maker() as db:
        url_service = URLService(db)

        # Clean up custom alias
        if custom_alias:
            custom_alias = custom_alias.strip()
            if not custom_alias:
                custom_alias = None

        try:
            # Create URL using the URLCreate schema
            url_data = URLCreate(url=url, custom_alias=custom_alias)

            # Check if custom alias already exists
            if custom_alias and await url_service.short_code_exists(custom_alias):
                return templates.TemplateResponse(
                    request,
                    "partials/result.html",
                    {"error": f"Alias '{custom_alias}' is already taken"},
                )

            shortened = await url_service.create(url_data=url_data, user_id=None)

            short_url = f"{settings.base_url}/{shortened.short_code}"
            qr_url = f"/api/v1/urls/{shortened.short_code}/qr"

            return templates.TemplateResponse(
                request,
                "partials/result.html",
                {
                    "short_url": short_url,
                    "original_url": shortened.original_url,
                    "qr_url": qr_url,
                    "short_code": shortened.short_code,
                },
            )
        except ValidationError as e:
            return templates.TemplateResponse(
                request,
                "partials/result.html",
                {"error": "Invalid URL format"},
            )
        except ValueError as e:
            return templates.TemplateResponse(
                request,
                "partials/result.html",
                {"error": str(e)},
            )
