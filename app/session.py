"""Logique de session chatbot.

Deux flux :
1. QUOTIDIEN : le cron cree la session + envoie le greeting + question 1.
   Le gerant repond OUI/NON (boutons interactifs), le chatbot enchaine.
2. OCCASIONNEL : l'admin declenche un check ponctuel depuis le panneau.
   Meme flux conversationnel, mais avec un sous-ensemble de questions.
"""

import logging
from datetime import date

from sqlalchemy.orm import Session as DBSession

from app.models import User, Question, CheckSession, Answer
from app.questions import (
    GREETING_DAILY,
    GREETING_OCCASIONAL,
    QUESTION_FORMAT,
    COMPLETION_OK,
    COMPLETION_PROBLEM,
    INVALID_RESPONSE,
    ALREADY_COMPLETED,
    NO_USER_FOUND,
    ALERT_MESSAGE,
)
from app.whatsapp import send_message, send_question
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


def format_question(question: Question, current: int, total: int) -> str:
    """Formate une question pour l'affichage chatbot."""
    return QUESTION_FORMAT.format(
        current=current,
        total=total,
        text=question.text,
    )


# ─── TRAITEMENT DES MESSAGES ENTRANTS ────────────────────────────────────────


def handle_incoming_message(db: DBSession, phone: str, body: str) -> tuple[str, bool]:
    """Traite un message WhatsApp entrant.

    Retourne un tuple (texte_reponse, is_question).
    is_question=True signifie qu'il faut envoyer avec des boutons OUI/NON.
    """

    # Identifier l'utilisateur
    user = db.query(User).filter(User.phone == phone, User.active == True).first()
    if not user:
        return (NO_USER_FOUND, False)

    today = date.today()

    # Chercher une session active (non terminee) pour aujourd'hui
    session = (
        db.query(CheckSession)
        .filter(
            CheckSession.user_id == user.id,
            CheckSession.check_date == today,
            CheckSession.completed == False,
        )
        .first()
    )

    # Pas de session active → l'utilisateur ecrit en premier, on demarre un check quotidien
    if not session:
        # Verifier si un check quotidien est deja termine aujourd'hui
        done_today = (
            db.query(CheckSession)
            .filter(
                CheckSession.user_id == user.id,
                CheckSession.check_date == today,
                CheckSession.completed == True,
            )
            .first()
        )
        if done_today:
            return (ALREADY_COMPLETED, False)

        return start_check_for_user(db, user, check_type="quotidien")

    # Session active, on attend une reponse
    if not session.awaiting_answer:
        # Relancer la question courante
        session.awaiting_answer = True
        db.commit()
        question_id = session.get_current_question_id()
        question = db.query(Question).get(question_id)
        return (format_question(question, session.current_index + 1, session.total_questions()), True)

    # Valider la reponse OUI/NON
    answer_value = normalize_response(body)
    if answer_value is None:
        return (INVALID_RESPONSE, False)

    # Enregistrer la reponse
    question_id = session.get_current_question_id()
    answer = Answer(
        session_id=session.id,
        question_id=question_id,
        answer=answer_value,
    )
    db.add(answer)

    # Avancer a la question suivante
    session.current_index += 1
    db.commit()

    # Toutes les questions posees ?
    if session.current_index >= session.total_questions():
        return (complete_check(db, user, session), False)

    # Poser la question suivante (avec boutons)
    next_question_id = session.get_current_question_id()
    next_question = db.query(Question).get(next_question_id)
    return (format_question(next_question, session.current_index + 1, session.total_questions()), True)


# ─── DEMARRAGE D'UN CHECK ────────────────────────────────────────────────────


def start_check_for_user(
    db: DBSession,
    user: User,
    check_type: str = "quotidien",
    question_ids: list[int] | None = None,
) -> tuple[str, bool]:
    """Demarre un check chatbot pour un gerant.

    Retourne (greeting + premiere question, True) car la premiere question
    doit etre envoyee avec des boutons.
    """
    if question_ids is None:
        questions = (
            db.query(Question)
            .filter(Question.schedule_type == check_type, Question.active == True)
            .order_by(Question.position)
            .all()
        )
        question_ids = [q.id for q in questions]
    else:
        questions = (
            db.query(Question)
            .filter(Question.id.in_(question_ids))
            .order_by(Question.position)
            .all()
        )
        question_ids = [q.id for q in questions]

    if not question_ids:
        return ("Aucune question configuree pour ce type de check.", False)

    # Creer la session
    session = CheckSession(
        user_id=user.id,
        check_date=date.today(),
        check_type=check_type,
        question_ids=",".join(str(qid) for qid in question_ids),
        current_index=0,
        awaiting_answer=True,
    )
    db.add(session)
    db.commit()

    # Construire le message
    total = len(question_ids)
    if check_type == "quotidien":
        greeting = GREETING_DAILY.format(name=user.name, station=user.station, total=total)
    else:
        greeting = GREETING_OCCASIONAL.format(name=user.name, station=user.station, total=total)

    first_question = db.query(Question).get(question_ids[0])
    question_text = format_question(first_question, 1, total)

    # On envoie le greeting en texte, puis la question avec boutons separement
    return (f"{greeting}\n\n{question_text}", True)


