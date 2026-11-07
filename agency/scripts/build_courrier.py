#!/usr/bin/env python3
"""Produit, pour un prospect de la base, le support de premier contact :
une lettre A5 prete a imprimer avec QR code vers sa demo, et/ou un dossier d'appel.

  build_courrier.py --cle siren:104221718 --format courrier
  build_courrier.py --top 10 --format les-deux

Refuse de produire un courrier tant que agency/config/agence.json porte des
champs « A RENSEIGNER » : une lettre signee d'une identite fausse est pire que
pas de lettre. Le dossier d'appel, lui, reste produit (usage interne).
"""
import argparse, io, json, os, re, sys, unicodedata
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "prospects.ndjson")
AGENCE = json.load(open(os.path.join(ROOT, "config", "agence.json"), encoding="utf-8"))
OFFRES = {o["code"]: o for o in json.load(open(os.path.join(ROOT, "config", "offers.json"), encoding="utf-8"))["offres"]}
MOIS = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout",
        "septembre", "octobre", "novembre", "decembre"]
LIBELLE = {"restauration": "votre restaurant", "beaute-bien-etre": "votre activite de beaute et bien-etre",
           "batiment": "votre activite du batiment", "commerce de detail": "votre commerce",
           "sante-liberal": "votre cabinet", "sport-loisirs": "votre activite sport et loisirs",
           "artisanat": "votre atelier", "services aux particuliers": "votre activite"}


