import os
from dotenv import load_dotenv

load_dotenv()

# Twilio WhatsApp
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

# Assistante - numero WhatsApp pour recevoir les alertes
ASSISTANT_WHATSAPP_NUMBER = os.getenv("ASSISTANT_WHATSAPP_NUMBER")

# Base de donnees (Supabase PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./nissa.db")

# Cron secret (protege l'endpoint /cron/daily-check)
CRON_SECRET = os.getenv("CRON_SECRET", "")

# Stripe
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Google Sheets (optionnel)
GOOGLE_SHEETS_ENABLED = os.getenv("GOOGLE_SHEETS_ENABLED", "false").lower() == "true"
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID", "")
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")
