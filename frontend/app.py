
from login.auth_ui import require_auth, auth_bar
from login.auth_state import init_state
from pathlib import Path
import sys
import streamlit as st
from utils.menubar import navegacion_path, sidebar_user_box
from utils.api_perfil import obtener_perfil_activo_publico_api
from utils.api_cv import get_cv_by_email, download_cv_file

ROOT = Path(__file__).parent.resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

st.set_page_config(page_title="Mi CV", layout="wide")

# --- AUTH mínimo ---

init_state()
auth_bar()
me = require_auth()
user_email = me.get("email") if isinstance(me, dict) else None

# -------------------- Helpers perezosos --------------------


@st.cache_data(show_spinner=False, ttl=60)
def _get_busqueda_activa() -> dict | None:
    access_token = st.session_state.get(
        "access_token")  # si tu API está protegida
    perfil, err = obtener_perfil_activo_publico_api(access_token=access_token)
    if err:
        return None
    return perfil


@st.cache_data(show_spinner=False, ttl=30)
def _get_cv_doc(email: str) -> dict | None:
    access_token = st.session_state.get(
        "access_token")  # si tu API lo requiere
    data, err = get_cv_by_email(email, access_token=access_token)
    return data if not err else None


def _download_pdf(file_id: str) -> bytes | None:
    access_token = st.session_state.get(
        "access_token")  # si tu API lo requiere
    return download_cv_file(file_id, access_token=access_token)


def _line(x):
    xs = _as_list(x)
    return ", ".join(xs) if xs else "—"


def _as_list(x):
    if x is None:
        return []
    if isinstance(x, (list, tuple, set)):
        return [str(i) for i in x]
    return [str(x)]


@st.cache_data(show_spinner=False, ttl=20)
def _fetch_my_cv(email: str):
    """Trae el último CV por email desde la API."""
    access_token = st.session_state.get(
        "access_token")  # si tu API lo requiere
    data, err = get_cv_by_email(email, access_token=access_token)
    return data, err


def _download_pdf(file_id: str) -> bytes | None:
    access_token = st.session_state.get(
        "access_token")  # si tu API lo requiere
    return download_cv_file(file_id, access_token=access_token)


navegacion_path()
sidebar_user_box()
# -------------------- UI --------------------

st.markdown("<h1 style='text-align: center; color:#a81247; font-size: 48px;'>Bienvenido al sistema de recomendación con IA</h1>", unsafe_allow_html=True)
st.header("📌 Búsqueda vigente: ")

with st.spinner("Cargando búsqueda activa…"):
    p = _get_busqueda_activa()

if not p:
    st.info("No hay búsquedas publicadas por el momento.")
else:
    st.subheader(p.get("puesto", "—"))
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Educación requerida**")
        st.write(_line(p.get("educacion")))
    with col2:
        st.markdown("**Habilidades clave**")
        st.write(_line(p.get("atributos")))
    with col3:
        st.markdown("**Experiencia**")
        st.write(_line(p.get("experiencia")))


st.subheader("Recomendaciones para armar tu CV")


st.write(
    """"¡Gracias por postularte! ✨\n\n"
    "Nuestro sistema analiza tu perfil comparándolo con los requisitos del puesto, y queremos compartirte algunos consejos "
    "para que tu CV tenga más impacto en futuras oportunidades:"

    
### Formación académica 🎓
- Destacá claramente tus estudios: título, institución y fechas.
- Si estás cursando, aclarar “En curso” también suma.

### Experiencia laboral 💼
- Incluí logros concretos y resultados medibles, no solo las tareas.
- Ejemplo: “Reduje un 20% los tiempos de proceso al automatizar reportes con Python”.

### Habilidades técnicas 🛠️
- Mencioná las tecnologías, frameworks o metodologías clave que dominás.
- Para este puesto, es muy valorado.

### Claridad y formato 📑
- Usá un diseño limpio, con secciones bien definidas y sin exceso de texto.
- Evitá abreviaturas poco comunes; escribí completo el nombre de herramientas o instituciones.

### Personalización 🎯
- Adaptá el CV al puesto que te interesa, resaltando la experiencia y habilidades más alineadas con el perfil solicitado.
"""
)


st.divider()
st.header("📄 Mi CV (contenido extraído)")

user_email = (me or {}).get("email")
if not user_email:
    st.info("Iniciá sesión para ver tu CV.")
    st.stop()

with st.spinner("Buscando tu CV…"):
    cv_doc, fetch_err = get_cv_by_email(user_email, full=True)

analisis = cv_doc.get("cv_analisis_gpt") or {}
nombre = analisis.get("nombre_completo", "—")
formacion = analisis.get("formacion_academica", "—")
exp_list = _as_list(analisis.get("experiencia_laboral"))
hab_list = _as_list(analisis.get("habilidades_tecnicas"))
idiomas = analisis.get("idiomas", "—")

st.write(f"**Nombre:** {nombre}")
st.write(f"**Email:** {user_email}")
st.write(f"**Formación académica:** {formacion}")
st.write("**Experiencia laboral:**")
for e in exp_list:
    st.write(f"- {e}")
st.write("**Habilidades técnicas:**")
for h in hab_list:
    st.write(f"- {h}")
st.write(f"**Idiomas:** {idiomas}")

if fetch_err:
    st.error(f"No se pudo obtener tu CV: {fetch_err}")
    st.stop()

if not cv_doc:
    st.warning("Aún no cargaste tu CV.")
    st.stop()


cv_id = cv_doc.get("cv_file_id")

if cv_id:
    if st.button("📥 Preparar descarga de mi PDF"):
        with st.spinner("Recuperando PDF…"):
            pdf_bytes = _download_pdf(cv_id)
        if pdf_bytes:
            st.download_button(
                label="Descargar mi CV (PDF)",
                data=pdf_bytes,
                file_name=f"{(nombre or 'mi_cv').replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.info("No se pudo recuperar el PDF desde GridFS.")
else:
    st.caption("No se encontró un archivo PDF asociado a este CV.")
