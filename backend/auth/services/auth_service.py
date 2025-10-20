# auth/services/auth_service.py
from datetime import datetime, timedelta, timezone
import uuid
import jwt
from core.config import get_settings
from user.models.user import User
from user.services.user_service import verify_password
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from core.database import get_db

from user.services.user_service import get_user_by_email, get_user_by_id, verify_password


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


async def authenticate_user(db, email: str, password: str):
    from user.services.user_service import get_user_by_email
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db=Depends(get_db),
) -> User:
    cfg = get_settings()
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, cfg.JWT_SECRET_KEY, algorithms=[
                             getattr(cfg, "JWT_ALGORITHM", "HS256")])
        sub = payload.get("sub")
        jti = payload.get("jti")
        v = payload.get("v", 0)
        if sub is None or jti is None:
            raise credentials_exc

        # 1) ¿Token revocado?
        if await db["revoked_tokens"].find_one({"jti": jti}):
            raise credentials_exc

        # 2) ¿Usuario existe y versión vigente?
        user = await get_user_by_id(db, sub) or await get_user_by_email(db, sub)
        if user is None or not user.is_active:
            raise credentials_exc
        if v != getattr(user, "token_version", 0):
            # versión cambió -> tokens viejos quedan inválidos
            raise credentials_exc

        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired", headers={
                            "WWW-Authenticate": "Bearer"})
    except jwt.InvalidTokenError:
        raise credentials_exc


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user


def create_access_token(subject: str, token_version: int = 0) -> str:
    cfg = get_settings()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=getattr(cfg, "JWT_ACCESS_EXPIRES_MIN", 30))
    payload = {
        "sub": subject,
        # opcional para logout por token
        "jti": uuid.uuid4().hex,
        # versión del usuario (logout-all)
        "v": token_version,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    algorithm = getattr(cfg, "JWT_ALGORITHM", "HS256")
    return jwt.encode(payload, cfg.JWT_SECRET_KEY, algorithm=algorithm)
