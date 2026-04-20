"""Client WhatsApp Cloud API (Meta Graph API)."""

import os
import logging
import httpx

logger = logging.getLogger("nissa.whatsapp")


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


def send_message(to: str, body: str) -> dict:
    """Envoie un message WhatsApp via Meta Cloud API.

    Retourne un dict avec le resultat (pour debug).
    """
    token = os.getenv("WHATSAPP_TOKEN")
    phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

    if not token or not phone_id:
        error = f"Config manquante: token={'OK' if token else 'MANQUANT'}, phone_id={'OK' if phone_id else 'MANQUANT'}"
        logger.error(error)
        return {"success": False, "error": error}

    url = f"https://graph.facebook.com/v21.0/{phone_id}/messages"
    recipient = _normalize_phone(to)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "text",
        "text": {"body": body},
    }

    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(url, headers=headers, json=payload)
            data = response.json()

            if response.status_code >= 400:
                logger.error(f"Erreur API Meta ({response.status_code}): {data}")
                return {"success": False, "status": response.status_code, "error": data}

            msg_id = data.get("messages", [{}])[0].get("id", "?")
            logger.info(f"Message envoye a {recipient} (ID: {msg_id})")
            return {"success": True, "message_id": msg_id}

    except Exception as e:
        logger.error(f"Erreur envoi message a {to}: {e}")
        return {"success": False, "error": str(e)}
