# app/api/endpoints/concepts.py

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query, Path
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

# Local imports - Use refactored schemas, crud, service
from app.db.database import get_database
from app.db import crud # Assumes crud is refactored for Option 2
from app.api.schemas import (
    ApiConceptCreate,
    ConceptRead, # Use the refactored schema
    ConceptFeedbackPayload,
    PyObjectId
)
from app.services.concept_service import ConceptService # Assumes service is refactored
from app.prompts.templates import HEALTH_TOPICS
from app.core.config import SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Dependency Injection ---
async def get_concept_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> ConceptService:
    """ Dependency function to instantiate and provide the ConceptService. """
    service = ConceptService(db)
    # Check if the LLM service model (Gemini) is available
    llm_model_available = bool(service.llm_service and hasattr(service.llm_service, 'model') and service.llm_service.model is not None)
    if not llm_model_available:
         logger.error("LLM Service model (Gemini) is unavailable within ConceptService dependency.")
         # Decide if this should block requests
         # raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LLM Service unavailable.")
    logger.debug("ConceptService dependency resolved.")
    return service

# --- API Endpoints ---

@router.post(
    "/concepts",
    response_model=ConceptRead, # Use refactored schema
    status_code=status.HTTP_201_CREATED,
    summary="Create Concept Manually",
    description="Manually creates a concept with concept-level metrics."
)
async def create_concept_manually(
    concept_in: ApiConceptCreate,
    concept_service: ConceptService = Depends(get_concept_service)
):
    """ Manually adds a concept. Checks for duplicates based on English term. """
    logger.info(f"API: Request to manually create concept for EN term: '{concept_in.english_term}'")
    created_concept = await concept_service.create_manual_concept(concept_in) # Assumes service refactored
    if created_concept is None:
        existing = await crud.get_concept_by_english_term(concept_service.db, concept_in.english_term.lower()) # Assumes crud refactored
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Concept EN term '{concept_in.english_term}' exists (ID: {existing.id}).")
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create concept.")
    logger.info(f"API: Manual concept created: ID {created_concept.id}")
    return created_concept

@router.get(
    "/concepts",
    response_model=List[ConceptRead], # Use refactored schema
    summary="List Concepts",
    description="Retrieves a paginated list of concepts with concept-level metrics."
)
async def list_concepts(
    skip: int = Query(0, ge=0, description="Pagination skip."),
    limit: int = Query(100, ge=1, le=500, description="Pagination limit."),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """ Fetches concepts with pagination. """
    logger.info(f"API: Request to list concepts: skip={skip}, limit={limit}")
    try:
        concepts = await crud.get_concepts(db, skip=skip, limit=limit) # Assumes crud refactored
        logger.info(f"API: Returning {len(concepts)} concepts.")
        return concepts
    except Exception as e:
        logger.error(f"API: Error listing concepts: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve concepts.")

@router.get(
    "/concepts/{concept_id}",
    response_model=ConceptRead, # Use refactored schema
    summary="Get Concept by ID",
    description="Retrieves a single concept by ObjectId."
)
async def get_concept(
    concept_id: PyObjectId = Path(..., description="The MongoDB ObjectId."),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """ Fetches a single concept by ID. """
    logger.info(f"API: Request to get concept ID: {concept_id}")
    concept = await crud.get_concept_by_id(db, concept_id) # Assumes crud refactored
    if not concept:
        logger.warning(f"API: Concept ID '{concept_id}' not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Concept ID '{concept_id}' not found")
    return concept

@router.post(
    "/feedback",
    response_model=ConceptRead, # Use refactored schema
    summary="Submit Feedback on Keyword Relevance",
    description="Receives feedback, updates concept-level metrics."
)
async def submit_feedback(
    feedback_payload: ConceptFeedbackPayload,
    concept_service: ConceptService = Depends(get_concept_service)
):
    """ Processes relevance feedback, updating concept-level metrics. """
    logger.info(f"API: Feedback received: Concept={feedback_payload.concept_id}, Lang={feedback_payload.language}")
    updated_concept = await concept_service.process_feedback(feedback_payload) # Assumes service refactored
    if not updated_concept:
         if not ObjectId.is_valid(feedback_payload.concept_id):
             raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid Concept ID format.")
         concept_exists = await crud.get_concept_by_id(concept_service.db, PyObjectId(feedback_payload.concept_id)) # Assumes crud refactored
         if not concept_exists: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Concept '{feedback_payload.concept_id}' not found.")
         else: raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Failed processing feedback for concept '{feedback_payload.concept_id}', language '{feedback_payload.language}'.")
    logger.info(f"API: Feedback processed for concept {updated_concept.id}")
    return updated_concept

@router.post(
    "/concepts/generate",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Background Concept Generation",
    description="Adds a background task for concept generation."
)
async def trigger_concept_generation(
    background_tasks: BackgroundTasks,
    category: Optional[str] = Query(None, enum=list(HEALTH_TOPICS.keys()), description="Optional category key."),
    concept_service: ConceptService = Depends(get_concept_service)
):
    """ Manually triggers background concept generation. """
    logger.info(f"API: Manual trigger for concept generation (Category: {category or 'Random'})")
    background_tasks.add_task(concept_service.generate_and_store_concepts, category=category) # Assumes service refactored
    return {"message": f"Concept generation task added for category: {category or 'Random'}."}