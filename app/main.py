# app/main.py

import sys
from contextlib import asynccontextmanager
import logging # Use standard logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pymongo.errors import ConnectionFailure

# Import settings and database functions
from app.core.config import settings
from app.db.database import connect_to_mongo, close_mongo_connection, get_database, db_instance

# Import scheduler functions and the scheduler instance itself for health check
from app.services.scheduler_service import start_scheduler, stop_scheduler, scheduler as apscheduler_instance

# Import API endpoint routers
from app.api.endpoints import concepts, keywords

# Import LLM service instance (now configured for Gemini) for health check
from app.services.llm_service import llm_service

# --- Logging Configuration ---
logging.basicConfig(level=settings.LOG_LEVEL.upper(), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# --- FastAPI Lifespan Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence
    logger.info(f"Starting up {settings.PROJECT_NAME}...")
    logger.info(f"Log Level set to: {settings.LOG_LEVEL.upper()}")
    try:
        await connect_to_mongo() # Connects DB and creates indexes
        if db_instance.db is not None:
             start_scheduler(db_instance.db) # Starts scheduler, initializes ConceptService
             logger.info("Database connected and scheduler initiated.")
        else:
             logger.critical("Database connection object not available. Scheduler not started.")
             # Consider raising error if DB/Scheduler are absolutely essential

    except SystemExit as e:
         logger.critical(f"SystemExit during startup: {e}")
         raise
    except Exception as e:
         logger.critical(f"Critical error during application startup: {e}", exc_info=True)
         # raise SystemExit("Application startup failed.") from e

    yield # Application runs

    # Shutdown sequence
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")
    stop_scheduler()
    await close_mongo_connection()
    logger.info("Scheduler stopped and database connection closed.")

# --- Create FastAPI App Instance ---
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
    version="1.0.0",
    description="Keyword Manager microservice using concept-level metrics and Google Gemini."
)

# --- Middleware ---
if settings.BACKEND_CORS_ORIGINS:
    logger.info(f"Configuring CORS for origins: {settings.BACKEND_CORS_ORIGINS}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
    )
else:
    logger.warning("No CORS origins configured via BACKEND_CORS_ORIGINS environment variable.")

# --- Include API Routers ---
app.include_router(concepts.router, prefix=settings.API_V1_STR, tags=["Concepts & Feedback"])
app.include_router(keywords.router, prefix=settings.API_V1_STR, tags=["Keyword Fetching"])

# --- Root Endpoint ---
@app.get("/", tags=["Root"], include_in_schema=False)
async def read_root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}

# --- Custom Exception Handlers ---
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
     logger.warning(f"Value Error: {exc} for request {request.method} {request.url.path}", exc_info=True)
     return JSONResponse(
         status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
         content={"detail": f"Invalid value or data format: {exc}"}
     )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
     logger.error(f"Unhandled exception for request {request.method} {request.url.path}: {exc}", exc_info=True)
     return JSONResponse(
         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
         content={"detail": "An unexpected internal server error occurred."}
     )

# --- Health Check Endpoint ---
@app.get("/health", tags=["Health"], summary="Health Check")
async def health_check():
    """ Performs basic health checks for service components (DB, Scheduler, LLM). """
    db_status, db_ok = "unknown", False
    if db_instance.client and db_instance.db is not None:
        try: await db_instance.client.admin.command('ping'); db_status, db_ok = "connected", True
        except ConnectionFailure: db_status = "connection_failed"; logger.error("Health check: DB ping failed.")
        except Exception as e: db_status = "error"; logger.error(f"Health check: DB error: {e}")
    else: db_status = "not_initialized"; logger.error("Health check: DB not initialized.")

    scheduler_status, scheduler_running = "unknown", False
    try:
        scheduler_running = apscheduler_instance and apscheduler_instance.running
        scheduler_status = "running" if scheduler_running else "stopped"
    except Exception as e: logger.error(f"Health check: Error checking scheduler: {e}"); scheduler_status = "error"

    # --- CORRECTED LLM CHECK for Gemini ---
    llm_ok = bool(llm_service and hasattr(llm_service, 'model') and llm_service.model is not None)
    llm_status = "available" if llm_ok else "unavailable"
    # --- END CORRECTION ---

    service_status = "ok" if db_ok and scheduler_running else "error"
    response_status = status.HTTP_200_OK if service_status == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
         status_code=response_status,
         content={ "status": service_status, "database": db_status, "scheduler": scheduler_status, "llm_service": llm_status }
    )