# utils/api_perfil.py
from __future__ import annotations
import os
import requests
from typing import Any, Dict, Optional, Tuple

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000").rstrip("/")
API_PERFIL_BASE = f"{BACKEND_URL}/api/perfil"


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
    """POST /api/perfil/  → {id: "..."}"""
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
    headers = {"Accept": "application/json",
               "Content-Type": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=timeout)
        if r.status_code == 200:
            return (r.json() or {}).get("id"), None
        # 201 también es válido en algunos routers
        if r.status_code == 201:
            body = r.json() or {}
            return body.get("id") or body.get("_id") or body.get("inserted_id"), None
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
    """
    Intenta varios endpoints comunes:
      GET /api/perfil/activo
      GET /api/perfil/actual
      GET /api/perfil/ (si devuelve el activo)
    Ajustá si tu backend usa otro path.
    """
    headers = {"Accept": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    for path in ("/activo", "/actual", "/"):
        url = f"{API_PERFIL_BASE}{path}"
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            if r.ok:
                data = r.json()
                # si viene como {"perfil": {...}} o directo {...}
                if isinstance(data, dict) and "perfil" in data and isinstance(data["perfil"], dict):
                    return data["perfil"], None
                if isinstance(data, dict):
                    return data, None
            # probar siguiente path si 404
        except Exception:
            pass
    return None, "No se pudo obtener el perfil activo desde la API."
