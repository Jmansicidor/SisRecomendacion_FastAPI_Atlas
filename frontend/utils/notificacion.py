# utils/notificacion.py
from typing import List, Tuple, Optional
import streamlit as st
import requests
import pandas as pd

# -------- helpers de compatibilidad --------


def _col_score(df: pd.DataFrame) -> str:
    """Devuelve la columna que representa el score global."""
    if "score" in df.columns:
        return "score"
    if "compatibilidad" in df.columns:
        return "compatibilidad"
    # fallback: si no existe ninguna, creamos score=0
    if "score" not in df.columns:
        df["score"] = 0.0
    return "score"


def _col_cos(df: pd.DataFrame) -> str:
    """Devuelve la columna que representa el coseno/ similitud semántica."""
    if "score_cos" in df.columns:
        return "score_cos"
    if "similitud" in df.columns:
        return "similitud"
    if "score_cos" not in df.columns:
        df["score_cos"] = 0.0
    return "score_cos"


def _resolve_selection(df: pd.DataFrame, modo: str, edited_df: Optional[pd.DataFrame], n: int, umbral: float) -> pd.DataFrame:
    """Devuelve el subset de candidatos seleccionados en base al 'modo'."""
    if df.empty:
        return df

    col_score = _col_score(df)

    if modo == "Todos":
        return df
    elif modo == "Peores N":
        n = max(1, min(n, len(df)))
        return df.sort_values(col_score, ascending=True).head(n)
    elif modo == "Por debajo de umbral":
        return df[df[col_score] < umbral]
    elif modo == "Selección manual":
        if edited_df is None:
            return df.iloc[0:0]
        # edited_df viene con columna booleana "Seleccionar"
        # devolvemos solo las filas marcadas
        return edited_df[edited_df.get("Seleccionar", False) == True]
    else:
        return df.iloc[0:0]


def _emails_from_df(df: pd.DataFrame) -> List[str]:
    if "email" not in df.columns:
        return []
    return [e for e in df["email"].tolist() if isinstance(e, str) and e.strip()]

# -------- API --------


def send_notifications_via_api(
    emails: List[str],
    subject: str,
    body: str,
    api_base: str,
    is_html: bool = False,
    endpoint: str = "/notification/notify",
    timeout: int = 30
) -> Tuple[bool, str]:
    if not emails:
        return False, "No hay emails para notificar."

    try:
        resp = requests.post(
            f"{api_base.rstrip('/')}{endpoint}",
            json={"emails": emails, "subject": subject,
                  "body": body, "is_html": is_html},
            timeout=timeout
        )
        if resp.status_code == 200:
            return True, f"Notificaciones enviadas a {len(emails)} destinatarios."
        return False, f"Error {resp.status_code}: {resp.text}"
    except Exception as e:
        return False, f"Fallo al contactar la API: {e}"

# -------- UI principal --------


def render_notify_panel(
    df_ranking: pd.DataFrame,
    api_base: str,
    default_subject: str = "Estado de tu postulación",
    default_body: str = (
        "Hola, muchas gracias por postularte. En esta instancia no daremos continuidad "
        "a tu candidatura, pero guardaremos tu CV para futuras oportunidades. ¡Éxitos!"
    ),
    show_table_above: bool = True,
) -> None:
    """
    Panel completo de selección + envío de notificaciones.
    Funciona con columnas nuevas ('score','score_cos') o viejas ('compatibilidad','similitud').
    """

    st.markdown("### ✉️ Notificaciones a candidatos")

    # Clonar para no modificar el df original
    df = df_ranking.copy()

    # Asegurar columnas de compatibilidad
    col_score = _col_score(df)      # 'score' o 'compatibilidad'
    col_cos = _col_cos(df)        # 'score_cos' o 'similitud'

    # Mostrar tabla base (opcional)
    if show_table_above:
        cols_show = ["nombre", "email", col_score, col_cos]
        cols_show = [c for c in cols_show if c in df.columns]
        if cols_show:
            st.dataframe(df[cols_show], hide_index=True,
                         use_container_width=True)

    # Modo de selección
    modo = st.radio(
        "¿A quiénes notificar?",
        ["Todos", "Peores N", "Por debajo de umbral", "Selección manual"],
        horizontal=True
    )

    n, umbral, edited_df = 0, 0.0, None
    if modo == "Peores N":
        n = st.number_input("Cantidad (N)", min_value=1,
                            max_value=len(df), value=min(10, len(df)))
    elif modo == "Por debajo de umbral":
        st.caption(f"Filtra por {col_score} (0–1)")
        umbral = st.slider("Umbral", 0.0, 1.0, 0.30, 0.01)
    elif modo == "Selección manual":
        df_edit = df.copy()
        df_edit.insert(0, "Seleccionar", False)
        # mostrar las columnas que existan
        base_cols = ["Seleccionar", "nombre", "email", col_score, col_cos]
        base_cols = [c for c in base_cols if c in df_edit.columns]
        edited_df = st.data_editor(
            df_edit[base_cols],
            hide_index=True,
            use_container_width=True
        )

    # Resolver selección
    seleccion_df = _resolve_selection(df, modo, edited_df, n, umbral)
    emails = _emails_from_df(seleccion_df)

    st.markdown(f"**Candidatos seleccionados:** {len(emails)}")
    with st.expander("Ver emails seleccionados"):
        st.write(emails if emails else "—")

    # Mensaje
    st.markdown("#### Mensaje")
    subject = st.text_input("Asunto", value=default_subject)
    is_html = st.checkbox("¿El cuerpo es HTML?", value=False)
    body = st.text_area("Cuerpo", value=default_body, height=140)

    # (Opcional) Vista previa si es HTML
    if is_html and body.strip():
        with st.expander("🔎 Vista previa HTML"):
            st.markdown(body, unsafe_allow_html=True)

    # Confirmación y envío
    colA, colB = st.columns([1, 1])
    with colA:
        disabled = len(emails) == 0 or not subject.strip() or not body.strip()
        if st.button("Enviar notificación", type="primary", disabled=disabled, use_container_width=True):
            ok, msg = send_notifications_via_api(
                emails, subject, body, api_base, is_html=is_html)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

    with colB:
        st.info("⚠️ Esta acción enviará correos reales a los candidatos seleccionados.")
