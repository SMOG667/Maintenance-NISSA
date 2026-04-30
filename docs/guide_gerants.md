# Guide du Gerant de Station - NISSA

## Qu'est-ce que NISSA ?

NISSA est un assistant WhatsApp qui vous envoie chaque jour un questionnaire rapide pour verifier l'etat de votre station-service. Vos reponses permettent a la direction de suivre les operations et d'intervenir rapidement en cas de probleme.

---

## Comment ca marche ?

### 1. Activation (une seule fois)

Avant de commencer, vous devez activer votre connexion au chatbot :

1. Ouvrez **WhatsApp** sur votre telephone
2. Envoyez le message suivant au numero **+1 415 523 8886** :

```
join assign approve bundle
```

3. Vous recevrez une confirmation
4. C'est fait ! Vous etes connecte a NISSA

> **Important** : cette activation doit etre refaite tous les 3 jours. Si vous ne recevez plus de messages, renvoyez simplement le message d'activation.

---

### 2. Le check journalier

Chaque jour, NISSA vous envoie un message de bienvenue suivi de questions sur votre station :

```
Bonjour [votre nom] !

C'est l'heure du check journalier pour la station [votre station].
Je vais vous poser 6 questions rapides.

Repondez uniquement par OUI ou NON.

C'est parti !

1/6 - Le coffre-fort fonctionne-t-il correctement ?
Repondez par OUI ou NON
```

---

### 3. Comment repondre ?

Repondez a chaque question par :

- **OUI** — si tout va bien
- **NON** — si il y a un probleme

Vous pouvez aussi ecrire : **O**, **N**, **YES**, **NO**, **1**, **0**

> **Attention** : Ne repondez que par OUI ou NON. Tout autre message ne sera pas compris.

---

### 4. Questions de suivi

Pour certaines questions, si vous repondez **NON**, NISSA vous demandera plus de details :

```
Toutes les pompes fonctionnent-elles correctement ?
→ NON

Un technicien est-il deja intervenu ?
→ Tapez votre reponse en texte libre
```

Dans ce cas, ecrivez votre reponse normalement (pas besoin de OUI/NON).

---

### 5. Fin du check

Quand toutes les questions sont terminees, vous recevez un message de confirmation :

**Si tout va bien :**
```
Merci [votre nom] !
Check termine pour [votre station].
Statut : OK - Aucun probleme detecte.
Bonne journee !
```

**Si un probleme est detecte :**
```
Merci [votre nom] !
Check termine pour [votre station].
Statut : PROBLEME DETECTE

L'assistante a ete notifiee. Problemes signales :
- [MAINTENANCE] Pompe hors service
Bonne journee !
```

> Quand un probleme est detecte, l'assistante commerciale est **automatiquement alertee** par WhatsApp.

---

## Questions frequentes

**Q : Je n'ai pas recu le check du jour, que faire ?**
R : Envoyez "bonjour" au numero NISSA. Le check demarrera automatiquement.

**Q : Je me suis trompe dans une reponse, que faire ?**
R : Continuez le check normalement. Signalez l'erreur a votre superviseur.

**Q : Je recois "votre numero n'est pas enregistre", que faire ?**
R : Contactez votre superviseur pour qu'il ajoute votre numero dans le systeme.

**Q : Je ne recois plus de messages ?**
R : Renvoyez le message d'activation : `join assign approve bundle` au +1 415 523 8886

**Q : A quelle heure le check est-il envoye ?**
R : Le check journalier est envoye automatiquement chaque jour a **8h00**.

---

## Resume

| Etape | Action |
|---|---|
| Activation | Envoyez `join assign approve bundle` au +1 415 523 8886 |
| Check du jour | Repondez OUI ou NON a chaque question |
| Question de suivi | Tapez votre reponse en texte |
| Probleme | L'assistante est alertee automatiquement |
