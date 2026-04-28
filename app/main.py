"""Application principale Nissa - Chatbot WhatsApp de maintenance."""

import csv
import io
import logging
import os
import secrets
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta

from fastapi import FastAPI, Form, Depends, Request, Query, Header, Response
from fastapi.responses import HTMLResponse, PlainTextResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session as DBSession

from app.database import get_db, init_db
from app.models import User, Question, CheckSession, Answer
from app.session import handle_incoming_message, start_daily_check, start_occasional_check
from app.sheets import sync_response_dynamic
from app.whatsapp import send_message, send_question
from app.config import GOOGLE_SHEETS_ENABLED, CRON_SECRET, STRIPE_SECRET_KEY

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("nissa")

# Admin credentials
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "nissa2026")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Application Nissa demarree")
    yield
    logger.info("Application Nissa arretee")


app = FastAPI(title="Nissa - Chatbot WhatsApp", version="4.0.0", lifespan=lifespan)
templates = Jinja2Templates(directory="app/templates")
templates.env.filters["todatetime"] = lambda ts: datetime.fromtimestamp(ts).strftime("%d/%m/%Y") if ts else "-"


# ─── AUTHENTIFICATION ADMIN ─────────────────────────────────────────────────


def verify_admin(request: Request) -> bool:
    """Verifie que l'utilisateur est authentifie via cookie."""
    token = request.cookies.get("nissa_admin_token")
    expected = _make_token(ADMIN_USERNAME, ADMIN_PASSWORD)
    return token == expected


def _make_token(username: str, password: str) -> str:
    """Genere un token d'authentification a partir des credentials."""
    import hashlib
    return hashlib.sha256(f"{username}:{password}:nissa_secret_salt".encode()).hexdigest()


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str | None = None):
    """Page de connexion admin."""
    if verify_admin(request):
        return RedirectResponse(url="/admin", status_code=303)
    return """
    <!DOCTYPE html>
    <html lang="fr">
    <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nissa - Connexion</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box;}
        body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#1a1a2e;display:flex;justify-content:center;align-items:center;min-height:100vh;}
        .login-box{background:white;border-radius:12px;padding:40px;width:90%;max-width:400px;box-shadow:0 10px 40px rgba(0,0,0,0.3);}
        .login-box h1{text-align:center;color:#1a1a2e;margin-bottom:8px;font-size:28px;}
        .login-box p{text-align:center;color:#888;margin-bottom:24px;font-size:14px;}
        .form-group{margin-bottom:16px;}
        .form-group label{display:block;font-size:12px;text-transform:uppercase;color:#888;margin-bottom:4px;letter-spacing:0.5px;}
        .form-group input{width:100%;padding:10px 14px;border:1px solid #ddd;border-radius:8px;font-size:15px;}
        .form-group input:focus{outline:none;border-color:#1a1a2e;}
        .btn{width:100%;padding:12px;background:#1a1a2e;color:white;border:none;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer;}
        .btn:hover{background:#2d2d4e;}
        .error{background:#f8d7da;color:#721c24;padding:10px;border-radius:8px;margin-bottom:16px;font-size:13px;text-align:center;}
    </style>
    </head>
    <body>
    <div class="login-box">
        <h1>NISSA</h1>
        <p>Panneau d'administration</p>
        """ + (f'<div class="error">{error}</div>' if error else '') + """
        <form method="POST" action="/login">
            <div class="form-group">
                <label>Identifiant</label>
                <input type="text" name="username" required autofocus>
            </div>
            <div class="form-group">
                <label>Mot de passe</label>
                <input type="password" name="password" required>
            </div>
            <button type="submit" class="btn">Se connecter</button>
        </form>
    </div>
    </body>
    </html>
    """


