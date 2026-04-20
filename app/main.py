"""Application principale Nissa - Chatbot WhatsApp."""

import csv
import io
import logging
from contextlib import asynccontextmanager
from datetime import date, timedelta

from fastapi import FastAPI, Form, Depends, Request, Query, Header
from fastapi.responses import HTMLResponse, PlainTextResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session as DBSession

from app.database import get_db, init_db
from app.models import User, Question, CheckSession, Answer
from app.session import handle_incoming_message, start_daily_check, start_occasional_check
from app.sheets import sync_response_dynamic
from app.whatsapp import send_message, send_question
from app.config import GOOGLE_SHEETS_ENABLED, CRON_SECRET, WHATSAPP_VERIFY_TOKEN, STRIPE_SECRET_KEY

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("nissa")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Application Nissa demarree")
    yield
    logger.info("Application Nissa arretee")


app = FastAPI(title="Nissa - Chatbot WhatsApp", version="3.0.0", lifespan=lifespan)
templates = Jinja2Templates(directory="app/templates")

from datetime import datetime as _dt
templates.env.filters["todatetime"] = lambda ts: _dt.fromtimestamp(ts).strftime("%d/%m/%Y") if ts else "-"


# ─── WEBHOOK WHATSAPP (META CLOUD API) ──────────────────────────────────────


@app.get("/webhook")
async def whatsapp_verify(
    request: Request,
):
    """Endpoint de verification du webhook Meta.

    Meta envoie une requete GET avec hub.mode, hub.verify_token et hub.challenge.
    On verifie le token et on renvoie le challenge.
    """
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook verifie avec succes")
        return PlainTextResponse(content=challenge, status_code=200)

    logger.warning(f"Verification webhook echouee: mode={mode}, token={token}")
    return PlainTextResponse(content="Forbidden", status_code=403)


@app.post("/webhook")
async def whatsapp_webhook(
    request: Request,
    db: DBSession = Depends(get_db),
):
    """Endpoint webhook pour recevoir les messages WhatsApp via Meta Cloud API."""
    try:
        body = await request.json()

        # Meta envoie des notifications de statut (sent, delivered, read) qu'on ignore
        entry = body.get("entry", [])
        if not entry:
            return {"status": "ok"}

        for e in entry:
            changes = e.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                messages = value.get("messages", [])

                for msg in messages:
                    msg_type = msg.get("type")

                    # Extraire le numero et le texte selon le type de message
                    sender = msg["from"]  # Format: 22790000000 (sans +)
                    phone = f"+{sender}"

                    if msg_type == "text":
                        text = msg["text"]["body"]
                    elif msg_type == "interactive":
                        # Reponse a un bouton (OUI/NON)
                        interactive = msg.get("interactive", {})
                        if interactive.get("type") == "button_reply":
                            text = interactive["button_reply"]["id"]  # "oui" ou "non"
                        else:
                            continue
                    else:
                        continue

                    logger.info(f"Message recu de {phone}: {text}")

                    reply_text, resp_type = handle_incoming_message(db, phone, text)

                    # Envoyer la reponse selon le type
                    if resp_type == "buttons":
                        send_question(phone, reply_text)
                    else:
                        send_message(phone, reply_text)

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

    except Exception as e:
        logger.error(f"Erreur webhook: {e}")

    return {"status": "ok"}


# ─── DEBUG ───────────────────────────────────────────────────────────────────


@app.get("/debug")
async def debug_info(db: DBSession = Depends(get_db)):
    """Endpoint de debug pour verifier la connexion DB."""
    import os
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db_status = "OK"
    except Exception as e:
        db_status = f"ERREUR: {e}"

    # Verifier si les tables existent
    tables_ok = False
    user_count = 0
    try:
        user_count = db.query(User).count()
        tables_ok = True
    except Exception as e:
        tables_ok = f"ERREUR: {e}"

    return {
        "db_status": db_status,
        "tables_ok": tables_ok,
        "user_count": user_count,
        "db_url_prefix": (os.getenv("DATABASE_URL", "")[:50] + "...") if os.getenv("DATABASE_URL") else "NON DEFINI",
        "whatsapp_token_set": bool(os.getenv("WHATSAPP_TOKEN")),
        "phone_number_id": os.getenv("WHATSAPP_PHONE_NUMBER_ID", "NON DEFINI"),
    }


