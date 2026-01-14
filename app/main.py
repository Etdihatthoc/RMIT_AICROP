"""
AI Crop Doctor - FastAPI Main Application
Entry point for the backend API
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
from pathlib import Path

from app.config import settings
from app.database.connection import init_database

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown events
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # Initialize database
    logger.info("Initializing database...")
    init_database()

    # Create upload directories if they don't exist
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(f"{settings.upload_dir}/images").mkdir(parents=True, exist_ok=True)
    Path(f"{settings.upload_dir}/audio").mkdir(parents=True, exist_ok=True)
    logger.info("Upload directories created")

    # Load AI model on startup
    logger.info("Loading AI model (this may take a few minutes)...")
    from app.services.ai_service import ai_service
    ai_service.load_model()
    logger.info("✓ AI model loaded successfully on GPU!")

    logger.info(f"Server ready at http://{settings.host}:{settings.port}")
    logger.info(f"API docs available at http://{settings.host}:{settings.port}/docs")

    yield

    # Shutdown
    logger.info("Shutting down server...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered crop disease diagnosis and epidemic monitoring system",
    lifespan=lifespan
)

# CORS middleware - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (uploaded images/audio)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - API info"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "diagnosis": "/api/v1/diagnose",
            "epidemic_alerts": "/api/v1/epidemic/alerts",
            "expert_login": "/api/v1/auth/expert/login"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# Import and include routers
from app.routes import diagnosis, epidemic, expert

app.include_router(diagnosis.router, prefix="/api/v1", tags=["Diagnosis"])
app.include_router(epidemic.router, prefix="/api/v1", tags=["Epidemic"])
app.include_router(expert.router, prefix="/api/v1", tags=["Expert"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