@app.post("/login")
async def login_submit(username: str = Form(...), password: str = Form(...)):
    """Traite la connexion admin."""
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        response = RedirectResponse(url="/admin", status_code=303)
        token = _make_token(username, password)
        response.set_cookie(
            key="nissa_admin_token",
            value=token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=86400 * 7,  # 7 jours
        )
        return response
    return RedirectResponse(url="/login?error=Identifiants+incorrects", status_code=303)


@app.get("/logout")
async def logout():
    """Deconnexion admin."""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("nissa_admin_token")
    return response


# ─── WEBHOOK WHATSAPP (TWILIO) ───────────────────────────────────────────────


@app.post("/webhook")
async def whatsapp_webhook(
    From: str = Form(...),
    Body: str = Form(...),
    db: DBSession = Depends(get_db),
):
    """Endpoint webhook pour recevoir les messages WhatsApp via Twilio."""
    try:
        phone = From.replace("whatsapp:", "").strip()
        text = Body.strip()

        logger.info(f"Message recu de {phone}: {text}")

        reply_text, resp_type, reply_phone = handle_incoming_message(db, phone, text)
        target_phone = reply_phone or phone

        send_message(target_phone, reply_text)

        # Sync Google Sheets si check complete
        if GOOGLE_SHEETS_ENABLED and ("Check termine" in reply_text):
            user = db.query(User).filter(User.phone == phone).first()
            if user:
                session = (
                    db.query(CheckSession)
                    .filter(
                        CheckSession.user_id == user.id,
                        CheckSession.check_date == date.today(),
                        CheckSession.completed == True,
                    )
                    .order_by(CheckSession.created_at.desc())
                    .first()
                )
                if session:
                    sync_response_dynamic(db, session, user.name)

        from twilio.twiml.messaging_response import MessagingResponse
        twiml = MessagingResponse()
        return PlainTextResponse(content=str(twiml), media_type="application/xml")

    except Exception as e:
        logger.error(f"Erreur webhook: {e}")
        from twilio.twiml.messaging_response import MessagingResponse
        twiml = MessagingResponse()
        return PlainTextResponse(content=str(twiml), media_type="application/xml")


# ─── CRON ────────────────────────────────────────────────────────────────────


@app.get("/cron/daily-check")
async def cron_daily_check(
    authorization: str | None = Header(default=None),
    db: DBSession = Depends(get_db),
):
    """Endpoint appele par Vercel Cron pour le check journalier automatique."""
    if CRON_SECRET:
        expected = f"Bearer {CRON_SECRET}"
        if authorization != expected:
            return PlainTextResponse("Unauthorized", status_code=401)

    start_daily_check(db)
    return {"status": "ok", "message": "Check journalier declenche"}


# ─── API ─────────────────────────────────────────────────────────────────────


@app.get("/api/stations")
async def api_list_stations(db: DBSession = Depends(get_db)):
    users = db.query(User).filter(User.active == True).all()
    return [
        {"id": u.id, "name": u.name, "station": u.station, "phone": u.phone}
        for u in users
    ]


@app.get("/api/questions")
async def api_list_questions(schedule_type: str | None = None, db: DBSession = Depends(get_db)):
    query = db.query(Question)
    if schedule_type:
        query = query.filter(Question.schedule_type == schedule_type)
    questions = query.order_by(Question.position).all()
    return [
        {"id": q.id, "text": q.text, "problem_type": q.problem_type,
         "schedule_type": q.schedule_type, "position": q.position, "active": q.active}
        for q in questions
    ]


@app.get("/api/checks")
async def api_list_checks(days: int = 7, db: DBSession = Depends(get_db)):
    since = date.today() - timedelta(days=days)
    sessions = (
        db.query(CheckSession)
        .filter(CheckSession.check_date >= since, CheckSession.completed == True)
        .order_by(CheckSession.check_date.desc())
        .all()
    )
    results = []
    for s in sessions:
        user = db.query(User).get(s.user_id)
        answers = db.query(Answer).filter(Answer.session_id == s.id).all()
        results.append({
            "date": s.check_date.isoformat(),
            "station": user.station if user else "?",
            "gerant": user.name if user else "?",
            "check_type": s.check_type,
            "status": s.status,
            "answers": [{"question_id": a.question_id, "answer": a.answer} for a in answers],
        })
    return results


