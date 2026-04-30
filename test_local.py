"""Script de test local - simule des interactions chatbot sans WhatsApp."""

from app.database import init_db, SessionLocal
from app.models import User, Question
from app.questions import DEFAULT_QUESTIONS
from app.session import handle_incoming_message

# Initialiser la base
init_db()

db = SessionLocal()

# Creer un utilisateur de test si necessaire
test_phone = "+22799999999"
user = db.query(User).filter(User.phone == test_phone).first()
if not user:
    user = User(phone=test_phone, name="Test Gerant", station="Station Test", active=True)
    db.add(user)
    db.commit()
    print("Utilisateur de test cree")

# Creer les questions par defaut si necessaire
if db.query(Question).count() == 0:
    for q_data in DEFAULT_QUESTIONS:
        db.add(Question(**q_data, active=True))
    db.commit()
    print("Questions par defaut creees")

print()
print("=" * 50)
print("SIMULATION CHATBOT NISSA")
print("=" * 50)
print("Tapez vos reponses (OUI/NON) ou 'quit' pour quitter")
print()

# Premier message pour demarrer le check
reply_text, resp_type, _ = handle_incoming_message(db, test_phone, "bonjour")
print(f"BOT: {reply_text}\n")

while True:
    user_input = input("VOUS: ").strip()
    if user_input.lower() == "quit":
        break

    reply_text, resp_type, _ = handle_incoming_message(db, test_phone, user_input)
    print(f"\nBOT: {reply_text}\n")

    if "Check termine" in reply_text or "deja" in reply_text:
        break

db.close()
print("Simulation terminee.")
