# utils/api_metricas.py
from __future__ import annotations
import os
import requests
from typing import Any, Dict, Optional, Tuple

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000").rstrip("/")
API_RANKING = f"{BACKEND_URL}/api/metricas/ranking"
API_BASE = f"{BACKEND_URL.rstrip('/')}/api"
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "120"))


def get_ranking(limit: int = 50, skip: int = 0, access_token: Optional[str] = None, timeout: int = 60
                ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        headers = {"Accept": "application/json"}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        params = {"limit": limit, "skip": skip}
        r = requests.get(API_RANKING, headers=headers,
                         params=params, timeout=timeout)
        if r.status_code == 200:
            return r.json(), None
        else:
            try:
                return None, f"{r.status_code}: {r.json()}"
            except Exception:
                return None, f"{r.status_code}: {r.text}"
    except Exception as e:
        return None, str(e)


def get_ranking(perfil_id: Optional[str] = None, limit: int = 100, timeout: int = API_TIMEOUT):
    params = {"limit": limit}
    if perfil_id:
        params["perfil_id"] = perfil_id
    r = requests.get(f"{API_BASE}/metricas/ranking",
                     params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def rebuild_ranking(perfil_id: Optional[str] = None, timeout: int = API_TIMEOUT):
    params = {}
    if perfil_id:
        params["perfil_id"] = perfil_id
    r = requests.post(f"{API_BASE}/metricas/ranking/rebuild",
                      params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()