# ─── ADMIN : GESTION DES GERANTS ────────────────────────────────────────────


@app.post("/admin/users/add")
async def admin_add_user(
    request: Request, phone: str = Form(...), name: str = Form(...),
    station: str = Form(...), db: DBSession = Depends(get_db),
):
    if not verify_admin(request):
        return RedirectResponse(url="/login", status_code=303)
    phone = phone.strip().replace("whatsapp:", "").strip()
    if not phone.startswith("+"):
        phone = f"+{phone}"

    existing = db.query(User).filter(User.phone == phone).first()
    if existing:
        return RedirectResponse(url="/admin?tab=gerants&error=Ce+numero+existe+deja", status_code=303)

    user = User(phone=phone, name=name.strip(), station=station.strip(), active=True)
    db.add(user)
    db.commit()
    logger.info(f"Admin: gerant ajoute - {name} ({station})")
    return RedirectResponse(url="/admin?tab=gerants&success=Gerant+ajoute", status_code=303)


@app.post("/admin/users/{user_id}/edit")
async def admin_edit_user(
    request: Request, user_id: int, phone: str = Form(...), name: str = Form(...),
    station: str = Form(...), db: DBSession = Depends(get_db),
):
    if not verify_admin(request):
        return RedirectResponse(url="/login", status_code=303)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(url="/admin?tab=gerants&error=Gerant+introuvable", status_code=303)

    phone = phone.strip().replace("whatsapp:", "").strip()
    if not phone.startswith("+"):
        phone = f"+{phone}"

    user.phone = phone
    user.name = name.strip()
    user.station = station.strip()
    db.commit()
    return RedirectResponse(url="/admin?tab=gerants&success=Gerant+modifie", status_code=303)


@app.post("/admin/users/{user_id}/toggle")
async def admin_toggle_user(request: Request, user_id: int, db: DBSession = Depends(get_db)):
    if not verify_admin(request):
        return RedirectResponse(url="/login", status_code=303)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(url="/admin?tab=gerants&error=Gerant+introuvable", status_code=303)
    user.active = not user.active
    db.commit()
    state = "active" if user.active else "desactive"
    return RedirectResponse(url=f"/admin?tab=gerants&success=Gerant+{state}", status_code=303)


@app.post("/admin/users/{user_id}/delete")
async def admin_delete_user(request: Request, user_id: int, db: DBSession = Depends(get_db)):
    if not verify_admin(request):
        return RedirectResponse(url="/login", status_code=303)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(url="/admin?tab=gerants&error=Gerant+introuvable", status_code=303)
    # Supprimer les sessions et reponses associees
    sessions = db.query(CheckSession).filter(CheckSession.user_id == user_id).all()
    for s in sessions:
        db.query(Answer).filter(Answer.session_id == s.id).delete()
    db.query(CheckSession).filter(CheckSession.user_id == user_id).delete()
    db.delete(user)
    db.commit()
    return RedirectResponse(url="/admin?tab=gerants&success=Gerant+supprime", status_code=303)


# ─── ADMIN : GESTION DES QUESTIONS ──────────────────────────────────────────


@app.post("/admin/questions/add")
async def admin_add_question(
    request: Request, text: str = Form(...), problem_type: str = Form(""),
    problem_label: str = Form(""), schedule_type: str = Form("quotidien"),
    position: int = Form(0), followup_trigger: str = Form(""),
    followup_text: str = Form(""), db: DBSession = Depends(get_db),
):
    if not verify_admin(request):
        return RedirectResponse(url="/login", status_code=303)
    question = Question(
        text=text.strip(), problem_type=problem_type.strip() or None,
        problem_label=problem_label.strip() or None, schedule_type=schedule_type,
        position=position, active=True,
        followup_trigger=followup_trigger.strip() or None,
        followup_text=followup_text.strip() or None,
    )
    db.add(question)
    db.commit()
    return RedirectResponse(url="/admin?tab=questions&success=Question+ajoutee", status_code=303)


