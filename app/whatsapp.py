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


def _get_api_config():
    """Recupere le token et phone_id depuis les variables d'env."""
    token = os.getenv("WHATSAPP_TOKEN")
    phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    return token, phone_id


def _send_payload(recipient: str, payload: dict) -> dict:
    """Envoie un payload a l'API Meta WhatsApp."""
    token, phone_id = _get_api_config()

    if not token or not phone_id:
        error = f"Config manquante: token={'OK' if token else 'MANQUANT'}, phone_id={'OK' if phone_id else 'MANQUANT'}"
        logger.error(error)
        return {"success": False, "error": error}

    url = f"https://graph.facebook.com/v21.0/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
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
        logger.error(f"Erreur envoi message a {recipient}: {e}")
        return {"success": False, "error": str(e)}


def send_message(to: str, body: str) -> dict:
    """Envoie un message texte simple."""
    recipient = _normalize_phone(to)
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "text",
        "text": {"body": body},
    }
    return _send_payload(recipient, payload)


def send_buttons(to: str, body: str, buttons: list[dict]) -> dict:
    """Envoie un message avec des boutons interactifs.

    Args:
        to: numero du destinataire
        body: texte de la question
        buttons: liste de {"id": "oui", "title": "OUI"}
    """
    recipient = _normalize_phone(to)
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": btn["id"], "title": btn["title"]}}
                    for btn in buttons
                ]
            },
        },
    }
    return _send_payload(recipient, payload)


OUI_NON_BUTTONS = [
    {"id": "oui", "title": "OUI"},
    {"id": "non", "title": "NON"},
]


def send_question(to: str, body: str) -> dict:
    """Envoie une question avec les boutons OUI / NON."""
    return send_buttons(to, body, OUI_NON_BUTTONS)
