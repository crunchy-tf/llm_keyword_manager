# app/api/schemas.py

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional, Dict, Literal, Any
from datetime import datetime
from bson import ObjectId

# Local imports
from app.db.models import TranslationStatus, ConceptGenerationMethod # Enums remain the same
from app.api.utils import PyObjectId # PyObjectId helper remains the same
from app.core.config import SUPPORTED_LANGUAGES, settings

# --- TranslationDetail Schemas are REMOVED ---

# --- Main Concept Schemas (Refactored for Concept-Level Metrics) ---

class ConceptBase(BaseModel):
    """Base schema for a health concept with concept-level metrics."""
    categories: Optional[List[str]] = Field(None, description="List of associated health topic category keys.")
    generation_method: ConceptGenerationMethod = Field(ConceptGenerationMethod.MANUAL, description="Method used to generate this concept.")
    confidence_score: float = Field(0.75, ge=0.0, le=1.0, description="Overall relevance score for the concept.")
    historical_yield: float = Field(0.5, ge=0.0, le=1.0, description="Overall moving average of past relevance feedback.")
    status: TranslationStatus = Field(TranslationStatus.ACTIVE, description="Current status of the concept (active, inactive).")
    usage_count: int = Field(0, ge=0, description="Total usage count across all terms of the concept.")
    last_used_at: Optional[datetime] = Field(None, description="Timestamp when any term of this concept was last used or received feedback.")
    last_positive_feedback_at: Optional[datetime] = Field(None, description="Timestamp of the last positive feedback received for any term.")
    translations: Dict[Literal[tuple(SUPPORTED_LANGUAGES)], str] = Field(..., description="Dictionary mapping language codes to the corresponding term string.")

    @field_validator('translations')
    @classmethod
    def check_languages(cls, v: Dict[str, str]):
        """Ensures translations exist, English is present, and terms are non-empty."""
        if not v: raise ValueError("Translations dictionary cannot be empty")
        if 'en' not in v or not v['en']: raise ValueError("English ('en') translation term is required")
        for lang, term in v.items():
            if lang not in SUPPORTED_LANGUAGES: raise ValueError(f"Unsupported language: {lang}")
            if not isinstance(term, str) or not term.strip(): raise ValueError(f"Term for lang '{lang}' cannot be empty")
        return v

class ConceptCreateInternal(ConceptBase):
    """Internal schema used just before saving to DB, includes timestamps."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ApiConceptCreate(BaseModel):
    """Schema for the API endpoint to manually create a concept."""
    english_term: str = Field(..., description="The primary English term.", min_length=1)
    categories: Optional[List[str]] = Field(None, description="Optional category keys.")
    french_term: Optional[str] = Field(None, description="Optional French term.", min_length=1)
    arabic_term: Optional[str] = Field(None, description="Optional Arabic term.", min_length=1)

class ConceptInDB(ConceptBase):
    """Schema representing the full concept document structure in MongoDB."""
    id: PyObjectId = Field(..., alias="_id", description="Unique MongoDB identifier.")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True, populate_by_name=True, arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )

class ConceptRead(ConceptInDB):
     """Schema for returning a concept via the API."""
     pass # Inherits structure from ConceptInDB

# --- API Input/Output Specific Schemas ---

class KeywordFetchParams(BaseModel):
    """Parameters for the GET /keywords endpoint."""
    lang: Literal[tuple(SUPPORTED_LANGUAGES)] = Field(..., description="Target language code.")
    limit: int = Field(100, gt=0, le=500, description="Maximum keywords to return.")
    min_score: float = Field(settings.KEYWORD_DEACTIVATION_THRESHOLD, ge=0.0, le=1.0, description="Minimum concept confidence score.")

class KeywordFetchItem(BaseModel):
    """Structure for items returned by GET /keywords."""
    term: str = Field(..., description="Keyword/term in the requested language.")
    language: str = Field(..., description="Language code of the term.")
    concept_id: str = Field(..., description="Parent concept's MongoDB ObjectId.")
    concept_display_name: str = Field(..., description="English term of the concept.")

class ConceptFeedbackPayload(BaseModel):
    """Schema for submitting feedback via POST /feedback."""
    concept_id: str = Field(..., description="MongoDB ObjectId of the concept.")
    language: Literal[tuple(SUPPORTED_LANGUAGES)] = Field(..., description="Language of the term generating feedback.")
    relevance_metric: float = Field(..., ge=0.0, le=1.0, description="Relevance metric from ingester.")
    source: str = Field(..., description="Identifier of the ingesting service.", min_length=1)
    term: Optional[str] = Field(None, description="Optional: Specific term used (for verification).")

    @field_validator('concept_id')
    @classmethod
    def validate_objectid_format(cls, v: str) -> str:
        """Validate if concept_id is a proper ObjectId string."""
        if not ObjectId.is_valid(v):
             raise ValueError(f"'{v}' is not a valid MongoDB ObjectId")
        return v

# Helper Schema for Health Check (Defined in main.py now, but could be here)
# class HealthCheckResponse(BaseModel): ...