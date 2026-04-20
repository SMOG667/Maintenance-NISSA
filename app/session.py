"""Logique de session chatbot.

Flux de conversation :
1. Question OUI/NON (boutons interactifs)
2. Si la question a un followup_trigger qui correspond a la reponse :
   → Pose une question de suivi (reponse texte libre)
   → Stocke le commentaire dans answer.comment
3. Passe a la question suivante
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

# Types de reponse attendue
EXPECT_BUTTONS = "buttons"  # OUI/NON avec boutons
EXPECT_TEXT = "text"        # Texte libre (pas de boutons)
EXPECT_NONE = "none"        # Message final, pas de reponse attendue


def normalize_response(text: str) -> bool | None:
    """Normalise la reponse utilisateur en booleen."""
    cleaned = text.strip().upper()
    if cleaned in ("OUI", "O", "YES", "1"):
        return True
    if cleaned in ("NON", "N", "NO", "0"):
        return False
    return None


def format_question(question: Question, current: int, total: int) -> str:
    return QUESTION_FORMAT.format(
        current=current,
        total=total,
        text=question.text,
    )


# ─── TRAITEMENT DES MESSAGES ENTRANTS ────────────────────────────────────────


def handle_incoming_message(db: DBSession, phone: str, body: str) -> tuple[str, str]:
    """Traite un message WhatsApp entrant.

    Retourne (texte_reponse, response_type).
    response_type: "buttons" (OUI/NON), "text" (texte libre), "none" (pas de reponse)
    """

    user = db.query(User).filter(User.phone == phone, User.active == True).first()
    if not user:
        return (NO_USER_FOUND, EXPECT_NONE)

    today = date.today()

    session = (
        db.query(CheckSession)
        .filter(
            CheckSession.user_id == user.id,
            CheckSession.check_date == today,
            CheckSession.completed == False,
        )
        .first()
    )

    # Pas de session active → demarrer un check quotidien
    if not session:
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
            return (ALREADY_COMPLETED, EXPECT_NONE)

        return start_check_for_user(db, user, check_type="quotidien")

    # ─── En attente d'une reponse de suivi (texte libre) ───
    if session.awaiting_followup:
        return handle_followup_response(db, session, body)

    # ─── En attente d'une reponse OUI/NON ───
    if not session.awaiting_answer:
        session.awaiting_answer = True
        db.commit()
        question_id = session.get_current_question_id()
        question = db.query(Question).get(question_id)
        return (format_question(question, session.current_index + 1, session.total_questions()), EXPECT_BUTTONS)

    # Valider la reponse OUI/NON
    answer_value = normalize_response(body)
    if answer_value is None:
        return (INVALID_RESPONSE, EXPECT_NONE)

    # Enregistrer la reponse
    question_id = session.get_current_question_id()
    question = db.query(Question).get(question_id)

    answer = Answer(
        session_id=session.id,
        question_id=question_id,
        answer=answer_value,
    )
    db.add(answer)
    db.flush()

    # Verifier si un suivi est declenche
    if question.followup_trigger and question.followup_text:
        trigger_value = question.followup_trigger.lower().strip()
        answer_matches = (trigger_value == "oui" and answer_value) or (trigger_value == "non" and not answer_value)

        if answer_matches:
            # Passer en mode suivi
            session.awaiting_answer = False
            session.awaiting_followup = True
            db.commit()
            return (question.followup_text, EXPECT_TEXT)

    # Pas de suivi → avancer a la question suivante
    return advance_to_next(db, session)


def handle_followup_response(db: DBSession, session: CheckSession, text: str) -> tuple[str, str]:
    """Traite la reponse texte libre d'une question de suivi."""

    # Trouver la derniere reponse (celle qui a declenche le suivi)
    last_answer = (
        db.query(Answer)
        .filter(Answer.session_id == session.id)
        .order_by(Answer.id.desc())
        .first()
    )

    if last_answer:
        last_answer.comment = text.strip()

    session.awaiting_followup = False
    db.commit()

    # Avancer a la question suivante
    return advance_to_next(db, session)


