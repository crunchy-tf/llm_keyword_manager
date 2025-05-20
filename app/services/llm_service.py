# app/services/llm_service.py

import logging
from typing import List, Optional, Dict, Union
import json
import re
import asyncio
from datetime import datetime, timedelta # Added timedelta

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from google.generativeai.types import generation_types

from app.core.config import settings
from app.prompts.templates import (
    TRANSLATION_PROMPT_TEMPLATE,
    CONTEXT_CONCEPT_PROMPT_TEMPLATE,
    BASE_CONCEPT_PROMPT_TEMPLATE,
    LANGUAGE_NAMES
)

logger = logging.getLogger(__name__)

# --- Rate Limiting Configuration ---
# Gemini Free Tier: 15 RPM -> 60 seconds / 15 requests = 4 seconds per request
# Add a small buffer, e.g., 4.1 seconds
MIN_SECONDS_BETWEEN_CALLS = 4.1
# Lock to prevent race conditions when checking/updating last call time
_api_call_lock = asyncio.Lock()
# --- End Rate Limiting Configuration ---


class LLMService:
    """ Handles interactions with the Google Gemini API, including rate limiting. """

    def __init__(self):
        """ Initializes the Gemini client, model, and rate limiting state. """
        self.model: Optional[genai.GenerativeModel] = None
        self.last_api_call_time: Optional[datetime] = None # Track last call time

        if not settings.GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY not configured. LLM Service unusable.")
            return
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(settings.GEMINI_LLM_MODEL)
            logger.info(f"LLMService initialized with Gemini model: {settings.GEMINI_LLM_MODEL}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client/model: {e}", exc_info=True)
            self.model = None
            raise RuntimeError(f"Gemini Client Initialization Failed: {e}") from e

    async def _apply_rate_limit_delay(self):
        """ Checks time since last call and sleeps if necessary to enforce RPM limit. """
        async with _api_call_lock: # Ensure atomic check and update
            now = datetime.utcnow()
            if self.last_api_call_time:
                elapsed = now - self.last_api_call_time
                wait_needed = MIN_SECONDS_BETWEEN_CALLS - elapsed.total_seconds()

                if wait_needed > 0:
                    logger.debug(f"Rate limit delay: sleeping for {wait_needed:.2f} seconds.")
                    await asyncio.sleep(wait_needed)
                    # Update 'now' after sleep for accurate timestamping of the call start
                    now = datetime.utcnow()

            # Record the time *before* the actual API call attempt
            self.last_api_call_time = now


    async def _call_gemini(self, prompt_text: str, max_output_tokens: int) -> Optional[str]:
        """
        Helper method to asynchronously call the Gemini model,
        enforcing rate limits before the call.
        """
        if self.model is None:
            logger.error("Gemini model not initialized. Cannot make API call.")
            return None

        # --- Apply Rate Limiting Delay ---
        await self._apply_rate_limit_delay()
        # --- End Rate Limiting Delay ---

        generation_config = genai.types.GenerationConfig(
            max_output_tokens=max_output_tokens,
            temperature=settings.LLM_TEMPERATURE,
        )
        safety_settings = [
            {"category": c, "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
            for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH",
                      "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]
        ]

        try:
            logger.debug(f"Calling Gemini model '{settings.GEMINI_LLM_MODEL}' with max_tokens={max_output_tokens} at {datetime.utcnow()}")
            response = await self.model.generate_content_async(
                contents=prompt_text,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            # --- Handle Response (No changes needed here) ---
            try:
                full_text = response.text
                cleaned_text = full_text.strip()
                logger.debug(f"Gemini call successful. Text: '{cleaned_text[:100]}...'")
                return cleaned_text
            except ValueError:
                finish_reason_detail = ""
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                     finish_reason_detail = f"Prompt blocked, reason: {response.prompt_feedback.block_reason}"
                elif response.candidates and response.candidates[0].finish_reason != generation_types.FinishReason.STOP:
                     finish_reason_detail = f"Candidate finished with reason: {response.candidates[0].finish_reason}"
                logger.warning(f"Gemini response has no text content. {finish_reason_detail}")
                return None
            except AttributeError:
                 logger.warning("Unexpected Gemini response structure. Could not extract text.")
                 return None
        except google_exceptions.PermissionDenied as e: logger.error(f"Gemini API Permission Denied: {e}", exc_info=False); return None
        # --- Add specific handling for Rate Limit Exceeded ---
        except google_exceptions.ResourceExhausted as e:
            logger.error(f"Gemini API Rate Limit Exceeded (ResourceExhausted): {e}. Check RPM/TPM limits.", exc_info=False)
            # Consider adding a longer sleep here or specific handling if needed
            return None
        # --- End specific handling ---
        except google_exceptions.InvalidArgument as e: logger.error(f"Gemini API Invalid Argument: {e}", exc_info=False); return None
        except google_exceptions.GoogleAPIError as e: logger.error(f"Gemini API Error: {e}", exc_info=False); return None
        except generation_types.StopCandidateException as e: logger.warning(f"Gemini generation stopped unexpectedly: {e}"); return None
        except Exception as e: logger.error(f"Unexpected error during Gemini API call: {e}", exc_info=True); return None

    # --- No changes needed in the public methods below ---
    async def generate_target_lang_concepts(
        self, topic_description: str, language_code: str, context: Optional[str] = None
    ) -> List[str]:
        """ Generates concept terms using Gemini. """
        if self.model is None: return []
        if language_code not in LANGUAGE_NAMES: logger.error(f"Unsupported language: {language_code}"); return []
        language_name = LANGUAGE_NAMES[language_code]

        if context:
            prompt_template = CONTEXT_CONCEPT_PROMPT_TEMPLATE
            prompt = prompt_template.format(
                topic_description=topic_description, context=context,
                language_name=language_name, language_code=language_code
            )
            logger.info(f"Generating concepts for '{topic_description}' in {language_name} using context (Gemini).")
        else:
            prompt_template = BASE_CONCEPT_PROMPT_TEMPLATE
            prompt = prompt_template.format(
                topic_description=topic_description, language_name=language_name,
                language_code=language_code
            )
            logger.info(f"Generating concepts for '{topic_description}' in {language_name} without context (Gemini).")

        raw_response = await self._call_gemini(prompt, settings.LLM_MAX_TOKENS_GENERATION)
        if not raw_response: logger.warning(f"No response from Gemini for concept gen ({topic_description}/{language_code})."); return []

        concepts = [ln.strip().strip('"\'').lower() for ln in raw_response.split('\n') if ln.strip() and len(ln.strip()) > 1]
        logger.debug(f"Parsed concepts from Gemini ({len(concepts)}): {concepts}")
        return concepts

    async def translate_term(
        self, term: str, source_language_code: str, target_language_code: str
    ) -> Optional[str]:
        """ Translates a term using Gemini, handles identical results across different languages. """
        if self.model is None: return None
        if source_language_code not in LANGUAGE_NAMES or target_language_code not in LANGUAGE_NAMES:
            logger.error(f"Unsupported language for translation: {source_language_code} or {target_language_code}"); return None

        prompt = TRANSLATION_PROMPT_TEMPLATE.format(
            term=term, source_language_name=LANGUAGE_NAMES[source_language_code],
            target_language_name=LANGUAGE_NAMES[target_language_code]
        )
        logger.info(f"Requesting translation for '{term}' from {source_language_code} to {target_language_code} (Gemini)")

        raw_response = await self._call_gemini(prompt, settings.LLM_MAX_TOKENS_TRANSLATION)
        if not raw_response: logger.warning(f"No response from Gemini for translation ('{term}')."); return None

        translation = raw_response.strip().strip('"\'').lower()
        if not translation: logger.warning(f"Gemini returned empty translation for '{term}'."); return None

        # --- ADJUSTED IDENTICAL CHECK ---
        if translation == term.lower():
             if source_language_code == target_language_code:
                  logger.warning(f"Translation failed: source/target same, result identical ('{term}').")
                  return None # Fail if langs are same and result is same
             else:
                  logger.info(f"Translation result ('{translation}') identical to source ('{term}') but languages differ. Accepting identical term.")
                  # Fall through to return the identical translation
        # --- END ADJUSTMENT ---

        logger.debug(f"Translation result from Gemini: '{translation}'")
        return translation


# --- Singleton Instance Creation (No changes needed here) ---
llm_service: Optional[LLMService] = None
try:
    llm_service_instance = LLMService()
    if hasattr(llm_service_instance, 'model') and llm_service_instance.model is not None:
         llm_service = llm_service_instance
    else: logger.error("LLMService init failed silently or Gemini model is None."); llm_service = None
except RuntimeError: logger.error("LLMService creation failed critically."); llm_service = None
except Exception as e: logger.error(f"Unexpected error creating LLMService: {e}", exc_info=True); llm_service = None