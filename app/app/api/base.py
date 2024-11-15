from app.api.types import HealthCheck

from fastapi import APIRouter, HTTPException, Depends

router = APIRouter()


@router.get("/api/health", response_model=HealthCheck)
async def health(
) -> HealthCheck:
    return HealthCheck(message="hello world")
