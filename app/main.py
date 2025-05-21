# app/main.py

import sys # Keep this if you ever consider sys.exit()
import logging # Use standard logging
from contextlib import asynccontextmanager

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
# Ensure this is called only once, ideally here or very early.
# If app.core.config also calls it, remove it from there.
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
             # This case itself indicates a failure in connect_to_mongo if it returned without db.instance.db being set
             # or if connect_to_mongo itself didn't raise an error but failed to set up the DB.
             # This path implies connect_to_mongo might not be raising on all its internal failures as SystemExit.
             logger.critical("Database connection object not available after connect_to_mongo. Scheduler not started.")
             raise RuntimeError("Database connection failed to initialize properly.") # Critical failure

    except SystemExit as e: # Handles explicit SystemExit from connect_to_mongo or start_scheduler
         logger.critical(f"SystemExit during startup: {e}")
         raise # Re-raise SystemExit to allow FastAPI/Uvicorn to handle clean shutdown
    except Exception as e: # Catches ALL OTHER unexpected exceptions during startup
         logger.critical(f"Critical unexpected error during application startup: {e}", exc_info=True)
         # Re-raise as a RuntimeError to ensure the application does not proceed to 'yield'
         # and clearly indicates a startup failure.
         raise RuntimeError(f"Application startup failed due to an unexpected error: {e}") from e

    yield # Application runs ONLY if startup was successful

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
    # Check if db_instance and its attributes are initialized before using them
    if db_instance and db_instance.client and db_instance.db is not None:
        try:
            await db_instance.client.admin.command('ping')
            db_status, db_ok = "connected", True
        except ConnectionFailure:
            db_status = "connection_failed"
            logger.error("Health check: DB ping failed.")
        except Exception as e:
            db_status = "error"
            logger.error(f"Health check: DB error: {e}")
    elif db_instance and db_instance.client is None: # Explicitly check if client is None after connect_to_mongo attempt
        db_status = "not_connected_after_attempt"
        logger.error("Health check: DB client is None after connection attempt.")
    else: # db_instance might be None or db_instance.db is None
        db_status = "not_initialized"
        logger.error("Health check: DB not initialized or client not available.")


    scheduler_status, scheduler_running = "unknown", False
    try:
        # Check if apscheduler_instance is not None before accessing .running
        if apscheduler_instance:
            scheduler_running = apscheduler_instance.running
            scheduler_status = "running" if scheduler_running else "stopped"
        else:
            scheduler_status = "not_initialized" # If apscheduler_instance itself is None
            logger.warning("Health check: APScheduler instance is None.")
    except Exception as e:
        logger.error(f"Health check: Error checking scheduler: {e}")
        scheduler_status = "error"

    llm_ok = bool(llm_service and hasattr(llm_service, 'model') and llm_service.model is not None)
    llm_status = "available" if llm_ok else "unavailable"
    if not llm_ok and llm_service is None: # If the service instance itself failed to init
        llm_status = "service_init_failed"
        logger.error("Health check: LLM service instance is None (failed to initialize).")
    elif not llm_ok: # Service instance exists, but model is missing
        logger.warning("Health check: LLM service model is unavailable.")


    # Service is "ok" only if DB is connected AND scheduler is running. LLM is good to have but not always a startup blocker.
    # Adjust this condition based on what you consider truly "critical" for the service to be "ok".
    # For instance, if LLM is critical for some core startup functions, include llm_ok.
    service_is_critically_healthy = db_ok and scheduler_running # Add llm_ok here if LLM is critical for startup tasks
    service_status = "ok" if service_is_critically_healthy else "error"
    response_status = status.HTTP_200_OK if service_status == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
         status_code=response_status,
         content={
             "status": service_status,
             "database": db_status,
             "scheduler": scheduler_status,
             "llm_service": llm_status
         }
    )