def advance_to_next(db: DBSession, session: CheckSession) -> tuple[str, str]:
    """Avance a la question suivante ou termine le check."""
    user = db.query(User).get(session.user_id)

    session.current_index += 1
    session.awaiting_answer = True
    db.commit()

    if session.current_index >= session.total_questions():
        return (complete_check(db, user, session), EXPECT_NONE)

    next_question_id = session.get_current_question_id()
    next_question = db.query(Question).get(next_question_id)
    return (format_question(next_question, session.current_index + 1, session.total_questions()), EXPECT_BUTTONS)


# ─── DEMARRAGE D'UN CHECK ────────────────────────────────────────────────────


def start_check_for_user(
    db: DBSession,
    user: User,
    check_type: str = "quotidien",
    question_ids: list[int] | None = None,
) -> tuple[str, str]:
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
        return ("Aucune question configuree pour ce type de check.", EXPECT_NONE)

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

    total = len(question_ids)
    if check_type == "quotidien":
        greeting = GREETING_DAILY.format(name=user.name, station=user.station, total=total)
    else:
        greeting = GREETING_OCCASIONAL.format(name=user.name, station=user.station, total=total)

    first_question = db.query(Question).get(question_ids[0])
    question_text = format_question(first_question, 1, total)

    return (f"{greeting}\n\n{question_text}", EXPECT_BUTTONS)


# ─── FINALISATION D'UN CHECK ─────────────────────────────────────────────────


def complete_check(db: DBSession, user: User, session: CheckSession) -> str:
    session.completed = True
    session.awaiting_answer = False
    session.awaiting_followup = False

    answers = db.query(Answer).filter(Answer.session_id == session.id).all()

    problems = []
    all_ok = True

    for ans in answers:
        question = db.query(Question).get(ans.question_id)
        if ans.answer is False and question.problem_type is not None:
            all_ok = False
            label = question.problem_label or question.text
            if ans.comment:
                label += f" — {ans.comment}"
            problems.append({
                "type": question.problem_type,
                "label": label,
            })
        elif ans.answer is False:
            all_ok = False

    session.status = "OK" if all_ok else "PROBLEME"
    db.commit()

    if all_ok:
        logger.info(f"Check OK pour {user.station} ({user.name})")
        return COMPLETION_OK.format(name=user.name, station=user.station)

    problems_text = "\n".join(f"- [{p['type'].upper()}] {p['label']}" for p in problems)

    send_alert(user, session, problems)

    logger.warning(f"PROBLEME detecte pour {user.station}: {problems_text}")

    return COMPLETION_PROBLEM.format(
        name=user.name,
        station=user.station,
        problems=problems_text,
    )


# ─── ALERTES ─────────────────────────────────────────────────────────────────


def send_alert(user: User, session: CheckSession, problems: list[dict]):
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
    users = db.query(User).filter(User.active == True).all()
    logger.info(f"Lancement check journalier pour {len(users)} gerants")

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

        message, resp_type = start_check_for_user(db, user, "quotidien", question_ids)

        if resp_type == EXPECT_BUTTONS:
            send_question(user.phone, message)
        else:
            send_message(user.phone, message)

        logger.info(f"Check journalier envoye a {user.name} ({user.station})")


# ─── CHECK OCCASIONNEL (ADMIN) ───────────────────────────────────────────────


def start_occasional_check(db: DBSession, user_ids: list[int], question_ids: list[int]):
    users = db.query(User).filter(User.id.in_(user_ids), User.active == True).all()
    logger.info(
        f"Lancement check occasionnel: {len(users)} gerants, {len(question_ids)} questions"
    )

    for user in users:
        message, resp_type = start_check_for_user(db, user, "occasionnel", question_ids)

        if resp_type == EXPECT_BUTTONS:
            send_question(user.phone, message)
        else:
            send_message(user.phone, message)

        logger.info(f"Check occasionnel envoye a {user.name} ({user.station})")

    return len(users)
