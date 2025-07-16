"""
Main FastAPI application for Teddy AI Service
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from prometheus_client import make_asgi_app

from api.core.config import settings
from api.core.dependencies import Base, engine
from api.endpoints import auth, chat, search, insights, recommendations, test
from api.models.schemas import HealthResponse, ErrorResponse

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s' if settings.LOG_FORMAT == 'text' else None
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    logger.info("Starting Teddy AI Service...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")
    
    # Initialize services
    # TODO: Initialize ML models, vector store, etc.
    
    yield
    
    # Shutdown
    logger.info("Shutting down Teddy AI Service...")
    # TODO: Cleanup resources


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="AI-powered land intelligence platform for BirdDog",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Configure CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Mount Prometheus metrics
if settings.ENABLE_METRICS:
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)


# Exception handlers
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error=str(exc),
            error_code="VALUE_ERROR"
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="An internal error occurred",
            error_code="INTERNAL_ERROR"
        ).model_dump()
    )


# Root endpoint
@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint - health check"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        services={
            "database": "connected",
            "redis": "connected",
            "openai": "connected",
            "snowflake": "connected"
        }
    )


# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Detailed health check"""
    # TODO: Add actual health checks for each service
    services_status = {
        "database": "healthy",
        "redis": "healthy",
        "openai": "healthy",
        "snowflake": "healthy",
        "vector_db": "healthy"
    }
    
    return HealthResponse(
        status="healthy" if all(s == "healthy" for s in services_status.values()) else "degraded",
        version="1.0.0",
        services=services_status
    )


# Include API routers
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["authentication"]
)

app.include_router(
    chat.router,
    prefix=f"{settings.API_V1_STR}/chat",
    tags=["chat"]
)

app.include_router(
    search.router,
    prefix=f"{settings.API_V1_STR}/search",
    tags=["search"]
)

app.include_router(
    insights.router,
    prefix=f"{settings.API_V1_STR}/insights",
    tags=["insights"]
)

app.include_router(
    recommendations.router,
    prefix=f"{settings.API_V1_STR}/recommendations",
    tags=["recommendations"]
)

app.include_router(
    test.router,
    prefix=f"{settings.API_V1_STR}/test",
    tags=["test"]
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
