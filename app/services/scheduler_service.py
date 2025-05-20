# app/services/scheduler_service.py
# (Content remains the same as the last corrected version provided previously)

import logging
import asyncio
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.services.concept_service import ConceptService

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")
_concept_service_instance: Optional[ConceptService] = None

async def scheduled_tasks_job():
    """ The core background job function executed by the scheduler. """
    if not _concept_service_instance:
         logger.error("ConceptService instance not available. Skipping scheduled tasks.")
         return
    logger.info("Scheduler starting periodic tasks: Concept Generation & Confidence Decay")
    start_time = asyncio.get_event_loop().time()
    try:
        logger.info("Running scheduled concept generation...")
        processed_count = await _concept_service_instance.generate_and_store_concepts()
        generation_duration = asyncio.get_event_loop().time() - start_time
        logger.info(f"Scheduled concept generation finished. Processed {processed_count} terms. Duration: {generation_duration:.2f}s")
    except Exception as e: logger.error(f"Error during scheduled concept generation: {e}", exc_info=True)
    await asyncio.sleep(5)
    decay_start_time = asyncio.get_event_loop().time()
    try:
        logger.info("Running scheduled confidence decay check...")
        decayed_count = await _concept_service_instance.apply_confidence_decay()
        decay_duration = asyncio.get_event_loop().time() - decay_start_time
        logger.info(f"Scheduled confidence decay check finished. Decayed {decayed_count} terms. Duration: {decay_duration:.2f}s")
    except Exception as e: logger.error(f"Error during scheduled confidence decay: {e}", exc_info=True)
    total_duration = asyncio.get_event_loop().time() - start_time
    logger.info(f"Scheduled tasks cycle complete. Total duration: {total_duration:.2f}s")

def start_scheduler(db: AsyncIOMotorDatabase):
    """ Initializes the ConceptService instance, adds the job, and starts the scheduler. """
    global _concept_service_instance
    if not scheduler.running:
        logger.info("Initializing scheduler...")
        try:
             _concept_service_instance = ConceptService(db)
             logger.info("ConceptService instance created for scheduler job.")
             if not _concept_service_instance.llm_service or not hasattr(_concept_service_instance.llm_service, 'model') or _concept_service_instance.llm_service.model is None:
                  logger.warning("LLM Service model unavailable when creating ConceptService.")
        except Exception as e: logger.error(f"Failed to create ConceptService for scheduler: {e}", exc_info=True); return
        job_interval_minutes = settings.SCHEDULER_INTERVAL_MINUTES
        logger.info(f"Adding scheduled job interval: {job_interval_minutes} minutes.")
        scheduler.add_job(
            scheduled_tasks_job, trigger=IntervalTrigger(minutes=job_interval_minutes, jitter=60),
            id="scheduled_tasks_job", name="Periodic Concept Generation and Decay",
            replace_existing=True, max_instances=1, misfire_grace_time=300
        )
        try: scheduler.start(); logger.info(f"Scheduler started. Tasks scheduled every {job_interval_minutes} minutes.")
        except Exception as e: logger.error(f"Failed to start APScheduler: {e}", exc_info=True); _concept_service_instance = None
    else: logger.warning("Scheduler is already running.")

def stop_scheduler():
    """ Stops the APScheduler if it is running. """
    global _concept_service_instance
    if scheduler.running:
        logger.info("Attempting to stop scheduler...")
        try: scheduler.shutdown(wait=False); logger.info("Scheduler stopped successfully.")
        except Exception as e: logger.error(f"Error stopping scheduler: {e}", exc_info=True)
    else: logger.info("Scheduler was not running.")
    _concept_service_instance = None