from contextlib import asynccontextmanager
from fastapi import FastAPI, Path, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .dependecies import current_user, fastapi_users
from app.auth.auth import auth_backend
from app.helpers.helpers import to_start, to_shutdown, create_admin
from app.schemas.user_schemas import UserCreate, UserRead, UserOut


@asynccontextmanager
async def lifespan_func(app: FastAPI):
    await to_start()
    await create_admin()
    print("База готова")
    yield
    await to_shutdown()
    print("База очищена")


app = FastAPI(lifespan=lifespan_func)

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
