# pages/loadCV.py
import time
from datetime import date
import streamlit as st
from utils.menubar import sidebar_user_box, navegacion_path
from login.auth_state import init_state
from login.auth_ui import require_auth, auth_bar
from utils.api_cv import guardar_cv as guardar_cv_api
from utils.api_perfil import obtener_perfil_activo_publico_api


st.set_page_config(page_title="Carga de CV", layout="wide")


# --- Auth / UI ---
init_state()
me = require_auth()
auth_bar()
navegacion_path()
sidebar_user_box()

redirect_flag_key = "_go_home_after_upload"


@st.cache_data(show_spinner=False, ttl=60)
def _get_busqueda_activa() -> dict | None:
    access_token = st.session_state.get(
        "access_token")  # si tu API lo requiere
    perfil, err = obtener_perfil_activo_publico_api(access_token=access_token)
    if err:
        return None
    return perfil


with st.spinner("Cargando búsqueda activa…"):
    p = _get_busqueda_activa()

if not p:
    st.info("No hay búsquedas publicadas por el momento.")
    st.stop()

st.title(":orange[Carga tu CV]")
st.subheader(f"Aplicar al puesto de: :red[{p.get('puesto', '—')}]")

# --- Formulario ---
formA = st.form(key="formA")
firstname = formA.text_input("Nombre *")
lastname = formA.text_input("Apellido *")
city = formA.text_input("Ciudad")
address = formA.text_input("Dirección")
fecha_nac = formA.date_input(
    "Fecha de nacimiento *",
    min_value=date(1950, 1, 1),
    max_value=date.today(),
    help="Seleccioná tu fecha de nacimiento"
)
archivo_cv = formA.file_uploader("Cargar CV (.pdf) *", type=["pdf"])

submit_button = formA.form_submit_button("Aplicar")
formA.page_link("app.py", label="Salir", icon="❌")

if submit_button:
    # Validación
    st.info('El procesamiento de tu CV puede demorar por favor no salgas ni cierre la pagina', icon="ℹ️")
    if not firstname or not lastname or not archivo_cv or not fecha_nac:
        st.error("Completa los campos marcados con * y carga tu CV.")
        st.stop()

    with st.status("⏳ Subiendo y procesando tu CV con IA…", expanded=True) as status:
        status.write("1/3 Subiendo archivo al servidor…")

    # Edad (el resto lo hace el backend)
    hoy = date.today()
    edad = hoy.year - fecha_nac.year - \
        ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))

    # Enviar al backend (sin reed_cv, sin cv_text, sin tokens, sin cv_vector)
    inserted_id, error = guardar_cv_api(
        firstname=firstname,
        lastname=lastname,
        city=city,
        address=address,
        mail=(me or {}).get("email", ""),
        cv_file=archivo_cv,              # el wrapper arma el multipart con el PDF
        extracted_data={},               # el backend ahora hace la extracción/embedding
        fecha_nacimiento=fecha_nac,
        edad=edad,
        cv_text="",                      # opcional; lo dejamos vacío
        cv_vector=None,                  # que lo calcule el backend
        tokens_formacion=None,
        tokens_habilidades=None,
        tokens_experiencia=None,
        # access_token=st.session_state.get("access_token")  # descomenta si tu API lo requiere
    )

    if error:
        status.update(
            label="❌ Ocurrió un error procesando tu CV", state="error")
        st.error(error)
    else:
        time.sleep(1.2)
        status.write("2/3 Extrayendo información del CV…")
        time.sleep(1.2)
        status.write(
            "3/3 Generando embeddings y guardando en base de datos…")
        time.sleep(1.2)
        status.update(
            label="✅ ¡Listo! Tu CV fue procesado con IA", state="complete")
        time.sleep(1.2)

        st.success(
            f"¡Gracias {firstname}! Tu CV se cargó (ID: {inserted_id})")
        st.toast("CV cargado con éxito", icon="✅")

        st.session_state[redirect_flag_key] = True

    # redirección suave al terminar
if st.session_state.get(redirect_flag_key):
    time.sleep(1.2)
    st.session_state.pop(redirect_flag_key, None)
    st.switch_page("app.py")
