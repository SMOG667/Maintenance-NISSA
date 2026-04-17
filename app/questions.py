# Mapping des questions du check journalier
# index -> (texte, champ en base, type de probleme)

QUESTIONS = [
    {
        "index": 0,
        "text": "1/6 - Toutes les pompes fonctionnent-elles correctement ?\n\nRepondez par *OUI* ou *NON*",
        "field": "pompes_ok",
        "problem_type": "maintenance",
        "problem_label": "Pompe hors service",
    },
    {
        "index": 1,
        "text": "2/6 - La station est-elle propre et en bon etat aujourd'hui ?\n\nRepondez par *OUI* ou *NON*",
        "field": "etat_ok",
        "problem_type": "exploitation",
        "problem_label": "Etat station defaillant",
    },
    {
        "index": 2,
        "text": "3/6 - La station dispose-t-elle de suffisamment de monnaie ?\n\nRepondez par *OUI* ou *NON*",
        "field": "monnaie_ok",
        "problem_type": "supervision",
        "problem_label": "Manque de monnaie",
    },
    {
        "index": 3,
        "text": "4/6 - Manquez-vous de materiel ou avez-vous un besoin particulier ?\n\nRepondez par *OUI* ou *NON*\n(OUI = pas de besoin, NON = besoin signale)",
        "field": "besoin_ok",
        "problem_type": "logistique",
        "problem_label": "Besoin materiel signale",
    },
    {
        "index": 4,
        "text": "5/6 - Y a-t-il un probleme ou incident a signaler ?\n\nRepondez par *OUI* ou *NON*\n(OUI = aucun incident, NON = incident signale)",
        "field": "incident_ok",
        "problem_type": "analyse",
        "problem_label": "Incident signale",
    },
    {
        "index": 5,
        "text": "6/6 - Confirmez-vous que ces informations sont correctes ?\n\nRepondez par *OUI* ou *NON*",
        "field": "confirmation",
        "problem_type": None,
        "problem_label": None,
    },
]

TOTAL_QUESTIONS = len(QUESTIONS)

GREETING_MESSAGE = (
    "Bonjour {name} ! \n\n"
    "C'est l'heure du check journalier pour la station *{station}*.\n"
    "Je vais vous poser 6 questions rapides.\n\n"
    "Repondez uniquement par *OUI* ou *NON*.\n\n"
    "C'est parti !"
)

COMPLETION_OK = (
    "Merci {name} !\n\n"
    "Check journalier termine pour *{station}*.\n"
    "Statut : *OK* - Aucun probleme detecte.\n\n"
    "Bonne journee !"
)

COMPLETION_PROBLEM = (
    "Merci {name} !\n\n"
    "Check journalier termine pour *{station}*.\n"
    "Statut : *PROBLEME DETECTE*\n\n"
    "L'assistante a ete notifiee. Les problemes suivants ont ete signales :\n{problems}\n\n"
    "Bonne journee !"
)

INVALID_RESPONSE = "Je n'ai pas compris. Merci de repondre uniquement par *OUI* ou *NON*."

ALREADY_COMPLETED = (
    "Vous avez deja complete le check journalier pour aujourd'hui.\n"
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
    "Date : {date}\n\n"
    "Problemes detectes :\n{problems}\n\n"
    "Action requise."
)
