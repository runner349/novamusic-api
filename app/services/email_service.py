import smtplib
from email.message import EmailMessage

from app.core.config import settings


def send_reset_email(to_email: str, reset_token: str) -> None:
    body = f"""
Hola,

Recibimos una solicitud para restablecer tu contraseña en NovaMusic.

Tu token de recuperación es:

{reset_token}

Este token expira en {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutos.

Si no solicitaste este cambio, puedes ignorar este correo.
"""

    msg = EmailMessage()
    msg["Subject"] = "Recuperación de contraseña - NovaMusic"
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to_email
    msg.set_content(body)

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
        server.starttls()
        server.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
        server.send_message(msg)