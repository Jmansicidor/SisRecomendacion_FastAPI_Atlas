# metricas/routes/metricas_router.py
from fastapi import APIRouter, Depends, Query
from core.database import get_db

from metricas.services.rebuild import rebuild_ranking_for_profile
from fastapi import HTTPException

metricas_router = APIRouter(prefix="/metricas", tags=["metricas"])


# 1) RANKING PERSISTIDO
@metricas_router.get("/ranking", response_model=dict)
async def get_ranking(perfil_id: str | None = None,
                      limit: int = Query(100, ge=1, le=1000),
                      db=Depends(get_db)):
    if not perfil_id:
        perf = await db["perfiles"].find_one({"activo": True}, projection={"_id": 1})
        if not perf:
            raise HTTPException(status_code=404, detail="No hay perfil activo")
        perfil_id = str(perf["_id"])

    cur = db["ranking"].find({"perfil_id": perfil_id}).sort(
        "score", -1).limit(limit)
    rows = await cur.to_list(length=limit)

    items = [{
        "cv_id": r["cv_id"],
        "score": float(r["score"]),
        "score_cos": float(r.get("score_cos", 0.0)),
        "score_j_total": float(r.get("score_j_total", 0.0)),
        "nombre": (r.get("snapshot") or {}).get("nombre"),
        "apellido": (r.get("snapshot") or {}).get("apellido"),
        "email": (r.get("snapshot") or {}).get("email"),
    } for r in rows]

    return {"perfil_id": perfil_id, "count": len(items), "items": items}


@metricas_router.post("/ranking/rebuild", response_model=dict)
async def rebuild(perfil_id: str | None = None, db=Depends(get_db)):
    if not perfil_id:
        perf = await db["perfiles"].find_one({"activo": True}, projection={"_id": 1})
        if not perf:
            raise HTTPException(status_code=404, detail="No hay perfil activo")
        perfil_id = str(perf["_id"])
    updated = await rebuild_ranking_for_profile(db, perfil_id)
    return {"perfil_id": perfil_id, "updated": updated}