@app.get("/debug/init")
async def debug_init_db(db: DBSession = Depends(get_db)):
    """Initialise les tables dans la base de donnees."""
    try:
        init_db()
        user_count = db.query(User).count()
        question_count = db.query(Question).count()
        return {
            "status": "OK",
            "tables_created": True,
            "users": user_count,
            "questions": question_count,
        }
    except Exception as e:
        return {"status": f"ERREUR: {e}"}


@app.get("/debug/migrate")
async def debug_migrate(db: DBSession = Depends(get_db)):
    """Ajoute les nouvelles colonnes aux tables existantes."""
    from sqlalchemy import text
    migrations = [
        "ALTER TABLE questions ADD COLUMN IF NOT EXISTS followup_trigger VARCHAR",
        "ALTER TABLE questions ADD COLUMN IF NOT EXISTS followup_text TEXT",
        "ALTER TABLE check_sessions ADD COLUMN IF NOT EXISTS awaiting_followup BOOLEAN DEFAULT FALSE",
        "ALTER TABLE answers ADD COLUMN IF NOT EXISTS comment TEXT",
    ]
    results = []
    for sql in migrations:
        try:
            db.execute(text(sql))
            db.commit()
            results.append({"sql": sql[:60], "status": "OK"})
        except Exception as e:
            db.rollback()
            results.append({"sql": sql[:60], "status": str(e)})
    return {"migrations": results}


@app.get("/debug/test-send")
async def debug_test_send():
    """Teste l'envoi d'un message WhatsApp."""
    result = send_message("+2250586752574", "Test Nissa - le chatbot fonctionne !")
    return result


# ─── CRON (appele par Vercel Cron chaque jour) ──────────────────────────────


@app.get("/cron/daily-check")
async def cron_daily_check(
    authorization: str | None = Header(default=None),
    db: DBSession = Depends(get_db),
):
    """Endpoint appele par Vercel Cron pour le check journalier automatique."""
    # Verifier le secret pour empecher les appels non autorises
    if CRON_SECRET:
        expected = f"Bearer {CRON_SECRET}"
        if authorization != expected:
            return PlainTextResponse("Unauthorized", status_code=401)

    start_daily_check(db)
    return {"status": "ok", "message": "Check journalier declenche"}


# ─── API ENDPOINTS ───────────────────────────────────────────────────────────


@app.get("/api/stations")
async def api_list_stations(db: DBSession = Depends(get_db)):
    """Liste toutes les stations et leurs gerants."""
    users = db.query(User).filter(User.active == True).all()
    return [
        {"id": u.id, "name": u.name, "station": u.station, "phone": u.phone}
        for u in users
    ]


@app.get("/api/questions")
async def api_list_questions(
    schedule_type: str | None = None,
    db: DBSession = Depends(get_db),
):
    """Liste les questions."""
    query = db.query(Question)
    if schedule_type:
        query = query.filter(Question.schedule_type == schedule_type)
    questions = query.order_by(Question.position).all()
    return [
        {
            "id": q.id,
            "text": q.text,
            "problem_type": q.problem_type,
            "schedule_type": q.schedule_type,
            "position": q.position,
            "active": q.active,
        }
        for q in questions
    ]


