from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends, Header
from sqlalchemy.orm import Session

from common.entity import User
from common.error import AppError, ErrorCode
from shared.config import get_settings
from shared.database import get_database_session

_JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_access_token(user_id: int) -> str:
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(days=settings.jwt_expire_days)
    return jwt.encode({"sub": str(user_id), "exp": expires_at}, settings.jwt_secret, algorithm=_JWT_ALGORITHM)


def _read_user_id(access_token: str) -> int:
    try:
        payload = jwt.decode(access_token, get_settings().jwt_secret, algorithms=[_JWT_ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as error:
        raise AppError(ErrorCode.UNAUTHORIZED) from error


def get_current_user(
    database_session: Annotated[Session, Depends(get_database_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """FastAPI 의존성. `Authorization: Bearer {token}` → User. 실패 시 UNAUTHORIZED."""
    if not authorization or not authorization.startswith("Bearer "):
        raise AppError(ErrorCode.UNAUTHORIZED)
    user = database_session.get(User, _read_user_id(authorization.removeprefix("Bearer ")))
    if user is None:
        raise AppError(ErrorCode.UNAUTHORIZED)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
