import logging
from datetime import date

from sqlalchemy.orm import Session as DBSession

from app.models import User, Session, Response
from app.questions import (
    QUESTIONS,
    TOTAL_QUESTIONS,
    GREETING_MESSAGE,
    COMPLETION_OK,
    COMPLETION_PROBLEM,
    INVALID_RESPONSE,
    ALREADY_COMPLETED,
    NO_USER_FOUND,
    ALERT_MESSAGE,
)
from app.whatsapp import send_message
from app.config import ASSISTANT_WHATSAPP_NUMBER

logger = logging.getLogger("nissa.session")


def normalize_response(text: str) -> bool | None:
    """Normalise la reponse utilisateur en booleen."""
    cleaned = text.strip().upper()
    if cleaned in ("OUI", "O", "YES", "1"):
        return True
    if cleaned in ("NON", "N", "NO", "0"):
        return False
    return None


def get_or_create_session(db: DBSession, user: User) -> Session | None:
    """Recupere ou cree la session du jour pour un utilisateur."""
    today = date.today()

    # Verifier si un check est deja complete aujourd'hui
    existing_response = (
        db.query(Response)
        .filter(Response.user_id == user.id, Response.check_date == today)
        .first()
    )
    if existing_response and existing_response.status is not None:
        return None  # Deja complete

    # Chercher une session active
    session = (
        db.query(Session)
        .filter(
            Session.user_id == user.id,
            Session.check_date == today,
            Session.completed == False,
        )
        .first()
    )

    if not session:
        session = Session(user_id=user.id, check_date=today, current_question=0)
        db.add(session)
        db.commit()
        db.refresh(session)

    return session


def handle_incoming_message(db: DBSession, phone: str, body: str) -> str:
    """Traite un message entrant et retourne la reponse."""
    # Identifier l'utilisateur
    user = db.query(User).filter(User.phone == phone, User.active == True).first()
    if not user:
        return NO_USER_FOUND

    # Obtenir ou creer la session
    session = get_or_create_session(db, user)
    if session is None:
        return ALREADY_COMPLETED

    # Si c'est le debut (question 0 pas encore posee), on envoie le greeting
    # et la premiere question. Cela arrive quand l'utilisateur ecrit en premier.
    if session.current_question == 0:
        # Verifier si c'est un message initial ou une reponse a la question 0
        existing_response = (
            db.query(Response)
            .filter(Response.user_id == user.id, Response.check_date == date.today())
            .first()
        )
        if not existing_response:
            # Premier message, on cree la reponse et envoie la premiere question
            response = Response(
                user_id=user.id,
                check_date=date.today(),
                station=user.station,
            )
            db.add(response)
            db.commit()

            greeting = GREETING_MESSAGE.format(name=user.name, station=user.station)
            question = QUESTIONS[0]["text"]
            return f"{greeting}\n\n{question}"

    # Valider la reponse
    answer = normalize_response(body)
    if answer is None:
        return INVALID_RESPONSE

    # Enregistrer la reponse
    response = (
        db.query(Response)
        .filter(Response.user_id == user.id, Response.check_date == date.today())
        .first()
    )
    if not response:
        response = Response(
            user_id=user.id,
            check_date=date.today(),
            station=user.station,
        )
        db.add(response)
        db.commit()
        db.refresh(response)

    current_q = QUESTIONS[session.current_question]
    setattr(response, current_q["field"], answer)
    db.commit()

    # Passer a la question suivante
    session.current_question += 1
    db.commit()

    # Verifier si on a termine
    if session.current_question >= TOTAL_QUESTIONS:
        return complete_check(db, user, session, response)

    # Poser la question suivante
    return QUESTIONS[session.current_question]["text"]


def complete_check(
    db: DBSession, user: User, session: Session, response: Response
) -> str:
    """Finalise le check et declenche les alertes si necessaire."""
    session.completed = True

    # Determiner le statut
    all_ok = all([
        response.pompes_ok,
        response.etat_ok,
        response.monnaie_ok,
        response.besoin_ok,
        response.incident_ok,
    ])

    response.status = "OK" if all_ok else "PROBLEME"
    db.commit()

    if all_ok:
        logger.info(f"Check OK pour {user.station} ({user.name})")
        return COMPLETION_OK.format(name=user.name, station=user.station)

    # Identifier les problemes
    problems = detect_problems(response)
    problems_text = "\n".join(f"- [{p['type']}] {p['label']}" for p in problems)

    # Envoyer alerte a l'assistante
    send_alert(user, problems, response.check_date)

    logger.warning(f"PROBLEME detecte pour {user.station}: {problems_text}")

    return COMPLETION_PROBLEM.format(
        name=user.name,
        station=user.station,
        problems=problems_text,
    )


def detect_problems(response: Response) -> list[dict]:
    """Detecte les problemes a partir des reponses."""
    problems = []
    fields_to_check = [
        ("pompes_ok", "maintenance", "Pompe hors service"),
        ("etat_ok", "exploitation", "Etat station defaillant"),
        ("monnaie_ok", "supervision", "Manque de monnaie"),
        ("besoin_ok", "logistique", "Besoin materiel signale"),
        ("incident_ok", "analyse", "Incident signale"),
    ]
    for field, problem_type, label in fields_to_check:
        value = getattr(response, field)
        if value is False:
            problems.append({"type": problem_type, "label": label, "field": field})
    return problems


def send_alert(user: User, problems: list[dict], check_date: date):
    """Envoie une alerte a l'assistante."""
    if not ASSISTANT_WHATSAPP_NUMBER:
        logger.warning("Pas de numero assistante configure, alerte non envoyee")
        return

    problems_text = "\n".join(f"- [{p['type'].upper()}] {p['label']}" for p in problems)

    alert = ALERT_MESSAGE.format(
        station=user.station,
        name=user.name,
        date=check_date.strftime("%d/%m/%Y"),
        problems=problems_text,
    )

    send_message(ASSISTANT_WHATSAPP_NUMBER, alert)
    logger.info(f"Alerte envoyee a l'assistante pour {user.station}")


def start_daily_check(db: DBSession):
    """Envoie le check journalier a tous les gerants actifs."""
    users = db.query(User).filter(User.active == True).all()
    logger.info(f"Lancement check journalier pour {len(users)} gerants")

    for user in users:
        today = date.today()

        # Verifier si deja fait aujourd'hui
        existing = (
            db.query(Response)
            .filter(
                Response.user_id == user.id,
                Response.check_date == today,
                Response.status != None,
            )
            .first()
        )
        if existing:
            logger.info(f"Check deja complete pour {user.name}, ignore")
            continue

        # Creer la session et la reponse
        session = Session(user_id=user.id, check_date=today, current_question=0)
        db.add(session)

        response = Response(user_id=user.id, check_date=today, station=user.station)
        db.add(response)
        db.commit()

        # Envoyer le greeting + premiere question
        greeting = GREETING_MESSAGE.format(name=user.name, station=user.station)
        question = QUESTIONS[0]["text"]
        message = f"{greeting}\n\n{question}"

        send_message(user.phone, message)
        logger.info(f"Check envoye a {user.name} ({user.station})")
