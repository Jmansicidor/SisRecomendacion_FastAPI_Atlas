# utils/api_perfil.py
from __future__ import annotations
import os
import requests
from typing import Any, Dict, Optional, Tuple

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000").rstrip("/")
API_PERFIL_BASE = f"{BACKEND_URL}/api/perfil"


def _auth_header(access_token: Optional[str]) -> Dict[str, str]:
    h = {"Accept": "application/json", "Content-Type": "application/json"}
    if access_token:
        h["Authorization"] = f"Bearer {access_token}"
    return h


def guardar_perfil_api(
    *,
    usuario: Optional[str],
    puesto: str,
    educacion: list[str],
    atributos: list[str],
    experiencia: list[str],
    idiomas: list[str],
    edad: int,
    activo: bool,
    publicado: bool,
    access_token: Optional[str] = None,
    timeout: int = 30
) -> Tuple[Optional[str], Optional[str]]:
    """POST /api/perfil/  → {id: "..."} (solo admin)"""
    url = f"{API_PERFIL_BASE}/"
    payload = {
        "usuario": usuario,
        "puesto": puesto,
        "educacion": educacion,
        "atributos": atributos,
        "experiencia": experiencia,
        "idiomas": idiomas,
        "edad": edad,
        "activo": activo,
        "publicado": publicado,
    }
    try:
        r = requests.post(url, json=payload, headers=_auth_header(
            access_token), timeout=timeout)
        if r.status_code in (200, 201):
            body = r.json() or {}
            return body.get("id") or body.get("_id") or body.get("inserted_id"), None
        # errores legibles
        try:
            return None, f"{r.status_code}: {r.json()}"
        except Exception:
            return None, f"{r.status_code}: {r.text}"
    except Exception as e:
        return None, str(e)


def obtener_perfil_activo_publico_api(
    access_token: Optional[str] = None,
    timeout: int = 20
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:

    headers = _auth_header(access_token)
    candidates = [
        f"{API_PERFIL_BASE}/activo",
        f"{API_PERFIL_BASE}/actual",
        f"{API_PERFIL_BASE}/",        # si devuelve el activo
    ]
    for url in candidates:
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            if r.ok:
                data = r.json()
                if isinstance(data, dict) and "perfil" in data and isinstance(data["perfil"], dict):
                    return data["perfil"], None
                if isinstance(data, dict):
                    return data, None
        except Exception:
            pass
    return None, "No se pudo obtener el perfil activo desde la API."
