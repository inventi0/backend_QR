"""
Tests for Products API

Тесты для CRUD операций с продуктами.
"""
import pytest
from httpx import AsyncClient


@pytest.fixture
async def test_product(db_session):
    """Создаём тестовый продукт."""
    from app.models.models import Product
    
    product = Product(
        type="Футболка",
        size="M",
        color="Белый",
        description="Тестовая футболка",
        price=1000,
    )
    
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    
    return product


@pytest.mark.asyncio
async def test_list_products(client: AsyncClient, auth_headers, test_product):
    """Тест получения списка продуктов."""
    response = await client.get("/products/", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["type"] == "Футболка"


@pytest.mark.asyncio
async def test_get_product(client: AsyncClient, auth_headers, test_product):
    """Тест получения конкретного продукта."""
    response = await client.get(f"/products/{test_product.id}", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_product.id
    assert data["type"] == "Футболка"
    assert data["price"] == 1000


@pytest.mark.asyncio
async def test_get_product_not_found(client: AsyncClient, auth_headers):
    """Тест получения несуществующего продукта."""
    response = await client.get("/products/99999", headers=auth_headers)
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_filter_products(client: AsyncClient, auth_headers, test_product):
    """Тест фильтрации продуктов."""
    response = await client.get(
        "/products/",
        params={"type": "Футболка", "color": "Белый"},
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert all(p["type"] == "Футболка" and p["color"] == "Белый" for p in data)
