import os
from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

ASSISTANT_WHATSAPP_NUMBER = os.getenv("ASSISTANT_WHATSAPP_NUMBER")

DAILY_CHECK_TIME = os.getenv("DAILY_CHECK_TIME", "08:00")
TIMEZONE = os.getenv("TIMEZONE", "Africa/Niamey")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./nissa.db")

GOOGLE_SHEETS_ENABLED = os.getenv("GOOGLE_SHEETS_ENABLED", "false").lower() == "true"
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID", "")
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")
