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
    # Traer perfil (vector + listas simbólicas)
    perf = await db["perfiles"].find_one(
        {"_id": ObjectId(perfil_id)},
        projection={"vector": 1, "atributos": 1,
                    "experiencia": 1, "educacion": 1, "idiomas": 1}
    )
    if not perf or not perf.get("vector"):
        return 0

    # Vector del perfil
    p = np.asarray(perf["vector"], dtype=np.float32)
    p_norm = float(np.linalg.norm(p)) or 1e-8

    # Normalización simbólica del perfil (sets)
    perf_atr = tokens_norm(perf.get("atributos", []))
    perf_exp = tokens_norm(perf.get("experiencia", []))
    perf_edu = tokens_norm(perf.get("educacion", []))
    perf_idi = tokens_norm(perf.get("idiomas", []))

    # Traer todos los CV con vector
    cur = db["curriculum"].find(
        {"cv_vector": {"$type": "array"}},
        projection={
            "_id": 1, "cv_vector": 1, "norm": 1,
            "nombre": 1, "apellido": 1, "email": 1,
            "tokens_habilidades": 1, "tokens_experiencia": 1, "tokens_formacion": 1,
            "tokens_idiomas": 1,      # 👈 incluir idiomas si los guardás
            "cv_file_id": 1           # 👈 útil para snapshot/descarga en front
        }
    )
    docs = await cur.to_list(length=None)

    count = 0
    for d in docs:
        # Coseno (con protección por norma)
        x = np.asarray(d.get("cv_vector") or [], dtype=np.float32)
        if x.size == 0:
            continue
        x_norm = float(d.get("norm") or (np.linalg.norm(x))) or 1e-8
        cos = float((x @ p) / (x_norm * p_norm + 1e-8))

        # Normalización simbólica del CV
        cv_hab = tokens_norm(d.get("tokens_habilidades", []))
        cv_exp = tokens_norm(d.get("tokens_experiencia", []))
        cv_edu = tokens_norm(d.get("tokens_formacion", []))
        # puede ser set() si no existe
        cv_idi = tokens_norm(d.get("tokens_idiomas", []))

        # Jaccards “blandos”, alineados con el live
        thr = THR_JACCARD
        J_hab = soft_jaccard(perf_atr, cv_hab, thr=thr)
        J_exp = soft_jaccard(perf_exp, cv_exp, thr=thr)
        J_edu = soft_jaccard(perf_edu, cv_edu, thr=thr)
        J_idi = soft_jaccard(perf_idi, cv_idi, thr=thr)

        j_total = W_HAB*J_hab + W_EXP*J_exp + W_EDU*J_edu + W_IDI*J_idi
        score = ALPHA*cos + (1.0 - ALPHA)*j_total

        snapshot = {
            "nombre": d.get("nombre", ""),
            "apellido": d.get("apellido", ""),
            "email": d.get("email", ""),
            # 👈 opcional pero práctico
            "cv_file_id": d.get("cv_file_id", None),
        }

        await db["ranking"].update_one(
            {"perfil_id": str(perfil_id), "cv_id": str(d["_id"])},
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
        count += 1

    return count
