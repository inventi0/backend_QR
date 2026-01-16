"""
Pytest Configuration & Fixtures

Основные фикстуры для тестирования backend.
"""
import asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.routes.user import app

# Test database URL (используйте отдельную БД для тестов!)
TEST_DATABASE_URL = "postgresql+asyncpg://admin:admin@localhost:5432/qr_test"


@pytest.fixture(scope="session")
def event_loop():
    """Создаём event loop для всех async тестов."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Создаём тестовый engine для БД."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    # Создаём все таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Удаляем все таблицы после тестов
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    """Создаём сессию БД для каждого теста."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session):
    """Создаём HTTP клиент для тестирования API."""
    # Переопределяем зависимость get_db на тестовую сессию
    from app.database import get_db
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session):
    """Создаём тестового пользователя."""
    from app.models.models import User
    from passlib.context import CryptContext
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=pwd_context.hash("testpass123"),
        role_id=1,
        is_active=True,
        is_superuser=False,
        is_verified=True,
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    return user


@pytest.fixture
async def auth_headers(client, test_user):
    """Получаем JWT токен для авторизованных запросов."""
    response = await client.post(
        "/auth/jwt/login",
        data={
            "username": "test@example.com",
            "password": "testpass123",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    
    assert response.status_code == 200
    token = response.json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}
