# app/db/database.py

import motor.motor_asyncio
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import CollectionInvalid, ConfigurationError, OperationFailure
import logging

# Local imports
from app.core.config import settings, SUPPORTED_LANGUAGES
from app.db.models import TranslationStatus # Use Enum for filters

logger = logging.getLogger(__name__)

class DataBase:
    """Class to hold the MongoDB client and database instances."""
    client: motor.motor_asyncio.AsyncIOMotorClient = None
    db: motor.motor_asyncio.AsyncIOMotorDatabase = None

# Create a singleton instance to hold the database connection details
db_instance = DataBase()

async def get_database() -> motor.motor_asyncio.AsyncIOMotorDatabase:
    """
    Dependency function for FastAPI endpoints to get the database instance.
    Raises a RuntimeError if the database is not initialized.
    """
    if db_instance.db is None:
        logger.error("Database not initialized. get_database() called before connect_to_mongo() completed successfully.")
        raise RuntimeError("Database connection is not available.")
    return db_instance.db

async def connect_to_mongo():
    """
    Establishes the connection to the MongoDB specified in settings.
    Verifies the connection, assigns client/db to singleton, and creates indexes.
    Raises SystemExit if connection or essential setup fails.
    """
    logger.info("Attempting to connect to MongoDB...")
    try:
        # --- ADD THIS LINE FOR DEBUGGING ---
        print(f"DEBUG: Attempting to use MONGO_URI: '{settings.MONGO_URI}'")
        # -------------------------------------

        # Create the Motor client instance
        db_instance.client = motor.motor_asyncio.AsyncIOMotorClient(
            settings.MONGO_URI,
            uuidRepresentation='standard' # Recommended setting
        )
        # Verify the connection by pinging
        await db_instance.client.admin.command('ping')
        # Assign the database object
        db_instance.db = db_instance.client[settings.MONGO_DB_NAME]
        logger.info(f"Successfully connected to MongoDB database: '{settings.MONGO_DB_NAME}'")

        # Create indexes after successful connection
        await create_indexes(db_instance.db)

    except ConfigurationError as e:
         logger.error(f"MongoDB configuration error: {e}. Check MONGO_URI.", exc_info=True)
         raise SystemExit(f"MongoDB configuration error: {e}") from e
    except OperationFailure as e:
         # This will catch authentication errors (like bad username/password)
         # or other command failures during connection setup (like ping).
         logger.error(f"MongoDB command failed during connection setup (e.g., ping, auth): {e.details}", exc_info=True)
         raise SystemExit(f"MongoDB command failed: {e}") from e
    except Exception as e:
        # Catch other potential errors like network issues, DNS resolution, etc.
        logger.error(f"Failed to connect to MongoDB or setup at {settings.MONGO_URI}: {e}", exc_info=True)
        raise SystemExit(f"Could not establish MongoDB connection or setup: {e}") from e


async def close_mongo_connection():
    """Closes the MongoDB client connection if it's open."""
    logger.info("Closing MongoDB connection...")
    if db_instance.client:
        try:
            db_instance.client.close()
            logger.info("MongoDB connection closed successfully.")
        except Exception as e:
            logger.error(f"Error encountered while closing MongoDB connection: {e}", exc_info=True)
        finally:
            db_instance.client = None
            db_instance.db = None
    else:
        logger.info("MongoDB connection was already closed or not established.")


