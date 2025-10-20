import streamlit as st
import login.auth_client as api


def sidebar_user_box() -> None:
    """Muestra datos del usuario y botón Salir en el sidebar."""
    me = st.session_state.get("me") or {}
    st.sidebar.caption(
        f"Conectado como:\n**{me.get('username', '')}**\n{me.get('email', '')}")
    if st.sidebar.button("⎋ Salir", use_container_width=True):
        api.logout()
        st.rerun()


def sidebar_nav(nav_items: list[dict]) -> None:

    me = st.session_state.get("me") or {}
    user_roles = set(me.get("roles", []))

    st.sidebar.divider()
    st.sidebar.subheader("Navegación")

    for item in nav_items:
        allowed = set(item.get("roles", []))
        if not allowed or not user_roles.isdisjoint(allowed):
            # Streamlit 1.25+ tiene st.page_link para multipage
            if hasattr(st, "page_link"):
                st.sidebar.page_link(
                    item["path"],
                    label=item.get("label", item["path"]),
                    icon=item.get("icon", None),
                )
            else:
                # Fallback: intento de cambiar de página
                label = f"{item.get('icon', '')} {item.get('label', item['path'])}".strip(
                )
                if st.sidebar.button(label, key=f"nav_{item['path']}"):
                    try:
                        st.switch_page(item["path"])
                    except Exception:
                        st.experimental_set_query_params(page=item["path"])


def navegacion_path():
    """Ejemplo de mapa de navegación por rol."""
    NAV_ITEMS = [
        {"path": "app.py", "label": "Inicio",  "icon": "🏠",
         "roles": []},               # visible para todos logueados
        {"path": "pages/perfiles.py",   "label": "Perfil buscado",
         "icon": "🪪", "roles": ["admin"]},
        {"path": "pages/loadCv.py",    "label": "Cargar CV",
         "icon": "📄", "roles": ["user", "admin"]},
        {"path": "pages/metricas.py",    "label": "Metricas",
         "icon": "📋", "roles": ["admin"]},
        {"path": "pages/perfil_usuario.py",    "label": "Mi Perfil",
         "icon": "👤", "roles": ["user", "admin"]},

    ]
    sidebar_nav(NAV_ITEMS)
