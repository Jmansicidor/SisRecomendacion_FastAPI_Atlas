# user/services/user_service.py
# Schemas de IO (sin password)
from user.schemas.user import UserSchema, UserCreate
# Modelo interno (incluye password_hash)
from user.models.user import User, Role
from passlib.context import CryptContext
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import Optional, List

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)

# ------------------ Helpers de mapeo ------------------


def _doc_to_user(doc: dict) -> User:
    """Devuelve el modelo interno User (con password_hash)."""
    return User(
        id=str(doc.get("_id")),
        username=doc["username"],
        email=doc["email"],
        password_hash=doc["password_hash"],
        is_active=doc.get("is_active", True),
        roles=[Role(r) for r in doc.get("roles", ["user"])],
    )


def _doc_to_userschema(doc: dict) -> UserSchema:
    """Devuelve el schema público UserSchema (sin password)."""
    return UserSchema(
        id=str(doc.get("_id")),
        username=doc["username"],
        email=doc["email"],
        is_active=doc.get("is_active", True),
        roles=[Role(r) for r in doc.get("roles", ["user"])],
    )

# ------------------ Queries para Auth ------------------


async def get_user_by_email(db: AsyncIOMotorDatabase, email: str) -> Optional[User]:
    doc = await db["users"].find_one({"email": email})
    return _doc_to_user(doc) if doc else None


async def get_user_by_id(db: AsyncIOMotorDatabase, user_id: str) -> Optional[User]:
    try:
        _id = ObjectId(user_id)
    except Exception:
        return None
    doc = await db["users"].find_one({"_id": _id})
    return _doc_to_user(doc) if doc else None

# ------------------ Funciones usadas por el router ------------------


async def get_users(db: AsyncIOMotorDatabase) -> List[UserSchema]:
    cursor = db["users"].find({}, {"password_hash": 0})
    items: List[UserSchema] = []
    async for doc in cursor:
        items.append(_doc_to_userschema(doc))
    return items


async def get_user(db: AsyncIOMotorDatabase, user_id: str) -> Optional[UserSchema]:

    doc = None
    try:
        _id = ObjectId(user_id)
        doc = await db["users"].find_one({"_id": _id}, {"password_hash": 0})
    except Exception:

        doc = await db["users"].find_one({"email": user_id}, {"password_hash": 0})

    return _doc_to_userschema(doc) if doc else None


async def delete_user(db: AsyncIOMotorDatabase, user_id: str) -> bool:
    try:
        _id = ObjectId(user_id)
    except Exception:
        # Si te interesa permitir borrar por email:
        res = await db["users"].delete_one({"email": user_id})
        return res.deleted_count == 1

    res = await db["users"].delete_one({"_id": _id})
    return res.deleted_count == 1


async def create_user(db: AsyncIOMotorDatabase, payload: UserCreate) -> UserSchema:
    # Unicidad por email (y opcionalmente username)
    existing = await db["users"].find_one({"email": payload.email})
    if existing:
        raise ValueError("El email ya está registrado")

    # (Opcional) verificar username único:
    existing_username = await db["users"].find_one({"username": payload.username})
    if existing_username:
        raise ValueError("El username ya está en uso")

    pw_hash = hash_password(payload.password)
    doc = {
        "username": payload.username,
        "email": payload.email,
        "password_hash": pw_hash,
        "is_active": True,
        "roles": ["user"],
    }
    res = await db["users"].insert_one(doc)
    doc["_id"] = res.inserted_id
    # devolvemos schema público (sin password)
    return _doc_to_userschema(doc)


async def add_role(db: AsyncIOMotorDatabase, user_id: str, role: Role) -> bool:
    try:
        oid = ObjectId(user_id)
    except Exception:
        return False
    res = await db["users"].update_one({"_id": oid}, {"$addToSet": {"roles": role.value}})
    return res.modified_count == 1


async def remove_role(db: AsyncIOMotorDatabase, user_id: str, role: Role) -> bool:
    try:
        oid = ObjectId(user_id)
    except Exception:
        return False
    res = await db["users"].update_one({"_id": oid}, {"$pull": {"roles": role.value}})
    return res.modified_count == 1
