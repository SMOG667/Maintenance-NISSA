"""Integration Google Sheets pour visualisation des donnees."""

import logging
from datetime import date

import gspread
from google.oauth2.service_account import Credentials

from app.config import GOOGLE_SHEETS_ENABLED, GOOGLE_SHEETS_ID, GOOGLE_SERVICE_ACCOUNT_FILE
from app.models import Response

logger = logging.getLogger("nissa.sheets")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_client = None


def get_sheet():
    """Obtient la feuille Google Sheets."""
    global _client
    if not GOOGLE_SHEETS_ENABLED:
        return None

    if _client is None:
        creds = Credentials.from_service_account_file(
            GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        _client = gspread.authorize(creds)

    spreadsheet = _client.open_by_key(GOOGLE_SHEETS_ID)
    return spreadsheet


def sync_response(response: Response, user_name: str):
    """Synchronise une reponse vers Google Sheets."""
    if not GOOGLE_SHEETS_ENABLED:
        return

    try:
        spreadsheet = get_sheet()
        if not spreadsheet:
            return

        # Utiliser ou creer la feuille "Checks"
        try:
            worksheet = spreadsheet.worksheet("Checks")
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title="Checks", rows=1000, cols=10)
            worksheet.append_row([
                "Date", "Station", "Gerant", "Pompes", "Etat",
                "Monnaie", "Besoin", "Incident", "Confirmation", "Statut",
            ])

        def bool_to_text(val):
            if val is True:
                return "OUI"
            if val is False:
                return "NON"
            return "-"

        row = [
            response.check_date.strftime("%d/%m/%Y"),
            response.station,
            user_name,
            bool_to_text(response.pompes_ok),
            bool_to_text(response.etat_ok),
            bool_to_text(response.monnaie_ok),
            bool_to_text(response.besoin_ok),
            bool_to_text(response.incident_ok),
            bool_to_text(response.confirmation),
            response.status or "-",
        ]

        worksheet.append_row(row)
        logger.info(f"Reponse synchronisee vers Google Sheets pour {response.station}")

    except Exception as e:
        logger.error(f"Erreur sync Google Sheets: {e}")
