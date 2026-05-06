import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_url_anonymous(client: AsyncClient):
    """Test creating a short URL without authentication."""
    response = await client.post(
        "/api/v1/urls",
        json={"url": "https://example.com/some/long/path"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "short_code" in data
    assert "short_url" in data
    assert data["original_url"] == "https://example.com/some/long/path"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_url_with_custom_alias(client: AsyncClient):
    """Test creating a short URL with a custom alias."""
    response = await client.post(
        "/api/v1/urls",
        json={
            "url": "https://example.com/custom",
            "custom_alias": "my-custom-link",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["short_code"] == "my-custom-link"


@pytest.mark.asyncio
async def test_create_url_duplicate_alias(client: AsyncClient):
    """Test that duplicate custom aliases are rejected."""
    # Create first URL
    await client.post(
        "/api/v1/urls",
        json={
            "url": "https://example.com/first",
            "custom_alias": "duplicate",
        },
    )
    
    # Try to create second URL with same alias
    response = await client.post(
        "/api/v1/urls",
        json={
            "url": "https://example.com/second",
            "custom_alias": "duplicate",
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_get_stats(client: AsyncClient):
    """Test getting URL statistics."""
    # Create URL first
    create_response = await client.post(
        "/api/v1/urls",
        json={"url": "https://example.com/stats-test"},
    )
    short_code = create_response.json()["short_code"]
    
    # Get stats
    response = await client.get(f"/api/v1/urls/{short_code}/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_clicks"] == 0
    assert data["recent_clicks"] == []


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
