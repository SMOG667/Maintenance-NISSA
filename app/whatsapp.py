import logging
from twilio.rest import Client

from app.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER

logger = logging.getLogger("nissa.whatsapp")

_client = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    return _client


def send_message(to: str, body: str) -> bool:
    """Envoie un message WhatsApp via Twilio."""
    try:
        client = get_client()
        message = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            to=to,
            body=body,
        )
        logger.info(f"Message envoye a {to} (SID: {message.sid})")
        return True
    except Exception as e:
        logger.error(f"Erreur envoi message a {to}: {e}")
        return False
