"""Script de test local - simule des interactions WhatsApp sans Twilio."""

from app.database import init_db, SessionLocal
from app.models import User
from app.session import handle_incoming_message

# Initialiser la base
init_db()

# Creer un utilisateur de test
db = SessionLocal()
test_phone = "whatsapp:+22799999999"
user = db.query(User).filter(User.phone == test_phone).first()
if not user:
    user = User(phone=test_phone, name="Test Gerant", station="Station Test", active=True)
    db.add(user)
    db.commit()
    print("Utilisateur de test cree\n")

print("=" * 50)
print("SIMULATION CHATBOT NISSA")
print("=" * 50)
print("Tapez vos reponses (OUI/NON) ou 'quit' pour quitter\n")

# Premier message pour demarrer
response = handle_incoming_message(db, test_phone, "bonjour")
print(f"BOT: {response}\n")

while True:
    user_input = input("VOUS: ").strip()
    if user_input.lower() == "quit":
        break

    response = handle_incoming_message(db, test_phone, user_input)
    print(f"\nBOT: {response}\n")

    if "Check journalier termine" in response or "deja complete" in response:
        break

db.close()
print("\nSimulation terminee.")
