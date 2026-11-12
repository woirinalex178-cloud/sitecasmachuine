# La Casa Demir — démo carte interactive

Démo générée le 6 novembre 2026 par Studio Cas Machuine, à partir de la fiche prospect `siren:104221718`.
Offre correspondante : **Carte interactive restaurant** (490 €, 4 jours).

## Ouvrir la démo

```bash
# double-clic sur index.html suffit (la carte bascule alors sur la copie intégrée du menu)
# ou, pour être au plus près de la mise en ligne :
python3 -m http.server 8080 --directory agency/clients/siren-104221718-carte
# puis http://localhost:8080
```

## Régénérer

```bash
python3 agency/scripts/build_demo.py --cle siren:104221718 --type carte
```

La commande est idempotente : elle réécrit le dossier à l'identique.
**Toute modification manuelle de ces fichiers sera écrasée** — si la démo devient un
chantier client, sortir le dossier du cycle de génération ou reporter les changements
dans le gabarit `agency/templates/carte-interactive/`.

## Ce qu'il y a dans le dossier

- `index.html` — la page, tout le contenu éditable est dedans
- `menu.json` — **la carte** : c'est le seul fichier à modifier au quotidien
- `assets/style.css` — un seul fichier de style ; les couleurs sont des variables en haut (`:root`)
- `assets/app.js` — comportements (menu, horaires du jour, filtres et QR code)
- `assets/favicon.svg`, `assets/og.svg` — icône et image de partage, générées en SVG
- `assets/qr.js` — générateur de QR code local (aucune API externe)

## À valider avec le client avant mise en ligne

- [ ] le **numéro de téléphone** (absent de la base — passer `--tel "03 87 …"` pour le réinjecter)
- [ ] l'**adresse e-mail** de contact (`--email`)
- [ ] les **horaires** (valeurs par défaut du secteur « restauration »)
- [ ] les **textes de présentation** et les intitulés de prestations
- [ ] les **plats, prix et allergènes** de `menu.json` (carte type, à remplacer par la vraie carte)
- [ ] le **formulaire de contact** : il valide les champs mais n'envoie rien tant qu'un
      service d'envoi n'est pas branché (Formspree, Netlify Forms ou une route serveur).
- [ ] l'**image de partage** `assets/og.svg` : l'exporter en PNG 1200×630 pour que les
      réseaux sociaux l'affichent (le SVG est ignoré par Facebook et LinkedIn).
- [ ] retirer `<meta name="robots" content="noindex, nofollow">` de `index.html`
      le jour de la mise en ligne, et remplacer `https://la-casa-demir.fr/` par le vrai domaine.

## Mettre la carte à jour

Tout se passe dans `menu.json`. Un plat ressemble à ceci :

```json
{ "nom": "Plat du jour", "description": "Annoncé en salle.", "prix": 13.5,
  "categorie": "plats", "vegetarien": false, "signature": false,
  "allergenes": ["gluten", "lait"] }
```

- `categorie` doit reprendre un `id` de la liste `categories` (`formules`, `sandwichs`, `assiettes`, `accompagnements`, `desserts`, `boissons`).
- `allergenes` reprend les clés de l'objet `allergenes` en haut du fichier (14 disponibles).
- `prix` est un nombre, sans symbole : `13.5`, pas `"13,50 €"`.

Après modification : recharger la page. Si elle est ouverte par double-clic
(`file://`), le navigateur refuse de lire `menu.json` — la page utilise alors la
copie intégrée au HTML, qui date de la dernière génération. **Pour voir ses
modifications, passer par `python3 -m http.server` ou régénérer la démo.**

## QR code de table

Bouton « QR code » en haut de page : le code est calculé dans le navigateur
(aucune API externe, aucune donnée envoyée), niveau de correction M.
L'adresse encodée est modifiable dans la fenêtre, et le code se télécharge en PNG
ou s'imprime directement en affichette.

## Contenu : ce qui est factuel, ce qui est proposé

Viennent de la base (sources publiques) : raison sociale, adresse, ville, SIREN,
date de création, secteur d'activité.
Tout le reste — accroches, descriptions de prestations, horaires, tarifs indicatifs,
carte, engagements — est une **proposition rédactionnelle**
à valider ou corriger par le client. Aucun faux avis client, aucune statistique inventée
ne figure sur la page.

## Mise en ligne

Site strictement statique (aucun build, aucune dépendance) : déposer le contenu du
dossier sur n'importe quel hébergement statique (Vercel, GitHub Pages, un FTP mutualisé).
Penser à activer HTTPS et à vérifier la fiche Google Business en parallèle.
