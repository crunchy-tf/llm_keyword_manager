# app/services/concept_service.py

import logging
import random
from datetime import datetime, timedelta
import os
import asyncio
from typing import Optional, Tuple, Dict, Any, List

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

# Local imports
from app.core.config import settings, SUPPORTED_LANGUAGES
from app.prompts.templates import HEALTH_TOPICS
from app.db import crud # Use refactored CRUD
from app.db.models import TranslationStatus, ConceptGenerationMethod
from app.api.schemas import (
    ConceptCreateInternal, ConceptRead, ConceptFeedbackPayload,
    ApiConceptCreate, PyObjectId, ConceptBase # Use refactored schemas
)
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)

class ConceptService:
    """ Orchestrates concept lifecycle with CONCEPT-LEVEL metrics using Gemini LLM. """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.llm_service = llm_service
        llm_model_available = bool(self.llm_service and hasattr(self.llm_service, 'model') and self.llm_service.model is not None)
        if not llm_model_available: logger.error("ConceptService init: Gemini LLM model unavailable.")
        else: logger.info("ConceptService.__init__: LLM model (Gemini) check passed.")

    def _get_context_for_category(self, category_key: str) -> Optional[str]:
        """ Reads context text from file based on category key. """
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        context_file_path = os.path.join(base_dir, "context_data", f"{category_key}.txt")
        logger.debug(f"Attempting context read: {context_file_path}")
        if os.path.exists(context_file_path):
            try:
                with open(context_file_path, 'r', encoding='utf-8') as f: content = f.read().strip()
                if content: logger.info(f"Loaded context for '{category_key}'."); return content
                logger.warning(f"Context file empty for '{category_key}'.")
            except Exception as e: logger.warning(f"Error reading context file {context_file_path}: {e}")
        else: logger.debug(f"No context file found for '{category_key}'.")
        return None

    async def generate_and_store_concepts(self, category: Optional[str] = None) -> int:
        """ Main workflow to generate terms and store/update concepts (Option 2 logic). """
        if not self.llm_service or not hasattr(self.llm_service, 'model') or self.llm_service.model is None:
             logger.error("Cannot generate concepts: Gemini LLM model unavailable."); return 0
        if not HEALTH_TOPICS: logger.error("Cannot generate concepts: HEALTH_TOPICS empty."); return 0

        logger.info(f"Starting concept generation cycle (Concept-Level Metrics/Gemini) (Category: {category or 'Random'})...")

        category_key = category if (category and category in HEALTH_TOPICS) else random.choice(list(HEALTH_TOPICS.keys()))
        target_language = random.choice(SUPPORTED_LANGUAGES)
        topic_description = HEALTH_TOPICS.get(category_key, "Unknown Topic")
        logger.info(f"Selected - Category: '{category_key}', Target Language: {target_language}")

        context = self._get_context_for_category(category_key)
        generation_method = ConceptGenerationMethod.PLACEHOLDER_CONTEXT if context else ConceptGenerationMethod.LLM

        try:
            generated_terms = await self.llm_service.generate_target_lang_concepts(
                topic_description=topic_description, language_code=target_language, context=context
            )
        except Exception as e: logger.error(f"LLM generation failed for {category_key}/{target_language}: {e}", exc_info=True); return 0
        if not generated_terms: logger.warning(f"LLM returned no terms for {category_key}/{target_language}."); return 0
        logger.info(f"LLM generated {len(generated_terms)} potential terms in {target_language} for '{category_key}'.")

        processed_count = 0
        # Use concurrent processing for terms
        tasks = [ self._process_single_generated_term_option2( term.lower(), target_language, category_key, generation_method ) for term in generated_terms if term ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful_processing = sum(1 for res in results if isinstance(res, bool) and res)
        errors = [res for res in results if isinstance(res, Exception)]
        if errors: logger.error(f"{len(errors)} errors processing terms: {errors}")
        processed_count = successful_processing

        logger.info(f"Finished generation cycle. Successfully processed {processed_count}/{len(generated_terms)} generated terms for {category_key}/{target_language}.")
        return processed_count

    # --- THIS METHOD CONTAINS THE IMPROVED DUPLICATE HANDLING v2 ---
    async def _process_single_generated_term_option2(
        self, original_term: str, original_language: str, category_key: str, generation_method: ConceptGenerationMethod
    ) -> bool:
        """ Processes a single generated term for the Concept-Level Metrics model using Gemini. """
        if not self.llm_service or not hasattr(self.llm_service, 'model') or self.llm_service.model is None:
            logger.error(f"LLM model unavailable, cannot process term '{original_term}'."); return False

        # --- Translate to English Anchor ---
        english_term: Optional[str] = None
        if original_language == 'en': english_term = original_term
        else:
            translation_result = await self.llm_service.translate_term(
                term=original_term, source_language_code=original_language, target_language_code='en'
            )
            if translation_result: english_term = translation_result.lower()
            else: logger.warning(f"Failed anchor translation for '{original_term}'. Skipping."); return False # Critical step failed

        # --- Find or Create Concept (Improved Logic v2) ---
        concept_id: Optional[ObjectId] = None
        concept_created_now = False
        try:
            # Step 1: Try to find existing concept first
            logger.debug(f"Step 1: Finding concept by EN term: '{english_term}'") # Log term before find
            concept = await crud.get_concept_by_english_term(self.db, english_term)
            if concept:
                concept_id = concept.id
                logger.debug(f"Found existing concept '{concept_id}' for EN term '{english_term}'")
            else:
                # Step 2: If not found, attempt to create
                logger.debug(f"Step 2: Creating new concept for EN term '{english_term}'")
                now = datetime.utcnow()
                new_concept_data = ConceptCreateInternal( # Uses Option 2 Schema
                    categories=[category_key], generation_method=generation_method,
                    confidence_score=ConceptBase.model_fields['confidence_score'].default, # Get defaults from schema
                    historical_yield=ConceptBase.model_fields['historical_yield'].default,
                    status=ConceptBase.model_fields['status'].default, usage_count=0,
                    last_used_at=None, last_positive_feedback_at=None,
                    translations={"en": english_term}, created_at=now, updated_at=now
                )
                # CRUD create returns ConceptRead on success, None ONLY on DuplicateKeyError, raises on others
                created_concept_obj = await crud.create_concept(self.db, new_concept_data)

                if created_concept_obj:
                    # Creation succeeded
                    concept_id = created_concept_obj.id # Extract ID from returned object
                    concept_created_now = True
                    logger.info(f"Successfully created new concept '{concept_id}' with EN term '{english_term}'")
                else:
                    # Creation returned None - CRUD confirmed it was DuplicateKeyError
                    logger.warning(f"Creation failed (likely DuplicateKeyError) for '{english_term}'. Fetching existing.")
                    # Step 3: Fetch the existing concept guaranteed (almost) to exist
                    logger.debug(f"Step 3: Re-Finding concept by EN term: '{english_term}'") # Log term before re-find
                    concept = await crud.get_concept_by_english_term(self.db, english_term)
                    if concept:
                        concept_id = concept.id
                        logger.info(f"Successfully fetched existing concept '{concept_id}' after duplicate error.")
                    else:
                        # This case is now *extremely* unlikely if DuplicateKey was the *only* error
                        logger.error(f"CRITICAL: EN term '{english_term}' caused DuplicateKeyError on create, but get_concept_by_english_term failed immediately after. DB consistency issue?")
                        return False # Stop processing this term

            # Add category to existing concept if needed (and not just created)
            if concept_id and not concept_created_now:
                 # Fetch concept again to check categories safely
                 concept_to_check = await crud.get_concept_by_id(self.db, concept_id)
                 if concept_to_check and category_key not in (concept_to_check.categories or []):
                      await crud.add_or_update_concept_category(self.db, concept_id, category_key)


        except Exception as e:
            # Catch errors raised by CRUD functions (if not DuplicateKeyError) or other issues
            logger.error(f"DB error during find/create concept logic for EN term '{english_term}': {e}", exc_info=True)
            return False

        # --- Ensure concept_id is valid ---
        if not concept_id:
             logger.error(f"Could not obtain valid concept_id for EN term '{english_term}'. Aborting.")
             return False

        # --- Add/Update Translations (Proceed only if concept ID confirmed) ---
        try:
            # Fetch current state only if we didn't just create it
            if not concept_created_now:
                current_concept = await crud.get_concept_by_id(self.db, concept_id)
                if not current_concept: logger.error(f"Concept {concept_id} disappeared"); return False
                existing_translations = current_concept.translations
            else:
                 existing_translations = { "en": english_term }

            translation_tasks = []
            # Add/update original language term if needed
            if original_language != 'en' and existing_translations.get(original_language) != original_term:
                 translation_tasks.append(crud.add_or_update_translation_term(self.db, concept_id, original_language, original_term))

            # Translate to and add/update third languages if missing
            languages_to_add = [lang for lang in SUPPORTED_LANGUAGES if lang != 'en' and lang != original_language and lang not in existing_translations]
            for third_language in languages_to_add:
                translation_tasks.append(self._translate_and_add_term_option2(concept_id, english_term, third_language))

            if translation_tasks: await asyncio.gather(*translation_tasks)

        except Exception as e:
            logger.error(f"Error during translation update phase for {concept_id}: {e}", exc_info=True)
            # Don't necessarily return False here, main concept processing succeeded
            pass # Logged error, but let the overall processing be marked successful

        return True # Indicate successful processing attempt for this term


    async def _translate_and_add_term_option2(self, concept_id: ObjectId, english_term: str, target_language: str):
        """ Helper to translate and add term string for Option 2 model. """
        if not self.llm_service or not hasattr(self.llm_service, 'model') or self.llm_service.model is None: return
        translated_term = await self.llm_service.translate_term(
             term=english_term, source_language_code='en', target_language_code=target_language
        )
        if translated_term:
             logger.debug(f"Adding/updating {target_language} translation ('{translated_term}') for {concept_id}")
             # Use refactored CRUD
             await crud.add_or_update_translation_term(self.db, concept_id, target_language, translated_term.lower())
        else: logger.warning(f"Failed translation '{english_term}' -> {target_language} for {concept_id}.")


    async def process_feedback(self, feedback: ConceptFeedbackPayload) -> Optional[ConceptRead]:
        """ Processes feedback, updating CONCEPT-LEVEL metrics. """
        logger.info(f"Processing feedback (Concept Level): Concept={feedback.concept_id}, Lang={feedback.language}, Metric={feedback.relevance_metric:.3f}")
        try: concept_id_obj = PyObjectId(feedback.concept_id)
        except ValueError: logger.error(f"Invalid feedback concept_id: {feedback.concept_id}"); return None

        concept = await crud.get_concept_by_id(self.db, concept_id_obj) # Assumes CRUD returns ConceptRead/InDB
        if not concept: logger.warning(f"Feedback for non-existent concept: {feedback.concept_id}"); return None
        if feedback.language not in concept.translations: logger.warning(f"Feedback lang '{feedback.language}' term not found for concept {feedback.concept_id}.")
        elif feedback.term and feedback.term.lower() != concept.translations.get(feedback.language, '').lower(): logger.warning(f"Feedback term mismatch for {feedback.concept_id}/{feedback.language}.")

        current_score = concept.confidence_score; current_yield = concept.historical_yield
        current_usage = concept.usage_count or 0; current_status = concept.status
        is_positive_feedback = feedback.relevance_metric >= settings.LOW_YIELD_THRESHOLD
        new_score = min(current_score * 1.05, 1.0) if is_positive_feedback else current_score * settings.SCORE_DECAY_FACTOR
        new_score = max(0.0, new_score)
        new_yield = feedback.relevance_metric if current_usage == 0 else ((current_yield * current_usage) + feedback.relevance_metric) / (current_usage + 1)
        new_yield = max(0.0, min(1.0, new_yield))
        new_status = current_status
        if new_score < settings.KEYWORD_DEACTIVATION_THRESHOLD and current_status == TranslationStatus.ACTIVE:
            logger.info(f"Deactivating concept {concept.id} due to score: {new_score:.3f}")
            new_status = TranslationStatus.INACTIVE
        elif new_score >= settings.KEYWORD_DEACTIVATION_THRESHOLD and current_status == TranslationStatus.INACTIVE:
            logger.info(f"Reactivating concept {concept.id} due to score: {new_score:.3f}")
            new_status = TranslationStatus.ACTIVE
        update_payload: Dict[str, Any] = { "confidence_score": new_score, "historical_yield": new_yield, "status": new_status.value, }
        if is_positive_feedback: update_payload["last_positive_feedback_at"] = datetime.utcnow()

        success = await crud.apply_feedback_update( db=self.db, concept_id=concept_id_obj, updates=update_payload ) # Assumes CRUD refactored
        if success:
            logger.info(f"Concept-level feedback applied for {feedback.concept_id}.")
            return await crud.get_concept_by_id(self.db, concept_id_obj)
        else: logger.error(f"Failed concept-level feedback update via CRUD for {feedback.concept_id}."); return None


    async def apply_confidence_decay(self) -> int:
        """ Applies time-based confidence decay to CONCEPT-LEVEL metrics. """
        if not settings.CONFIDENCE_DECAY_ENABLED: logger.info("Concept time decay disabled."); return 0
        logger.info("Starting concept confidence score time decay process...")
        decay_count = 0; now = datetime.utcnow()
        cutoff_time = now - timedelta(days=settings.CONFIDENCE_DECAY_PERIOD_DAYS)
        logger.info(f"Decay cutoff time: {cutoff_time.isoformat()}")
        try: concepts_to_check = await crud.get_all_concepts_for_decay(self.db) # Assumes CRUD refactored
        except Exception as e: logger.error(f"Failed fetch concepts for decay: {e}", exc_info=True); return 0

        decay_tasks = []
        for concept_decay_info in concepts_to_check:
            try:
                concept_id = concept_decay_info["_id"]; current_status_val = concept_decay_info.get("status")
                current_score = concept_decay_info.get("confidence_score", 0.0); last_positive = concept_decay_info.get("last_positive_feedback_at")
                current_status = TranslationStatus(current_status_val) if current_status_val else None
                if current_status == TranslationStatus.ACTIVE and (last_positive is None or last_positive < cutoff_time):
                    decayed_score = max(0.0, current_score * settings.CONFIDENCE_TIME_DECAY_FACTOR)
                    new_status = TranslationStatus.INACTIVE if decayed_score < settings.KEYWORD_DEACTIVATION_THRESHOLD else TranslationStatus.ACTIVE
                    if decayed_score != current_score or new_status != current_status:
                         logger.debug(f"Decay triggered for concept {concept_id}.")
                         decay_tasks.append(crud.apply_time_decay_to_concept( self.db, concept_id, decayed_score, new_status )) # Assumes CRUD refactored
            except Exception as e: logger.error(f"Error processing concept {concept_decay_info.get('_id')} for decay: {e}", exc_info=True)

        if decay_tasks:
            logger.info(f"Applying concept decay updates concurrently for {len(decay_tasks)} concepts...")
            results = await asyncio.gather(*decay_tasks, return_exceptions=True)
            successful_decays = sum(1 for res in results if isinstance(res, bool) and res)
            errors = [res for res in results if isinstance(res, Exception)]
            if errors: logger.error(f"{len(errors)} errors during concurrent concept decay update: {errors}")
            decay_count = successful_decays
            logger.info(f"Concept decay applied successfully to {decay_count} concepts.")
        else: logger.info("No concepts met criteria for time decay.")
        logger.info(f"Concept confidence score time decay process finished. Decayed {decay_count} concepts.")
        return decay_count


    async def create_manual_concept(self, concept_in: ApiConceptCreate) -> Optional[ConceptRead]:
         """ Handles the business logic for creating a concept manually (Option 2). """
         logger.info(f"Attempting manual concept creation (Concept Level Metrics) for EN term: '{concept_in.english_term}'")
         english_term_lower = concept_in.english_term.lower()
         existing = await crud.get_concept_by_english_term(self.db, english_term_lower) # Assumes CRUD refactored
         if existing: logger.warning(f"Manual creation failed: Concept EN term '{english_term_lower}' exists."); return None
         now = datetime.utcnow()
         translations: Dict[str, str] = {"en": english_term_lower}
         if concept_in.french_term: translations["fr"] = concept_in.french_term.lower()
         if concept_in.arabic_term: translations["ar"] = concept_in.arabic_term.lower()
         new_concept_internal = ConceptCreateInternal( # Uses Option 2 Schema
             categories=concept_in.categories or [], generation_method=ConceptGenerationMethod.MANUAL,
             confidence_score=ConceptBase.model_fields['confidence_score'].default,
             historical_yield=ConceptBase.model_fields['historical_yield'].default,
             status=ConceptBase.model_fields['status'].default, usage_count=0,
             last_used_at=None, last_positive_feedback_at=None,
             translations=translations, created_at=now, updated_at=now
         )
         created_concept = await crud.create_concept(self.db, new_concept_internal) # Assumes CRUD refactored
         if created_concept: logger.info(f"Successfully created manual concept {created_concept.id}")
         else: logger.error(f"Failed to create manual concept '{english_term_lower}' via CRUD.")
         return created_concept