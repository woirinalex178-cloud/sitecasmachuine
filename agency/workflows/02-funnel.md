# Workflow 2 — Tunnel de contact

**Declencheur** : au moins 5 prospects avec score >= 75.

1. `prospects.py next --n 5`.
2. Par prospect : video motion 15s personnalisee (`highfields`) + email 1 (max 110 mots, un signal precis, une question fermee).
3. `qa-agence` sur les 5 emails + 5 videos -> corrections -> 2e passe.
4. Gmail : `create_draft` uniquement. Validation du manager, puis envoi.
5. `prospects.py set <cle> --statut contacte`.
6. J+3 relance "angle", J+8 porte de sortie. Reponse -> `repondu`, puis `rdv`.

**Plafonds** : 20 nouveaux contacts/jour, 1 email/entreprise/semaine, 3 emails maximum par prospect.

**Mesure** : taux d'ouverture non mesurable sans tracker -> on mesure le taux de reponse par accroche
et par secteur, consigne dans `state/pipeline.md`.
