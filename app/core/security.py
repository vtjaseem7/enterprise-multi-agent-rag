from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.core.config import get_settings

settings = get_settings()
bearer_scheme = HTTPBearer()


class CurrentUser(BaseModel):
    user_id: str
    tenant_id: str
    role: str  # "admin" | "employee" | "customer"
    access_groups: list[str] = []


def create_access_token(user: CurrentUser, expires_minutes: int = 60) -> str:
    """Create a signed JWT containing the user's verified tenant and role."""
    payload = {
        "sub": user.user_id,
        "tenant_id": user.tenant_id,
        "role": user.role,
        "access_groups": user.access_groups,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> CurrentUser:
    """Verify the JWT from the Authorization header and return the CurrentUser."""
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return CurrentUser(
            user_id=payload["sub"],
            tenant_id=payload["tenant_id"],
            role=payload["role"],
            access_groups=payload.get("access_groups", []),
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        )