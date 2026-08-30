import logging

from bson.errors import InvalidId
from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError, PyMongoError

logger = logging.getLogger("recruvoskill.mongo")


def resource_not_found(name: str = "Resource") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{name} not found")


def invalid_id(name: str = "id") -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {name}")


def safe_object_id(value: str, name: str = "id"):
    """bson.ObjectId(value) but raising a clean 400 instead of leaking bson's
    raw InvalidId message/traceback to the client."""
    from app.config.database import to_object_id

    try:
        return to_object_id(value)
    except (InvalidId, TypeError):
        raise invalid_id(name)


def to_http_error(e: Exception) -> HTTPException:
    """Map a PyMongo exception to a clean, non-leaking HTTP error. The real
    exception (which may include connection strings/hosts) is always logged
    server-side only — never included in the response body."""
    if isinstance(e, DuplicateKeyError):
        logger.warning("Duplicate key error: %s", e)
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Resource already exists.")
    if isinstance(e, PyMongoError):
        logger.error("MongoDB operation failed: %s", e)
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database temporarily unavailable.")
    logger.error("Unexpected error during a database operation: %s", e)
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
