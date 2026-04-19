import os
from dotenv import load_dotenv

load_dotenv()

# WhatsApp Cloud API (Meta)
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "nissa_verify")

# Assistante - numero WhatsApp pour recevoir les alertes (format: +227XXXXXXXX)
ASSISTANT_WHATSAPP_NUMBER = os.getenv("ASSISTANT_WHATSAPP_NUMBER")

# Base de donnees (Supabase PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./nissa.db")

# Cron secret (protege l'endpoint /cron/daily-check)
CRON_SECRET = os.getenv("CRON_SECRET", "")

# Google Sheets (optionnel)
GOOGLE_SHEETS_ENABLED = os.getenv("GOOGLE_SHEETS_ENABLED", "false").lower() == "true"
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID", "")
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")