@app.post("/admin/questions/{question_id}/edit")
async def admin_edit_question(
    request: Request, question_id: int, text: str = Form(...),
    problem_type: str = Form(""), problem_label: str = Form(""),
    schedule_type: str = Form("quotidien"), position: int = Form(0),
    followup_trigger: str = Form(""), followup_text: str = Form(""),
    db: DBSession = Depends(get_db),
):
    if not verify_admin(request):
        return RedirectResponse(url="/login", status_code=303)
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        return RedirectResponse(url="/admin?tab=questions&error=Question+introuvable", status_code=303)

    question.text = text.strip()
    question.problem_type = problem_type.strip() or None
    question.problem_label = problem_label.strip() or None
    question.followup_trigger = followup_trigger.strip() or None
    question.followup_text = followup_text.strip() or None
    question.schedule_type = schedule_type
    question.position = position
    db.commit()
    return RedirectResponse(url="/admin?tab=questions&success=Question+modifiee", status_code=303)


@app.post("/admin/questions/{question_id}/toggle")
async def admin_toggle_question(request: Request, question_id: int, db: DBSession = Depends(get_db)):
    if not verify_admin(request):
        return RedirectResponse(url="/login", status_code=303)
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        return RedirectResponse(url="/admin?tab=questions&error=Question+introuvable", status_code=303)
    question.active = not question.active
    db.commit()
    state = "activee" if question.active else "desactivee"
    return RedirectResponse(url=f"/admin?tab=questions&success=Question+{state}", status_code=303)


@app.post("/admin/questions/{question_id}/delete")
async def admin_delete_question(request: Request, question_id: int, db: DBSession = Depends(get_db)):
    if not verify_admin(request):
        return RedirectResponse(url="/login", status_code=303)
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        return RedirectResponse(url="/admin?tab=questions&error=Question+introuvable", status_code=303)
    db.delete(question)
    db.commit()
    return RedirectResponse(url="/admin?tab=questions&success=Question+supprimee", status_code=303)


# ─── ADMIN : CHECKS ─────────────────────────────────────────────────────────


@app.post("/admin/trigger-daily")
async def admin_trigger_daily(request: Request, db: DBSession = Depends(get_db)):
    if not verify_admin(request):
        return RedirectResponse(url="/login", status_code=303)
    start_daily_check(db)
    return RedirectResponse(url="/admin?tab=checks&success=Check+journalier+envoye", status_code=303)


@app.post("/admin/trigger-occasional")
async def admin_trigger_occasional(request: Request, db: DBSession = Depends(get_db)):
    if not verify_admin(request):
        return RedirectResponse(url="/login", status_code=303)
    form = await request.form()
    question_ids = [int(v) for k, v in form.multi_items() if k == "question_ids"]
    user_ids = [int(v) for k, v in form.multi_items() if k == "user_ids"]

    if not question_ids or not user_ids:
        return RedirectResponse(
            url="/admin?tab=checks&error=Selectionnez+au+moins+une+question+et+un+gerant",
            status_code=303,
        )
    count = start_occasional_check(db, user_ids, question_ids)
    return RedirectResponse(
        url=f"/admin?tab=checks&success=Check+occasionnel+envoye+a+{count}+gerants",
        status_code=303,
    )


# ─── ADMIN : ABONNEMENT STRIPE ──────────────────────────────────────────────


@app.post("/admin/subscribe")
async def admin_subscribe(request: Request):
    if not verify_admin(request):
        return RedirectResponse(url="/login", status_code=303)
    from app.stripe_billing import create_checkout_session
    base_url = str(request.base_url).rstrip("/")
    checkout_url = create_checkout_session(base_url)
    return RedirectResponse(url=checkout_url, status_code=303)


