# auth/routes/auth_router.py
import datetime
from time import timezone
from fastapi import APIRouter, Depends, HTTPException, Response, status
import jwt
from pydantic import BaseModel, EmailStr, Field
from core.database import get_db
from auth.services.auth_service import authenticate_user, create_access_token, get_current_user, oauth2_scheme
import user
from user.models.user import User
from user.schemas.user import UserCreate, UserSchema
from core.config import get_settings
from user.services.user_service import create_user
from typing import Any
from fastapi.security import OAuth2PasswordRequestForm

auth_router = APIRouter(prefix="/auth", tags=["auth"])

# auth/routes/auth_router.py (login)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    email: EmailStr
    password: str = Field(min_length=6)


@auth_router.post("/login")
async def login(payload: LoginRequest, db=Depends(get_db)) -> dict[str, Any]:
    cfg = get_settings()
    email = payload.email.strip().lower()
    user = await authenticate_user(db, email, payload.password)
    if not user or not user.is_active:
        # mensaje genérico para evitar user-enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    token = create_access_token(user.id)  # preferimos id, no email
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": cfg.JWT_ACCESS_EXPIRES_MIN * 60,  # segundos
    }


@auth_router.post("/register", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db=Depends(get_db)):
    try:
        # <-- PASAR EL PAYLOAD (no args sueltos)
        user = await create_user(db, payload)
        return user
    except ValueError as ex:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))


async def login_token(form: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)):
    email = form.username.strip().lower()  # aquí username es tu email
    user = await authenticate_user(db, email, form.password)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    token = create_access_token(user.id)
    return {"access_token": token, "token_type": "bearer"}


@auth_router.post("/logout", status_code=204)
async def logout(token: str = Depends(oauth2_scheme), db=Depends(get_db)):
    cfg = get_settings()
    try:
        payload = jwt.decode(token, cfg.JWT_SECRET_KEY, algorithms=[
                             getattr(cfg, "JWT_ALGORITHM", "HS256")])
    except jwt.ExpiredSignatureError:
        return Response(status_code=204)
    except jwt.InvalidTokenError:
        return Response(status_code=204)

    jti = payload.get("jti")
    exp = payload.get("exp")
    if not jti or not exp:
        return Response(status_code=204)

    exp_dt = datetime.fromtimestamp(int(exp), tz=timezone.utc)
    await db["revoked_tokens"].update_one({"jti": jti}, {"$set": {"jti": jti, "exp": exp_dt}}, upsert=True)
    return Response(status_code=204)


@auth_router.post("/token")
async def login_token(
    form: OAuth2PasswordRequestForm = Depends(),
    db=Depends(get_db),
) -> dict[str, Any]:
    cfg = get_settings()
    email = form.username.strip().lower()
    user = await authenticate_user(db, email, form.password)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    token = create_access_token(
        user.id, token_version=getattr(user, "token_version", 0))
    return {
        "access_token": token,
        "token_type": "bearer",
        # segundos (opcional)
        "expires_in": getattr(cfg, "JWT_ACCESS_EXPIRES_MIN", 30) * 60,
    }
