from fastapi import APIRouter

from terratrain.api.v1 import athletes, auth, coaching, documents, health, routes, workouts, weekly_plans

router = APIRouter()

router.include_router(health.router, tags=["health"])
router.include_router(athletes.router, prefix="/athletes", tags=["athletes"])
router.include_router(routes.router, tags=["routes"])
router.include_router(workouts.router, tags=["workouts"])
router.include_router(weekly_plans.router, tags=["weekly-plans"])
router.include_router(coaching.router, prefix="/coaching", tags=["coaching"])
router.include_router(documents.router, prefix="/documents", tags=["documents"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
