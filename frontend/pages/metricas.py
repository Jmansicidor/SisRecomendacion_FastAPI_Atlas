# pages/metricas.py
import math
import pandas as pd
import requests
import streamlit as st

from backend.auth.utils.permissions import require_roles
from login.auth_state import init_state
from login.auth_ui import require_auth, auth_bar
from utils.menubar import navegacion_path, sidebar_user_box
from utils.api_metricas import get_ranking, rebuild_ranking
from utils.notificacion import render_notify_panel
from utils.api_cv import get_cv_by_email

st.set_page_config(page_title="Métricas de Candidatos", layout="wide")

# --- Auth / UI ---
init_state()
me = require_auth()
auth_bar()
navegacion_path()
sidebar_user_box()
require_roles({"admin"})


API_BASE = st.secrets.get("API_BASE", "http://backend:8000").rstrip("/")

# --- Toggle de debug en barra lateral ---
DEBUG_DL = st.sidebar.toggle("🔎 Debug descarga CV", value=False)

# ---------- Helpers ----------


@st.cache_data(ttl=120, show_spinner=False)
def _get_cv_count() -> int | None:
    headers = {}
    if st.session_state.get("access_token"):
        headers["Authorization"] = f"Bearer {st.session_state['access_token']}"
    try:
        # 1) intento con /api/cv/count
        r = requests.get(f"{API_BASE}/api/cv/count",
                         headers=headers, timeout=20)
        if r.ok:
            return (r.json() or {}).get("count", None)
        # 2) fallback sin /api
        r2 = requests.get(f"{API_BASE}/cv/count", headers=headers, timeout=20)
        if r2.ok:
            return (r2.json() or {}).get("count", None)
    except Exception:
        pass
    return None


def _download_cv_bytes_by_file_id(cv_file_id: str) -> bytes | None:
    """Descarga el PDF vía /api/cv/file/{id}. Si DEBUG_DL está activo, muestra URL y status al fallar."""
    if not cv_file_id:
        return None
    try:
        headers = {}
        if st.session_state.get("access_token"):
            headers["Authorization"] = f"Bearer {st.session_state['access_token']}"
        url = f"{API_BASE}/api/cv/file/{cv_file_id}"
        r = requests.get(url, headers=headers, timeout=60)
        if r.ok:
            return r.content
        else:
            if DEBUG_DL:
                st.error(
                    f"CV no disponible (HTTP {r.status_code}) — URL={url}")
            return None
    except Exception as e:
        if DEBUG_DL:
            st.error(f"Error al descargar: {type(e).__name__}: {e}")
        return None


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_ranking(perfil_id: str | None, limit: int):
    data = get_ranking(perfil_id=perfil_id, limit=limit, timeout=60)  # dict
    items = data.get("items", []) or []

    flat = []
    for it in items:
        row = dict(it)  # copia superficial

        # 1) aplanar snapshot si existe
        snap = row.pop("snapshot", {}) or {}
        for k in ("nombre", "apellido", "email", "cv_file_id"):
            if k not in row and k in snap:
                row[k] = snap.get(k)

        # 2) compat con respuesta vieja
        if "score" not in row and "compatibilidad" in row:
            row["score"] = row.get("compatibilidad", 0)
        if "score_cos" not in row and "similitud" in row:
            row["score_cos"] = row.get("similitud", 0)
        if "score_j_total" not in row:
            j_parts = []
            for jk in ("sim_atributos", "sim_experiencia", "sim_educacion", "sim_idiomas", "sim_idioma"):
                if jk in row and row[jk] is not None:
                    j_parts.append(row[jk])
            row["score_j_total"] = (
                sum(j_parts) / len(j_parts)) if j_parts else row.get("score_j_total", 0)

        # 3) coerción a float
        for k in ("score", "score_cos", "score_j_total", "score_j_hab", "score_j_exp", "score_j_edu", "score_j_idi"):
            try:
                row[k] = float(row.get(k, 0) or 0)
            except Exception:
                row[k] = 0.0

        flat.append(row)

    data["items"] = flat
    # st.write("DEBUG first item:"); st.json(flat[:1])
    return data


# ---------- Encabezado ----------
ci1, ci2 = st.columns([4, 1])
with ci1:
    st.header("🏆 Métricas / Ranking de Candidatos")
with ci2:
    total_cv = _get_cv_count()
    st.metric(label="Total CV Recibidos",
              value=total_cv if total_cv is not None else "—")

# ---------- Controles ----------
topN_col, perfil_col, actions_col = st.columns([1, 2, 2])

with topN_col:
    topN = st.selectbox("Top N", [10, 25, 50, 100, 200], index=2)

with perfil_col:
    perfil_id_opt = st.text_input(
        "Perfil ID (opcional)", value="", placeholder="Si lo dejás vacío usa el activo")

with actions_col:
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Refrescar"):
            st.cache_data.clear()
            st.rerun()
    with c2:
        if st.button("🛠️ Recalcular"):
            with st.status("Recalculando métricas…", expanded=True) as stt:
                try:
                    info = rebuild_ranking(
                        perfil_id=perfil_id_opt or None, timeout=600)
                    stt.update(
                        label=f"✅ OK: {info.get('updated', 0)} CVs recalculados", state="complete")
                    st.toast("Rebuild completo", icon="✅")
                except Exception as e:
                    stt.update(label="❌ Error en rebuild", state="error")
                    st.error(str(e))

