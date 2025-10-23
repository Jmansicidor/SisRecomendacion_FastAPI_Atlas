# utils/api_metricas.py
from __future__ import annotations
import os
import requests
from typing import Any, Dict, Optional, Tuple

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000").rstrip("/")
API_RANKING = f"{BACKEND_URL}/api/metricas/ranking"
API_BASE = f"{BACKEND_URL.rstrip('/')}/api"
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "120"))


def _auth_header(access_token: Optional[str] = None) -> Dict[str, str]:
    """Construye el header Authorization si hay token."""
    headers = {"Accept": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    return headers


def get_ranking(
    perfil_id: Optional[str] = None,
    limit: int = 100,
    access_token: Optional[str] = None,
    timeout: int = API_TIMEOUT
) -> Dict[str, Any]:
    params = {"limit": str(limit)}
    if perfil_id:
        params["perfil_id"] = perfil_id
    r = requests.get(
        f"{API_BASE}/metricas/ranking",
        params=params,
        headers=_auth_header(access_token),
        timeout=timeout
    )
    r.raise_for_status()
    return r.json() or {}


def rebuild_ranking(
    perfil_id: Optional[str] = None,
    access_token: Optional[str] = None,
    timeout: int = API_TIMEOUT
) -> Dict[str, Any]:
    params = {}
    if perfil_id:
        params["perfil_id"] = perfil_id
    r = requests.post(
        f"{API_BASE}/metricas/ranking/rebuild",
        params=params,
        headers=_auth_header(access_token),
        timeout=timeout
    )
    r.raise_for_status()
    return r.json() or {}
