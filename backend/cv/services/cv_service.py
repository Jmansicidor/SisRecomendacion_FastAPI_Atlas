import time
import re
from typing import Optional, Dict, Any, List, Tuple
from io import BytesIO
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket
from metricas.services.ranking_upsert import upsert_ranking_for_active_profile
from utils.extract_gpt import build_cv_text_from_gpt, reed_cv_bytes
from core.ai import embed_texts
import anyio
import fitz  # PyMuPDF
import numpy as np

# ----------------- helpers -----------------


def _tokens_simple(s: str) -> List[str]:
    return list({t.lower() for t in re.findall(r"\w+", s or "")})


async def _embed_one(text: str) -> List[float]:
    # embed_texts(["..."]) -> List[List[float]]
    vecs = await anyio.to_thread.run_sync(embed_texts, [text])
    return vecs[0]


def _gridfs(db: AsyncIOMotorDatabase) -> AsyncIOMotorGridFSBucket:
    return AsyncIOMotorGridFSBucket(db)


def _norm(v: Optional[List[float]]) -> float:
    if not v:
        return 0.0
    arr = np.asarray(v, dtype=np.float32)
    return float(np.linalg.norm(arr)) if arr.size else 0.0


def _pick(d: Dict[str, Any], keys: List[str], default: Any = "") -> Any:
    for k in keys:
        if k in d and d[k]:
            return d[k]
    return default


def _fecha_iso(x) -> Optional[str]:
    if x is None:
        return None
    # date -> iso
    try:
        import datetime as _dt
        if isinstance(x, _dt.date):
            return x.isoformat()
    except Exception:
        pass
    # string ya iso o similar
    return str(x)


def _pdf_text_from_bytes(pdf_bytes: bytes) -> str:
    text = ""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf:
        for page in pdf:
            text += page.get_text() or ""
    return text

# ----------------- API pública -----------------


async def count_cv(db: AsyncIOMotorDatabase, collection_name: str = "curriculum") -> int:
    return await db[collection_name].count_documents({})


async def guardar_cv(
    db: AsyncIOMotorDatabase,
    file_bytes: bytes,
    payload: Dict[str, Any]
) -> Tuple[Optional[str], Optional[str]]:
    try:
        fs = _gridfs(db)

        # 1) Subir PDF
        upload_id = await fs.upload_from_stream(
            f"{payload['firstname']}_{payload['lastname']}.pdf",
            file_bytes,
            metadata={
                "usuario": f"{payload['firstname']} {payload['lastname']}", "ts": time.time()},
        )

        # 2) Extraer (si hace falta)
        extracted_data = payload.get("extracted_data") or {}
        if not extracted_data:
            extracted_data = await anyio.to_thread.run_sync(reed_cv_bytes, file_bytes)

        # 3) Texto para embedding
        gpt_text = build_cv_text_from_gpt(
            extracted_data) if extracted_data else ""
        texto_para_embedding = gpt_text or (payload.get("cv_text") or "")
        if not texto_para_embedding.strip():
            try:
                texto_para_embedding = await anyio.to_thread.run_sync(_pdf_text_from_bytes, file_bytes)
            except Exception:
                texto_para_embedding = ""

        # 4) Embedding
        cv_vector = payload.get("cv_vector")
        if cv_vector is None and texto_para_embedding.strip():
            cv_vector = await _embed_one(texto_para_embedding)

        # 5) Tokens
        formacion_src = _pick(extracted_data, [
                              "formacion_academica", "formacion_academical", "formación_académica"], "")
        habilidades_src = _pick(
            extracted_data, ["habilidades_tecnicas", "habilidades"], "")
        experiencia_src = _pick(
            extracted_data, ["experiencia_laboral", "experiencia"], "")

        tokens_formacion = payload.get(
            "tokens_formacion") or _tokens_simple(str(formacion_src))
        tokens_habilidades = payload.get(
            "tokens_habilidades") or _tokens_simple(str(habilidades_src))
        tokens_experiencia = payload.get(
            "tokens_experiencia") or _tokens_simple(str(experiencia_src))

        # 6) Fuente del vector
        if gpt_text:
            cv_vector_src = "gpt"
        elif payload.get("cv_text"):
            cv_vector_src = "cv_text"
        elif texto_para_embedding:
            cv_vector_src = "pdf_text"
        else:
            cv_vector_src = None

        # 7) Norma del vector (¡calcular valor!)
        norm_val = _norm(cv_vector)

        # 8) Documento
        doc = {
            "nombre":   payload["firstname"],
            "apellido": payload["lastname"],
            "ciudad":   payload.get("city", ""),
            "direccion": payload.get("address", ""),
            "email":    payload.get("mail", ""),
            "cv_file_id": str(upload_id),

            "cv_analisis_gpt": extracted_data,
            "fecha_nacimiento": _fecha_iso(payload.get("fecha_nacimiento")),
            "edad": int(payload["edad"]) if payload.get("edad") is not None else None,
            "timestamp": time.time(),

            "cv_text": texto_para_embedding or "",
            # ✅ usar list(...) solo si hay vector
            "cv_vector": (list(cv_vector) if cv_vector is not None else None),
            "cv_vector_src": cv_vector_src,
            "norm": norm_val,

            "tokens_formacion": list(tokens_formacion or []),
            "tokens_habilidades": list(tokens_habilidades or []),
            "tokens_experiencia": list(tokens_experiencia or []),
        }

        # 9) Insert
        res = await db["curriculum"].insert_one(doc)
        cv_id = str(res.inserted_id)

        # 10) Upsert ranking (si hay vector) — ✅ pasar norm_val, NO la función
        if doc["cv_vector"] is not None:
            await upsert_ranking_for_active_profile(
                db,
                cv_id,
                doc["cv_vector"],
                norm_val or 0.0
            )

        return cv_id, None

    except Exception as e:
        return None, str(e)
        # 9) Upsert de ranking (solo si hay vector)
        if doc["cv_vector"] is not None:
            await upsert_ranking_for_active_profile(
                db,
                cv_id,
                doc["cv_vector"],
                _norm or 0.0
            )

        # 10) OK
        return cv_id, None

    except Exception as e:
        return None, str(e)


