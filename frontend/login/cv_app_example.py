
import streamlit as st
from login.auth_state import init_state
from login.auth_ui import require_auth, auth_bar

st.set_page_config(page_title="Mi CV", layout="wide")

# Inicializa session_state
init_state()

with st.sidebar:
    st.text_input("Backend API URL", key="api_url", help="Ej: http://127.0.0.1:8000")

# Gate de autenticación
me = require_auth()
auth_bar()

# --- A partir de aquí, tu contenido de CV ---
st.title("📄 Curriculum Vitae")
st.subheader(me.get("username", "Usuario"))

st.header("Experiencia")
st.markdown("- Desarrollador Backend — Empresa X (2022–2025)  \n  Tech: FastAPI, MongoDB, Docker")

st.header("Educación")
st.markdown("- Licenciatura en Informática — Universidad Y")

st.header("Proyectos Destacados")
st.markdown("- **API Auth + RBAC**: Login con JWT y roles.  \n- **Panel Admin**: gestión de usuarios y roles.")

roles = me.get("roles", [])
if "admin" in roles:
    st.divider()
    st.subheader("🛠️ Panel (admin)")
    if st.button("Ver mis datos actuales (/me)"):
        st.json(me)
