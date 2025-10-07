from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .faq_router import faq_router
from .product_router import products_router
from .qr_router import qr_router
from .dependecies import fastapi_users
from app.auth.auth import auth_backend
from app.helpers.helpers import to_start, to_shutdown, create_admin, create_product
from app.schemas.user_schemas import UserCreate, UserRead, UserOut
from .review_router import review_router


from app.admin import admin
from .templates_router import templates_router


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

admin.mount_to(app)
@app.get("/ping")
async def ping():
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
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_users_router(UserOut, UserCreate),
    tags=["me"],
)

app.include_router(qr_router)
app.include_router(review_router)
app.include_router(faq_router)
app.include_router(templates_router)
app.include_router(products_router)