async def obtener_cv_por_email(db: AsyncIOMotorDatabase, email: str) -> Optional[Dict[str, Any]]:
    return await db["curriculum"].find_one({"email": email}, sort=[("timestamp", -1)])


async def cargar_cv(db, cv_file_id: str) -> Tuple[Optional[bytes], Optional[str]]:
    try:
        fs = _gridfs(db)  # AsyncIOMotorGridFSBucket(db)
        oid = ObjectId(cv_file_id)
        file_doc = await db["fs.files"].find_one({"_id": oid})
        filename = file_doc.get("filename") if file_doc else "cv.pdf"
        buf = BytesIO()
        await fs.download_to_stream(oid, buf)
        return buf.getvalue(), filename
    except Exception:
        return None, None


async def eliminar_cv(db: AsyncIOMotorDatabase, cv_id: str) -> bool:
    try:
        cv_oid = ObjectId(cv_id)
        cv_doc = await db["curriculum"].find_one({"_id": cv_oid})
        if not cv_doc:
            return False
        if "cv_file_id" in cv_doc:
            try:
                fs = _gridfs(db)
                file_oid = ObjectId(cv_doc["cv_file_id"])
                await fs.delete(file_oid)
            except Exception:
                pass
        await db["curriculum"].delete_one({"_id": cv_oid})
        return True
    except Exception:
        return False


async def actualizar_perfil_usuario(
    db: AsyncIOMotorDatabase,
    email: str,
    patch: Dict[str, Any]
) -> Tuple[bool, Optional[str]]:

    try:
        # doc más reciente por email
        doc = await db["curriculum"].find_one({"email": email}, sort=[("timestamp", -1)])
        if not doc:
            return False, "No existe CV previo para este email"

        updates = {}
        for k in ("nombre", "apellido", "ciudad", "direccion", "fecha_nacimiento", "edad"):
            if patch.get(k) is not None:
                updates[k] = patch[k]

        if not updates:
            return True, None  # nada que actualizar

        await db["curriculum"].update_one(
            {"_id": doc["_id"]},
            {"$set": updates}
        )
        return True, None
    except Exception as e:
        return False, str(e)

# cv/services/cv_service.py (añadir)


