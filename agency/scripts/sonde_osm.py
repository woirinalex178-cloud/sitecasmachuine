#!/usr/bin/env python3
"""Confronte la base de prospects aux commerces cartographies dans OpenStreetMap
(Overpass, gratuit, sans cle) pour recuperer site web et telephone verifiables.

  sonde_osm.py --ville Metz [--ville Thionville] --out lot.ndjson

Prudence de methode : OSM est incomplet. Une etiquette presente est une preuve
(il a un site, voici son numero) ; une etiquette absente ne prouve rien et ne
produit donc jamais le signal 'pas_de_site'.
"""
import argparse, json, os, re, sys, time, unicodedata, urllib.parse, urllib.request

OVERPASS = "https://overpass-api.de/api/interpreter"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "prospects.ndjson")

REQ = """[out:json][timeout:90];
area["name"="%s"]["boundary"="administrative"]->.a;
(
  node(area.a)["name"]["amenity"];
  way(area.a)["name"]["amenity"];
  node(area.a)["name"]["shop"];
  way(area.a)["name"]["shop"];
  node(area.a)["name"]["craft"];
  node(area.a)["name"]["office"];
  node(area.a)["name"]["leisure"];
);
out tags center;"""


def slug(s):
    s = unicodedata.normalize("NFKD", (s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


MOTS_VIDES = {"le", "la", "les", "de", "du", "des", "sarl", "sas", "eurl", "sasu", "et", "l", "d", "chez"}


def jetons(nom):
    return {m for m in slug(nom).split() if m not in MOTS_VIDES and len(m) > 2}


def overpass(ville):
    data = urllib.parse.urlencode({"data": REQ % ville}).encode()
    for n in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(OVERPASS, data=data), timeout=120) as r:
                return json.loads(r.read().decode())["elements"]
        except Exception as e:
            if n == 2:
                print(f"overpass {ville} : {e}", file=sys.stderr)
                return []
            time.sleep(5 * (n + 1))


p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument("--ville", action="append", required=True)
p.add_argument("--out", default="-")
p.add_argument("--seuil", type=float, default=0.6, help="recouvrement minimal des jetons du nom")
a = p.parse_args()

base = [json.loads(l) for l in open(DB, encoding="utf-8") if l.strip()]
sortie, vus = [], set()
for ville in a.ville:
    poi = overpass(ville)
    print(f"{ville} : {len(poi)} commerces cartographies", file=sys.stderr)
    cibles = [r for r in base if slug(r.get("ville")) == slug(ville) and r.get("statut") != "exclu"]
    for r in cibles:
        jr = jetons(r.get("enseigne") or r.get("nom"))
        if not jr:
            continue
        best, bscore = None, 0.0
        for e in poi:
            t = e.get("tags", {})
            je = jetons(t.get("name"))
            if not je:
                continue
            rec = len(jr & je) / len(jr)
            if rec > bscore:
                best, bscore = t, rec
        if not best or bscore < a.seuil:
            continue
        site = best.get("website") or best.get("contact:website") or best.get("url")
        tel = best.get("phone") or best.get("contact:phone")
        if not site and not tel:
            continue
        cle = r.get("cle")
        if cle in vus:
            continue
        vus.add(cle)
        ligne = {k: r.get(k) for k in ("nom", "ville", "dept", "secteur", "siren")}
        ligne["source"] = f"OpenStreetMap ({ville}), nom cartographie « {best.get('name')} »"
        ligne["signaux"] = {}
        if site:
            ligne["site"] = site
        else:
            ligne["signaux"]["site_obsolete_ou_non_mobile"] = False
        if tel:
            ligne["telephone"] = tel
        sortie.append(ligne)
    time.sleep(2)

f = sys.stdout if a.out == "-" else open(a.out, "w", encoding="utf-8")
for r in sortie:
    f.write(json.dumps(r, ensure_ascii=False) + "\n")
if f is not sys.stdout:
    f.close()
print(f"{len(sortie)} correspondance(s) utile(s) -> {a.out}", file=sys.stderr)
