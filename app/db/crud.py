# app/db/crud.py

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from bson import ObjectId
from pymongo import ReturnDocument, ASCENDING, DESCENDING
# Import specific pymongo errors
from pymongo.errors import DuplicateKeyError, CollectionInvalid, OperationFailure

from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection

# Local imports
from app.core.config import settings, SUPPORTED_LANGUAGES
# Import refactored Schemas
from app.api.schemas import (
    ConceptCreateInternal,
    ConceptRead,
    ConceptInDB,
    PyObjectId
)
# Import Enum for comparisons
from app.db.models import TranslationStatus as TranslationStatusEnum

logger = logging.getLogger(__name__)

# --- Helper Function ---
def get_concept_collection(db: AsyncIOMotorDatabase) -> AsyncIOMotorCollection:
     """ Convenience function to get the concept collection. """
     return db[settings.MONGO_COLLECTION_CONCEPTS]

# --- Concept Level Operations (Refactored for Concept-Level Metrics) ---

async def create_concept(db: AsyncIOMotorDatabase, concept_in: ConceptCreateInternal) -> Optional[ConceptRead]:
    """
    Creates a concept document with concept-level metrics.
    Returns ConceptRead on success, None ONLY on DuplicateKeyError, raises others.
    Raises RuntimeError if immediate fetch after insert fails.
    """
    collection = get_concept_collection(db)
    concept_dict = concept_in.model_dump(exclude_unset=True, by_alias=False)
    en_term = concept_in.translations.get('en', 'N/A') # For logging
    logger.debug(f"Attempting DB Insert for EN term: '{en_term}'") # Log before insert

    try:
        insert_result = await collection.insert_one(concept_dict)
        # IMPORTANT: Fetch immediately after insert to return the full object
        created_doc = await collection.find_one({"_id": insert_result.inserted_id})
        if created_doc:
            logger.info(f"Created concept ID: {insert_result.inserted_id} for EN term '{en_term}'")
            return ConceptRead.model_validate(created_doc)
        else:
            # This is highly unexpected if insert succeeded
            logger.error(f"CRITICAL! Failed retrieval immediately after successful insert! ID: {insert_result.inserted_id}")
            raise RuntimeError(f"Post-insert fetch failed for ID {insert_result.inserted_id}")
    except DuplicateKeyError as e: # Catch DuplicateKeyError specifically
         logger.warning(f"DuplicateKeyError creating concept with EN term: '{en_term}'. Details: {e.details}")
         return None # Explicitly return None ONLY for this error
    except OperationFailure as e:
        # Database command failed (permissions, config issues, etc.)
        logger.error(f"MongoDB Operation Failure creating concept for EN term '{en_term}': {e.details}", exc_info=True)
        raise # Re-raise database operational errors so they aren't masked
    except Exception as e:
         # Catch any other unexpected error during insert/fetch
         logger.error(f"Unexpected error creating concept for EN term '{en_term}': {e}", exc_info=True)
         raise # Re-raise other unexpected errors


async def get_concept_by_id(db: AsyncIOMotorDatabase, concept_id: ObjectId) -> Optional[ConceptRead]:
    """ Retrieves a single concept by ObjectId. Validates against refactored schema. """
    collection = get_concept_collection(db)
    logger.debug(f"Querying for concept with _id = {concept_id}")
    try:
        concept_doc = await collection.find_one({"_id": concept_id})
        if concept_doc:
            logger.debug(f"Found concept by ID: {concept_id}")
            return ConceptRead.model_validate(concept_doc)
        else:
            logger.debug(f"Concept not found by ID: {concept_id}")
            return None
    except Exception as e:
        logger.error(f"Error fetching concept by ID '{concept_id}': {e}", exc_info=True)
        return None # Return None on error


async def get_concept_by_english_term(db: AsyncIOMotorDatabase, english_term: str) -> Optional[ConceptRead]:
    """ Retrieves a single concept by its English term string (case-insensitive safe). """
    collection = get_concept_collection(db)
    term_lower = english_term.lower() # Ensure lowercase for query
    logger.debug(f"Querying for concept with translations.en = '{term_lower}'")
    try:
        # Query the simple string field directly
        concept_doc = await collection.find_one({"translations.en": term_lower})
        if concept_doc:
            logger.debug(f"Found concept by EN term '{term_lower}': ID {concept_doc.get('_id')}")
            # Validate against the refactored ConceptRead schema
            return ConceptRead.model_validate(concept_doc)
        else:
            logger.debug(f"Concept not found by EN term '{term_lower}'")
            return None
    except Exception as e:
        logger.error(f"Error fetching concept by EN term '{term_lower}': {e}", exc_info=True)
        return None # Return None on error during fetch


async def get_concepts(db: AsyncIOMotorDatabase, skip: int = 0, limit: int = 100) -> List[ConceptRead]:
    """ Retrieves a paginated list of concepts. Validates against refactored schema. """
    collection = get_concept_collection(db)
    concepts_list = []
    try:
        concepts_cursor = collection.find().sort("created_at", DESCENDING).skip(skip).limit(limit)
        concepts_docs = await concepts_cursor.to_list(length=limit)
        # Validate each document with the refactored ConceptRead schema
        for doc in concepts_docs:
            try:
                concepts_list.append(ConceptRead.model_validate(doc))
            except Exception as val_err:
                 logger.warning(f"Validation failed for concept doc {doc.get('_id', 'N/A')}: {val_err}")
                 # Skip invalid documents
    except Exception as e:
        logger.error(f"Error fetching concepts list: {e}", exc_info=True)
        # Return empty list or raise depending on desired error handling
    return concepts_list


