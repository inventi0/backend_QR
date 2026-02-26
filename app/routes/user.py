from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .auth_custom import profile_router, auth_custom_router
from .faq_router import faq_router
from .logs_router import logs_router
from .order_router import orders_router
from .product_router import products_router
from .qr_router import qr_router
from .moderation_router import moderation_router
from .dependecies import fastapi_users
from app.auth.auth import auth_backend
from app.helpers.helpers import to_start, to_shutdown, create_admin, create_product, create_mock_reviews
from app.schemas.user_schemas import UserCreate, UserRead, UserOut, UserUpdate
from .review_router import review_router
# from .payment_router import payment_router
from .templates_router import templates_router
from ..admin import admin_star
from ..logging_config import app_logger
from ..rate_limit import limiter


@asynccontextmanager
async def lifespan_func(app: FastAPI):
    await to_start()
    await create_admin()
    await create_product()
    # await create_mock_reviews()
    print("База готова")
    yield
    # await to_shutdown()
    # print("База очищена")

app = FastAPI(lifespan=lifespan_func)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

def _filter_sensitive_data(data: str) -> str:
    """Фильтрует чувствительные данные из логов (пароли, токены)."""
    import re
    import json
    
    try:
        parsed = json.loads(data)
        if isinstance(parsed, dict):
            # Фильтруем sensitive поля
            sensitive_fields = {"password", "token", "access_token", "refresh_token", 
                              "secret", "api_key", "private_key", "hashed_password"}
            for field in sensitive_fields:
                if field in parsed:
                    parsed[field] = "***FILTERED***"
        data = json.dumps(parsed)
    except (json.JSONDecodeError, TypeError):
        # Если не JSON, используем regex
        data = re.sub(r'("password"|"token"|"secret")["\s]*:["\s]*"[^"]*"', 
                     r'\1: "***FILTERED***"', data, flags=re.IGNORECASE)
        data = re.sub(r'password=[^&\s]+', 'password=***FILTERED***', data, flags=re.IGNORECASE)
    
    return data

@app.middleware("http")
async def log_requests(request: Request, call_next):
    try:
        body = await request.body()
        try:
            body_text = body.decode("utf-8")
            body_text = _filter_sensitive_data(body_text)  # ✅ Фильтрация
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
                resp_text = _filter_sensitive_data(resp_text)  # ✅ Фильтрация
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

app.include_router(auth_custom_router)
app.include_router(profile_router)

app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

app.include_router(qr_router)
app.include_router(review_router)
app.include_router(faq_router)
app.include_router(templates_router)
app.include_router(products_router)
app.include_router(orders_router)
app.include_router(logs_router)
# app.include_router(payment_router)
app.include_router(moderation_router)

app.mount("/admin", admin_star)