# app_notify.py
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from notification.mailer import enviar_email_smtp

notification_router = APIRouter(prefix="/notification", tags=["Notifications"])

# --- HARDCODE PARA PRUEBA ---
# Variante MAILTRAP (sandbox): usa tus credenciales reales de Mailtrap aquí
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "manciprograma@gmail.com"
SMTP_PASS = "uzxq bzag grms swjx "
SENDER_NAME = "RRHH"
REPLY_TO = None


# --- FIN HARDCODE ---

class NotifyReq(BaseModel):
    emails: List[EmailStr] = Field(..., min_items=1)
    subject: str = Field(..., min_length=3, max_length=200)
    body: str = Field(..., min_length=1)
    is_html: bool = False


class NotifyResp(BaseModel):
    ok: bool
    sent: int
    errors: List[str] = []
    message: Optional[str] = None


def _send_batch(req: NotifyReq):
    enviar_email_smtp(
        smtp_host=SMTP_HOST,
        smtp_port=SMTP_PORT,
        smtp_user=SMTP_USER,
        smtp_pass=SMTP_PASS,
        destinatarios=req.emails,
        asunto=req.subject,
        cuerpo_html=req.body if req.is_html else None,
        cuerpo_texto=req.body if not req.is_html else None,
        remitente_name=SENDER_NAME,
        # reply_to=REPLY_TO  # si querés usarlo
    )


@notification_router.get("/health")
def health():
    return {
        "host": SMTP_HOST,
        "port": SMTP_PORT,
        "user_set": bool(SMTP_USER),
        "pass_set": bool(SMTP_PASS),
        "sender_name": SENDER_NAME,
    }


@notification_router.post("/notify", response_model=NotifyResp)
def notify(req: NotifyReq, background: BackgroundTasks):
    missing = []
    if not SMTP_HOST:
        missing.append("SMTP_HOST")
    if not SMTP_PORT:
        missing.append("SMTP_PORT")
    if not SMTP_USER:
        missing.append("SMTP_USER")
    if not SMTP_PASS:
        missing.append("SMTP_PASS")
    if missing:
        raise HTTPException(
            status_code=500, detail=f"SMTP no configurado. Faltan: {', '.join(missing)}")

    background.add_task(_send_batch, req)
    return NotifyResp(ok=True, sent=len(req.emails), message="Envío programado")
