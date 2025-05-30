# Minbar Keyword Manager

Keyword Manager microservice using concept-level metrics and Google Gemini.

This service allows for manual creation and management of health-related concepts, processes feedback on their relevance, and provides keywords for ingestion by other services. It also includes scheduled background tasks for automatic concept generation and confidence decay.

## API Endpoints

The base path for all versioned API endpoints is `/api/v1`.

---

### Root

#### `GET /`
-   **Description**: Retrieves a welcome message for the service.
-   **Sample Request**:
    ```http
    GET /
    ```

---

### Health Check

#### `GET /health`
-   **Description**: Performs basic health checks for critical service components, including the database connection, scheduler status, and LLM service availability.
-   **Sample Request**:
    ```http
    GET /health
    ```

---

### Concepts & Feedback

These endpoints are prefixed with `/api/v1`.

#### `POST /concepts`
-   **Description**: Manually creates a new health concept.
-   **Sample Request Body** (Minimal - only required fields):
    ```http
    POST /api/v1/concepts
    Content-Type: application/json

    {
      "english_term": "headache"
    }
    ```
-   **Sample Request Body** (With optional fields):
    ```http
    POST /api/v1/concepts
    Content-Type: application/json

    {
      "english_term": "common cold",
      "categories": ["respiratory_illness"],
      "french_term": "rhume",
      "arabic_term": "الزكام"
    }
    ```

#### `GET /concepts`
-   **Description**: Retrieves a paginated list of all concepts.
-   **Query Parameters**:
    -   `skip` (integer, optional, default: 0): Number of concepts to skip for pagination.
    -   `limit` (integer, optional, default: 100): Maximum number of concepts to return.
-   **Sample Request**:
    ```http
    GET /api/v1/concepts?skip=0&limit=10
    ```
-   **Minimal Sample Request** (uses default pagination):
    ```http
    GET /api/v1/concepts
    ```

#### `GET /concepts/{concept_id}`
-   **Description**: Retrieves a single concept by its unique MongoDB ObjectId.
-   **Path Parameters**:
    -   `concept_id` (string, required): The MongoDB ObjectId of the concept.
-   **Sample Request**:
    ```http
    GET /api/v1/concepts/66243f8a1d5b8e9f7a0c1d2e
    ```

#### `POST /feedback`
-   **Description**: Submits relevance feedback for a given concept, which updates its metrics.
-   **Supported Languages** for `language` field: "en", "fr", "ar".
-   **Sample Request Body** (Minimal - required fields):
    ```http
    POST /api/v1/feedback
    Content-Type: application/json

    {
      "concept_id": "66243f8a1d5b8e9f7a0c1d2e",
      "language": "en",
      "relevance_metric": 0.9,
      "source": "news_ingester_v1"
    }
    ```
-   **Sample Request Body** (With optional `term` field):
    ```http
    POST /api/v1/feedback
    Content-Type: application/json

    {
      "concept_id": "66243f8a1d5b8e9f7a0c1d2e",
      "language": "en",
      "relevance_metric": 0.9,
      "source": "news_ingester_v1",
      "term": "flu symptoms"
    }
    ```

#### `POST /concepts/generate`
-   **Description**: Triggers a background task to generate new concepts, optionally for a specific health category.
-   **Query Parameters**:
    -   `category` (string, optional): A specific health topic category key to generate concepts for. If omitted, a random category is chosen.
-   **Sample Request** (for a specific category):
    ```http
    POST /api/v1/concepts/generate?category=mental_health
    ```
-   **Minimal Sample Request** (uses a random category):
    ```http
    POST /api/v1/concepts/generate
    ```

---

### Keyword Fetching

These endpoints are prefixed with `/api/v1`.

#### `GET /keywords`
-   **Description**: Retrieves a list of active keywords (terms) in a specified language, filtered by a minimum concept confidence score and sorted by score.
-   **Query Parameters**:
    -   `lang` (string, required): Target language code for the keywords. Supported: "en", "fr", "ar".
    -   `limit` (integer, optional, default: 100): Maximum number of keywords to return.
    -   `min_score` (float, optional, default: 0.2): Minimum concept confidence score for a keyword's parent concept to be included.
-   **Sample Request**:
    ```http
    GET /api/v1/keywords?lang=fr&limit=50&min_score=0.5
    ```
-   **Minimal Sample Request** (uses default `limit` and `min_score`):
    ```http
    GET /api/v1/keywords?lang=en
    ```

---