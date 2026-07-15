"""Strava OAuth 2.0 client."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from terratrain.db.models.athlete import Athlete
from terratrain.db.models.strava import StravaToken
from terratrain.services.security import encrypt_value

logger = structlog.get_logger()

STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_API_BASE = "https://www.strava.com/api/v3"


class StravaClient:
    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret

    @staticmethod
    def build_auth_url(client_id: str, redirect_uri: str, state: str) -> str:
        params = (
            f"client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&scope=activity:read_all,profile:read_all"
            f"&state={state}"
        )
        return f"{STRAVA_AUTH_URL}?{params}"

    async def exchange_code(
        self, code: str, athlete_id: str, db_session: AsyncSession
    ) -> StravaToken:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                STRAVA_TOKEN_URL,
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        athlete_uuid = uuid.UUID(athlete_id)
        athlete = await db_session.get(Athlete, athlete_uuid)
        if not athlete:
            raise ValueError(f"Athlete {athlete_id} not found")

        strava_id = str(data["athlete"]["id"])
        athlete.strava_athlete_id = strava_id

        existing_token = await db_session.get(StravaToken, {"athlete_id": athlete_uuid})
        expires_at = datetime.fromtimestamp(data["expires_at"], tz=timezone.utc)

        if existing_token:
            existing_token.access_token_encrypted = encrypt_value(data["access_token"])
            existing_token.refresh_token_encrypted = encrypt_value(data["refresh_token"])
            existing_token.expires_at = expires_at
            existing_token.scope = data.get("scope", "")
            token = existing_token
        else:
            token = StravaToken(
                athlete_id=athlete_uuid,
                access_token_encrypted=encrypt_value(data["access_token"]),
                refresh_token_encrypted=encrypt_value(data["refresh_token"]),
                expires_at=expires_at,
                scope=data.get("scope", ""),
            )
            db_session.add(token)

        await db_session.commit()
        return token
