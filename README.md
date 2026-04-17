# NISSA - Chatbot WhatsApp de Maintenance Stations

Systeme de check journalier des stations-service par WhatsApp.

## Architecture

```
app/
├── main.py          # FastAPI - endpoints + webhook + dashboard
├── config.py        # Configuration (.env)
├── database.py      # SQLAlchemy setup
├── models.py        # Modeles: User, Session, Response
├── questions.py     # Questions, messages, mapping problemes
├── session.py       # Logique de session + traitement messages
├── whatsapp.py      # Integration Twilio WhatsApp
├── scheduler.py     # Cron journalier (APScheduler)
├── sheets.py        # Integration Google Sheets (optionnel)
└── templates/
    └── dashboard.html
```

## Installation

```bash
# 1. Cloner et entrer dans le projet
cd Maintenance_NISSA

# 2. Creer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate

# 3. Installer les dependances
pip install -r requirements.txt

# 4. Configurer les variables d'environnement
cp .env.example .env
# Editer .env avec vos credentials Twilio
```

## Configuration Twilio

1. Creer un compte sur https://www.twilio.com
2. Activer le Sandbox WhatsApp dans la console Twilio
3. Recuperer `ACCOUNT_SID` et `AUTH_TOKEN`
4. Configurer le webhook dans Twilio :
   - URL : `https://votre-domaine.com/webhook`
   - Methode : POST
5. Renseigner les valeurs dans `.env`

## Lancement

```bash
# Initialiser la base avec des donnees de test
python seed.py

# Lancer le serveur
python run.py
```

Le serveur demarre sur `http://localhost:8000`

## Test local (sans Twilio)

```bash
python test_local.py
```

Ce script simule l'interaction chatbot dans le terminal.

## Test avec ngrok (avec Twilio)

```bash
# Terminal 1 : lancer le serveur
python run.py

# Terminal 2 : exposer le serveur
ngrok http 8000
```

Copier l'URL ngrok (ex: `https://abc123.ngrok.io/webhook`) dans la config webhook Twilio.

## Endpoints API

| Methode | URL                 | Description                    |
|---------|---------------------|--------------------------------|
| POST    | `/webhook`          | Webhook Twilio WhatsApp        |
| POST    | `/api/trigger-check`| Declencher le check manuellement|
| GET     | `/api/stations`     | Liste des stations/gerants     |
| GET     | `/api/responses`    | Historique des reponses        |
| GET     | `/api/problems`     | Liste des problemes detectes   |
| POST    | `/api/users`        | Ajouter un gerant              |
| GET     | `/`                 | Dashboard de suivi             |

### Parametres

- `GET /api/responses?station=Station Niamey&days=30`
- `GET /api/problems?days=14`

## Google Sheets (optionnel)

1. Creer un projet Google Cloud + activer l'API Sheets
2. Creer un compte de service et telecharger le JSON
3. Placer le fichier `service_account.json` a la racine
4. Partager le Google Sheet avec l'email du compte de service
5. Configurer dans `.env` :
   ```
   GOOGLE_SHEETS_ENABLED=true
   GOOGLE_SHEETS_ID=votre_id_spreadsheet
   ```

## Deploiement Production

### Option 1 : VPS (recommande)

```bash
# Sur le serveur
pip install -r requirements.txt
cp .env.example .env
# Configurer .env

# Avec systemd ou supervisor
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Option 2 : Railway / Render

1. Connecter le repo GitHub
2. Configurer les variables d'environnement
3. Commande de demarrage : `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## Structure Base de Donnees

### users
| Colonne  | Type    | Description                      |
|----------|---------|----------------------------------|
| id       | INTEGER | Cle primaire                     |
| phone    | TEXT    | Numero WhatsApp (whatsapp:+XXX)  |
| name     | TEXT    | Nom du gerant                    |
| station  | TEXT    | Nom de la station                |
| active   | BOOLEAN | Gerant actif                     |

### sessions
| Colonne          | Type    | Description                |
|------------------|---------|----------------------------|
| id               | INTEGER | Cle primaire               |
| user_id          | INTEGER | FK vers users              |
| check_date       | DATE    | Date du check              |
| current_question | INTEGER | Question en cours (0-5)    |
| completed        | BOOLEAN | Session terminee           |

### responses
| Colonne      | Type    | Description                    |
|--------------|---------|--------------------------------|
| id           | INTEGER | Cle primaire                   |
| user_id      | INTEGER | FK vers users                  |
| check_date   | DATE    | Date du check                  |
| station      | TEXT    | Station                        |
| pompes_ok    | BOOLEAN | Pompes fonctionnelles          |
| etat_ok      | BOOLEAN | Station propre/bon etat        |
| monnaie_ok   | BOOLEAN | Monnaie suffisante             |
| besoin_ok    | BOOLEAN | Pas de besoin materiel         |
| incident_ok  | BOOLEAN | Pas d'incident                 |
| confirmation | BOOLEAN | Confirmation des informations  |
| status       | TEXT    | OK / PROBLEME                  |
