"""Application principale Nissa - Chatbot WhatsApp."""

import csv
import io
import logging
from contextlib import asynccontextmanager
from datetime import date, timedelta

from fastapi import FastAPI, Form, Depends, Request, Query
from fastapi.responses import HTMLResponse, PlainTextResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session as DBSession
from twilio.twiml.messaging_response import MessagingResponse

from app.database import get_db, init_db
from app.models import User, Response, Session
from app.session import handle_incoming_message, start_daily_check
from app.scheduler import start_scheduler, stop_scheduler
from app.sheets import sync_response
from app.config import GOOGLE_SHEETS_ENABLED

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("nissa.log"),
    ],
)
logger = logging.getLogger("nissa")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_scheduler()
    logger.info("Application Nissa demarree")
    yield
    stop_scheduler()
    logger.info("Application Nissa arretee")


app = FastAPI(title="Nissa - Chatbot WhatsApp", version="1.0.0", lifespan=lifespan)
templates = Jinja2Templates(directory="app/templates")


# ─── WEBHOOK WHATSAPP (TWILIO) ───────────────────────────────────────────────


@app.post("/webhook")
async def whatsapp_webhook(
    From: str = Form(...),
    Body: str = Form(...),
    db: DBSession = Depends(get_db),
):
    """Endpoint webhook pour recevoir les messages WhatsApp via Twilio."""
    logger.info(f"Message recu de {From}: {Body}")

    reply_text = handle_incoming_message(db, From, Body)

    # Sync Google Sheets si check complete
    if GOOGLE_SHEETS_ENABLED and ("Check journalier termine" in reply_text):
        user = db.query(User).filter(User.phone == From).first()
        if user:
            response = (
                db.query(Response)
                .filter(
                    Response.user_id == user.id,
                    Response.check_date == date.today(),
                )
                .first()
            )
            if response:
                sync_response(response, user.name)

    # Reponse TwiML
    twiml = MessagingResponse()
    twiml.message(reply_text)
    return PlainTextResponse(content=str(twiml), media_type="application/xml")


# ─── API ENDPOINTS ───────────────────────────────────────────────────────────


@app.post("/api/trigger-check")
async def trigger_daily_check(db: DBSession = Depends(get_db)):
    """Declenche manuellement le check journalier."""
    start_daily_check(db)
    return {"status": "ok", "message": "Check journalier declenche"}


@app.get("/api/stations")
async def list_stations(db: DBSession = Depends(get_db)):
    """Liste toutes les stations et leurs gerants."""
    users = db.query(User).filter(User.active == True).all()
    return [
        {"id": u.id, "name": u.name, "station": u.station, "phone": u.phone}
        for u in users
    ]


@app.get("/api/responses")
async def list_responses(
    station: str | None = None,
    days: int = 7,
    db: DBSession = Depends(get_db),
):
    """Liste les reponses des derniers jours."""
    since = date.today() - timedelta(days=days)
    query = db.query(Response).filter(Response.check_date >= since)

    if station:
        query = query.filter(Response.station == station)

    responses = query.order_by(Response.check_date.desc()).all()

    return [
        {
            "id": r.id,
            "date": r.check_date.isoformat(),
            "station": r.station,
            "pompes_ok": r.pompes_ok,
            "etat_ok": r.etat_ok,
            "monnaie_ok": r.monnaie_ok,
            "besoin_ok": r.besoin_ok,
            "incident_ok": r.incident_ok,
            "confirmation": r.confirmation,
            "status": r.status,
        }
        for r in responses
    ]


@app.get("/api/problems")
async def list_problems(days: int = 7, db: DBSession = Depends(get_db)):
    """Liste les problemes detectes."""
    since = date.today() - timedelta(days=days)
    responses = (
        db.query(Response)
        .filter(Response.check_date >= since, Response.status == "PROBLEME")
        .order_by(Response.check_date.desc())
        .all()
    )

    results = []
    for r in responses:
        problems = []
        if r.pompes_ok is False:
            problems.append({"type": "maintenance", "label": "Pompe hors service"})
        if r.etat_ok is False:
            problems.append({"type": "exploitation", "label": "Etat station defaillant"})
        if r.monnaie_ok is False:
            problems.append({"type": "supervision", "label": "Manque de monnaie"})
        if r.besoin_ok is False:
            problems.append({"type": "logistique", "label": "Besoin materiel signale"})
        if r.incident_ok is False:
            problems.append({"type": "analyse", "label": "Incident signale"})

        results.append({
            "date": r.check_date.isoformat(),
            "station": r.station,
            "problems": problems,
        })

    return results


# ─── ADMIN : GESTION DES GERANTS ─────────────────────────────────────────────


@app.post("/admin/users/add")
async def admin_add_user(
    phone: str = Form(...),
    name: str = Form(...),
    station: str = Form(...),
    db: DBSession = Depends(get_db),
):
    """Ajoute un gerant depuis le panneau admin."""
    # Normaliser le numero
    phone = phone.strip()
    if not phone.startswith("whatsapp:"):
        phone = f"whatsapp:{phone}"

    existing = db.query(User).filter(User.phone == phone).first()
    if existing:
        return RedirectResponse(url="/admin?error=Ce+numero+existe+deja", status_code=303)

    user = User(phone=phone, name=name.strip(), station=station.strip(), active=True)
    db.add(user)
    db.commit()
    logger.info(f"Admin: gerant ajoute - {name} ({station})")
    return RedirectResponse(url="/admin?success=Gerant+ajoute", status_code=303)


