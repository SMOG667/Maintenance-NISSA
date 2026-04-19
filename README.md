# NISSA - Chatbot WhatsApp de Maintenance Stations

Systeme de check journalier des stations-service par WhatsApp, utilisant l'API WhatsApp Cloud de Meta.

## Architecture

```
app/
├─��� main.py          # FastAPI - endpoints + webhook Meta + dashboard + admin
├── config.py        # Configuration (.env)
├── database.py      # SQLAlchemy setup (SQLite / PostgreSQL)
├── models.py        # Modeles: User, Question, CheckSession, Answer
├── questions.py     # Questions par defaut + messages du chatbot
├── session.py       # Logique de session + traitement messages
├── whatsapp.py      # Client WhatsApp Cloud API (Meta Graph API)
├── sheets.py        # Integration Google Sheets (optionnel)
└── templates/
    ├── dashboard.html  # Dashboard public
    └── admin.html      # Panneau d'administration
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
# Editer .env avec vos credentials Meta WhatsApp
```

## Configuration WhatsApp Cloud API (Meta)

1. Creer un compte sur https://developers.facebook.com
2. Creer une app de type "WhatsApp Business"
3. Recuperer le **Token d'acces** et le **Phone Number ID**
4. Configurer le webhook dans l'app Meta :
   - URL : `https://votre-domaine.com/webhook`
   - Verify Token : celui defini dans votre `.env` (WHATSAPP_VERIFY_TOKEN)
   - S'abonner a l'evenement **messages**
5. Renseigner les valeurs dans `.env`

## Lancement

```bash
# Initialiser la base avec des donnees de test
python seed.py

# Lancer le serveur
python run.py
```

Le serveur demarre sur `http://localhost:8000`

- Dashboard : `http://localhost:8000/`
- Admin : `http://localhost:8000/admin`

## Test local (sans WhatsApp)

```bash
python test_local.py
```

Ce script simule l'interaction chatbot dans le terminal.

## Endpoints

| Methode | URL                      | Description                          |
|---------|--------------------------|--------------------------------------|
| GET     | `/webhook`               | Verification webhook Meta            |
| POST    | `/webhook`               | Reception messages WhatsApp          |
| GET     | `/cron/daily-check`      | Check journalier (cron Vercel)       |
| GET     | `/api/stations`          | Liste des stations/gerants           |
| GET     | `/api/questions`         | Liste des questions                  |
| GET     | `/api/checks`            | Historique des checks                |
| GET     | `/`                      | Dashboard de suivi                   |
| GET     | `/admin`                 | Panneau d'administration             |
| GET     | `/admin/export`          | Export CSV                           |

## Deploiement Vercel + Supabase

1. Creer un projet Supabase et recuperer l'URL PostgreSQL
2. Deployer sur Vercel (connecter le repo GitHub)
3. Configurer les variables d'environnement dans Vercel :
   - `WHATSAPP_TOKEN`
   - `WHATSAPP_PHONE_NUMBER_ID`
   - `WHATSAPP_VERIFY_TOKEN`
   - `ASSISTANT_WHATSAPP_NUMBER`
   - `DATABASE_URL` (URL PostgreSQL Supabase)
   - `CRON_SECRET`
4. Le cron Vercel envoie automatiquement le check journalier a 7h UTC

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
