# perfil/routes/perfil_router.py
from fastapi import APIRouter, Depends, HTTPException
from perfil.schemas.perfil_schemas import PerfilCreate, PerfilOut
from perfil.services.perfil_service import guardar_perfil, obtener_perfil_activo
from core.database import get_db
from bson import ObjectId
from auth.utils.permissions import require_admin

perfil_router = APIRouter(prefix="/perfil", tags=["perfil"])


@perfil_router.post("/", response_model=dict)
async def crear_perfil(payload: PerfilCreate, db=Depends(get_db)):
    _id = await guardar_perfil(db, payload.model_dump())
    return {"id": _id}


@perfil_router.get("/activo", response_model=PerfilOut | dict)
async def get_perfil_activo(db=Depends(get_db)):
    doc = await obtener_perfil_activo(db)
    if not doc:
        return {}
    doc["id"] = str(doc.pop("_id"))
    return PerfilOut(**doc)
