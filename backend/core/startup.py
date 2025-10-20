# core/startup.py
async def ensure_indexes(db):
    await db["curriculum"].create_index("email")
    await db["curriculum"].create_index([("timestamp", -1)])
    await db["perfiles"].create_index([("activo", 1)])
    await db["ranking"].create_index([("perfil_id", 1), ("score", -1)])
    await db["ranking"].create_index([("perfil_id", 1), ("cv_id", 1)], unique=True)
