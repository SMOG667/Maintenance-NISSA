"""Script pour initialiser la base de donnees avec des donnees de test."""

from app.database import init_db, SessionLocal
from app.models import User

STATIONS = [
    {"phone": "whatsapp:+22790000001", "name": "Moussa Ibrahim", "station": "Station Niamey Centre"},
    {"phone": "whatsapp:+22790000002", "name": "Amadou Boubacar", "station": "Station Niamey Plateau"},
    {"phone": "whatsapp:+22790000003", "name": "Fatima Abdou", "station": "Station Maradi"},
    {"phone": "whatsapp:+22790000004", "name": "Ousmane Sani", "station": "Station Zinder"},
    {"phone": "whatsapp:+22790000005", "name": "Aisha Moussa", "station": "Station Tahoua"},
]


def seed():
    init_db()
    db = SessionLocal()

    for data in STATIONS:
        existing = db.query(User).filter(User.phone == data["phone"]).first()
        if not existing:
            user = User(**data, active=True)
            db.add(user)
            print(f"Ajout: {data['name']} - {data['station']}")
        else:
            print(f"Existe deja: {data['name']}")

    db.commit()
    db.close()
    print("\nBase de donnees initialisee avec succes.")


if __name__ == "__main__":
    seed()
