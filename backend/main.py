"""
LifeMemory AI - Main FastAPI Application
Production-grade backend for personal journaling and memory system.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config.settings import get_settings
from middleware.logging import RequestIDMiddleware, setup_logging

from api.journal import router as journal_router
from api.ask import router as ask_router
from api.insights import router as insights_router
from api.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown tasks."""
    import logging
    logger = logging.getLogger(__name__)
    
    settings = get_settings()
    
    # Setup logging
    setup_logging(settings.LOG_LEVEL)
    
    # Production safety validation
    try:
        from utils.safety import validate_production_safety
        validate_production_safety()
    except Exception as e:
        logger.error(f"Production safety validation failed: {e}")
        if settings.ENV.lower() == "production":
            raise  # Fail fast in production
    
    # Startup: Initialize database connections, verify pgvector extension
    from database.connection import verify_database_setup
    try:
        await verify_database_setup()
        logger.info("Database connection verified successfully")
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        logger.warning("Server will start but database operations may fail. Check DATABASE_URL in .env")
        # Don't raise in development - allow server to start for testing
        if settings.ENV.lower() == "production":
            raise
    
    # Validate LLM availability (initializes router and validates models)
    try:
        from llm.router import get_router
        # Initialize LLM router (validates models at startup)
        router = get_router()
        logger.info(f"LLM router initialized: OpenAI (primary), Gemini and Groq (optional fallbacks)")
    except Exception as e:
        logger.error(f"LLM initialization failed: {e}")
        if settings.ENV.lower() == "production":
            raise RuntimeError(f"LLM initialization failed in production: {e}") from e
        else:
            logger.warning("Server will start but LLM operations may fail")
    
    # Validate embedding provider
    try:
        from embeddings.embedder import get_embedder
        embedder = get_embedder()
        logger.info(f"Embedding provider initialized: {embedder.get_provider()}")
    except Exception as e:
        logger.error(f"Embedding initialization failed: {e}")
        raise
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown: Cleanup if needed
    from database.connection import close_db_pool
    await close_db_pool()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="LifeMemory AI API",
    description="Privacy-first personal journaling and memory system",
    version="1.0.0",
    lifespan=lifespan
)

# Get settings
settings = get_settings()

# Request ID middleware (must be first)
app.add_middleware(RequestIDMiddleware)

# CORS middleware - Allow Next.js frontend (Vercel + local development)
# Explicitly include production frontend URL for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://life-memory-ai.vercel.app",  # Production frontend (Vercel)
        "http://localhost:3000",  # Local development
        "http://localhost:3001",  # Local development (alternative port)
        "http://127.0.0.1:3000",  # Local development (IP)
        *settings.allowed_origins_list  # Additional origins from env (comma-separated)
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
app.include_router(health_router, tags=["Health"])
app.include_router(journal_router, prefix="/journal", tags=["Journals"])
app.include_router(ask_router, prefix="/ask", tags=["Memory Query"])
app.include_router(insights_router, prefix="/insights", tags=["Insights"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.is_development
    )

