# Guide de l'Assistante Commerciale - NISSA

## Qu'est-ce que NISSA ?

NISSA est une plateforme de suivi de maintenance des stations-service. Elle envoie automatiquement un questionnaire quotidien aux gerants de station via WhatsApp et vous alerte en temps reel quand un probleme est detecte.

---

## 1. Connexion au panel d'administration

1. Ouvrez votre navigateur et allez sur l'adresse de la plateforme
2. Entrez vos identifiants :
   - **Identifiant** : fourni par l'administrateur
   - **Mot de passe** : fourni par l'administrateur
3. Cliquez **"Se connecter"**

Pour vous deconnecter, cliquez sur **"Deconnexion"** en haut a droite.

---

## 2. Le Dashboard (page d'accueil)

La page d'accueil (`/`) affiche :

- **Statut du jour** : quelles stations ont complete leur check, lesquelles sont en attente
- **Statistiques de la semaine** : nombre total de checks, nombre de problemes, taux de conformite
- **Details** : pour chaque check du jour, les reponses question par question

> Le dashboard est **public** (pas besoin de connexion). Vous pouvez le consulter a tout moment.

---

## 3. Le Panel Admin

Le panel admin (`/admin`) est accessible apres connexion. Il contient 5 onglets :

### Onglet "Questions"

Gerez les questions posees aux gerants.

**Ajouter une question :**
- **Texte** : la question (ex: "Le coffre-fort fonctionne-t-il correctement ?")
- **Type de probleme** : categorie (maintenance, exploitation, supervision, logistique, analyse)
- **Label du probleme** : description courte pour les alertes (ex: "Coffre en panne")
- **Programmation** : "Quotidien" (envoye chaque jour) ou "Occasionnel" (envoye sur demande)
- **Ordre** : position de la question dans le questionnaire (1, 2, 3...)
- **Question de suivi** : optionnel — si le gerant repond NON (ou OUI), poser une question complementaire en texte libre

**Exemple de question avec suivi :**
- Question : "Toutes les pompes fonctionnent-elles correctement ?"
- Suivi si : **NON**
- Question de suivi : "Un technicien est-il deja intervenu ?"

**Actions disponibles :**
- **Modifier** : changer le texte, le type, l'ordre
- **Activer/Desactiver** : une question desactivee n'est plus envoyee
- **Supprimer** : retirer definitivement la question

---

### Onglet "Gerants"

Gerez les gerants de station.

**Ajouter un gerant :**
- **Nom complet** : nom du gerant
- **Station** : nom de la station
- **Telephone WhatsApp** : numero au format international (ex: +22586752574)

**Important :** Apres l'ajout, le gerant doit :
1. Envoyer `join assign approve bundle` au +1 415 523 8886 sur WhatsApp
2. Cette activation est a refaire tous les 3 jours

**Actions disponibles :**
- **Modifier** : changer les informations
- **Activer/Desactiver** : un gerant desactive ne recoit plus de checks
- **Supprimer** : retirer definitivement le gerant et toutes ses donnees

---

### Onglet "Envoyer un check"

Declenchez des checks manuellement.

**Check quotidien :**
- Cliquez **"Envoyer le check quotidien maintenant"**
- Envoie toutes les questions quotidiennes a tous les gerants actifs
- Utile si le check automatique du matin n'a pas fonctionne

**Check occasionnel :**
1. Cochez les **questions** a envoyer
2. Cochez les **gerants** concernes
3. Cliquez **"Envoyer le check occasionnel"**
- Permet d'envoyer un questionnaire specifique a des gerants specifiques

**Export des donnees :**
- Telechargez l'historique des checks en fichier CSV (Excel)
- Choix : 7 jours, 30 jours ou 90 jours

---

### Onglet "Historique"

Consultez les 50 derniers checks completes :

| Colonne | Description |
|---|---|
| Date | Date du check |
| Station | Nom de la station |
| Gerant | Nom du gerant |
| Type | Quotidien ou Occasionnel |
| Statut | OK (vert) ou PROBLEME (rouge) |
| Problemes | Liste des problemes detectes |

---

### Onglet "Abonnement"

Gerez votre abonnement a la plateforme NISSA.

- **S'abonner** : cliquez pour acceder a la page de paiement Stripe (500$/mois)
- **Gerer l'abonnement** : modifier le moyen de paiement, annuler, etc.
- **Factures** : consultez et telechargez vos factures en PDF

---

## 4. Les alertes WhatsApp

Quand un gerant signale un probleme (repond NON a une question), vous recevez **automatiquement** une alerte sur votre WhatsApp :

```
ALERTE NISSA

Station : Station Niamey Centre
Gerant : Moussa Ibrahim
Date : 28/04/2026
Type : Quotidien

Problemes detectes :
- [MAINTENANCE] Pompe hors service — Technicien pas encore intervenu
- [LOGISTIQUE] Besoin materiel signale — Manque de jerricans

Action requise.
```

> Vous recevez cette alerte en temps reel, des que le gerant termine son check.

---

## 5. Le check automatique quotidien

- Le check est envoye **chaque jour a 8h00** automatiquement
- Il utilise toutes les questions marquees "Quotidien" et actives
- Les gerants inactifs ne recoivent pas le check
- Si un gerant a deja un check en cours ou termine pour la journee, il n'en recoit pas un deuxieme

---

## 6. Bonnes pratiques

1. **Verifiez le dashboard chaque matin** apres 9h pour voir qui a repondu
2. **Relancez** les gerants qui n'ont pas repondu (via le check occasionnel ou en les contactant)
3. **Reagissez rapidement** aux alertes PROBLEME
4. **Mettez a jour** les questions si les besoins changent
5. **Exportez les donnees** chaque mois pour vos rapports
6. **Desactivez** les gerants qui quittent leur poste (ne les supprimez pas pour garder l'historique)

---

## 7. Problemes courants

| Probleme | Solution |
|---|---|
| Un gerant ne recoit pas les messages | Verifiez qu'il est actif dans l'admin. Demandez-lui de renvoyer `join assign approve bundle` |
| Le check quotidien n'a pas ete envoye | Declenchez-le manuellement depuis l'onglet "Envoyer un check" |
| Un gerant a change de numero | Modifiez son numero dans l'onglet "Gerants" |
| Vous ne recevez pas les alertes | Verifiez que votre numero est bien configure et que vous avez active le sandbox |
| La page admin ne charge pas | Verifiez votre connexion internet et reconnectez-vous |

---

## 8. Resume des actions quotidiennes

| Heure | Action |
|---|---|
| 8h00 | Check automatique envoye aux gerants |
| 9h00 | Consultez le dashboard pour voir les reponses |
| 9h-10h | Reagissez aux alertes PROBLEME |
| 10h | Relancez les gerants qui n'ont pas repondu |
| Fin de mois | Exportez les donnees CSV pour le rapport |
