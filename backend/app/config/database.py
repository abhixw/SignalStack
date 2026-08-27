import logging
from typing import Optional

from bson import ObjectId
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import PyMongoError

from app.config.config import config

logger = logging.getLogger("signalstack.db")

_client: Optional[AsyncMongoClient] = None
_db: Optional[AsyncDatabase] = None


async def connect_to_mongo() -> None:
    """Create the (single, reused) MongoDB client and run a lightweight
    connectivity check. Called once from the FastAPI lifespan on startup."""
    global _client, _db

    client = AsyncMongoClient(config.MONGODB_URI, serverSelectionTimeoutMS=5000)
    database = client[config.MONGODB_ACTIVE_DATABASE]

    try:
        await client.admin.command("ping")
    except PyMongoError as e:
        logger.error("MongoDB connectivity check failed: %s", e)
        await client.close()
        # Fail startup with a clear message rather than an opaque pymongo traceback,
        # and never let a raw connection-string/credential leak into the error.
        raise RuntimeError(
            "Could not connect to MongoDB. Check MONGODB_URI, network access (IP allowlist "
            "on Atlas), and that the cluster is reachable."
        ) from e

    _client = client
    _db = database
    logger.info("Connected to MongoDB database '%s'", config.MONGODB_ACTIVE_DATABASE)

    await _ensure_indexes(database)


async def close_mongo_connection() -> None:
    global _client, _db
    if _client is not None:
        await _client.close()
        logger.info("MongoDB connection closed")
    _client = None
    _db = None


async def ping() -> bool:
    """Used by GET /health — returns False instead of raising."""
    if _client is None:
        return False
    try:
        await _client.admin.command("ping")
        return True
    except PyMongoError:
        return False


def get_database() -> AsyncDatabase:
    if _db is None:
        raise RuntimeError("Database not initialized — connect_to_mongo() must run before handling requests.")
    return _db


async def get_db() -> AsyncDatabase:
    """FastAPI dependency. Returns the already-connected shared database handle —
    this does NOT open a new connection per request."""
    return get_database()


async def _ensure_indexes(database: AsyncDatabase) -> None:
    await database.users.create_index("email", unique=True)
    # Partial index: most users have no github_id (None) — a plain unique index
    # would reject the second such user as a "duplicate null". This only
    # enforces uniqueness once github_id is an actual linked account.
    await database.users.create_index(
        "github_id", unique=True, partialFilterExpression={"github_id": {"$type": "int"}}
    )

    await database.outcomes.create_index("owner_id")
    await database.outcomes.create_index("is_public")
    await database.outcomes.create_index("created_at")

    await database.proofs.create_index("outcome_id")
    await database.proofs.create_index("candidate_user_id")
    await database.proofs.create_index("created_at")
    # One application per candidate per outcome. Partial (not plain) unique:
    # legacy/edge-case proofs with no candidate_user_id (string, always set by
    # the current app) must not collide with each other on "null".
    await database.proofs.create_index(
        [("outcome_id", 1), ("candidate_user_id", 1)],
        unique=True,
        partialFilterExpression={"candidate_user_id": {"$type": "string"}},
    )

    await database.evaluations.create_index("job_id")
    await database.evaluations.create_index("outcome_id")
    await database.evaluations.create_index("created_at")

    await database.feedback.create_index("evaluation_id")
    await database.feedback.create_index("job_id")
    await database.feedback.create_index("created_at")

    await database.audit_logs.create_index("entity_type")
    await database.audit_logs.create_index("entity_id")
    await database.audit_logs.create_index("created_at")

    await database.signal_weights.create_index([("signal_name", 1), ("task_id", 1)])

    await database.password_resets.create_index("email")
    # TTL index: Mongo automatically deletes a doc once its expires_at is in the
    # past (expireAfterSeconds=0 means "at expires_at", not 0 seconds after insert).
    await database.password_resets.create_index("expires_at", expireAfterSeconds=0)

    await database.oauth_states.create_index("state", unique=True)
    await database.oauth_states.create_index("expires_at", expireAfterSeconds=0)

    await database.github_pending.create_index("pending_token", unique=True)
    await database.github_pending.create_index("expires_at", expireAfterSeconds=0)

    await database.pending_registrations.create_index("registration_id", unique=True)
    await database.pending_registrations.create_index("expires_at", expireAfterSeconds=0)


def oid_str(value) -> Optional[str]:
    """Convert a Mongo _id (ObjectId, or a plain string for collections like
    `outcomes` that use a client-supplied string _id) into a JSON-safe string."""
    if value is None:
        return None
    return str(value)


def to_object_id(value: str) -> ObjectId:
    """Raises bson.errors.InvalidId for a malformed id. Callers must catch this
    (see app/services/mongo_errors.py) and return 400/404, never a raw 500."""
    return ObjectId(value)
