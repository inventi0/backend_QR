from typing import Optional
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, IntegerIDMixin, exceptions, models, schemas
from dotenv import load_dotenv
import os

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User, get_user_db
from app.database import get_db
from app.s3.s3 import S3Client
from app.helpers.codegen import ensure_user_editor_and_qr

load_dotenv()

forgot_password_key = os.getenv("private_key")


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    """
    Кастомный UserManager:
      - create(): ваши правила создания пользователя (role_id=1 и т.д.)
      - on_after_register(): сразу создаёт Editor + QR для пользователя и, при необходимости,
        генерирует PNG с QR в S3 (ссылка ведёт на /editor/{public_id}).
    """
    reset_password_token_secret = forgot_password_key
    verification_token_secret = forgot_password_key

    async def create(
        self,
        user_create: schemas.UC,
        safe: bool = False,
        request: Optional[Request] = None,
    ) -> models.UP:
        await self.validate_password(user_create.password, user_create)

        existing_user = await self.user_db.get_by_email(user_create.email)
        if existing_user is not None:
            raise exceptions.UserAlreadyExists()

        user_dict = (
            user_create.create_update_dict() if safe else user_create.create_update_dict_superuser()
        )
        password = user_dict.pop("password")
        user_dict["hashed_password"] = self.password_helper.hash(password)
        user_dict["role_id"] = 1  # ваш дефолт

        created_user = await self.user_db.create(user_dict)
        await self.on_after_register(created_user, request)

        return created_user

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        """
        Инициализация «1 QR ↔ 1 Editor ↔ 1 User».
        - Гарантирует наличие Editor и QR.
        - Если у QR нет PNG, генерирует и загружает в S3.
        """
        session: Optional[AsyncSession] = getattr(self.user_db, "session", None)

        if session is None:
            async for db in get_db():
                session = db
                break

        if session is None:
            print(f"[WARN] on_after_register: DB session not available for user={user.id}")
            return

        s3 = S3Client(
            access_key=os.getenv("S3_ACCESS_KEY"),
            secret_key=os.getenv("S3_SECRET_KEY"),
            endpoint_url=os.getenv("S3_ENDPOINT_URL"),
            bucket_name=os.getenv("S3_BUCKET_NAME"),
        )

        await ensure_user_editor_and_qr(session, s3, user)

        print(f"User {user.id} has registered (Editor+QR initialized).")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"User {user.id} has forgot their password. Reset token: {token}")

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"Verification requested for user {user.id}. Verification token: {token}")


async def get_user_manager(user_db: Depends = Depends(get_user_db)):
    yield UserManager(user_db)
