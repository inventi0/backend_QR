"""
Tests for Authentication

Тесты для регистрации, логина, logout.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ping(client: AsyncClient):
    """Тест healthcheck эндпоинта."""
    response = await client.get("/ping")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user):
    """Тест успешного логина."""
    response = await client.post(
        "/auth/jwt/login",
        data={
            "username": "test@example.com",
            "password": "testpass123",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user):
    """Тест логина с неправильным паролем."""
    response = await client.post(
        "/auth/jwt/login",
        data={
            "username": "test@example.com",
            "password": "wrongpassword",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, auth_headers):
    """Тест получения профиля авторизованного пользователя."""
    response = await client.get("/users/me", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"


@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient):
    """Тест получения профиля без авторизации."""
    response = await client.get("/users/me")
    
    assert response.status_code == 401
