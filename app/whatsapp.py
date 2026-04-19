"""Client WhatsApp Cloud API (Meta Graph API)."""

import logging
import httpx

from app.config import WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID

logger = logging.getLogger("nissa.whatsapp")

GRAPH_API_URL = f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"


def _normalize_phone(phone: str) -> str:
    """Convertit un numero au format Meta (sans + ni whatsapp:).

    Exemples:
        '+22790000000' -> '22790000000'
        'whatsapp:+22790000000' -> '22790000000'
        '22790000000' -> '22790000000'
    """
    phone = phone.replace("whatsapp:", "").strip()
    if phone.startswith("+"):
        phone = phone[1:]
    return phone


def send_message(to: str, body: str) -> bool:
    """Envoie un message WhatsApp via Meta Cloud API."""
    try:
        recipient = _normalize_phone(to)
        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {"body": body},
        }
        with httpx.Client(timeout=30) as client:
            response = client.post(GRAPH_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            msg_id = data.get("messages", [{}])[0].get("id", "?")
            logger.info(f"Message envoye a {recipient} (ID: {msg_id})")
            return True
    except Exception as e:
        logger.error(f"Erreur envoi message a {to}: {e}")
        return False
