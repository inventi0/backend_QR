from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .auth_custom import profile_router, auth_custom_router
from .faq_router import faq_router
from .order_router import orders_router
from .product_router import products_router
from .qr_router import qr_router
from .dependecies import fastapi_users
from app.auth.auth import auth_backend
from app.helpers.helpers import to_start, to_shutdown, create_admin, create_product
from app.schemas.user_schemas import UserCreate, UserRead, UserOut, UserUpdate
from .review_router import review_router

from .templates_router import templates_router
from ..admin import admin_star
from ..logging_config import app_logger


@asynccontextmanager
async def lifespan_func(app: FastAPI):
    await to_start()
    await create_admin()
    await create_product()
    print("База готова")
    yield
    await to_shutdown()
    print("База очищена")

app = FastAPI(lifespan=lifespan_func)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    try:
        body = await request.body()
        try:
            body_text = body.decode("utf-8")
        except Exception:
            body_text = "<binary data>"
    except Exception:
        body_text = "<unreadable>"

    app_logger.info(f"REQUEST {request.method} {request.url} | body={body_text}")

    try:
        response = await call_next(request)
    except Exception as e:
        app_logger.exception(f"ERROR handling {request.method} {request.url}: {e}")
        raise

    try:
        if hasattr(response, "body") and response.body is not None:
            try:
                resp_text = response.body.decode("utf-8")
            except Exception:
                resp_text = "<binary data>"
        else:
            resp_text = "<streaming or empty>"

        app_logger.info(
            f"RESPONSE {request.method} {request.url} | "
            f"status={response.status_code} | body={resp_text}"
        )
    except Exception:
        app_logger.exception("error logging response")

    return response

@app.get("/ping")
async def ping():
    app_logger.info("Ping endpoint вызван")
    return {"status": "ok", "message": "Приложение поднялось!"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

app.include_router(auth_custom_router)
app.include_router(profile_router)

app.include_router(qr_router)
app.include_router(review_router)
app.include_router(faq_router)
app.include_router(templates_router)
app.include_router(products_router)
app.include_router(orders_router)

app.mount("/admin", admin_star)