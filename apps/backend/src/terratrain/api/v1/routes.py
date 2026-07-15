import uuid

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from terratrain.api.deps import get_session
from terratrain.db.models.athlete import Athlete
from terratrain.db.models.route import Route
from terratrain.schemas.route import RouteResponse
from terratrain.services.gpx_analyzer import GpxAnalyzer

logger = structlog.get_logger()
router = APIRouter()


@router.post("/routes/upload", response_model=RouteResponse, status_code=status.HTTP_201_CREATED)
async def upload_route(
    athlete_id: uuid.UUID = Form(...),
    name: str = Form(...),
    sport: str = Form(default="cycling"),
    surface_type: str | None = Form(default=None),
    gpx_file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> Route:
    athlete = await session.get(Athlete, athlete_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")

    gpx_content = await gpx_file.read()
    analysis = GpxAnalyzer.analyze(gpx_content.decode("utf-8"))

    route = Route(
        athlete_id=athlete_id,
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


@router.get("/routes/{route_id}", response_model=RouteResponse)
async def get_route(
    route_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> Route:
    route = await session.get(Route, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return route


@router.get("/athletes/{athlete_id}/routes", response_model=list[RouteResponse])
async def list_routes(
    athlete_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> list[Route]:
    result = await session.execute(select(Route).where(Route.athlete_id == athlete_id))
    return list(result.scalars().all())


@router.delete("/routes/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_route(
    route_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    route = await session.get(Route, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    await session.delete(route)
    await session.commit()