@app.get("/api/checks")
async def api_list_checks(days: int = 7, db: DBSession = Depends(get_db)):
    """Liste les checks recents."""
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
            "answers": [
                {"question_id": a.question_id, "answer": a.answer}
                for a in answers
            ],
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
    phone = phone.strip()
    # Nettoyer le format : on stocke en +XXXXXXXXXXX
    phone = phone.replace("whatsapp:", "").strip()
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
    user_id: int,
    phone: str = Form(...),
    name: str = Form(...),
    station: str = Form(...),
    db: DBSession = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(url="/admin?tab=gerants&error=Gerant+introuvable", status_code=303)

    phone = phone.strip()
    phone = phone.replace("whatsapp:", "").strip()
    if not phone.startswith("+"):
        phone = f"+{phone}"

    user.phone = phone
    user.name = name.strip()
    user.station = station.strip()
    db.commit()
    return RedirectResponse(url="/admin?tab=gerants&success=Gerant+modifie", status_code=303)


@app.post("/admin/users/{user_id}/toggle")
async def admin_toggle_user(user_id: int, db: DBSession = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(url="/admin?tab=gerants&error=Gerant+introuvable", status_code=303)
    user.active = not user.active
    db.commit()
    state = "active" if user.active else "desactive"
    return RedirectResponse(url=f"/admin?tab=gerants&success=Gerant+{state}", status_code=303)


@app.post("/admin/users/{user_id}/delete")
async def admin_delete_user(user_id: int, db: DBSession = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(url="/admin?tab=gerants&error=Gerant+introuvable", status_code=303)
    db.delete(user)
    db.commit()
    return RedirectResponse(url="/admin?tab=gerants&success=Gerant+supprime", status_code=303)


# ─── ADMIN : GESTION DES QUESTIONS ───────────────────────────────────────────


@app.post("/admin/questions/add")
async def admin_add_question(
    text: str = Form(...),
    problem_type: str = Form(""),
    problem_label: str = Form(""),
    schedule_type: str = Form("quotidien"),
    position: int = Form(0),
    followup_trigger: str = Form(""),
    followup_text: str = Form(""),
    db: DBSession = Depends(get_db),
):
    question = Question(
        text=text.strip(),
        problem_type=problem_type.strip() or None,
        problem_label=problem_label.strip() or None,
        schedule_type=schedule_type,
        position=position,
        active=True,
        followup_trigger=followup_trigger.strip() or None,
        followup_text=followup_text.strip() or None,
    )
    db.add(question)
    db.commit()
    logger.info(f"Admin: question ajoutee - {text[:50]}")
    return RedirectResponse(url="/admin?tab=questions&success=Question+ajoutee", status_code=303)


@app.post("/admin/questions/{question_id}/edit")
async def admin_edit_question(
    question_id: int,
    text: str = Form(...),
    problem_type: str = Form(""),
    problem_label: str = Form(""),
    schedule_type: str = Form("quotidien"),
    position: int = Form(0),
    followup_trigger: str = Form(""),
    followup_text: str = Form(""),
    db: DBSession = Depends(get_db),
):
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
async def admin_toggle_question(question_id: int, db: DBSession = Depends(get_db)):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        return RedirectResponse(url="/admin?tab=questions&error=Question+introuvable", status_code=303)
    question.active = not question.active
    db.commit()
    state = "activee" if question.active else "desactivee"
    return RedirectResponse(url=f"/admin?tab=questions&success=Question+{state}", status_code=303)


@app.post("/admin/questions/{question_id}/delete")
async def admin_delete_question(question_id: int, db: DBSession = Depends(get_db)):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        return RedirectResponse(url="/admin?tab=questions&error=Question+introuvable", status_code=303)
    db.delete(question)
    db.commit()
    return RedirectResponse(url="/admin?tab=questions&success=Question+supprimee", status_code=303)


# ─── ADMIN : CHECKS ──────────────────────────────────────────────────────────


@app.post("/admin/trigger-daily")
async def admin_trigger_daily(db: DBSession = Depends(get_db)):
    """Declenche le check journalier maintenant."""
    start_daily_check(db)
    return RedirectResponse(url="/admin?tab=checks&success=Check+journalier+envoye", status_code=303)


@app.post("/admin/trigger-occasional")
async def admin_trigger_occasional(
    request: Request,
    db: DBSession = Depends(get_db),
):
    """Declenche un check occasionnel avec les questions et gerants selectionnes."""
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
    """Cree une session Stripe Checkout pour s'abonner."""
    from app.stripe_billing import create_checkout_session
    base_url = str(request.base_url).rstrip("/")
    checkout_url = create_checkout_session(base_url)
    return RedirectResponse(url=checkout_url, status_code=303)


@app.post("/admin/billing-portal")
async def admin_billing_portal(request: Request, customer_id: str = Form(...)):
    """Redirige vers le portail client Stripe pour gerer l'abonnement."""
    from app.stripe_billing import create_portal_session
    base_url = str(request.base_url).rstrip("/")
    portal_url = create_portal_session(customer_id, base_url)
    return RedirectResponse(url=portal_url, status_code=303)


@app.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    """Webhook Stripe pour recevoir les evenements de paiement."""
    import stripe
    from app.config import STRIPE_WEBHOOK_SECRET
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if STRIPE_WEBHOOK_SECRET and sig_header:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        except Exception as e:
            logger.error(f"Erreur verification webhook Stripe: {e}")
            return PlainTextResponse("Invalid signature", status_code=400)
    else:
        import json
        event = json.loads(payload)

    event_type = event.get("type", "")
    logger.info(f"Stripe event: {event_type}")

    return {"status": "ok"}


# ─── ADMIN : EXPORT ──────────────────────────────────────────────────────────


@app.get("/admin/export")
async def admin_export_csv(days: int = Query(default=30), db: DBSession = Depends(get_db)):
    """Exporte les checks en CSV."""
    since = date.today() - timedelta(days=days)
    sessions = (
        db.query(CheckSession)
        .filter(CheckSession.check_date >= since, CheckSession.completed == True)
        .order_by(CheckSession.check_date.desc())
        .all()
    )

    # Toutes les questions pour les en-tetes
    all_questions = db.query(Question).order_by(Question.position).all()
    q_map = {q.id: q for q in all_questions}

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


# ─── PAGES HTML ──────────────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: DBSession = Depends(get_db)):
    """Dashboard de suivi."""
    today = date.today()
    week_ago = today - timedelta(days=7)

    users = db.query(User).filter(User.active == True).all()

    # Checks du jour
    today_sessions = (
        db.query(CheckSession)
        .filter(CheckSession.check_date == today)
        .all()
    )

    # Stats semaine
    week_sessions = (
        db.query(CheckSession)
        .filter(CheckSession.check_date >= week_ago, CheckSession.completed == True)
        .all()
    )

    total_checks = len(week_sessions)
    problems_count = sum(1 for s in week_sessions if s.status == "PROBLEME")
    ok_count = total_checks - problems_count

    # Stations en attente aujourd'hui
    completed_user_ids = {s.user_id for s in today_sessions if s.completed}
    all_user_map = {u.id: u.station for u in users}
    completed_stations = {all_user_map[uid] for uid in completed_user_ids if uid in all_user_map}
    all_stations = {u.station for u in users}
    pending_stations = all_stations - completed_stations

    # Details des checks du jour avec reponses
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


@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(
    request: Request,
    tab: str = "questions",
    success: str | None = None,
    error: str | None = None,
    db: DBSession = Depends(get_db),
):
    """Panneau d'administration."""
    users = db.query(User).order_by(User.station).all()
    questions = db.query(Question).order_by(Question.schedule_type, Question.position).all()

    # Historique
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

    # Questions occasionnelles pour le formulaire d'envoi
    occasional_questions = [q for q in questions if q.schedule_type == "occasionnel" and q.active]

    # Abonnement Stripe
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