# ---------- Traer ranking ----------
with st.spinner("Obteniendo ranking…"):
    try:
        data = _fetch_ranking(perfil_id_opt or None, topN)
    except Exception as e:
        st.error(f"No se pudo obtener el ranking: {e}")
        st.stop()

items = (data or {}).get("items", [])
if not items:
    st.info("Aún no hay candidatos con métricas calculadas o no hay un perfil activo.")
    st.stop()
perfil_id = (data or {}).get("perfil_id")
count = (data or {}).get("count", len(items))

st.caption(f"Perfil: {perfil_id or 'activo'} • Ítems: {count}")

# ---------- DataFrame ----------
df = pd.DataFrame(items)

prefer_order = [c for c in ["nombre", "apellido", "email", "score",
                            "score_cos", "score_j_total", "cv_id", "cv_file_id"] if c in df.columns]
if prefer_order:
    df = df[prefer_order]

# ---------- Filtros ----------
with st.expander("🔧 Filtros", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        min_score = st.slider("Score mínimo", 0.0, 1.0, 0.50, step=0.05)
    with c2:
        max_score = st.slider("Score máximo", 0.0, 1.0, 1.00, step=0.05)
    name_query = st.text_input(
        "🔍 Buscar por nombre o email", placeholder="Escribí parte del nombre o email…")

df_view = df.copy()
if "score" in df_view.columns:
    df_view = df_view[(df_view["score"] >= min_score) &
                      (df_view["score"] <= max_score)]

if name_query:
    if "nombre" in df_view.columns:
        df_view = df_view[df_view["nombre"].fillna(
            "").str.contains(name_query, case=False)]
    if "apellido" in df_view.columns:
        df_view = df_view[df_view["apellido"].fillna("").str.contains(name_query, case=False) |
                          (df_view["nombre"].fillna("").str.contains(name_query, case=False))]
    if "email" in df_view.columns:
        df_view = df_view[df_view["email"].fillna("").str.contains(name_query, case=False) |
                          (df_view["nombre"].fillna("").str.contains(name_query, case=False))]

# ---------- Tabla ----------
st.subheader("Candidatos (filtrados)")
col_cfg = {}
if "score" in df_view.columns:
    col_cfg["score"] = st.column_config.ProgressColumn(
        "Score", help="Puntuación combinada", format="%.3f", min_value=0.0, max_value=1.0)
if "score_cos" in df_view.columns:
    col_cfg["score_cos"] = st.column_config.ProgressColumn(
        "Coseno", help="Similitud semántica embeddings", format="%.3f", min_value=0.0, max_value=1.0)
if "score_j_total" in df_view.columns:
    col_cfg["score_j_total"] = st.column_config.ProgressColumn(
        "Jaccard", help="Coincidencias discretas (skills/exp/edu/idiomas)", format="%.3f", min_value=0.0, max_value=1.0)

st.dataframe(df_view, hide_index=True,
             use_container_width=True, column_config=col_cfg)

# ---------- Descarga de CV ----------


st.markdown("### 📄 Descarga de CVs")
if "cv_file_id" not in df.columns:
    st.info("Para habilitar descargas directas, guarda `cv_file_id` en el snapshot del ranking desde el backend.")
else:
    dl_query = st.text_input(
        "🔍 Buscar candidato por email para descargar su CV", placeholder="Escribí parte del nombre…")
    if dl_query:
        df_filtrado = df_view[df_view["email"].fillna(
            "").str.contains(dl_query, case=False)]
        if df_filtrado.empty:
            st.warning(f"No se encontraron candidatos para \"{dl_query}\".")
        else:
            for _, row in df_filtrado.iterrows():
                nombre = f"{row.get('nombre', '')} {row.get('apellido', '')}".strip(
                ) or row.get("email", "candidato")
                cv_file_id = row.get("cv_file_id")
                if not cv_file_id:
                    st.error("CV no disponible (cv_file_id ausente).")
                    continue
                pdf_bytes = _download_cv_bytes_by_file_id(cv_file_id)
                if pdf_bytes:
                    st.download_button(
                        label="📄 Descargar CV",
                        data=pdf_bytes,
                        file_name=f"{nombre.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        key=f"dl-{cv_file_id}"
                    )
                else:
                    st.error("CV no disponible")

st.divider()

# Notificaciones
render_notify_panel(
    df_ranking=df,
    api_base=API_BASE,
    default_subject="Estado de tu postulación",
    default_body=(
        "SISTEMA DE RECOMENDACIÓN - RRHH\n\n"
        "Estimado/a:\n\n"
        "Nos comunicamos en relación a su postulación para la vacante disponible. "
        "En esta etapa, continuaremos con otros candidatos. Agradecemos el tiempo y el interés. "
        "Guardamos sus datos para futuras búsquedas.\n\n"
        "Saludos cordiales,\n"
        "Equipo de Recursos Humanos"
    ),
    show_table_above=True,
)