def slug(s):
    s = unicodedata.normalize("NFKD", (s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def qr_svg(url):
    import qrcode, qrcode.image.svg
    q = qrcode.QRCode(box_size=9, border=1, error_correction=qrcode.constants.ERROR_CORRECT_M)
    q.add_data(url)
    b = io.BytesIO()
    q.make_image(image_factory=qrcode.image.svg.SvgPathImage).save(b)
    svg = b.getvalue().decode()
    return re.sub(r'<\?xml[^>]*\?>', '', svg).replace('<svg', '<svg class="qr"', 1)


def ouverture(r):
    d = (r.get("ouverture") or "")[:10]
    if not re.match(r"\d{4}-\d{2}", d):
        return ""
    a, m = d[:4], int(d[5:7])
    return f"en {MOIS[m - 1]} {a}"


def offre_de(r):
    code = r.get("offre_cible") or ("CARTE-INTER" if r.get("secteur") == "restauration" else "SITE-VITRINE")
    return OFFRES.get(code) or OFFRES["SITE-VITRINE"]


CSS = """@page{size:A5;margin:14mm}
*{box-sizing:border-box}
body{margin:0;font:11.5pt/1.5 Georgia,'Times New Roman',serif;color:#16181d}
header{display:flex;justify-content:space-between;align-items:flex-start;border-bottom:1.5pt solid #16181d;padding-bottom:5mm;margin-bottom:7mm}
.agence{font:600 13pt/1.2 Helvetica,Arial,sans-serif;letter-spacing:.02em}
.agence small{display:block;font:400 8.5pt/1.4 Helvetica,Arial,sans-serif;color:#5b6270;margin-top:1.5mm}
.dest{text-align:right;font-size:9.5pt;color:#333}
h1{font:600 15pt/1.25 Helvetica,Arial,sans-serif;margin:0 0 5mm}
p{margin:0 0 3.5mm}
.encart{display:flex;gap:6mm;align-items:center;border:1pt solid #c9cdd6;border-radius:3mm;padding:4mm;margin:5mm 0;background:#f8f9fb}
.encart p{margin:0;font-size:10pt}
.qr{width:26mm;height:26mm;flex:0 0 26mm}
.offre{font:600 10.5pt Helvetica,Arial,sans-serif}
footer{margin-top:6mm;border-top:.5pt solid #c9cdd6;padding-top:3mm;font:8.5pt/1.4 Helvetica,Arial,sans-serif;color:#5b6270}
@media screen{body{max-width:148mm;margin:8mm auto;padding:14mm;background:#fff;box-shadow:0 2px 18px #0002}}"""


def courrier(r, url):
    o = offre_de(r)
    nom = r.get("enseigne") or r.get("nom")
    quoi = LIBELLE.get(r.get("secteur"), "votre activite")
    ouv = ouverture(r)
    acc = r.get("accroche")
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<title>Courrier {nom}</title><style>{CSS}</style></head><body>
<header>
  <div class="agence">{AGENCE['nom']}<small>{AGENCE['adresse']}<br>{AGENCE['telephone']} &middot; {AGENCE['email']}</small></div>
  <div class="dest">{nom}<br>{r.get('adresse') or ''}</div>
</header>
<h1>Vous avez ouvert {ouv}. Voici a quoi {quoi} ressemblerait en ligne.</h1>
<p>Bonjour,</p>
<p>J'ai vu que vous aviez cree votre activite a {r.get('ville')} {ouv}. {acc or
 "Quand quelqu'un cherche votre nom sur son telephone, ce qu'il trouve decide s'il vient ou s'il passe a cote."}</p>
<p>Plutot que de vous le decrire, je l'ai fabrique. Le code ci-dessous ouvre une
maquette faite a votre nom, sur votre telephone, en dix secondes.</p>
<div class="encart">{qr_svg(url)}
  <p><span class="offre">{o['nom']} &middot; {o['prix']} &euro;</span><br>
  Livre en {o['delai_j']} jours. {", ".join(o['livrables'][:3])}.<br>
  Si la maquette ne vous parle pas, vous ne me devez rien et vous gardez le lien.</p></div>
<p>Si vous voulez la version complete, un appel de dix minutes suffit : {AGENCE['telephone']}.</p>
<p>{AGENCE['signataire']}</p>
<footer>{AGENCE['nom']} &middot; {AGENCE['adresse']} &middot; SIRET {AGENCE['siret']}<br>
Vous ne souhaitez plus etre contacte : un appel ou un email et vos coordonnees sont supprimees de nos fichiers.</footer>
</body></html>"""


def dossier_appel(r, url):
    o = offre_de(r)
    nom = r.get("enseigne") or r.get("nom")
    sig = [k for k, v in (r.get("signaux") or {}).items() if v is True]
    av = r.get("a_verifier") or []
    return f"""# Dossier d'appel — {nom}

**{r.get('ville')} ({r.get('dept')}) · {r.get('secteur')} · ouvert {ouverture(r) or 'date inconnue'} · score {r.get('score')}**
{r.get('adresse') or 'adresse inconnue'}
SIREN {r.get('siren') or '—'} · NAF {r.get('naf') or '—'}
Telephone : {r.get('telephone') or 'A TROUVER AVANT L APPEL'} · Email : {r.get('email') or '—'}
Site connu : {r.get('site') or 'aucun site trouve'}

## Ce qui est etabli
{chr(10).join('- ' + s.replace('_', ' ') for s in sig) or '- rien de verifie au-dela du registre'}
{('- reste a verifier : ' + ', '.join(av)) if av else ''}

## Accroche
{r.get('accroche') or "A ouvrir sur le fait qu'il vient d'ouvrir, pas sur ce qui lui manque : rien n'est verifie."}

## Offre a proposer
**{o['nom']} — {o['prix']} €**, livre en {o['delai_j']} jours.
Livrables : {', '.join(o['livrables'])}.
Declencheur attendu : {o['declencheur']}.

## Demo a envoyer juste apres l'appel
{url}

## A ne pas faire
- ne rien affirmer sur sa fiche Google ni sur ses reseaux : ce n'est pas verifie
- ne pas annoncer de chiffre de resultat, aucun n'est prouvable
- s'il a deja un site, basculer sur la carte interactive ou la fiche Google, ne pas insister

## Issue
- interesse → `prospects.py set {r.get('cle')} --statut rdv --note "..."`
- pas maintenant → `--statut relance`
- non → `--statut perdu` · ne plus contacter → `--statut exclu`
"""


p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument("--cle", action="append")
p.add_argument("--top", type=int, default=0, help="les N meilleurs scores non encore contactes")
p.add_argument("--format", choices=["courrier", "appel", "les-deux"], default="les-deux")
a = p.parse_args()

rows = [json.loads(l) for l in open(DB, encoding="utf-8") if l.strip()]
if a.cle:
    choisis = [r for r in rows if r.get("cle") in set(a.cle)]
elif a.top:
    choisis = [r for r in rows if r.get("statut") in ("nouveau", "qualifie")][: a.top]
else:
    sys.exit("precise --cle ou --top")
if not choisis:
    sys.exit("aucun prospect ne correspond")

manque = [k for k, v in AGENCE.items() if not k.startswith("_") and v == "A RENSEIGNER"]
faits = []
for r in choisis:
    d = os.path.join(ROOT, "clients", slug(r["cle"]))
    os.makedirs(d, exist_ok=True)
    base = AGENCE["base_url_demos"].rstrip("/") if "A RENSEIGNER" not in AGENCE["base_url_demos"] else "https://demo.invalide"
    url = f"{base}/{slug(r['cle'])}/"
    if a.format in ("appel", "les-deux"):
        open(os.path.join(d, "dossier-appel.md"), "w", encoding="utf-8").write(dossier_appel(r, url))
        faits.append(f"{d}/dossier-appel.md")
    if a.format in ("courrier", "les-deux"):
        if manque:
            print(f"courrier non produit : agence.json incomplet ({', '.join(manque)})", file=sys.stderr)
        else:
            open(os.path.join(d, "courrier.html"), "w", encoding="utf-8").write(courrier(r, url))
            faits.append(f"{d}/courrier.html")
for f in faits:
    print(f)
