# utils/api_cv.py
from __future__ import annotations
import os
import json
import requests
from typing import Dict, Any, Optional, Tuple, List, BinaryIO

# BACKEND_URL en .env (ej: http://localhost:8000)
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
API_CV_URL = f"{BACKEND_URL.rstrip('/')}/api/cv/"
API_BASE = f"{BACKEND_URL}/api"


def _read_file_bytes(cv_file) -> tuple[str, bytes]:
    """
    cv_file puede ser el objeto de Streamlit (UploadedFile) o un path.
    Devuelve (filename, bytes)
    """
    if hasattr(cv_file, "name") and hasattr(cv_file, "getbuffer"):
        filename = cv_file.name or "cv.pdf"
        data = bytes(cv_file.getbuffer())
        return filename, data
    elif isinstance(cv_file, (str, bytes)):
        # path a archivo
        if isinstance(cv_file, str):
            filename = os.path.basename(cv_file)
            with open(cv_file, "rb") as f:
                return filename, f.read()
        else:
            # bytes
            return "cv.pdf", cv_file
    else:
        raise ValueError("Formato de cv_file no soportado.")


def guardar_cv(
    *,
    firstname: str,
    lastname: str,
    city: str,
    address: str,
    mail: str,
    cv_file,  # UploadedFile de Streamlit o path o bytes
    extracted_data: Dict[str, Any],
    fecha_nacimiento,
    edad: int,
    cv_text: str = "",
    cv_vector: Optional[List[float]] = None,
    tokens_formacion: Optional[List[str]] = None,
    tokens_habilidades: Optional[List[str]] = None,
    tokens_experiencia: Optional[List[str]] = None,
    access_token: Optional[str] = None,   # ← por si tenés auth con Bearer
    timeout: int = 240
) -> Tuple[Optional[str], Optional[str]]:
    """
    Llama al backend FastAPI POST /api/cv/ y devuelve (inserted_id, error).
    """
    try:
        filename, file_bytes = _read_file_bytes(cv_file)

        meta = {
            "firstname": firstname,
            "lastname": lastname,
            "city": city,
            "address": address,
            "mail": mail,
            "extracted_data": extracted_data or {},
            "fecha_nacimiento": (
                fecha_nacimiento.isoformat()
                if hasattr(fecha_nacimiento, "isoformat")
                else fecha_nacimiento
            ),
            "edad": int(edad) if edad is not None else None,
            # campos opcionales (si los mandás, el backend los usará;
            # si no, el backend los calcula)
            "cv_text": cv_text or None,
            "cv_vector": cv_vector or None,
            "tokens_formacion": list(tokens_formacion or []),
            "tokens_habilidades": list(tokens_habilidades or []),
            "tokens_experiencia": list(tokens_experiencia or []),
        }

        files = {
            "file": (filename, file_bytes, "application/pdf"),
        }
        data = {
            # MUY IMPORTANTE: meta va como string JSON
            "meta": json.dumps(meta, ensure_ascii=False),
        }
        headers = {}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        resp = requests.post(
            API_CV_URL,
            headers=headers,
            files={  # ← SOLO el PDF acá
                "file": (filename, file_bytes, "application/pdf"),
            },
            data={   # ← meta VA EN data como STRING JSON
                "meta": json.dumps(meta, ensure_ascii=False),
            },
            timeout=timeout,
        )
        if resp.status_code == 200:
            j = resp.json()
            return j.get("id"), None
        else:
            try:
                return None, f"{resp.status_code}: {resp.json()}"
            except Exception:
                return None, f"{resp.status_code}: {resp.text}"
    except Exception as e:
        return None, str(e)


def get_cv_by_email(email: str, access_token: Optional[str] = None, timeout: int = 30,
                    full: bool = False):
    headers = {"Accept": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    r = requests.get(f"{API_BASE}/cv/by-email",
                     params={"email": email,
                             "full": "true" if full else "false"},
                     headers=headers, timeout=timeout)
    if r.ok:
        return r.json(), None
    try:
        return None, f"{r.status_code}: {r.json()}"
    except Exception:
        return None, f"{r.status_code}: {r.text}"


def download_cv_file(file_id: str, access_token: Optional[str] = None, timeout: int = 60) -> bytes | None:
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    r = requests.get(f"{API_BASE}/cv/file/{file_id}",
                     headers=headers, timeout=timeout)
    return r.content if r.ok else None


def update_profile_api(payload: Dict[str, Any], access_token: Optional[str] = None, timeout: int = 30
                       ) -> Tuple[bool, Optional[str]]:
    headers = {"Content-Type": "application/json",
               "Accept": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    r = requests.put(f"{API_BASE}/cv/profile", json=payload,
                     headers=headers, timeout=timeout)
    if r.ok:
        return True, None
    try:
        return False, f"{r.status_code}: {r.json()}"
    except Exception:
        return False, f"{r.status_code}: {r.text}"


def reupload_cv_api(email: str, cv_file, keep_history: bool = False,
                    access_token: Optional[str] = None, timeout: int = 120
                    ) -> Tuple[Optional[str], Optional[str]]:
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    # leer bytes
    def _read_file_bytes(cv):
        if hasattr(cv, "name") and hasattr(cv, "getbuffer"):
            return (cv.name or "cv.pdf", bytes(cv.getbuffer()))
        elif isinstance(cv, str):
            import os as _os
            with open(cv, "rb") as f:
                return (_os.path.basename(cv), f.read())
        elif isinstance(cv, (bytes, bytearray)):
            return ("cv.pdf", bytes(cv))
        else:
            raise ValueError("Formato de cv_file no soportado.")

    filename, file_bytes = _read_file_bytes(cv_file)

    files = {"file": (filename, file_bytes, "application/pdf")}
    data = {"email": email, "keep_history": str(bool(keep_history)).lower()}

    r = requests.post(f"{API_BASE}/cv/reupload", headers=headers,
                      files=files, data=data, timeout=timeout)
    if r.ok:
        return r.json().get("id"), None
    try:
        return None, f"{r.status_code}: {r.json()}"
    except Exception:
        return None, f"{r.status_code}: {r.text}"
