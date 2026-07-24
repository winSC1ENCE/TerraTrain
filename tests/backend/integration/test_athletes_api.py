"""Integration tests for the multi-user athlete flow.

Accounts are admin-invite only (no self-registration), so tests seed
users directly via the DB session fixture and drive the authenticated
``/api/v1/athletes/me`` endpoints through a real login.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from terratrain.db.engine import get_db_session
from terratrain.db.models.user import User
from terratrain.main import app
from terratrain.services.auth_service import hash_password


@pytest_asyncio.fixture
async def client(engine):
    """An AsyncClient whose DB dependency is overridden to the testcontainer engine."""
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def _override_get_db_session():
        async with factory() as db_session:
            yield db_session

    app.dependency_overrides[get_db_session] = _override_get_db_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db_session, None)


async def _seed_user(session: AsyncSession, email: str, password: str) -> User:
    user = User(email=email, hashed_password=hash_password(password), role="user", is_active=True)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _login(client: AsyncClient, email: str, password: str) -> str:
    """Log in and return the CSRF token for subsequent mutating requests."""
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return client.cookies.get("terratrain_csrf")


@pytest.mark.asyncio
async def test_create_and_get_athlete(client, session):
    await _seed_user(session, "rider@example.com", "TestPass123!")
    csrf = await _login(client, "rider@example.com", "TestPass123!")

    payload = {
        "intervals_user_id": "test_user_001",
        "name": "Test Rider",
        "sport": "cycling",
        "ftp_watts": 300,
        "weight_kg": 72.0,
    }
    response = await client.post(
        "/api/v1/athletes/me", json=payload, headers={"X-CSRF-Token": csrf}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Rider"
    assert data["ftp_watts"] == 300

    get_resp = await client.get("/api/v1/athletes/me")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == data["id"]


@pytest.mark.asyncio
async def test_get_athlete_without_profile_returns_404(client, session):
    await _seed_user(session, "noprofile@example.com", "TestPass123!")
    await _login(client, "noprofile@example.com", "TestPass123!")

    resp = await client.get("/api/v1/athletes/me")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_request_returns_401(client):
    resp = await client.get("/api/v1/athletes/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_athlete_data_is_isolated_between_users(client, session):
    """User B must not be able to see, list, or delete User A's route."""
    await _seed_user(session, "a@example.com", "PassA123!")
    await _seed_user(session, "b@example.com", "PassB123!")

    csrf_a = await _login(client, "a@example.com", "PassA123!")
    await client.post(
        "/api/v1/athletes/me",
        json={"intervals_user_id": "athlete_a", "name": "Athlete A", "sport": "cycling"},
        headers={"X-CSRF-Token": csrf_a},
    )
    upload_resp = await client.post(
        "/api/v1/routes/upload",
        files={"gpx_file": ("r.gpx", b"<gpx></gpx>", "application/gpx+xml")},
        data={"name": "Route A", "sport": "cycling"},
        headers={"X-CSRF-Token": csrf_a},
    )
    assert upload_resp.status_code == 201
    route_a_id = upload_resp.json()["id"]

    csrf_b = await _login(client, "b@example.com", "PassB123!")
    await client.post(
        "/api/v1/athletes/me",
        json={"intervals_user_id": "athlete_b", "name": "Athlete B", "sport": "running"},
        headers={"X-CSRF-Token": csrf_b},
    )

    read_resp = await client.get(f"/api/v1/routes/{route_a_id}")
    assert read_resp.status_code == 404

    list_resp = await client.get("/api/v1/routes")
    assert list_resp.status_code == 200
    assert list_resp.json() == []

    delete_resp = await client.delete(
        f"/api/v1/routes/{route_a_id}", headers={"X-CSRF-Token": csrf_b}
    )
    assert delete_resp.status_code == 404


@pytest.mark.asyncio
async def test_list_all_athletes_requires_admin(client, session):
    await _seed_user(session, "plainuser@example.com", "TestPass123!")
    await _login(client, "plainuser@example.com", "TestPass123!")

    resp = await client.get("/api/v1/athletes")
    assert resp.status_code == 403