# ─── FINALISATION D'UN CHECK ─────────────────────────────────────────────────


def complete_check(db: DBSession, user: User, session: CheckSession) -> str:
    """Finalise un check : determine le statut et envoie les alertes."""
    session.completed = True
    session.awaiting_answer = False

    # Charger les reponses avec les questions
    answers = (
        db.query(Answer)
        .filter(Answer.session_id == session.id)
        .all()
    )

    # Trouver les problemes (reponse NON sur une question avec problem_type)
    problems = []
    all_ok = True

    for ans in answers:
        question = db.query(Question).get(ans.question_id)
        if ans.answer is False and question.problem_type is not None:
            all_ok = False
            problems.append({
                "type": question.problem_type,
                "label": question.problem_label or question.text,
            })
        elif ans.answer is False:
            all_ok = False

    session.status = "OK" if all_ok else "PROBLEME"
    db.commit()

    if all_ok:
        logger.info(f"Check OK pour {user.station} ({user.name})")
        return COMPLETION_OK.format(name=user.name, station=user.station)

    problems_text = "\n".join(f"- [{p['type'].upper()}] {p['label']}" for p in problems)

    # Envoyer alerte a l'assistante
    send_alert(user, session, problems)

    logger.warning(f"PROBLEME detecte pour {user.station}: {problems_text}")

    return COMPLETION_PROBLEM.format(
        name=user.name,
        station=user.station,
        problems=problems_text,
    )


# ─── ALERTES ─────────────────────────────────────────────────────────────────


def send_alert(user: User, session: CheckSession, problems: list[dict]):
    """Envoie une alerte WhatsApp a l'assistante."""
    if not ASSISTANT_WHATSAPP_NUMBER:
        logger.warning("Pas de numero assistante configure, alerte non envoyee")
        return

    problems_text = "\n".join(f"- [{p['type'].upper()}] {p['label']}" for p in problems)
    check_type_label = "Quotidien" if session.check_type == "quotidien" else "Occasionnel"

    alert = ALERT_MESSAGE.format(
        station=user.station,
        name=user.name,
        date=session.check_date.strftime("%d/%m/%Y"),
        check_type=check_type_label,
        problems=problems_text,
    )

    send_message(ASSISTANT_WHATSAPP_NUMBER, alert)
    logger.info(f"Alerte envoyee a l'assistante pour {user.station}")


# ─── CHECK JOURNALIER (CRON) ─────────────────────────────────────────────────


def start_daily_check(db: DBSession):
    """Envoie le check journalier automatique a tous les gerants actifs.

    Appele par le cron chaque jour. Cree une session chatbot par gerant
    et envoie le greeting en texte + premiere question avec boutons.
    """
    users = db.query(User).filter(User.active == True).all()
    logger.info(f"Lancement check journalier pour {len(users)} gerants")

    # Questions quotidiennes actives
    daily_questions = (
        db.query(Question)
        .filter(Question.schedule_type == "quotidien", Question.active == True)
        .order_by(Question.position)
        .all()
    )
    question_ids = [q.id for q in daily_questions]

    if not question_ids:
        logger.warning("Aucune question quotidienne active, check annule")
        return

    today = date.today()

    for user in users:
        # Verifier si deja un check aujourd'hui
        existing = (
            db.query(CheckSession)
            .filter(
                CheckSession.user_id == user.id,
                CheckSession.check_date == today,
            )
            .first()
        )
        if existing:
            logger.info(f"Check deja en cours/termine pour {user.name}, ignore")
            continue

        # Demarrer le check
        message, is_question = start_check_for_user(db, user, "quotidien", question_ids)

        # Envoyer avec boutons si c'est une question
        if is_question:
            send_question(user.phone, message)
        else:
            send_message(user.phone, message)

        logger.info(f"Check journalier envoye a {user.name} ({user.station})")


# ─── CHECK OCCASIONNEL (ADMIN) ───────────────────────────────────────────────


def start_occasional_check(db: DBSession, user_ids: list[int], question_ids: list[int]):
    """Lance un check occasionnel pour des gerants specifiques."""
    users = db.query(User).filter(User.id.in_(user_ids), User.active == True).all()
    logger.info(
        f"Lancement check occasionnel: {len(users)} gerants, {len(question_ids)} questions"
    )

    for user in users:
        message, is_question = start_check_for_user(db, user, "occasionnel", question_ids)

        if is_question:
            send_question(user.phone, message)
        else:
            send_message(user.phone, message)

        logger.info(f"Check occasionnel envoye a {user.name} ({user.station})")

    return len(users)
