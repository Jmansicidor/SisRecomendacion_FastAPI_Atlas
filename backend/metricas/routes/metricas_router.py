# metricas/routes/metricas_router.py
from fastapi import APIRouter, Depends, Query
from core.database import get_db
from motor.motor_asyncio import AsyncIOMotorDatabase
from metricas.services.rebuild import rebuild_ranking_for_profile
from fastapi import HTTPException
from bson import ObjectId
from auth.utils.permissions import require_admin

metricas_router = APIRouter(prefix="/metricas", tags=["metricas"])


@metricas_router.get("/ranking", dependencies=[Depends(require_admin())])
async def get_ranking(
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    perfil_id: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    # 🔍 1) Determinar perfil activo si no se pasa perfil_id
    if not perfil_id:
        perfil_doc = await db["perfiles"].find_one({"activo": True})
        if not perfil_doc:
            return {"perfil_id": None, "count": 0, "items": []}
        perfil_id = str(perfil_doc["_id"])

    # 🔎 2) Filtro siempre por perfil_id
    q = {"perfil_id": perfil_id}

    # 3️⃣ Proyección base
    projection = {
        "_id": 0,
        "perfil_id": 1,
        "cv_id": 1,
        "score": 1,
        "score_cos": 1,
        "score_j_total": 1,
        "snapshot": 1,
    }

    cur = db["ranking"].find(q, projection=projection).skip(skip).limit(limit)

    items = []
    async for r in cur:
        snap = (r.get("snapshot") or {}) if isinstance(
            r.get("snapshot"), dict) else {}

        # 🔧 Enriquecer snapshot si falta cv_file_id o datos básicos
        if not snap.get("cv_file_id"):
            cv = await db["curriculum"].find_one(
                {"_id": ObjectId(r["cv_id"])},
                projection={"cv_file_id": 1, "nombre": 1,
                            "apellido": 1, "email": 1},
            )
            if cv:
                snap.setdefault("cv_file_id", cv.get("cv_file_id"))
                snap.setdefault("nombre", cv.get("nombre"))
                snap.setdefault("apellido", cv.get("apellido"))
                snap.setdefault("email", cv.get("email"))

        items.append({
            "cv_id": r.get("cv_id"),
            "perfil_id": perfil_id,
            "score": float(r.get("score", 0)),
            "score_cos": float(r.get("score_cos", 0)),
            "score_j_total": float(r.get("score_j_total", 0)),
            "nombre": snap.get("nombre"),
            "apellido": snap.get("apellido"),
            "email": snap.get("email"),
            "cv_file_id": snap.get("cv_file_id"),  # 👈 necesario para descarga
        })

    count = await db["ranking"].count_documents(q)

    return {
        "perfil_id": perfil_id,
        "count": count,
        "items": items,
    }


@metricas_router.post("/ranking/rebuild", response_model=dict)
async def rebuild(perfil_id: str | None = None, db=Depends(get_db)):
    if not perfil_id:
        perf = await db["perfiles"].find_one({"activo": True}, projection={"_id": 1})
        if not perf:
            raise HTTPException(status_code=404, detail="No hay perfil activo")
        perfil_id = str(perf["_id"])
    updated = await rebuild_ranking_for_profile(db, perfil_id)
    return {"perfil_id": perfil_id, "updated": updated}
