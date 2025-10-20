# pages/mi_perfil.py
import time
import streamlit as st
from datetime import date
from utils.api_cv import get_cv_by_email, update_profile_api, reupload_cv_api
from login.auth_state import init_state
from login.auth_ui import require_auth, auth_bar
from utils.menubar import navegacion_path, sidebar_user_box

st.set_page_config(page_title="Mi Perfil", layout="wide")
init_state()
me = require_auth()
auth_bar()
navegacion_path()
sidebar_user_box()

email = (me or {}).get("email")
if not email:
    st.info("Iniciá sesión para ver tu perfil.")
    st.stop()

with st.spinner("Cargando tu perfil…"):
    cv_doc, err = get_cv_by_email(email, full=True)  # ← trae cv_analisis_gpt y datos personales
if err:
    st.error(err)
    st.stop()
if not cv_doc:
    st.warning("Aún no cargaste tu CV. Podés hacerlo en 'Carga tu CV'.")
    st.stop()

st.header("👤 Mi Perfil")
col1, col2 = st.columns(2)
with col1:
    nombre   = st.text_input("Nombre", value=cv_doc.get("nombre", ""))
    apellido = st.text_input("Apellido", value=cv_doc.get("apellido", ""))
    ciudad   = st.text_input("Ciudad", value=cv_doc.get("ciudad", ""))
    direccion= st.text_input("Dirección", value=cv_doc.get("direccion", ""))

with col2:
    # fecha_nacimiento viene como string ISO o None
    fn_iso = cv_doc.get("fecha_nacimiento")
    try:
        fn = date.fromisoformat(fn_iso) if fn_iso else None
    except Exception:
        fn = None
    fecha_nac = st.date_input("Fecha de nacimiento", value=fn) if fn else st.date_input("Fecha de nacimiento")
    edad = st.number_input("Edad", min_value=0, max_value=120, value=int(cv_doc.get("edad") or 0))

if st.button("Guardar cambios", type="primary"):
    payload = {
        "email": email,
        "nombre": nombre,
        "apellido": apellido,
        "ciudad": ciudad,
        "direccion": direccion,
        "fecha_nacimiento": fecha_nac.isoformat() if fecha_nac else None,
        "edad": int(edad) if edad else None,
    }
    ok, uerr = update_profile_api(payload)
    if ok:
        st.success("Perfil actualizado ✅")
        st.toast("Cambios guardados", icon="✅")
        time.sleep(0.6)
        st.rerun()
    else:
        st.error(uerr or "No se pudo actualizar el perfil.")

st.divider()
st.subheader("📄 Re-subir CV")

colA, colB = st.columns([3,1])
with colA:
    new_cv = st.file_uploader("Elegí un nuevo archivo PDF", type=["pdf"])
with colB:
    keep_history = st.toggle("Mantener historial", value=False, help="Si está activo, se guarda un nuevo registro (no se borra el archivo anterior).")

if st.button("Subir nuevo CV", disabled=not new_cv):
    with st.status("Procesando nuevo CV…", expanded=True) as stt:
        stt.write("Subiendo archivo…")
        doc_id, rerr = reupload_cv_api(email=email, cv_file=new_cv, keep_history=keep_history)
        if rerr:
            stt.update(label="❌ Error al re-subir CV", state="error")
            st.error(rerr)
        else:
            stt.write("Extrayendo y generando embeddings…")
            stt.update(label="✅ ¡Listo! CV actualizado", state="complete")
            st.success(f"Nuevo CV guardado (doc id: {doc_id})")
            st.toast("CV actualizado", icon="✅")
            time.sleep(0.8)
            st.rerun()