async def create_indexes(database: motor.motor_asyncio.AsyncIOMotorDatabase):
    """
    Creates required indexes for the Concept-Level Metrics model (Option 2).
    Attempts to drop the old incorrect unique index if found.

    Args:
        database: The active Motor database instance.
    """
    if database is None:
         logger.error("Database instance provided to create_indexes is None. Cannot create indexes.")
         return

    try:
        concept_collection = database[settings.MONGO_COLLECTION_CONCEPTS]
        logger.info(f"Checking/Creating indexes for collection: '{settings.MONGO_COLLECTION_CONCEPTS}' (Concept-Level Metrics)...")

        # --- REFACTORED INDEX DEFINITIONS for Option 2 ---
        index_definitions = [
            # 1. Unique index on the English term value directly
            {"keys": [("translations.en", ASCENDING)], "options": {"unique": True, "name": "concept_english_term_unique_idx"}},

            # 2. Index on categories array
            {"keys": [("categories", ASCENDING)], "options": {"name": "concept_categories_idx", "sparse": True}},

            # 3. Compound index for fetching active keywords (based on concept metrics)
            {"keys": [("status", ASCENDING), ("confidence_score", DESCENDING)],
             "options": {"name": "concept_fetch_keywords_idx",
                         "partialFilterExpression": {"status": TranslationStatus.ACTIVE.value}}},

            # 4. Compound index for decay check (based on concept metrics)
            {"keys": [("status", ASCENDING), ("last_positive_feedback_at", ASCENDING)],
             "options": {"name": "concept_decay_check_idx",
                         "partialFilterExpression": {"status": TranslationStatus.ACTIVE.value}}},

            # 5. Index on created_at for sorting list endpoint
            {"keys": [("created_at", DESCENDING)], "options": {"name": "concept_created_at_idx"}},
        ]
        # --- END REFACTORED INDEX DEFINITIONS ---

        # --- Attempt to Drop Old Incorrect Index ---
        # This index was based on the Option 1 schema (nested term object)
        old_index_name_option1 = "english_term_unique_idx"
        try:
            existing_indexes_info = await concept_collection.index_information()
            if old_index_name_option1 in existing_indexes_info:
                 # Check if the keys match the *old* schema's index definition
                 old_index_keys = existing_indexes_info[old_index_name_option1].get('key')
                 # Expected old key format: [('translations.en.term', 1)]
                 if old_index_keys and len(old_index_keys) == 1 and old_index_keys[0][0] == 'translations.en.term':
                     logger.warning(f"Found old index '{old_index_name_option1}' on 'translations.en.term'. Attempting to drop...")
                     await concept_collection.drop_index(old_index_name_option1)
                     logger.info(f"Successfully dropped old index: {old_index_name_option1}")
                 else:
                      logger.debug(f"Index named '{old_index_name_option1}' exists but does not match expected old key structure. Skipping drop.")

        except OperationFailure as e:
            # May fail if index doesn't exist or due to permissions, log but continue
            logger.warning(f"Could not drop potential old index '{old_index_name_option1}' (may not exist or error): {e}")
        except Exception as e:
             logger.error(f"Unexpected error checking/dropping old index '{old_index_name_option1}': {e}", exc_info=True)
        # --- End Drop Old Index ---


        # --- Create New Indexes ---
        # Refresh index info after potential drop
        existing_indexes = await concept_collection.index_information()
        existing_index_names = list(existing_indexes.keys())
        logger.debug(f"Existing indexes after potential drop: {existing_index_names}")

        created_count = 0
        for index_def in index_definitions:
            index_name = index_def["options"]["name"]
            target_keys = index_def["keys"]

            # Check if index with this name exists
            if index_name not in existing_index_names:
                 # If name doesn't exist, check if index with *same keys* exists under different name
                 key_exists_different_name = False
                 for name, info in existing_indexes.items():
                     # Compare keys as tuples for reliable comparison
                     current_index_keys_tuple = tuple(tuple(item) for item in info['key'])
                     target_keys_tuple = tuple(tuple(item) for item in target_keys)
                     if current_index_keys_tuple == target_keys_tuple:
                         key_exists_different_name = True
                         logger.warning(f"Index with keys {target_keys} already exists but under a different name ('{name}'). Skipping creation of '{index_name}'.")
                         break # Found matching keys, no need to create

                 if not key_exists_different_name:
                     # Attempt to create the index
                     try:
                         await concept_collection.create_index(target_keys, **index_def["options"])
                         logger.info(f"Successfully created index: {index_name}")
                         created_count += 1
                     except OperationFailure as e:
                          # Handle specific conflicts if creation fails
                          if e.code in [85, 86]: # IndexOptionsConflict or IndexKeySpecsConflict/NameClash
                               logger.warning(f"Index '{index_name}' conflicted with existing index. Check MongoDB. Error: {e.details.get('errmsg')}")
                          else: # Log other operational failures more seriously
                               logger.error(f"Operation failure creating index '{index_name}': {e}", exc_info=True)
                     except Exception as e: # Catch any other error during creation
                          logger.error(f"Unexpected error creating index '{index_name}': {e}", exc_info=True)
            else:
                 logger.debug(f"Index '{index_name}' already exists.")

        logger.info(f"Finished checking/creating indexes. {created_count} new indexes created.")

    except Exception as e:
        # Catch errors during initial connection or index listing
        logger.error(f"Unexpected error during index setup process: {e}", exc_info=True)