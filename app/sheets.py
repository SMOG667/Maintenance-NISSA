"""Integration Google Sheets pour visualisation des donnees (optionnel)."""

import logging

from sqlalchemy.orm import Session as DBSession

from app.config import GOOGLE_SHEETS_ENABLED, GOOGLE_SHEETS_ID, GOOGLE_SERVICE_ACCOUNT_FILE

logger = logging.getLogger("nissa.sheets")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_client = None


def get_sheet():
    global _client
    if not GOOGLE_SHEETS_ENABLED:
        return None

    import gspread
    from google.oauth2.service_account import Credentials

    if _client is None:
        creds = Credentials.from_service_account_file(
            GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        _client = gspread.authorize(creds)

    return _client.open_by_key(GOOGLE_SHEETS_ID)


def sync_response_dynamic(db: DBSession, session, user_name: str):
    """Synchronise un check vers Google Sheets."""
    if not GOOGLE_SHEETS_ENABLED:
        return

    try:
        import gspread
        from app.models import Answer, Question

        spreadsheet = get_sheet()
        if not spreadsheet:
            return

        try:
            worksheet = spreadsheet.worksheet("Checks")
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title="Checks", rows=1000, cols=20)

        answers = db.query(Answer).filter(Answer.session_id == session.id).all()

        row = [
            session.check_date.strftime("%d/%m/%Y"),
            user_name,
            session.check_type,
        ]

        for ans in answers:
            question = db.query(Question).get(ans.question_id)
            q_text = question.text[:30] if question else "?"
            row.append(f"{q_text}: {'OUI' if ans.answer else 'NON'}")

        row.append(session.status or "")
        worksheet.append_row(row)
        logger.info(f"Check synchronise vers Google Sheets")

    except Exception as e:
        logger.error(f"Erreur sync Google Sheets: {e}")
