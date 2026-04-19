"""Script pour initialiser la base de donnees avec des donnees de test."""

from app.database import init_db, SessionLocal
from app.models import User, Question
from app.questions import DEFAULT_QUESTIONS

STATIONS = [
    {"phone": "+22790000001", "name": "Moussa Ibrahim", "station": "Station Niamey Centre"},
    {"phone": "+22790000002", "name": "Amadou Boubacar", "station": "Station Niamey Plateau"},
    {"phone": "+22790000003", "name": "Fatima Abdou", "station": "Station Maradi"},
    {"phone": "+22790000004", "name": "Ousmane Sani", "station": "Station Zinder"},
    {"phone": "+22790000005", "name": "Aisha Moussa", "station": "Station Tahoua"},
]


def seed():
    init_db()
    db = SessionLocal()

    # Gerants
    print("--- Gerants ---")
    for data in STATIONS:
        existing = db.query(User).filter(User.phone == data["phone"]).first()
        if not existing:
            user = User(**data, active=True)
            db.add(user)
            print(f"  Ajout: {data['name']} - {data['station']}")
        else:
            print(f"  Existe deja: {data['name']}")

    # Questions
    print("\n--- Questions ---")
    existing_count = db.query(Question).count()
    if existing_count == 0:
        for q_data in DEFAULT_QUESTIONS:
            question = Question(**q_data, active=True)
            db.add(question)
            print(f"  Ajout: {q_data['text'][:50]}...")
    else:
        print(f"  {existing_count} questions deja en base")

    db.commit()
    db.close()
    print("\nBase de donnees initialisee avec succes.")


if __name__ == "__main__":
    seed()
