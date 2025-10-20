from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import AsyncGenerator
from .config import get_settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    """Singleton del cliente Mongo."""
    global _client
    if _client is None:
        cfg = get_settings()
        _client = AsyncIOMotorClient(
            cfg.MONGODB_URI, serverSelectionTimeoutMS=3000)
    return _client


async def get_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """Dependency para usar en endpoints: Depends(get_db)."""
    db = get_client().get_default_database()
    yield db
