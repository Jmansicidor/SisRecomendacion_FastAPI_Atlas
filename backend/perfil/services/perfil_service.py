# perfil/services/perfil_service.py
import anyio
import time
from typing import Dict, Any, Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from core.ai import embed_texts
# ← recalcula métricas del perfil activo
from metricas.services.rebuild import rebuild_ranking_for_profile


def _construir_perfil_texto(
    puesto: str,
    educacion: List[str],
    atributos: List[str],
    experiencia: List[str],
    idiomas: List[str],
) -> str:
    parts: List[str] = []
    if puesto:
        parts.append(puesto)
    if educacion:
        parts.append(" ".join(educacion))
    if atributos:
        parts.append(" ".join(atributos))
    if experiencia:
        parts.append(" ".join(experiencia))
    if idiomas:
        parts.append(" ".join(idiomas))  # ← idiomas ahora impacta el embedding
    return " ".join(parts).strip()


async def _embed_async(texts: List[str]) -> List[List[float]]:
    # ejecuta embed_texts en hilo para no bloquear el event loop
    return await anyio.to_thread.run_sync(embed_texts, texts)


async def guardar_perfil(db: AsyncIOMotorDatabase, data: Dict[str, Any]) -> str:
    """
    Crea un perfil:
      - Construye el texto a indexar (incluye idiomas).
      - Genera embedding y guarda el doc.
      - Si 'activo' es True, desactiva otros perfiles del mismo owner y
        dispara el rebuild del ranking para este perfil.
    """
    # 1) Normalización de entradas (listas seguras)
    educacion = list(data.get("educacion", []) or [])
    atributos = list(data.get("atributos", []) or [])
    experiencia = list(data.get("experiencia", []) or [])
    idiomas = list(data.get("idiomas", []) or [])

    # 2) Texto del perfil + embedding
    perfil_texto = _construir_perfil_texto(
        data["puesto"], educacion, atributos, experiencia, idiomas
    )
    vector = (await _embed_async([perfil_texto]))[0]

    owner = data.get("usuario")

    doc = {
        "owner": owner,
        "puesto": data["puesto"],
        "educacion": educacion,
        "atributos": atributos,
        "experiencia": experiencia,
        "idiomas": idiomas,
        "edad": int(data["edad"]),
        "perfil": perfil_texto,
        "vector": vector,
        "activo": bool(data.get("activo", False)),
        "publicado": bool(data.get("publicado", False)),
        "timestamp": time.time(),
    }

    # 3) Si será activo, desactivar otros perfiles del mismo owner (no de todos)
    if doc["activo"] and owner:
        await db["perfiles"].update_many({"owner": owner}, {"$set": {"activo": False}})

    # 4) Insertar
    res = await db["perfiles"].insert_one(doc)
    perfil_id = str(res.inserted_id)

    # 5) Si quedó activo → recalcular métricas (ranking) para este perfil
    if doc["activo"]:
        # No esperamos resultado; si preferís no bloquear, podrías usar asyncio.create_task(...)
        await rebuild_ranking_for_profile(db, perfil_id)

    return perfil_id


async def obtener_perfil_activo(db: AsyncIOMotorDatabase) -> Optional[Dict[str, Any]]:
    """
    Devuelve el perfil activo (global). Si manejás multi-owner y querés
    “perfil activo por usuario”, filtrá también por owner.
    """
    return await db["perfiles"].find_one({"activo": True})