@app.post("/admin/users/{user_id}/edit")
async def admin_edit_user(
    user_id: int,
    phone: str = Form(...),
    name: str = Form(...),
    station: str = Form(...),
    db: DBSession = Depends(get_db),
):
    """Modifie un gerant."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(url="/admin?error=Gerant+introuvable", status_code=303)

    phone = phone.strip()
    if not phone.startswith("whatsapp:"):
        phone = f"whatsapp:{phone}"

    user.phone = phone
    user.name = name.strip()
    user.station = station.strip()
    db.commit()
    logger.info(f"Admin: gerant modifie - {name} ({station})")
    return RedirectResponse(url="/admin?success=Gerant+modifie", status_code=303)


@app.post("/admin/users/{user_id}/toggle")
async def admin_toggle_user(user_id: int, db: DBSession = Depends(get_db)):
    """Active ou desactive un gerant."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(url="/admin?error=Gerant+introuvable", status_code=303)

    user.active = not user.active
    db.commit()
    state = "active" if user.active else "desactive"
    logger.info(f"Admin: gerant {state} - {user.name}")
    return RedirectResponse(url="/admin?success=Gerant+{state}", status_code=303)


@app.post("/admin/users/{user_id}/delete")
async def admin_delete_user(user_id: int, db: DBSession = Depends(get_db)):
    """Supprime un gerant."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(url="/admin?error=Gerant+introuvable", status_code=303)

    name = user.name
    db.delete(user)
    db.commit()
    logger.info(f"Admin: gerant supprime - {name}")
    return RedirectResponse(url="/admin?success=Gerant+supprime", status_code=303)


# ─── ADMIN : EXPORT CSV ──────────────────────────────────────────────────────


@app.get("/admin/export")
async def admin_export_csv(
    days: int = Query(default=30),
    db: DBSession = Depends(get_db),
):
    """Exporte les reponses en CSV."""
    since = date.today() - timedelta(days=days)
    responses = (
        db.query(Response)
        .filter(Response.check_date >= since)
        .order_by(Response.check_date.desc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "Date", "Station", "Pompes", "Etat", "Monnaie",
        "Besoin", "Incident", "Confirmation", "Statut",
    ])

    def b(val):
        if val is True:
            return "OUI"
        if val is False:
            return "NON"
        return ""

    for r in responses:
        writer.writerow([
            r.check_date.strftime("%d/%m/%Y"),
            r.station,
            b(r.pompes_ok),
            b(r.etat_ok),
            b(r.monnaie_ok),
            b(r.besoin_ok),
            b(r.incident_ok),
            b(r.confirmation),
            r.status or "",
        ])

    output.seek(0)
    filename = f"nissa_export_{date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ─── ADMIN : DECLENCHEMENT MANUEL ────────────────────────────────────────────


@app.post("/admin/trigger-check")
async def admin_trigger_check(db: DBSession = Depends(get_db)):
    """Declenche le check journalier depuis l'admin."""
    start_daily_check(db)
    return RedirectResponse(url="/admin?success=Check+journalier+envoye", status_code=303)


# ─── PAGES HTML ──────────────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: DBSession = Depends(get_db)):
    """Dashboard de suivi."""
    today = date.today()
    week_ago = today - timedelta(days=7)

    users = db.query(User).filter(User.active == True).all()

    today_responses = (
        db.query(Response).filter(Response.check_date == today).all()
    )

    week_responses = (
        db.query(Response)
        .filter(Response.check_date >= week_ago, Response.status != None)
        .all()
    )

    total_checks = len(week_responses)
    problems_count = sum(1 for r in week_responses if r.status == "PROBLEME")
    ok_count = total_checks - problems_count

    completed_stations = {r.station for r in today_responses if r.status is not None}
    all_stations = {u.station for u in users}
    pending_stations = all_stations - completed_stations

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "today": today.strftime("%d/%m/%Y"),
        "users": users,
        "today_responses": today_responses,
        "total_checks": total_checks,
        "problems_count": problems_count,
        "ok_count": ok_count,
        "pending_stations": sorted(pending_stations),
        "completed_stations": sorted(completed_stations),
    })


@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(
    request: Request,
    success: str | None = None,
    error: str | None = None,
    db: DBSession = Depends(get_db),
):
    """Panneau d'administration."""
    users = db.query(User).order_by(User.station).all()

    # Historique recent
    since = date.today() - timedelta(days=30)
    recent_responses = (
        db.query(Response)
        .filter(Response.check_date >= since, Response.status != None)
        .order_by(Response.check_date.desc())
        .limit(50)
        .all()
    )

    return templates.TemplateResponse("admin.html", {
        "request": request,
        "users": users,
        "recent_responses": recent_responses,
        "success": success,
        "error": error,
    })
