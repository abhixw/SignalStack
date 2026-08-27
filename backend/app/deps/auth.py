import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pymongo.asynchronous.database import AsyncDatabase

from app.config.database import get_db
from app.services import crud
from app.services.auth import decode_access_token

# tokenUrl is documentation-only here (login takes JSON, not form data) — it just
# tells the OpenAPI UI where to send users for the "Authorize" flow.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncDatabase = Depends(get_db),
) -> dict:
    if not token:
        raise _UNAUTHORIZED
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise _UNAUTHORIZED

    user_id = payload.get("sub")
    if not user_id:
        raise _UNAUTHORIZED

    # get_user_by_id returns None both for a malformed ObjectId and for a
    # genuinely missing user — either way the token is not valid.
    user = await crud.get_user_by_id(db, user_id)
    if not user:
        raise _UNAUTHORIZED
    return user


def require_roles(*roles: str):
    """Dependency factory: 403s any authenticated user not in `roles`."""

    def dependency(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return dependency
