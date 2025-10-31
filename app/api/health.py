from datetime import datetime
from typing import Dict

import redis
from fastapi import APIRouter
from sqlalchemy import text

from app.api.schemas import HealthResponse
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint to verify service status"""
    services = {}
    
    # Check database connectivity
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        services["database"] = "healthy"
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        services["database"] = "unhealthy"
    
    # Check Redis connectivity
    try:
        r = redis.from_url(settings.redis_url)
        r.ping()
        services["redis"] = "healthy"
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        services["redis"] = "unhealthy"
    
    # Check Celery (through Redis)
    try:
        # Simple check - in production you might want to check worker status
        r = redis.from_url(settings.celery_broker_url)
        r.ping()
        services["celery"] = "healthy"
    except Exception as e:
        logger.error("Celery health check failed", error=str(e))
        services["celery"] = "unhealthy"
    
    # Overall status
    overall_status = "healthy" if all(
        status == "healthy" for status in services.values()
    ) else "degraded"
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        services=services,
    )


@router.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe endpoint"""
    health = await health_check()
    
    if health.status == "healthy":
        return {"status": "ready"}
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Service not ready")


@router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe endpoint"""
    return {"status": "alive"}