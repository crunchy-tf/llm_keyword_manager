# app/api/endpoints/keywords.py

import logging
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

# Local imports - use refactored schemas and CRUD
from app.db.database import get_database
from app.db import crud # Assumes crud.get_active_keywords is refactored for Option 2
from app.api.schemas import KeywordFetchItem, KeywordFetchParams
from app.core.config import SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get(
    "/keywords",
    response_model=List[KeywordFetchItem],
    summary="Fetch Active Keywords for Ingestion",
    description="Retrieves terms for active concepts based on concept-level status and score, sorted by concept score."
)
async def get_keywords(
    params: KeywordFetchParams = Depends(), # Validate query params using schema
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Provides prioritized keywords based on concept relevance.

    Filters concepts by `status=active` & concept `confidence_score >= min_score`.
    Returns the term for the requested `lang`. Sorted by concept score.
    """
    logger.info(f"API: Request keywords: lang={params.lang}, limit={params.limit}, min_score={params.min_score}")
    try:
        # Call refactored CRUD function (queries concept-level fields, projects translations)
        results: List[Dict[str, Any]] = await crud.get_active_keywords(
            db=db,
            lang=params.lang,
            min_score=params.min_score, # Refers to concept-level score
            limit=params.limit
        ) # Assumes results contain _id, translations, confidence_score

        keyword_items: List[KeywordFetchItem] = []
        for doc in results:
            try:
                concept_id = str(doc["_id"])
                translations = doc.get("translations", {})

                # Extract term for requested language and English for display
                term = translations.get(params.lang)
                display_name = translations.get("en", f"Concept {concept_id}") # Fallback

                # Only add if the requested term exists for this concept
                if term:
                    keyword_items.append(
                        KeywordFetchItem(
                            term=term,
                            language=params.lang,
                            concept_id=concept_id,
                            concept_display_name=display_name
                        )
                    )
                else:
                    logger.warning(f"Concept {concept_id} matched query but missing term for '{params.lang}'.")
            except Exception as e:
                 logger.error(f"Error processing keyword result doc {doc.get('_id', 'N/A')}: {e}", exc_info=True)

        logger.info(f"API: Returning {len(keyword_items)} keywords for '{params.lang}'.")
        return keyword_items

    except Exception as e:
        logger.error(f"API: Error fetching keywords for lang={params.lang}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error fetching keywords."
        )