@app.post("/admin/billing-portal")
async def admin_billing_portal(request: Request, customer_id: str = Form(...)):
    if not verify_admin(request):
        return RedirectResponse(url="/login", status_code=303)
    from app.stripe_billing import create_portal_session
    base_url = str(request.base_url).rstrip("/")
    portal_url = create_portal_session(customer_id, base_url)
    return RedirectResponse(url=portal_url, status_code=303)


@app.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    import stripe
    from app.config import STRIPE_WEBHOOK_SECRET
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if STRIPE_WEBHOOK_SECRET and sig_header:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        except Exception as e:
            logger.error(f"Erreur verification webhook Stripe: {e}")
            return PlainTextResponse("Invalid signature", status_code=400)
    else:
        import json
        event = json.loads(payload)

    logger.info(f"Stripe event: {event.get('type', '')}")
    return {"status": "ok"}


# ─── ADMIN : EXPORT ─────────────────────────────────────────────────────────


@app.get("/admin/export")
async def admin_export_csv(request: Request, days: int = Query(default=30), db: DBSession = Depends(get_db)):
    if not verify_admin(request):
        return RedirectResponse(url="/login", status_code=303)
    since = date.today() - timedelta(days=days)
    sessions = (
        db.query(CheckSession)
        .filter(CheckSession.check_date >= since, CheckSession.completed == True)
        .order_by(CheckSession.check_date.desc())
        .all()
    )
    all_questions = db.query(Question).order_by(Question.position).all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    header = ["Date", "Station", "Gerant", "Type"]
    for q in all_questions:
        header.append(q.text[:30])
    header.append("Statut")
    writer.writerow(header)

    for s in sessions:
        user = db.query(User).get(s.user_id)
        answers = db.query(Answer).filter(Answer.session_id == s.id).all()
        answer_map = {a.question_id: a.answer for a in answers}
        row = [
            s.check_date.strftime("%d/%m/%Y"),
            user.station if user else "?",
            user.name if user else "?",
            s.check_type,
        ]
        for q in all_questions:
            val = answer_map.get(q.id)
            row.append("OUI" if val is True else ("NON" if val is False else ""))
        row.append(s.status or "")
        writer.writerow(row)

    output.seek(0)
    filename = f"nissa_export_{date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ─── PAGES PUBLIQUES ────────────────────────────────────────────────────────


@app.get("/data-deletion", response_class=HTMLResponse)
async def data_deletion():
    return """<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><title>Nissa - Suppression des donnees</title>
    <style>body{font-family:sans-serif;max-width:800px;margin:40px auto;padding:0 20px;line-height:1.6;color:#333;}h1{color:#1a1a2e;}</style></head><body>
    <h1>Demande de suppression des donnees - Nissa</h1>
    <p>Envoyez un message a votre superviseur avec votre nom, numero et la mention "Demande de suppression". Vos donnees seront supprimees sous 30 jours.</p>
    </body></html>"""


@app.get("/privacy", response_class=HTMLResponse)
async def privacy_policy():
    return """<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><title>Nissa - Politique de confidentialite</title>
    <style>body{font-family:sans-serif;max-width:800px;margin:40px auto;padding:0 20px;line-height:1.6;color:#333;}h1{color:#1a1a2e;}h2{margin-top:30px;}</style></head><body>
    <h1>Politique de confidentialite - Nissa</h1><p><strong>Avril 2026</strong></p>
    <h2>1. Donnees collectees</h2><p>Numero WhatsApp, nom, station, reponses aux checks.</p>
    <h2>2. Utilisation</h2><p>Checks de maintenance, alertes superviseur, rapports.</p>
    <h2>3. Partage</h2><p>Aucun partage avec des tiers.</p>
    <h2>4. Securite</h2><p>Stockage securise sur serveurs proteges.</p>
    <h2>5. Suppression</h2><p>Sur demande, sous 30 jours.</p>
    </body></html>"""


