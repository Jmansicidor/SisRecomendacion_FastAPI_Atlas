# metricas/services/rebuild.py
import time
import numpy as np
from bson import ObjectId

from core.config import ALPHA, W_HAB, W_EXP, W_EDU, W_IDI
# Podés definir THR_JACCARD en core.config (por ej. 87); si no existe, fijamos un default acá.
try:
    from core.config import THR_JACCARD
except Exception:
    THR_JACCARD = 87

from utils.text_normalizer import tokens_norm, soft_jaccard


async def rebuild_ranking_for_profile(db, perfil_id: str) -> int:

    # 0) Limpia ranking existente de ese perfil (evita mezclas con perfiles previos)
    await db["ranking"].delete_many({"perfil_id": perfil_id})

    # 1) Traer perfil (vector + listas simbólicas)
    perf = await db["perfiles"].find_one(
        {"_id": ObjectId(perfil_id)},
        projection={"vector": 1, "atributos": 1,
                    "experiencia": 1, "educacion": 1, "idiomas": 1}
    )
    if not perf or not perf.get("vector"):
        return 0

    p = np.asarray(perf["vector"], dtype=np.float32)
    if p.size == 0:
        return 0
    p_norm = float(np.linalg.norm(p)) or 1e-8

    # Perfil normalizado para jaccard blando
    perf_atr = tokens_norm(perf.get("atributos", []))
    perf_exp = tokens_norm(perf.get("experiencia", []))
    perf_edu = tokens_norm(perf.get("educacion", []))
    perf_idi = tokens_norm(perf.get("idiomas", []))

    # 2) Recorrer todos los CVs
    projection = {
        "_id": 1, "nombre": 1, "apellido": 1, "email": 1, "cv_file_id": 1,
        "cv_vector": 1, "norm": 1,
        "tokens_habilidades": 1, "tokens_experiencia": 1, "tokens_formacion": 1, "tokens_idiomas": 1,
    }
    cur = db["curriculum"].find({}, projection=projection)

    updated = 0
    async for cv in cur:
        # --- Coseno ---
        x = np.asarray(cv.get("cv_vector") or [], dtype=np.float32)
        if x.size == 0:
            cos = 0.0
        else:
            x_norm = float(cv.get("norm") or np.linalg.norm(x)) or 1e-8
            cos = float((x @ p) / (x_norm * p_norm + 1e-8))

        # --- Jaccards blandos ---
        cv_hab = tokens_norm(cv.get("tokens_habilidades", []))
        cv_exp = tokens_norm(cv.get("tokens_experiencia", []))
        cv_edu = tokens_norm(cv.get("tokens_formacion", []))
        cv_idi = tokens_norm(cv.get("tokens_idiomas", []))

        thr = THR_JACCARD
        J_hab = soft_jaccard(perf_atr, cv_hab, thr=thr)
        J_exp = soft_jaccard(perf_exp, cv_exp, thr=thr)
        J_edu = soft_jaccard(perf_edu, cv_edu, thr=thr)
        J_idi = soft_jaccard(perf_idi, cv_idi, thr=thr)

        j_total = W_HAB * J_hab + W_EXP * J_exp + W_EDU * J_edu + W_IDI * J_idi
        score = ALPHA * cos + (1.0 - ALPHA) * j_total

        # --- Snapshot para el front (incluye cv_file_id para descarga) ---
        snapshot = {
            "nombre": cv.get("nombre", ""),
            "apellido": cv.get("apellido", ""),
            "email": cv.get("email", ""),
            "cv_file_id": cv.get("cv_file_id", None),
        }

        await db["ranking"].update_one(
            {"perfil_id": perfil_id, "cv_id": str(cv["_id"])},
            {"$set": {
                "perfil_id": perfil_id,
                "cv_id": str(cv["_id"]),
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
                "snapshot": snapshot,
            }},
            upsert=True
        )
        updated += 1

    return updated
