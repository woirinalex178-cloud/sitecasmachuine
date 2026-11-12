# Workflow 3 — Production apres accord

**Declencheur** : prospect `gagne`.

1. Manager : fiche de production dans `agency/clients/<cle>/brief.md` (offre, delai, contenus fournis, acces).
2. Contenus manquants -> `social-producer` genere les visuels, `web-designer` ecrit les textes.
3. Livraison selon l'offre :
   - `SITE-VITRINE` / `CARTE-INTER` -> `web-designer`, mise en ligne Vercel, 5 jours.
   - `GBP` / `SOCIAL-PACK` -> `social-producer`, 2 jours / 30 jours.
   - `MOTION-TEASER` -> `funnel` (meme chaine motion), 3 jours.
4. `qa-agence` : VERDICT LIVRABLE obligatoire avant envoi au client.
5. Remise : lien, `README.md` de maintenance, 1 boucle de retouches incluse.
6. Apres livraison : demande d'avis Google, proposition du palier suivant, prospect -> `client`.