# ─── DASHBOARD ───────────────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: DBSession = Depends(get_db)):
    today = date.today()
    week_ago = today - timedelta(days=7)
    users = db.query(User).filter(User.active == True).all()

    today_sessions = db.query(CheckSession).filter(CheckSession.check_date == today).all()
    week_sessions = (
        db.query(CheckSession)
        .filter(CheckSession.check_date >= week_ago, CheckSession.completed == True)
        .all()
    )

    total_checks = len(week_sessions)
    problems_count = sum(1 for s in week_sessions if s.status == "PROBLEME")
    ok_count = total_checks - problems_count

    completed_user_ids = {s.user_id for s in today_sessions if s.completed}
    all_user_map = {u.id: u.station for u in users}
    completed_stations = {all_user_map[uid] for uid in completed_user_ids if uid in all_user_map}
    all_stations = {u.station for u in users}
    pending_stations = all_stations - completed_stations

    today_details = []
    for s in today_sessions:
        user = db.query(User).get(s.user_id)
        answers = db.query(Answer).filter(Answer.session_id == s.id).all()
        answer_details = []
        for a in answers:
            q = db.query(Question).get(a.question_id)
            answer_details.append({"question": q.text[:40] if q else "?", "answer": a.answer})
        today_details.append({
            "station": user.station if user else "?",
            "name": user.name if user else "?",
            "check_type": s.check_type,
            "status": s.status,
            "completed": s.completed,
            "answers": answer_details,
        })

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "today": today.strftime("%d/%m/%Y"),
        "users": users,
        "today_details": today_details,
        "total_checks": total_checks,
        "problems_count": problems_count,
        "ok_count": ok_count,
        "pending_stations": sorted(pending_stations),
        "completed_stations": sorted(completed_stations),
    })


# ─── ADMIN PANEL ─────────────────────────────────────────────────────────────


@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(
    request: Request, tab: str = "questions",
    success: str | None = None, error: str | None = None,
    db: DBSession = Depends(get_db),
):
    if not verify_admin(request):
        return RedirectResponse(url="/login", status_code=303)

    users = db.query(User).order_by(User.station).all()
    questions = db.query(Question).order_by(Question.schedule_type, Question.position).all()

    since = date.today() - timedelta(days=30)
    recent_sessions = (
        db.query(CheckSession)
        .filter(CheckSession.check_date >= since, CheckSession.completed == True)
        .order_by(CheckSession.check_date.desc())
        .limit(50)
        .all()
    )

    history = []
    for s in recent_sessions:
        user = db.query(User).get(s.user_id)
        answers = db.query(Answer).filter(Answer.session_id == s.id).all()
        problems = []
        for a in answers:
            if not a.answer:
                q = db.query(Question).get(a.question_id)
                if q and q.problem_type:
                    problems.append(q.problem_label or q.text[:30])
        history.append({
            "date": s.check_date.strftime("%d/%m/%Y"),
            "station": user.station if user else "?",
            "name": user.name if user else "?",
            "check_type": s.check_type,
            "status": s.status,
            "problems": problems,
        })

    occasional_questions = [q for q in questions if q.schedule_type == "occasionnel" and q.active]

    subscription_info = {"active": False, "status": "aucun"}
    invoices = []
    if STRIPE_SECRET_KEY:
        try:
            from app.stripe_billing import get_subscription_status, get_invoices
            subscription_info = get_subscription_status()
            invoices = get_invoices(limit=10)
        except Exception as e:
            logger.error(f"Erreur Stripe: {e}")

    return templates.TemplateResponse("admin.html", {
        "request": request,
        "tab": tab,
        "users": users,
        "questions": questions,
        "occasional_questions": occasional_questions,
        "history": history,
        "subscription": subscription_info,
        "invoices": invoices,
        "success": success,
        "error": error,
    })
