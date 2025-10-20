# login/auth_client.py
import os
import requests
import streamlit as st
from typing import Tuple, Optional, Dict, Any

# ---------- Config común ----------


def _get_api_base() -> str:
    # Una sola fuente de verdad (secrets > env > fallback)
    return (
        st.secrets.get("API_BASE")
        or os.getenv("API_BASE")
        or "http://127.0.0.1:8000"  # ajustá si corresponde
    )


def _ensure_api_base_in_state() -> None:
    if not st.session_state.get("api_url"):
        st.session_state["api_url"] = _get_api_base()


def _norm_email(e: str) -> str:
    return (e or "").strip().lower()


def _norm_pwd(p: str) -> str:
    return (p or "").strip()

# ---------- Helpers ----------


def auth_headers() -> Dict[str, str]:
    token = st.session_state.get("token")
    if token and token.get("access_token"):
        return {"Authorization": f"Bearer {token['access_token']}"}
    return {}

# ---------- Flujos de Auth ----------


def login_oauth(email: str, password: str) -> Tuple[bool, Optional[str]]:
    """
    Login contra /api/auth/token (OAuth2PasswordRequestForm).
    Normaliza SIEMPRE email/pass aquí y guarda el token si es exitoso.
    """
    _ensure_api_base_in_state()
    url = f"{st.session_state.api_url}/api/auth/token"
    data = {"username": _norm_email(email), "password": _norm_pwd(password)}
    try:
        res = requests.post(url, data=data, timeout=10)
    except requests.RequestException as e:
        return False, f"Error de red: {e}"

    # Debug mínimo (útil para diferenciar 401 de 500/404). Quitá si molesta.
    print("LOGIN status:", res.status_code, res.text[:200])

    if res.status_code == 200:
        payload = res.json()
        st.session_state["token"] = payload
        st.session_state["raw_jwt"] = payload.get("access_token")
        return True, None

    if res.status_code == 401:
        return False, "Credenciales inválidas"

    return False, f"Backend {res.status_code}: {res.text}"


def fetch_me() -> Optional[Dict[str, Any]]:
    """
    Llama a /api/users/me. Si 200, guarda en session_state['me'] y lo retorna.
    Si 401/403, limpia sesión para forzar re-login.
    """
    _ensure_api_base_in_state()
    url = f"{st.session_state.api_url}/api/users/me"
    try:
        res = requests.get(url, headers=auth_headers(), timeout=10)
    except requests.RequestException:
        st.session_state["me"] = None
        return None

    if res.status_code == 200:
        st.session_state["me"] = res.json()
        return st.session_state["me"]

    if res.status_code in (401, 403):
        st.session_state["me"] = None
        st.session_state["token"] = None
        st.session_state["raw_jwt"] = None
        return None

    print("ME status:", res.status_code, res.text[:200])
    st.session_state["me"] = None
    return None


def register_user(username: str, email: str, password: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Registro contra /api/auth/register. Normaliza email/pass igual que en login.
    """
    _ensure_api_base_in_state()
    url = f"{st.session_state.api_url}/api/auth/register"
    payload = {
        "username": (username or "").strip(),
        "email": _norm_email(email),
        "password": _norm_pwd(password),
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
    except requests.RequestException as e:
        return False, f"Error de red: {e}", None

    print("REGISTER status:", res.status_code, res.text[:200])

    if res.status_code in (200, 201):
        return True, None, res.json()

    return False, f"Backend {res.status_code}: {res.text}", None


def logout() -> None:
    """
    Server-side (si existe /api/auth/logout) + cleanup local.
    """
    _ensure_api_base_in_state()
    url = f"{st.session_state.api_url}/api/auth/logout"
    try:
        requests.post(url, headers=auth_headers(), timeout=10)
    except requests.RequestException:
        pass
    st.session_state["token"] = None
    st.session_state["raw_jwt"] = None
    st.session_state["me"] = None
