
# auth_ui.py
import streamlit as st
import login.auth_client as api


def login_or_register_panel() -> None:
    tab_login, tab_register = st.tabs(["Ingresar", "Registrarse"])

    # --- Login ---
    with tab_login:
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("Email", key="login_email")
            password = st.text_input(
                "Contraseña", type="password", key="login_password")
            submitted = st.form_submit_button("Entrar")
        if submitted:
            if not email or not password:
                st.warning("Completá email y contraseña.")
            else:
                ok, err = api.login_oauth(email, password)
                if ok:
                    st.success("Sesión iniciada ✅")
                    st.rerun()
                else:
                    st.error(f"Login falló: {err}")

    # --- Registro ---
    with tab_register:
        with st.form("register_form", clear_on_submit=True):
            username = st.text_input("Usuario")
            email_r = st.text_input("Email")
            password_r = st.text_input("Contraseña", type="password")
            submitted_r = st.form_submit_button("Crear cuenta")
        if submitted_r:
            if not username or not email_r or not password_r:
                st.warning("Completá todos los campos.")
            else:
                ok, err, created = api.register_user(
                    username, email_r, password_r)
                if ok:
                    st.success(
                        "Usuario creado. Podés ingresar en la pestaña 'Ingresar'.")
                else:
                    st.error(f"Registro falló: {err}")


def require_auth(roles: list[str] | None = None) -> dict:
    """
    Si no hay sesión válida, muestra Login/Registro y st.stop().
    Si hay sesión, retorna `me`. Con `roles`, exige al menos uno.
    """
    if not st.session_state.get("token"):
        st.info("Ingresá (o registrate) para continuar.")
        login_or_register_panel()
        st.stop()

    if st.session_state.get("me") is None:
        api.fetch_me()

    me = st.session_state.get("me")
    if not me:
        st.warning("Sesión inválida o expirada. Volvé a iniciar sesión.")
        login_or_register_panel()
        st.stop()

    if roles:
        user_roles = set(me.get("roles", []))
        if user_roles.isdisjoint(set(roles)):
            st.error("No tenés permisos para ver esta página.")
            st.stop()

    return me


def sidebar_user_box() -> None:
    me = st.session_state.get("me") or {}
    st.sidebar.caption(
        f"Hola:\n**{me.get('username', '')}**\n{me.get('email', '')}")
    if st.sidebar.button("⎋ Salir", use_container_width=True):
        api.logout()
        st.rerun()


def auth_bar() -> None:
    col1, col2 = st.columns([3, 1])
    with col1:
        me = st.session_state.get("me") or {}
        st.caption(f"Conectado como: {me.get('email', '(desconocido)')}")
