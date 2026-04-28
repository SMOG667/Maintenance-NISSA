# NISSA - Chatbot WhatsApp de Maintenance Stations

Systeme automatise de check journalier des stations-service via WhatsApp.

## Fonctionnalites

- **Check journalier automatique** a 7h UTC via cron
- **Check occasionnel** declenchable depuis le panel admin
- **Questions OUI/NON** avec suivi conditionnel (ex: si NON → "Precisez le probleme")
- **Alertes superviseur** en temps reel quand un probleme est detecte
- **Panel admin securise** (login/mot de passe) pour gerer gerants, questions, historique
- **Dashboard public** avec statut du jour et stats hebdomadaires
- **Export CSV** des donnees
- **Abonnement Stripe** (500$/mois)
- **Integration Google Sheets** (optionnelle)

## Stack technique

- **Backend** : FastAPI (Python)
- **Base de donnees** : PostgreSQL (Supabase)
- **WhatsApp** : Twilio WhatsApp API
- **Hebergement** : Vercel (serverless)
- **Paiement** : Stripe

## Installation locale

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Editer .env avec vos credentials
python seed.py
python run.py
```

## Deploiement

Deploye automatiquement sur Vercel via GitHub. Les variables d'environnement sont dans `vercel.json`.

## Endpoints

| URL | Description |
|---|---|
| `/` | Dashboard public |
| `/admin` | Panel admin (protege) |
| `/login` | Page de connexion |
| `/webhook` | Webhook Twilio WhatsApp |
| `/cron/daily-check` | Check journalier (cron) |
| `/privacy` | Politique de confidentialite |
| `/data-deletion` | Suppression des donnees |