async def resubir_cv(
    db: AsyncIOMotorDatabase,
    email: str,
    file_bytes: bytes,
    keep_history: bool = False
) -> Tuple[Optional[str], Optional[str]]:
    try:
        fs = _gridfs(db)

        # Doc más reciente del usuario
        prev = await db["curriculum"].find_one({"email": email}, sort=[("timestamp", -1)])
        if not prev:
            return None, "No existe CV previo para este email, suba uno nuevo primero."

        # 1) Subir nuevo PDF
        upload_id = await fs.upload_from_stream(
            f"{prev.get('nombre', 'user')}_{prev.get('apellido', 'cv')}.pdf",
            file_bytes,
            metadata={
                "usuario": f"{prev.get('nombre', '')} {prev.get('apellido', '')}", "ts": time.time()},
        )

        # 2) Extraer + construir texto + embed
        extracted_data = prev.get("cv_analisis_gpt") or {}
        if not extracted_data:
            try:
                extracted_data = await anyio.to_thread.run_sync(reed_cv_bytes, file_bytes)
            except Exception:
                extracted_data = {}

        gpt_text = build_cv_text_from_gpt(
            extracted_data) if extracted_data else ""
        texto_para_embedding = gpt_text
        if not texto_para_embedding.strip():
            try:
                texto_para_embedding = await anyio.to_thread.run_sync(_pdf_text_from_bytes, file_bytes)
            except Exception:
                texto_para_embedding = ""

        cv_vector = None
        if texto_para_embedding.strip():
            cv_vector = await _embed_one(texto_para_embedding)
        norm_val = _norm(cv_vector)

        # 3) Tokens mínimos desde análisis
        formacion_src = _pick(extracted_data, [
                              "formacion_academica", "formacion_academical", "formación_académica"], "")
        habilidades_src = _pick(
            extracted_data, ["habilidades_tecnicas", "habilidades"], "")
        experiencia_src = _pick(
            extracted_data, ["experiencia_laboral", "experiencia"], "")

        tokens_formacion = _tokens_simple(str(formacion_src))
        tokens_habilidades = _tokens_simple(str(habilidades_src))
        tokens_experiencia = _tokens_simple(str(experiencia_src))

        if keep_history:
            # 4A) Crear NUEVO documento (historial)
            doc = {
                "nombre": prev.get("nombre", ""),
                "apellido": prev.get("apellido", ""),
                "ciudad": prev.get("ciudad", ""),
                "direccion": prev.get("direccion", ""),
                "email": email,
                "cv_file_id": str(upload_id),

                "cv_analisis_gpt": extracted_data,
                "fecha_nacimiento": prev.get("fecha_nacimiento"),
                "edad": prev.get("edad"),
                "timestamp": time.time(),

                "cv_text": texto_para_embedding or "",
                "cv_vector": (list(cv_vector) if cv_vector is not None else None),
                "cv_vector_src": "gpt" if gpt_text else ("pdf_text" if texto_para_embedding else None),
                "norm": norm_val,

                "tokens_formacion": list(tokens_formacion or []),
                "tokens_habilidades": list(tokens_habilidades or []),
                "tokens_experiencia": list(tokens_experiencia or []),
            }
            res = await db["curriculum"].insert_one(doc)
            cv_id = str(res.inserted_id)

            # Upsert ranking (si hay vector)
            if doc["cv_vector"] is not None:
                await upsert_ranking_for_active_profile(db, cv_id, doc["cv_vector"], norm_val or 0.0)

            return cv_id, None

        else:
            # 4B) Reemplazar en el doc más reciente y borrar archivo anterior
            old_file_id = prev.get("cv_file_id")
            updates = {
                "cv_file_id": str(upload_id),
                "cv_analisis_gpt": extracted_data,
                "cv_text": texto_para_embedding or "",
                "cv_vector": (list(cv_vector) if cv_vector is not None else None),
                "cv_vector_src": "gpt" if gpt_text else ("pdf_text" if texto_para_embedding else None),
                "norm": norm_val,
                "tokens_formacion": list(tokens_formacion or []),
                "tokens_habilidades": list(tokens_habilidades or []),
                "tokens_experiencia": list(tokens_experiencia or []),
                "timestamp": time.time(),
            }

            await db["curriculum"].update_one({"_id": prev["_id"]}, {"$set": updates})
            cv_id = str(prev["_id"])

            # Upsert ranking (si hay vector)
            if updates["cv_vector"] is not None:
                await upsert_ranking_for_active_profile(db, cv_id, updates["cv_vector"], norm_val or 0.0)

            # Limpieza de archivo anterior (best-effort)
            if old_file_id:
                try:
                    await fs.delete(ObjectId(old_file_id))
                except Exception:
                    pass

            return cv_id, None

    except Exception as e:
        return None, str(e)
