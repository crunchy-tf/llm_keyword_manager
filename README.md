# Minbar Keyword Manager

A FastAPI microservice designed to manage health-related keywords for the Minbar project. It uses concept-level metrics, integrates with Google Gemini for keyword generation and translation, handles relevance feedback, and manages keyword lifecycle through scoring and decay mechanisms.

## Features

*   **Concept-Level Management:** Tracks keywords grouped by underlying health concepts.
*   **LLM Integration (Google Gemini):**
    *   Generates new concept keywords based on health topics.
    *   Optionally uses context snippets (`context_data/`) for more targeted generation.
    *   Translates terms between supported languages (English, French, Arabic).
*   **API Endpoints:** Provides RESTful endpoints for managing concepts, fetching keywords, submitting feedback, and monitoring health (see [API Documentation](#api-documentation) below).
*   **Concept Lifecycle Management:**
    *   **Scoring:** Concepts have a `confidence_score` based on feedback and time.
    *   **Feedback Loop:** `POST /feedback` updates `confidence_score` and `historical_yield`.
    *   **Status:** Concepts can be `active` or `inactive` based on score thresholds.
    *   **Decay:** Confidence scores decay over time if no positive feedback is received (configurable).
*   **Background Tasks (APScheduler):**
    *   Periodically generates new concepts.
    *   Periodically applies confidence score decay.
*   **Configuration:** Driven by environment variables (`.env` file).
*   **Asynchronous:** Built with FastAPI and Motor for non-blocking performance.
*   **Rate Limiting:** Implements delays to respect configured Gemini API RPM limits.

## Architecture Overview

The application follows a standard layered architecture:

*   **`main.py`**: Entry point, FastAPI app setup, lifespan management (DB connection, scheduler start/stop), root endpoint, basic middleware (CORS), exception handlers.
*   **`api/`**: Handles HTTP requests and responses.
    *   **`endpoints/`**: Defines API routes (`APIRouter`).
    *   **`schemas.py`**: Pydantic models for request/response validation and data structuring.
    *   **`utils.py`**: API-specific utilities (e.g., `PyObjectId`).
*   **`services/`**: Contains the core business logic.
    *   **`concept_service.py`**: Orchestrates concept creation, feedback processing, generation logic, and decay.
    *   **`llm_service.py`**: Interacts with the Google Gemini API for generation and translation, including rate limiting.
    *   **`scheduler_service.py`**: Manages background tasks using APScheduler.
*   **`db/`**: Handles database interactions (MongoDB).
    *   **`database.py`**: Manages DB connection pool, provides DB access, creates indexes.
    *   **`crud.py`**: Implements Create, Read, Update, Delete operations on the database.
    *   **`models.py`**: Defines database-related enums (e.g., `TranslationStatus`).
*   **`core/`**: Application configuration.
    *   **`config.py`**: Loads settings from environment variables using Pydantic Settings.
*   **`prompts/`**: Stores LLM prompt templates and related static data (e.g., `HEALTH_TOPICS`).
*   **`context_data/`**: Contains `.txt` files used as optional context for LLM generation.

    


      
## Technology Stack

*   **Backend Framework:** FastAPI
*   **ASGI Server:** Uvicorn
*   **Database:** MongoDB (accessed via Motor async driver)
*   **Data Validation:** Pydantic
*   **Configuration:** Pydantic-Settings, python-dotenv
*   **LLM:** Google Gemini API (via `google-generativeai` SDK)
*   **Background Tasks:** APScheduler
*   **Containerization:** Docker

## Prerequisites

*   **Python:** 3.10+
*   **MongoDB:** A running instance (local install or Docker recommended for local setup).
*   **Git:** For cloning the repository.
*   **Google Gemini API Key:** Obtainable from Google AI Studio or Google Cloud Console.

## Setup and Installation (Local)

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd keyword_manager
    ```

2.  **Create and Activate Virtual Environment:**
    ```bash
    # Create
    python -m venv venv
    # Activate (Linux/macOS)
    source venv/bin/activate
    # Activate (Windows)
    .\venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    *   Copy the example file: `cp .env.example .env`
    *   Edit the `.env` file:
        *   **`GEMINI_API_KEY`**: **REQUIRED**. Enter your Google Gemini API key.
        *   **`MONGO_URI`**: Ensure this points to your running MongoDB instance (e.g., `mongodb://localhost:27017` for default local/Docker).
        *   **`GEMINI_RPM_LIMIT`**: Set the Requests Per Minute limit according to your Gemini API tier (default is 15 for free tier). The app calculates the delay needed.
        *   Review other variables like `MONGO_DB_NAME`, `SCHEDULER_INTERVAL_MINUTES`, etc., and adjust if necessary.

5.  **Ensure MongoDB is Running:**
    *   Start your local MongoDB service.
    *   *Or*, if using Docker: `docker run -d -p 27017:27017 --name local-mongo mongo:latest`

## Running the Application (Local)

Once setup is complete and MongoDB is running:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

    


    --reload: Enables auto-reload on code changes (for development).

    --host 0.0.0.0: Makes the server accessible on your network.

    --port 8000: Runs the server on port 8000.

Accessing the Application:

    API Docs (Swagger UI): http://localhost:8000/docs

    API Docs (ReDoc): http://localhost:8000/redoc

    Health Check: http://localhost:8000/health

    Root Endpoint: http://localhost:8000/

Running with Docker

    Build the Docker Image:

          
    docker build -t keyword-manager .

        


Run the Docker Container:

    Ensure MongoDB is Accessible: The container needs to connect to MongoDB. You can run MongoDB in another Docker container on the same Docker network, connect to a host instance, or use Docker Compose (recommended).

    Provide Environment Variables: Use the --env-file flag with your configured .env file.

    Map the Port: Expose port 8000.

      
# Example assuming MongoDB is accessible and .env is configured
docker run -d -p 8000:8000 --env-file .env --name keyword-manager-app keyword-manager

    Adjust MONGO_URI in your .env file as needed depending on how MongoDB is hosted relative to the container (e.g., use the service name if using Docker Compose, or host.docker.internal for host access on some systems).

API Documentation

The API provides endpoints for managing concepts, submitting feedback, fetching keywords, and checking service health.

Base Path: /api/v1

Authentication: None (currently).

Interactive Docs: For detailed request/response models and trying out the API, access the Swagger UI at /docs or ReDoc at /redoc when the service is running.

Common Responses:

    200 OK: Standard success response for GET requests or updates.

    201 Created: Success response for resource creation (e.g., POST /concepts).

    202 Accepted: Indicates a background task has been successfully initiated (e.g., POST /concepts/generate).

    404 Not Found: The requested resource (e.g., a specific concept) could not be found.

    409 Conflict: Attempted to create a resource that already exists (e.g., duplicate English term).

    422 Unprocessable Entity: Request data failed validation (e.g., invalid format, missing required fields, invalid parameter values). The response body often contains details about the validation error.

    500 Internal Server Error: An unexpected error occurred on the server. Check server logs for details.

    503 Service Unavailable: A required downstream service (e.g., Database, LLM) might be temporarily unavailable (primarily indicated by the /health endpoint).

Concepts & Feedback

These endpoints manage the lifecycle of health concepts.

1. Create Concept Manually

    Endpoint: POST /concepts

    Summary: Manually adds a new concept based on provided terms. Primarily useful for seeding specific concepts or correcting LLM omissions.

    Request Body: (application/json) Based on ApiConceptCreate schema.

        english_term (string, required): The primary English term for the concept.

        categories (List[string], optional): List of associated health topic category keys (from HEALTH_TOPICS).

        french_term (string, optional): The corresponding French term.

        arabic_term (string, optional): The corresponding Arabic term.

    Success Response (201 Created): Body contains the newly created concept as a ConceptRead object (includes _id, timestamps, default scores, provided translations, etc.).

    Error Responses: 409 Conflict, 422 Unprocessable Entity, 500 Internal Server Error.

2. List Concepts

    Endpoint: GET /concepts

    Summary: Retrieves a paginated list of all concepts, sorted by creation date descending.

    Query Parameters:

        skip (integer, optional, default: 0): Number of concepts to skip for pagination.

        limit (integer, optional, default: 100, max: 500): Maximum number of concepts to return.

    Success Response (200 OK): Body contains a JSON list of ConceptRead objects. Each object represents a full concept document.

    Error Responses: 422 Unprocessable Entity, 500 Internal Server Error.

3. Get Concept by ID

    Endpoint: GET /concepts/{concept_id}

    Summary: Retrieves a single concept by its unique MongoDB ObjectId.

    Path Parameter:

        concept_id (string, required): The MongoDB ObjectId of the concept.

    Success Response (200 OK): Body contains the requested concept as a ConceptRead object.

    Error Responses: 404 Not Found, 422 Unprocessable Entity (if concept_id is not a valid ObjectId format), 500 Internal Server Error.

4. Submit Feedback

    Endpoint: POST /feedback

    Summary: Submits relevance feedback from an ingesting service for a specific concept/term usage. Updates the concept's confidence_score, historical_yield, usage_count, last_used_at, and potentially status and last_positive_feedback_at.

    Request Body: (application/json) Based on ConceptFeedbackPayload schema.

        concept_id (string, required): The MongoDB ObjectId of the concept receiving feedback.

        language (string, required, enum: en, fr, ar): The language code of the term that generated the feedback.

        relevance_metric (float, required, range: 0.0 to 1.0): The relevance score provided by the ingester.

        source (string, required, min_length: 1): An identifier for the service providing the feedback.

        term (string, optional): The specific term used (for logging/verification, not strictly required for processing).

    Success Response (200 OK): Body contains the updated concept as a ConceptRead object, reflecting the new scores and potentially status.

    Error Responses: 404 Not Found, 422 Unprocessable Entity, 500 Internal Server Error.

5. Trigger Background Concept Generation

    Endpoint: POST /concepts/generate

    Summary: Manually triggers a background task to generate new concepts using the LLM. The task will run asynchronously.

    Query Parameter:

        category (string, optional): If provided, must be a valid key from HEALTH_TOPICS. Generation will focus on this category (potentially using context from context_data/). If omitted, a random category is chosen.

    Success Response (202 Accepted): Body contains a simple confirmation message: {"message": "Concept generation task added for category: <category_name>."}. This only confirms the task was queued, not that it completed successfully.

    Error Responses: 422 Unprocessable Entity (if category is provided but invalid), 500 Internal Server Error.

Keyword Fetching

This endpoint is used by ingesting services to retrieve relevant keywords.

1. Fetch Active Keywords

    Endpoint: GET /keywords

    Summary: Retrieves a list of keyword terms for active concepts, filtered by language and minimum confidence score, sorted by score descending. Designed to provide high-priority terms for data ingestion.

    Query Parameters: (Validated via KeywordFetchParams schema)

        lang (string, required, enum: en, fr, ar): The target language code for the keywords.

        limit (integer, optional, default: 100, range: 1-500): Maximum number of keyword items to return.

        min_score (float, optional, default: configured KEYWORD_DEACTIVATION_THRESHOLD, range: 0.0 to 1.0): Minimum confidence_score a concept must have to be included.

    Success Response (200 OK): Body contains a JSON list of KeywordFetchItem objects. Each item includes:

        term (string): The keyword in the requested language.

        language (string): The language code requested.

        concept_id (string): The ObjectId of the parent concept.

        concept_display_name (string): The English term of the parent concept (for context).

    Error Responses: 422 Unprocessable Entity, 500 Internal Server Error.

Service Health & Root

1. Health Check

    Endpoint: GET /health (No /api/v1 prefix)

    Summary: Performs basic checks on essential service components (Database connection, Scheduler status, LLM service availability).

    Success Response (200 OK / 503 Service Unavailable): Body contains a JSON object detailing the status of each component:

        status ("ok" or "error"): Overall service status based on components.

        database (string): Status of the database connection (e.g., "connected", "connection_failed", "not_initialized").

        scheduler (string): Status of the background task scheduler ("running" or "stopped").

        llm_service (string): Status of the LLM service initialization ("available" or "unavailable").
        The overall HTTP status code will be 200 if status is "ok", otherwise 503.

2. Root Endpoint

    Endpoint: GET / (No /api/v1 prefix)

    Summary: Simple welcome message endpoint.

    Success Response (200 OK): {"message": "Welcome to Minbar Keyword Manager"}

Background Tasks

The application uses APScheduler to run periodic background tasks defined in app/services/scheduler_service.py:

    Concept Generation: Calls concept_service.generate_and_store_concepts() to discover and store new concepts using the LLM. This involves selecting a topic (randomly or specified), generating potential terms in a target language, translating them to English (as an anchor) and other supported languages, and creating/updating concept documents in the database.

    Confidence Decay: Calls concept_service.apply_confidence_decay() to reduce the score of concepts that haven't received positive feedback recently. Concepts falling below the KEYWORD_DEACTIVATION_THRESHOLD may become inactive.

The interval for these tasks is configured by SCHEDULER_INTERVAL_MINUTES in the .env file (default: 60 minutes).
Context Data (context_data/)

The context_data/ directory can hold .txt files. If a file exists whose name matches a key in the HEALTH_TOPICS dictionary (defined in app/prompts/templates.py), its content will be used as additional context when the LLM is asked to generate keywords for that specific health topic. This can be triggered via the POST /concepts/generate?category=<category_key> endpoint or when that category is randomly selected by the scheduler's generation task.

This allows for generating keywords that are more relevant to specific, observed online discussions or documents related to a topic. If no context file is found for a category, the LLM generates keywords based solely on the topic description provided in HEALTH_TOPICS. Ensure context files contain relevant text snippets (e.g., simulated headlines, social media posts) for best results.