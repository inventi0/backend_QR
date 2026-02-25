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
        base_url: Optional[str] = None,
        is_temporary_data: bool = False,
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
        user_dict["is_temporary_data"] = is_temporary_data

        created_user = await self.user_db.create(user_dict)
        await self.on_after_register(created_user, request, base_url)

        return created_user

    async def on_after_register(self, user: User, request: Optional[Request] = None, base_url: Optional[str] = None):
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

        await ensure_user_editor_and_qr(session, s3, user, base_url=base_url)

        print(f"User {user.id} has registered (Editor+QR initialized).")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"User {user.id} has forgot their password. Reset token: {token}")

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"Verification requested for user {user.id}. Verification token: {token}")

    async def on_after_update(
        self,
        user: User,
        update_dict: dict,
        request: Optional[Request] = None,
    ):
        """
        Если пользователь обновил данные, и у него стоял флаг is_temporary_data=True,
        снимаем этот флаг.
        """
        if user.is_temporary_data:
            # Важно: user уже обновлен в БД (fastapi-users делает commit до вызова этого метода)
            # Но если мы хотим изменить еще поле, нам нужно сделать это явно.
            # fastapi-users передает user, который уже является ORM объектом.
            
            # Мы можем попробовать обновить его через user_db.update, 
            # но чтобы избежать рекурсии (update -> on_after_update),
            # лучше сделать прямой SQL update или изменить поле и сохранить,
            # если мы уверены, что это не вызовет бесконечный цикл.
            
            # В BaseUserManager.update происходит:
            # 1. user_db.update(user, update_dict)
            # 2. on_after_update(...)
            
            # Простой способ: если в update_dict есть username или password, снимаем флаг
            # Но update_dict содержит только новые данные.
            
            # Давайте просто обновим поле напрямую в БД.
            # Для этого нужен session.
            
            print(f"User {user.id} updated profile. Resetting is_temporary_data.")
            
            # Update the user directly via user_db.
            # safe=True is not needed here as we are bypassing the manager's safe check logic
            # and interacting with the DB adapter directly.
            await self.user_db.update(user, {"is_temporary_data": False})


async def get_user_manager(user_db: Depends = Depends(get_user_db)):
    yield UserManager(user_db)
