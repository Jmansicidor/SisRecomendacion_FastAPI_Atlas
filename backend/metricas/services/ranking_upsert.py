# metricas/services/ranking_upsert.py
import time
import numpy as np
from bson import ObjectId

from core.config import ALPHA, W_HAB, W_EXP, W_EDU, W_IDI
# Umbral de similitud para soft_jaccard; si no está en config, usamos 87 por defecto
try:
    from core.config import THR_JACCARD
except Exception:
    THR_JACCARD = 87

from utils.text_normalizer import tokens_norm, soft_jaccard


async def upsert_ranking_for_active_profile(db, cv_id: str, cv_vector: list[float], cv_norm: float):
    """
    Calcula score (coseno + jaccards blandos) para el CV dado contra el perfil ACTIVO,
    y lo persiste en la colección 'ranking' (upsert).
    """
    # 1) Perfil activo (vector + listas simbólicas)
    perfil = await db["perfiles"].find_one(
        {"activo": True},
        projection={"_id": 1, "vector": 1, "atributos": 1,
                    "experiencia": 1, "educacion": 1, "idiomas": 1}
    )
    if not perfil or not perfil.get("vector"):
        return

    # 2) CV (tokens + snapshot)
    cv_doc = await db["curriculum"].find_one(
        {"_id": ObjectId(cv_id)},
        projection={
            "nombre": 1, "apellido": 1, "email": 1, "cv_file_id": 1,
            "tokens_habilidades": 1, "tokens_experiencia": 1, "tokens_formacion": 1,
            "tokens_idiomas": 1,   
        }
    )
    if not cv_doc:
        return

    # ---------- Coseno ----------
    p = np.asarray(perfil["vector"], dtype=np.float32)
    x = np.asarray(cv_vector or [], dtype=np.float32)
    if x.size == 0 or p.size == 0:
        cos = 0.0
    else:
        p_norm = float(np.linalg.norm(p)) or 1e-8
        x_norm = float(cv_norm or (np.linalg.norm(x))) or 1e-8
        cos = float((x @ p) / (x_norm * p_norm + 1e-8))

    # ---------- Jaccards blandos: normalización + soft_jaccard ----------
    # Perfil (sets normalizados)
    perf_atr = tokens_norm(perfil.get("atributos", []))
    perf_exp = tokens_norm(perfil.get("experiencia", []))
    perf_edu = tokens_norm(perfil.get("educacion", []))
    perf_idi = tokens_norm(perfil.get("idiomas", []))

    # CV (sets normalizados)
    cv_hab = tokens_norm(cv_doc.get("tokens_habilidades", []))
    cv_exp = tokens_norm(cv_doc.get("tokens_experiencia", []))
    cv_edu = tokens_norm(cv_doc.get("tokens_formacion", []))
    cv_idi = tokens_norm(cv_doc.get("tokens_idiomas", []))  # puede ser set()

    thr = THR_JACCARD
    J_hab = soft_jaccard(perf_atr, cv_hab, thr=thr)
    J_exp = soft_jaccard(perf_exp, cv_exp, thr=thr)
    J_edu = soft_jaccard(perf_edu, cv_edu, thr=thr)
    J_idi = soft_jaccard(perf_idi, cv_idi, thr=thr)

    j_total = W_HAB * J_hab + W_EXP * J_exp + W_EDU * J_edu + W_IDI * J_idi
    score = ALPHA * cos + (1.0 - ALPHA) * j_total

    snapshot = {
        "nombre": cv_doc.get("nombre", ""),
        "apellido": cv_doc.get("apellido", ""),
        "email": cv_doc.get("email", ""),
        # 👈 útil para descarga directa en front
        "cv_file_id": cv_doc.get("cv_file_id", None),
    }

    await db["ranking"].update_one(
        {"perfil_id": str(perfil["_id"]), "cv_id": str(cv_id)},
        {"$set": {
            "score": float(score),
            "score_cos": float(cos),
            "score_j_total": float(j_total),
            "score_j_hab": float(J_hab),
            "score_j_exp": float(J_exp),
            "score_j_edu": float(J_edu),
            "score_j_idi": float(J_idi),
            "weights": {
                "alpha": float(ALPHA),
                "j": {"hab": float(W_HAB), "exp": float(W_EXP), "edu": float(W_EDU), "idi": float(W_IDI)},
                "thr": int(thr),
            },
            "updated_at": time.time(),
            "snapshot": snapshot
        }},
        upsert=True
    )
