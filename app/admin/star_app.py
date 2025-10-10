from pathlib import Path
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

async def index_redirect(request: Request):
    return RedirectResponse(url="/admin/dashboard")

def create_admin_starlette() -> Starlette:
    app = Starlette(debug=False, routes=[
        Route("/", endpoint=index_redirect),
        Route("/login", endpoint=login_page),
        Route("/dashboard", endpoint=dashboard_page),
        Mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static"),
        Route("/orders", endpoint=orders_page),
    ])
    return app

async def orders_page(request: Request):
    return templates.TemplateResponse("orders_list.html", {"request": request})
