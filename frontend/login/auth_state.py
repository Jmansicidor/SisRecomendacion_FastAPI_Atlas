
import os
import streamlit as st

DEFAULT_API_URL = os.getenv("API_URL", "http://backend:8000")


def init_state() -> None:
    """
    Inicializa las claves de session_state esperadas por la app.
    """
    st.session_state.setdefault("api_url", DEFAULT_API_URL)
    # dict con {access_token, token_type, expires_in?}
    st.session_state.setdefault("token", None)
    st.session_state.setdefault("raw_jwt", None)   # el string del JWT
    # dict del usuario de /api/users/me
    st.session_state.setdefault("me", None)