async def get_active_keywords(
    db: AsyncIOMotorDatabase, lang: str, min_score: float, limit: int
) -> List[Dict[str, Any]]:
     """ Fetches terms for active concepts meeting score criteria (concept-level). """
     collection = get_concept_collection(db)
     lang_term_field = f"translations.{lang}"
     query = {
         "status": TranslationStatusEnum.ACTIVE.value,
         "confidence_score": {"$gte": min_score},
         lang_term_field: {"$exists": True, "$ne": None, "$ne": ""}
     }
     projection = { "_id": 1, "translations": 1, "confidence_score": 1 }
     sort_order = [("confidence_score", DESCENDING)]
     try:
         cursor = collection.find(query, projection=projection).sort(sort_order).limit(limit)
         results = await cursor.to_list(length=limit)
         return results
     except Exception as e:
          logger.error(f"Error getting active keywords for lang '{lang}': {e}", exc_info=True)
          return []


async def add_or_update_concept_category(db: AsyncIOMotorDatabase, concept_id: ObjectId, category: str) -> bool:
    """ Adds category to concept's list. Updates concept 'updated_at'. """
    collection = get_concept_collection(db)
    try:
        result = await collection.update_one(
            {"_id": concept_id},
            {"$addToSet": {"categories": category}, "$set": {"updated_at": datetime.utcnow()}}
        )
        modified = result.modified_count > 0
        matched = result.matched_count > 0
        if modified: logger.info(f"Added/updated category '{category}' for concept {concept_id}")
        elif not matched: logger.warning(f"Concept {concept_id} not found for category add.")
        return matched # Return True if found
    except Exception as e:
        logger.error(f"Error adding category '{category}' to concept {concept_id}: {e}", exc_info=True)
        return False


async def apply_feedback_update(
    db: AsyncIOMotorDatabase, concept_id: ObjectId, updates: Dict[str, Any]
) -> bool:
    """ Applies feedback by updating CONCEPT-LEVEL metrics and incrementing usage count. """
    collection = get_concept_collection(db)
    now = datetime.utcnow()
    set_payload = updates.copy()
    set_payload["updated_at"] = now
    set_payload["last_used_at"] = now
    inc_payload = {"usage_count": 1}
    update_doc = {"$set": set_payload, "$inc": inc_payload}
    logger.debug(f"Applying concept-level feedback update to {concept_id}: {update_doc}")
    try:
        result = await collection.update_one({"_id": concept_id}, update_doc)
        matched = result.matched_count > 0
        if not matched: logger.warning(f"Concept {concept_id} not found for feedback update.")
        elif result.modified_count > 0: logger.info(f"Applied concept-level feedback to {concept_id}.")
        return matched
    except Exception as e:
        logger.error(f"Error applying feedback to concept {concept_id}: {e}", exc_info=True)
        return False


async def add_or_update_translation_term(
    db: AsyncIOMotorDatabase, concept_id: ObjectId, lang: str, term: str
) -> bool:
    """ Adds or updates a specific language term string within the translations dict. """
    collection = get_concept_collection(db)
    if lang not in SUPPORTED_LANGUAGES:
        logger.error(f"Attempted add/update unsupported lang: {lang} for {concept_id}")
        return False
    term_field = f"translations.{lang}"
    term_lower = term.lower()
    try:
        result = await collection.update_one(
            {"_id": concept_id},
            {"$set": {term_field: term_lower, "updated_at": datetime.utcnow()}},
            upsert=False
        )
        modified = result.modified_count > 0
        matched = result.matched_count > 0
        if modified: logger.info(f"Set translation term {lang}='{term_lower}' for {concept_id}.")
        elif not matched: logger.warning(f"Concept {concept_id} not found for translation update.")
        return matched
    except Exception as e:
        logger.error(f"Error setting translation for {concept_id}/{lang}: {e}", exc_info=True)
        return False


async def apply_time_decay_to_concept(
    db: AsyncIOMotorDatabase, concept_id: ObjectId, decayed_score: float, new_status: TranslationStatusEnum
) -> bool:
    """ Applies time decay updates to CONCEPT-LEVEL score and status. """
    collection = get_concept_collection(db)
    now = datetime.utcnow()
    try:
        result = await collection.update_one(
            {"_id": concept_id},
            {"$set": {"confidence_score": decayed_score, "status": new_status.value, "updated_at": now}}
        )
        modified = result.modified_count > 0
        return modified
    except Exception as e:
        logger.error(f"Error applying time decay to concept {concept_id}: {e}", exc_info=True)
        return False


async def get_all_concepts_for_decay(db: AsyncIOMotorDatabase) -> List[Dict[str, Any]]:
    """ Fetches active concepts potentially needing decay (minimal projection). """
    collection = get_concept_collection(db)
    projection = { "_id": 1, "status": 1, "confidence_score": 1, "last_positive_feedback_at": 1 }
    query = {"status": TranslationStatusEnum.ACTIVE.value}
    try:
        cursor = collection.find(query, projection=projection)
        results = await cursor.to_list(length=None)
        logger.info(f"Fetched {len(results)} active concepts for decay check.")
        return results
    except Exception as e:
         logger.error(f"Error fetching concepts for decay check: {e}", exc_info=True)
         return []