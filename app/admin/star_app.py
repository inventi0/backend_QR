from pathlib import Path
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import RedirectResponse
from starlette.requests import Request
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "show_tabs": False})

async def orders_page(request: Request):
    return templates.TemplateResponse("orders.html", {"request": request, "show_tabs": True})

async def logs_page(request: Request):
    return templates.TemplateResponse("logs.html", {"request": request, "show_tabs": True})

async def users_page(request: Request):
    return templates.TemplateResponse("users.html", {"request": request, "show_tabs": True})

async def products_page(request: Request):
    return templates.TemplateResponse("products.html", {"request": request, "show_tabs": True})

async def profile_page(request: Request):
    return templates.TemplateResponse("profile.html", {"request": request, "show_tabs": True})

async def root_redirect(_: Request):
    return RedirectResponse(url="/admin/orders")

def create_admin_starlette() -> Starlette:
    return Starlette(
        debug=False,
        routes=[
            Route("/", endpoint=root_redirect),
            Route("/login", endpoint=login_page),
            Route("/orders", endpoint=orders_page),
            Route("/logs", endpoint=logs_page),
            Route("/users", endpoint=users_page),
            Route("/products", endpoint=products_page),
            Route("/profile", endpoint=profile_page),
            # ВАЖНО: имя 'static' нужно для url_for('static', path='...')
            Mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static"),
        ],
    )
