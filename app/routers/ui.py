from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.url_service import URLService
from app.config import get_settings

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the home page."""
    return templates.TemplateResponse("home.html", {"request": request})


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
            shortened = await url_service.create_short_url(
                original_url=url,
                custom_alias=custom_alias,
                user_id=None,
            )
            
            short_url = f"{settings.base_url}/{shortened.short_code}"
            
            return templates.TemplateResponse(
                "partials/result.html",
                {
                    "request": request,
                    "short_url": short_url,
                    "original_url": shortened.original_url,
                },
            )
        except ValueError as e:
            return templates.TemplateResponse(
                "partials/result.html",
                {
                    "request": request,
                    "error": str(e),
                },
            )
