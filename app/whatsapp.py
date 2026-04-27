"""Client WhatsApp via Twilio."""

import os
import logging

logger = logging.getLogger("nissa.whatsapp")


def _get_client():
    """Cree et retourne un client Twilio."""
    from twilio.rest import Client
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    if not sid or not token:
        logger.error(f"Config Twilio manquante: SID={'OK' if sid else 'MANQUANT'}, Token={'OK' if token else 'MANQUANT'}")
        return None
    return Client(sid, token)


def _to_whatsapp(phone: str) -> str:
    """Convertit un numero au format Twilio WhatsApp.

    Exemples:
        '+2250586752574' -> 'whatsapp:+2250586752574'
        'whatsapp:+2250586752574' -> 'whatsapp:+2250586752574'
        '2250586752574' -> 'whatsapp:+2250586752574'
    """
    phone = phone.strip()
    if phone.startswith("whatsapp:"):
        return phone
    if not phone.startswith("+"):
        phone = f"+{phone}"
    return f"whatsapp:{phone}"


def send_message(to: str, body: str) -> dict:
    """Envoie un message WhatsApp via Twilio."""
    try:
        client = _get_client()
        if not client:
            return {"success": False, "error": "Client Twilio non configure"}

        from_number = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
        to_number = _to_whatsapp(to)

        message = client.messages.create(
            from_=from_number,
            to=to_number,
            body=body,
        )
        logger.info(f"Message envoye a {to_number} (SID: {message.sid})")
        return {"success": True, "message_id": message.sid}

    except Exception as e:
        logger.error(f"Erreur envoi message a {to}: {e}")
        return {"success": False, "error": str(e)}


def send_question(to: str, body: str) -> dict:
    """Envoie une question.

    Twilio Sandbox ne supporte pas les boutons interactifs,
    donc on envoie un message texte simple.
    """
    return send_message(to, body)
