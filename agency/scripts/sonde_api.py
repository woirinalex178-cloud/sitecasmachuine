#!/usr/bin/env python3
"""Sonde l'API publique recherche-entreprises (gratuite, sans cle) et sort un lot NDJSON
au format attendu par prospects.py. Stdlib uniquement.

Exemples :
  sonde_api.py --cp 57000 --sections I,S --depuis 2026-05-01 --out /tmp/lot.ndjson
  sonde_api.py --dept 88 --sections I --depuis 2026-01-01 --max-pages 40

Le departement 54 est refuse par securite (reserve Studio Celeste).
L'API ne filtre pas sur la date de creation : le filtre est applique ici, apres lecture.
"""
import argparse, json, os, re, sys, time, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datetime import date

API = "https://recherche-entreprises.api.gouv.fr/search"
DEPT_INTERDITS = {"54"}
import naf as naf_mod  # module local, voir agency/scripts/naf.py
secteur_de = naf_mod.secteur_de

EXCLUS_NOM = re.compile(r"\b(SCI|HOLDING|SAS SCI|MARCHAND DE BIENS)\b", re.I)


def get(params, essais=3):
    url = API + "?" + urllib.parse.urlencode(params)
    for n in range(essais):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if n == essais - 1:
                print(f"echec {url} : {e}", file=sys.stderr)
                return None
            time.sleep(2 ** n)


def ligne(e, section, depuis, dept_attendu=None):
    s = e.get("siege") or {}
    creation = e.get("date_creation") or s.get("date_creation") or ""
    if creation < depuis:
        return None
    if (s.get("etat_administratif") or "A") != "A":
        return None
    dept = (s.get("code_postal") or "")[:2]
    if dept in DEPT_INTERDITS or not dept:
        return None
    if dept_attendu and dept != dept_attendu:
        return None  # siege hors zone : etablissement d une societe non locale
    nom = e.get("nom_complet") or e.get("nom_raison_sociale") or ""
    if EXCLUS_NOM.search(nom):
        return None
    secteur = secteur_de(s.get("activite_principale"))
    if not secteur:
        return None  # code NAF exclu par l'ICP ou hors cible
    mois = (date.today() - date(*map(int, creation.split("-")))).days / 30.4
    return {
        "nom": nom.title(),
        "enseigne": (e.get("liste_enseignes") or [None])[0],
        "ville": (s.get("libelle_commune") or "").title(),
        "dept": dept,
        "secteur": secteur,
        "source": f"recherche-entreprises.api.gouv.fr siren {e.get('siren')}",
        "siren": e.get("siren"),
        "naf": s.get("activite_principale"),
        "adresse": s.get("adresse"),
        "ouverture": creation,
        "email": None, "telephone": None, "site": None,
        "signaux": {"creation_moins_6_mois": mois <= 6},
        "a_verifier": ["site", "fiche google", "reseaux"],
    }


p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument("--cp", help="code postal, ex 57000")
p.add_argument("--dept", help="departement, ex 88")
p.add_argument("--sections", default="I,S,G,F,R", help="sections NAF, ex I,S")
p.add_argument("--depuis", required=True, help="date de creation minimale AAAA-MM-JJ")
p.add_argument("--max-pages", type=int, default=25)
p.add_argument("--out", default="-")
a = p.parse_args()

if not a.cp and not a.dept:
    sys.exit("il faut --cp ou --dept")
if (a.dept or "") in DEPT_INTERDITS or (a.cp or "")[:2] in DEPT_INTERDITS:
    sys.exit("departement 54 interdit : reserve Studio Celeste")

sortie, vus = [], set()
for section in [s.strip().upper() for s in a.sections.split(",") if s.strip()]:
    for page in range(1, a.max_pages + 1):
        q = {"section_activite_principale": section, "etat_administratif": "A",
             "per_page": 25, "page": page, "minimal": "true",
             "include": "siege", "sort_by_size": "false"}
        if a.cp:
            q["code_postal"] = a.cp
        else:
            q["departement"] = a.dept
        d = get(q)
        if not d or not d.get("results"):
            break
        for e in d["results"]:
            if e.get("siren") in vus:
                continue
            vus.add(e.get("siren"))
            r = ligne(e, section, a.depuis, (a.cp or a.dept or "")[:2])
            if r:
                sortie.append(r)
        if page * 25 >= (d.get("total_results") or 0):
            break
        time.sleep(0.2)

f = sys.stdout if a.out == "-" else open(a.out, "w", encoding="utf-8")
for r in sortie:
    f.write(json.dumps(r, ensure_ascii=False) + "\n")
if f is not sys.stdout:
    f.close()
    print(f"{len(sortie)} entreprises creees depuis {a.depuis} -> {a.out}", file=sys.stderr)
