"""Messages et donnees de seed pour les questions par defaut."""

# Questions par defaut a inserer au premier lancement
DEFAULT_QUESTIONS = [
    {
        "text": "Toutes les pompes fonctionnent-elles correctement ?",
        "problem_type": "maintenance",
        "problem_label": "Pompe hors service",
        "schedule_type": "quotidien",
        "position": 1,
    },
    {
        "text": "La station est-elle propre et en bon etat aujourd'hui ?",
        "problem_type": "exploitation",
        "problem_label": "Etat station defaillant",
        "schedule_type": "quotidien",
        "position": 2,
    },
    {
        "text": "La station dispose-t-elle de suffisamment de monnaie ?",
        "problem_type": "supervision",
        "problem_label": "Manque de monnaie",
        "schedule_type": "quotidien",
        "position": 3,
    },
    {
        "text": "Manquez-vous de materiel ou avez-vous un besoin particulier ?",
        "problem_type": "logistique",
        "problem_label": "Besoin materiel signale",
        "schedule_type": "quotidien",
        "position": 4,
    },
    {
        "text": "Y a-t-il un probleme ou incident a signaler ?",
        "problem_type": "analyse",
        "problem_label": "Incident signale",
        "schedule_type": "quotidien",
        "position": 5,
    },
    {
        "text": "Confirmez-vous que ces informations sont correctes ?",
        "problem_type": None,
        "problem_label": None,
        "schedule_type": "quotidien",
        "position": 6,
    },
]

# ─── MESSAGES DU CHATBOT ─────────────────────────────────────────────────────

GREETING_DAILY = (
    "Bonjour {name} !\n\n"
    "C'est l'heure du check journalier pour la station *{station}*.\n"
    "Je vais vous poser {total} questions rapides.\n\n"
    "Repondez uniquement par *OUI* ou *NON*.\n\n"
    "C'est parti !"
)

GREETING_OCCASIONAL = (
    "Bonjour {name} !\n\n"
    "Un check ponctuel a ete lance pour la station *{station}*.\n"
    "Je vais vous poser {total} questions.\n\n"
    "Repondez uniquement par *OUI* ou *NON*."
)

QUESTION_FORMAT = "{current}/{total} - {text}\n\nRepondez par *OUI* ou *NON*"

COMPLETION_OK = (
    "Merci {name} !\n\n"
    "Check termine pour *{station}*.\n"
    "Statut : *OK* - Aucun probleme detecte.\n\n"
    "Bonne journee !"
)

COMPLETION_PROBLEM = (
    "Merci {name} !\n\n"
    "Check termine pour *{station}*.\n"
    "Statut : *PROBLEME DETECTE*\n\n"
    "L'assistante a ete notifiee. Problemes signales :\n{problems}\n\n"
    "Bonne journee !"
)

INVALID_RESPONSE = "Je n'ai pas compris. Merci de repondre uniquement par *OUI* ou *NON*."

ALREADY_COMPLETED = (
    "Vous avez deja un check en cours ou complete.\n"
    "Merci et bonne journee !"
)

NO_USER_FOUND = (
    "Desole, votre numero n'est pas enregistre dans le systeme Nissa.\n"
    "Contactez votre superviseur pour etre ajoute."
)

ALERT_MESSAGE = (
    "ALERTE NISSA\n\n"
    "Station : *{station}*\n"
    "Gerant : {name}\n"
    "Date : {date}\n"
    "Type : {check_type}\n\n"
    "Problemes detectes :\n{problems}\n\n"
    "Action requise."
)
