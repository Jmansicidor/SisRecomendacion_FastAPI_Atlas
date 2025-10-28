# pages/perfiles.py
import streamlit as st
from login.auth_state import init_state
from login.auth_ui import require_auth, auth_bar, require_roles
from utils.menubar import navegacion_path, sidebar_user_box
from utils.api_perfil import guardar_perfil_api, obtener_perfil_activo_publico_api

st.set_page_config(page_title="Perfil", layout="wide")

# --- Auth / UI ---
init_state()
me = require_auth()                 # asegura sesión
require_roles({"admin"})            # asegura rol admin (frontend)
auth_bar()
navegacion_path()
sidebar_user_box()

st.title("Perfiles")


st.subheader("Perfil buscado para la vacante")
st.write("Ingresá múltiples valores separándolos con comas…")

# Inputs
puesto_input = st.text_input(
    "Puesto Disponible:", placeholder="Lic. en Sistemas, Analista de datos, etc.")
educacion_input = st.text_input(
    "Educaciones (separadas por comas)", placeholder="Ej: Ingeniero, Magíster")
atributos_input = st.text_input(
    "Habilidades (separadas por comas)", placeholder="Ej: Python, Liderazgo")
experiencia_input = st.text_area("Experiencias laborales (separadas por comas)",
                                 placeholder="Ej: Gestión de proyectos, Análisis de datos")
idioma_input = st.text_area(
    "Idiomas requeridos (separados por comas)", placeholder="Ej: Inglés, Francés")

edad_input = st.slider("Edad deseada (referencia)", 18, 100, value=25)

colA, colB = st.columns(2)
with colA:
    flag_activo = st.checkbox("Marcar como ACTIVO (vigente)", value=True)
with colB:
    flag_publicado = st.checkbox("Publicar (visible para todos)", value=True)

if st.button("Guardar perfil"):
    puesto = (puesto_input or "").strip()
    educaciones = [e.strip()
                   for e in (educacion_input or "").split(",") if e.strip()]
    atributos = [a.strip()
                 for a in (atributos_input or "").split(",") if a.strip()]
    experiencias = [x.strip()
                    for x in (experiencia_input or "").split(",") if x.strip()]
    idiomas = [x.strip() for x in (idioma_input or "").split(",") if x.strip()]
    edad = int(edad_input)

    if not (puesto and educaciones and atributos and experiencias and idiomas):
        st.error("Completá puesto, educación, habilidades, experiencias e idiomas.")
    else:
        access_token = st.session_state.get("access_token")
        perfil_id, err = guardar_perfil_api(
            usuario=(me or {}).get("id") or (me or {}).get("email"),
            puesto=puesto,
            educacion=educaciones,
            atributos=atributos,
            experiencia=experiencias,
            idiomas=idiomas,
            edad=edad,
            activo=flag_activo,
            publicado=flag_publicado,
            access_token=access_token
        )
        if err:
            st.error(err)
        else:
            st.success(f"Perfil guardado (id={perfil_id}).")
            st.cache_data.clear()
            st.rerun()

st.markdown("### Perfil activo/público actual")


def _line(x):
    return ", ".join(x) if isinstance(x, (list, tuple)) else (x or "")


with st.spinner("Cargando perfil activo desde API…"):
    access_token = st.session_state.get("access_token")
    perfil, per_err = obtener_perfil_activo_publico_api(
        access_token=access_token)

if per_err:
    st.info(per_err)
else:
    if not perfil:
        st.info("Aún no hay un perfil publicado.")
    else:
        st.write(f"- **Puesto**: {perfil.get('puesto', '—')}")
        st.write(f"- **Educación**: {_line(perfil.get('educacion', ''))}")
        st.write(f"- **Habilidades**: {_line(perfil.get('atributos', ''))}")
        st.write(f"- **Experiencias**: {_line(perfil.get('experiencia', ''))}")
        # <- corregido
        st.write(f"- **Idiomas**: {_line(perfil.get('idiomas', ''))}")
        edad = perfil.get("edad")
        if isinstance(edad, int) and edad > 0:
            st.write(f"- **Edad objetivo**: {edad}")
        st.caption(
            f"activo={perfil.get('activo')} • publicado={perfil.get('publicado')} • owner={perfil.get('owner')}")
