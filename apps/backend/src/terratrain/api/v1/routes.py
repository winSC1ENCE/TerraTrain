import uuid

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from terratrain.api.deps import get_current_athlete, get_session
from terratrain.db.models.athlete import Athlete
from terratrain.db.models.route import Route
from terratrain.schemas.route import RouteResponse, RouteUpdateRequest
from terratrain.services.gpx_analyzer import GpxAnalyzer

logger = structlog.get_logger()
router = APIRouter()


@router.post("/routes/upload", response_model=RouteResponse, status_code=status.HTTP_201_CREATED)
async def upload_route(
    name: str = Form(...),
    sport: str = Form(default="cycling"),
    surface_type: str | None = Form(default=None),
    gpx_file: UploadFile = File(...),
    athlete: Athlete = Depends(get_current_athlete),
    session: AsyncSession = Depends(get_session),
) -> Route:
    gpx_content = await gpx_file.read()
    analysis = GpxAnalyzer.analyze(gpx_content.decode("utf-8"))

    route = Route(
        athlete_id=athlete.id,
        name=name,
        sport=sport,
        gpx_data=gpx_content.decode("utf-8"),
        surface_type=surface_type,
        **analysis,
    )
    session.add(route)
    await session.commit()
    await session.refresh(route)
    return route


def _ensure_track_points(route: Route) -> Route:
    if not isinstance(route.analysis, dict):
        route.analysis = {}
    if "track_points" not in route.analysis and route.gpx_data:
        try:
            an = GpxAnalyzer.analyze(route.gpx_data)
            route.analysis["track_points"] = an.get("analysis", {}).get("track_points", [])
        except Exception:
            route.analysis["track_points"] = []
    return route


async def _get_owned_route(route_id: uuid.UUID, athlete: Athlete, session: AsyncSession) -> Route:
    route = await session.get(Route, route_id)
    if not route or route.athlete_id != athlete.id:
        # 404 (not 403) so a foreign id doesn't confirm the resource exists.
        raise HTTPException(status_code=404, detail="Route not found")
    return route


@router.get("/routes/{route_id}", response_model=RouteResponse)
async def get_route(
    route_id: uuid.UUID,
    athlete: Athlete = Depends(get_current_athlete),
    session: AsyncSession = Depends(get_session),
) -> Route:
    route = await _get_owned_route(route_id, athlete, session)
    return _ensure_track_points(route)


@router.get("/routes", response_model=list[RouteResponse])
async def list_routes(
    athlete: Athlete = Depends(get_current_athlete),
    session: AsyncSession = Depends(get_session),
) -> list[Route]:
    result = await session.execute(select(Route).where(Route.athlete_id == athlete.id))
    routes = list(result.scalars().all())
    return [_ensure_track_points(r) for r in routes]


@router.delete("/routes/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_route(
    route_id: uuid.UUID,
    athlete: Athlete = Depends(get_current_athlete),
    session: AsyncSession = Depends(get_session),
) -> None:
    route = await _get_owned_route(route_id, athlete, session)
    await session.delete(route)
    await session.commit()


@router.put("/routes/{route_id}", response_model=RouteResponse)
async def update_route(
    route_id: uuid.UUID,
    body: RouteUpdateRequest,
    athlete: Athlete = Depends(get_current_athlete),
    session: AsyncSession = Depends(get_session),
) -> Route:
    route = await _get_owned_route(route_id, athlete, session)
    route.name = body.name
    await session.commit()
    await session.refresh(route)
    return route
