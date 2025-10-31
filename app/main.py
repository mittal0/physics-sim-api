import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.api.jobs import router as jobs_router
from app.core.config import settings
from app.core.database import create_tables
from app.core.logging import setup_logging, get_logger

# Setup logging first
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Physics Simulation API")
    
    # Create database tables
    create_tables()
    logger.info("Database tables created/verified")
    
    # Ensure artifacts directory exists
    os.makedirs(settings.artifacts_path, exist_ok=True)
    logger.info("Artifacts directory ready", path=settings.artifacts_path)
    
    yield
    
    # Shutdown
    logger.info("Shutting down Physics Simulation API")


app = FastAPI(
    title="Physics Simulation API",
    description="API for managing containerized physics simulations with job orchestration",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests"""
    start_time = request.state.start_time = request.headers.get("x-request-start")
    
    response = await call_next(request)
    
    logger.info(
        "HTTP request",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        user_agent=request.headers.get("user-agent"),
    )
    
    return response


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(
        "Unhandled exception",
        method=request.method,
        url=str(request.url),
        error=str(exc),
        exc_info=True,
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred",
            "timestamp": "2024-01-01T00:00:00Z",  # In production, use actual timestamp
        },
    )


# Include routers
app.include_router(health_router, tags=["Health"])
app.include_router(jobs_router, prefix="/api/v1", tags=["Jobs"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Physics Simulation API",
        "version": "0.1.0",
        "docs_url": "/docs",
        "health_url": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        workers=1 if settings.debug else settings.api_workers,
        log_config=None,  # Use our custom logging setup
    )