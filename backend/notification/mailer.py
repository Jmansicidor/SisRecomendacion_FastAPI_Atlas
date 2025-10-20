# notification/mailer.py
import smtplib
import ssl
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Tuple, Optional


class MailResult:
    def __init__(self):
        self.sent = 0
        self.errors: list[str] = []
        self.per_recipient: list[tuple[str, bool,
                                       str | None]] = []  # (to, ok, err)


def enviar_email_smtp(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_pass: str,
    destinatarios: List[str],
    asunto: str,
    cuerpo_html: str | None = None,
    cuerpo_texto: str | None = None,
    remitente_name: str | None = None,
    reply_to: str | None = None,
    timeout: int = 20,
    max_retries: int = 2,
) -> MailResult:
 
    res = MailResult()
    if not destinatarios:
        res.errors.append("Lista de destinatarios vacía")
        return res

    from_header = f"{remitente_name} <{smtp_user}>" if remitente_name else smtp_user

    # Preparar MIME base (adjuntando partes luego por destinatario)
    def build_message(to_addr: str) -> MIMEMultipart:
        msg = MIMEMultipart("alternative")
        msg["From"] = from_header
        msg["To"] = to_addr
        msg["Subject"] = asunto
        if reply_to:
            msg.add_header("Reply-To", reply_to)

        # Si no viene texto, generamos uno a partir del HTML pelado
        plain = cuerpo_texto or (cuerpo_html or "").replace(
            "<br>", "\n").replace("<br/>", "\n")
        if plain:
            msg.attach(MIMEText(plain, "plain", "utf-8"))
        if cuerpo_html:
            msg.attach(MIMEText(cuerpo_html, "html", "utf-8"))
        return msg

    # Conexión (SSL 465 o STARTTLS 587)
    context = ssl.create_default_context()
    for attempt in range(max_retries + 1):
        try:
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(
                    host=smtp_host, port=smtp_port, timeout=timeout, context=context)
            else:
                server = smtplib.SMTP(
                    host=smtp_host, port=smtp_port, timeout=timeout)
                server.starttls(context=context)
            server.login(smtp_user, smtp_pass)
            break
        except Exception as e:
            if attempt >= max_retries:
                res.errors.append(f"Conexión SMTP falló: {e}")
                return res
            time.sleep(0.8 * (attempt + 1))
    # envío por destinatario
    try:
        for to in destinatarios:
            try:
                msg = build_message(to)
                server.sendmail(smtp_user, [to], msg.as_string())
                res.sent += 1
                res.per_recipient.append((to, True, None))
            except Exception as e:
                res.errors.append(f"{to}: {e}")
                res.per_recipient.append((to, False, str(e)))
    finally:
        try:
            server.quit()
        except Exception:
            pass

    return res
