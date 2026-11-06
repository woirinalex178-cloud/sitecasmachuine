#!/usr/bin/env python3
"""Base de prospects : anti-doublon, scoring, pipeline. Stdlib uniquement.

Usage :
  prospects.py add fichier.ndjson        # ingere un lot (dedup + score)
  prospects.py stats                     # etat de la base
  prospects.py next --n 10 [--zone 57]   # prochains a contacter (score desc)
  prospects.py set SIREN_OU_ID --statut contacte [--note "..."]
  prospects.py check                     # controle qualite (exit 1 si erreur)
  prospects.py export --out prospects.csv
"""
import argparse, csv, json, os, re, sys, unicodedata
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "prospects.ndjson")
ICP = json.load(open(os.path.join(ROOT, "config", "icp.json"), encoding="utf-8"))
ZONES = json.load(open(os.path.join(ROOT, "config", "zones.json"), encoding="utf-8"))
DEPT_INTERDITS = set(ZONES["exclusions"])
STATUTS = ["nouveau", "qualifie", "contacte", "relance", "repondu", "rdv", "gagne", "perdu", "exclu"]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.I)


def slug(s):
    s = unicodedata.normalize("NFKD", (s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def key(p):
    """Cle d'unicite : SIREN si connu, sinon nom+ville."""
    siren = re.sub(r"\D", "", p.get("siren") or "")
    return f"siren:{siren}" if len(siren) == 9 else f"nv:{slug(p.get('nom'))}|{slug(p.get('ville'))}"


def score(p):
    s, g = ICP["scoring"], p.get("signaux", {})
    total = sum(v for k, v in s.items() if g.get(k) is True)
    if p.get("secteur") in ICP["secteurs_prioritaires"]:
        total += s["secteur_prioritaire"]
    return max(0, total)


def load():
    if not os.path.exists(DB):
        return []
    out = []
    for line in open(DB, encoding="utf-8"):
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def save(rows):
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    rows.sort(key=lambda r: (-r.get("score", 0), r.get("cle", "")))
    with open(DB, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def cmd_add(a):
    rows = load()
    index = {r["cle"]: r for r in rows}
    added = dup = refused = 0
    for line in open(a.fichier, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        p = json.loads(line)
        if (p.get("dept") or "") in DEPT_INTERDITS:
            refused += 1
            continue
        if p.get("secteur") in ICP["secteurs_exclus"]:
            refused += 1
            continue
        p["cle"] = key(p)
        if p["cle"] in index:
            # enrichit sans ecraser l'existant
            cur = index[p["cle"]]
            for k, v in p.items():
                if k in ("cle", "statut", "historique", "signaux", "score", "ajoute_le"):
                    continue
                if v not in (None, "", {}, []) and cur.get(k) in (None, "", {}, []):
                    cur[k] = v
            # les signaux verifies les plus recents gagnent
            cur["signaux"] = {**cur.get("signaux", {}), **p.get("signaux", {})}
            avant = cur.get("score", 0)
            cur["score"] = score(cur)
            if cur["score"] != avant:
                cur.setdefault("historique", []).append(
                    f"{now()} enrichi : score {avant} -> {cur['score']}")
            if cur.get("statut") == "nouveau" and cur["score"] >= ICP["seuil_qualifie"]:
                cur["statut"] = "qualifie"
            dup += 1
            continue
        p["score"] = score(p)
        p["statut"] = "qualifie" if p["score"] >= ICP["seuil_qualifie"] else "nouveau"
        p["ajoute_le"] = now()
        p["historique"] = [f"{now()} ajoute (score {p['score']})"]
        index[p["cle"]] = p
        rows.append(p)
        added += 1
    save(rows)
    print(json.dumps({"ajoutes": added, "doublons": dup, "refuses": refused, "total": len(rows)}, ensure_ascii=False))


def cmd_stats(a):
    rows = load()
    par_statut, par_zone = {}, {}
    for r in rows:
        par_statut[r.get("statut")] = par_statut.get(r.get("statut"), 0) + 1
        par_zone[r.get("dept")] = par_zone.get(r.get("dept"), 0) + 1
    print(json.dumps({"total": len(rows), "statuts": par_statut, "depts": par_zone,
                      "prioritaires": sum(1 for r in rows if r.get("score", 0) >= ICP["seuil_prioritaire"])},
                     ensure_ascii=False, indent=2))


def cmd_next(a):
    rows = [r for r in load() if r.get("statut") in ("nouveau", "qualifie")]
    if a.zone:
        rows = [r for r in rows if r.get("dept") == a.zone]
    for r in rows[: a.n]:
        print(json.dumps({k: r.get(k) for k in
                          ("cle", "nom", "ville", "dept", "secteur", "score", "email", "site", "signaux", "offre_cible")},
                         ensure_ascii=False))


def cmd_set(a):
    rows, hit = load(), False
    for r in rows:
        if a.ident in (r.get("cle"), r.get("siren"), r.get("nom")):
            r["statut"] = a.statut
            r.setdefault("historique", []).append(f"{now()} {a.statut}" + (f" : {a.note}" if a.note else ""))
            hit = True
    save(rows)
    print("ok" if hit else "introuvable")
    sys.exit(0 if hit else 1)


def cmd_check(a):
    rows, err, warn, seen = load(), [], [], {}
    for i, r in enumerate(rows, 1):
        tag = r.get("nom") or f"ligne {i}"
        for champ in ("nom", "ville", "dept", "secteur", "source"):
            if not r.get(champ):
                err.append(f"{tag}: champ '{champ}' manquant")
        if (r.get("dept") or "") in DEPT_INTERDITS:
            err.append(f"{tag}: departement interdit {r['dept']}")
        if r.get("statut") not in STATUTS:
            err.append(f"{tag}: statut inconnu '{r.get('statut')}'")
        k = r.get("cle") or key(r)
        if k in seen:
            err.append(f"{tag}: doublon de {seen[k]}")
        seen[k] = tag
        if r.get("email") and not EMAIL_RE.match(r["email"]):
            err.append(f"{tag}: email invalide '{r['email']}'")
        if r.get("score") != score(r):
            warn.append(f"{tag}: score desynchronise ({r.get('score')} != {score(r)})")
        if r.get("statut") == "contacte" and not r.get("email"):
            warn.append(f"{tag}: marque contacte sans email")
    for w in warn:
        print("WARN " + w)
    for e in err:
        print("ERR  " + e)
    print(f"-- {len(rows)} prospects, {len(err)} erreur(s), {len(warn)} avertissement(s)")
    sys.exit(1 if err else 0)


def cmd_export(a):
    rows = load()
    cols = ["cle", "nom", "ville", "dept", "secteur", "score", "statut", "email", "telephone", "site", "offre_cible", "source", "ajoute_le"]
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"{len(rows)} lignes -> {a.out}")


p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
sub = p.add_subparsers(dest="cmd", required=True)
s = sub.add_parser("add"); s.add_argument("fichier"); s.set_defaults(f=cmd_add)
s = sub.add_parser("stats"); s.set_defaults(f=cmd_stats)
s = sub.add_parser("next"); s.add_argument("--n", type=int, default=10); s.add_argument("--zone"); s.set_defaults(f=cmd_next)
s = sub.add_parser("set"); s.add_argument("ident"); s.add_argument("--statut", required=True, choices=STATUTS); s.add_argument("--note"); s.set_defaults(f=cmd_set)
s = sub.add_parser("check"); s.set_defaults(f=cmd_check)
s = sub.add_parser("export"); s.add_argument("--out", default="prospects.csv"); s.set_defaults(f=cmd_export)
a = p.parse_args(); a.f(a)
