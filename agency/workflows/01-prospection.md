# Workflow 1 — Prospection d'une zone

**Declencheur** : zone `active` dans `config/zones.json`, ou base sous 20 prospects qualifies.

1. Manager : ouvre un agent `prospecteur` avec la zone et les secteurs prioritaires.
2. Prospecteur : 3 angles minimum par passe (presse locale "vient d'ouvrir", annuaires, Google Maps,
   pages Facebook recentes sans site).
3. Verification des signaux pour chaque candidat (site, mobile, fiche Google, photos, reseaux, carte PDF).
4. `prospects.py add` -> `check`.
5. Manager : `stats`, commit, puis passe suivante ou zone suivante.

**Zone epuisee** : 3 passes consecutives sans ajout -> `statut: epuisee`, la premiere de la file devient `active`.

**Grille de refus** : dept 54, secteur exclu, deja client d'une agence, pas de source verifiable,
entreprise fermee, meme SIREN deja en base.
