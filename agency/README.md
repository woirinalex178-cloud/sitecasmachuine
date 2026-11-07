# Agence multimedia — systeme de production piloté par agents

Objectif : trouver des entreprises recemment creees, leur proposer ce qui leur manque en ligne
(site, fiche Google, reseaux, carte interactive), produire et livrer — en interne, sans budget.

## Qui fait quoi

| Role | Agent | Entree | Sortie |
|---|---|---|---|
| Chef d'orchestre | session principale | objectifs | affectations, arbitrages, commits |
| Atelier | `builder` | un manque d'outil | scripts, workflows n8n testes |
| Prospection | `prospecteur` | une zone | lignes NDJSON dedoublonnees et scorees |
| Acquisition | `funnel` | prospects scores | email + video motion 15s personnalisee |
| Studio web | `web-designer` | prospect gagne ou demo | site / carte interactive livree |
| Reseaux & local | `social-producer` | offre GBP ou SOCIAL-PACK | fiche Google, calendrier, visuels |
| Controle | `qa-agence` | un livrable | VERDICT + corrections |

Lancement : `Agent(subagent_type: "<nom>")`. Relance d'un agent existant : `SendMessage`.

## Regle territoriale
**Departement 54 (Meurthe-et-Moselle) interdit** — reserve a Studio Celeste. Refus automatique
a l'ingestion (`prospects.py`) et interdiction explicite dans la fiche de chaque agent.

## Base de prospects
`agency/data/prospects.ndjson` — une ligne JSON par prospect, triee par score.
Cle d'unicite : SIREN si connu, sinon `nom+ville` normalises. **Aucune ecriture manuelle** :

```bash
python3 agency/scripts/prospects.py add lot.ndjson   # ingere (dedup + score + refus zone/secteur)
python3 agency/scripts/prospects.py stats            # etat du pipeline
python3 agency/scripts/prospects.py next --n 10       # prochains a contacter
python3 agency/scripts/prospects.py set <cle> --statut contacte --note "..."
python3 agency/scripts/prospects.py check            # controle qualite, exit 1 si erreur
python3 agency/scripts/prospects.py export --out /tmp/prospects.csv
```

Statuts : `nouveau -> qualifie -> contacte -> relance -> repondu -> rdv -> gagne | perdu | exclu`.

## Reglages
- `config/zones.json` — zones, file d'attente, exclusions
- `config/icp.json` — cible, secteurs, grille de score (seuil qualifie 50, prioritaire 75)
- `config/offers.json` — catalogue et prix

## Boucle IA (auto-amelioration)
Chaque cycle : **produire -> `check` / `qa-agence` -> corriger -> mesurer -> ajuster les reglages**.
Ce qui est mesure a chaque cycle : prospects ajoutes/doublons, taux de reponse par accroche,
score moyen des prospects qui repondent. Les seuils et le scoring de `icp.json` sont ajustes
avec ces chiffres, pas a l'intuition. Journal : `agency/state/pipeline.md`.

## Limites connues et division du travail

Le conteneur de cette session est sur liste blanche reseau. Ce qui marche et ce qui ne marche pas,
teste, pas suppose :

| Source | Depuis ce conteneur | Consequence |
|---|---|---|
| `recherche-entreprises.api.gouv.fr` | oui | gisement des creations recentes, gratuit, sans cle |
| Overpass / OpenStreetMap | non (connexion reinitialisee) | `sonde_osm.py` est ecrit et pret, mais doit tourner ailleurs |
| `html.duckduckgo.com` | non (page anti-robot) | pas de recherche scriptee |
| Google, Planity, Facebook, Instagram | non | fiche Google et activite reseaux invisibles en masse |
| WebSearch / web-fetch des agents | oui | seule voie de verification fiable, mais elle coute des tokens |

**Regle qui en decoule :** la verification en masse (site, telephone, fiche, reseaux) appartient au
VPS n8n, qui n'a pas ces restrictions. Les agents de cette session verifient a la main les
prospects a forte valeur, pas les 250 de la file. Ordre de grandeur mesure : environ 7 000 tokens
par prospect verifie a la main.

**Signaux jamais deduits.** Une etiquette absente d'une source incomplete ne prouve rien :
`gbp_absente` et `reseaux_inactifs` restent vides tant qu'une source ne les a pas etablis, et
figurent dans `a_verifier`. Un prospect vendu sur un constat faux coute plus cher qu'un prospect perdu.

- Aucun envoi d'email reel sans validation explicite dans la session.
