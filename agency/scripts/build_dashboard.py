#!/usr/bin/env python3
"""Genere agency/dashboard/index.html depuis agency/data/prospects.ndjson. Stdlib uniquement.

Usage : build_dashboard.py [--db fichier.ndjson] [--out index.html]
Idempotent : reecrit la page entiere a chaque appel. Lecture seule sur la base.
"""
import argparse, json, os
from collections import Counter
from datetime import datetime
from html import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATUTS = ["nouveau", "qualifie", "contacte", "relance", "repondu", "rdv", "gagne", "perdu", "exclu"]
ICP = json.load(open(os.path.join(ROOT, "config", "icp.json"), encoding="utf-8"))
SEUIL_Q, SEUIL_P = ICP["seuil_qualifie"], ICP["seuil_prioritaire"]

CSS = """
:root{--bg:#f6f7f9;--card:#fff;--fg:#1c2330;--mut:#667085;--line:#e3e6ec;--acc:#2b5fd9;--bar:#2b5fd9}
@media(prefers-color-scheme:dark){:root{--bg:#12151b;--card:#1b2029;--fg:#e8ebf1;--mut:#9aa3b2;--line:#2a313d;--acc:#7da2ff;--bar:#7da2ff}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:960px;margin:0 auto;padding:16px}
h1{font-size:1.4rem;margin:0 0 4px}h2{font-size:1.05rem;margin:0 0 10px}
.sub{color:var(--mut);font-size:.85rem;margin-bottom:16px}
.grid{display:grid;grid-template-columns:1fr;gap:12px}
@media(min-width:700px){.grid{grid-template-columns:1fr 1fr}.wide{grid-column:1/-1}}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
.kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.kpi{text-align:center}.kpi b{display:block;font-size:1.6rem;font-variant-numeric:tabular-nums}.kpi span{color:var(--mut);font-size:.8rem}
.row{display:grid;grid-template-columns:7rem 1fr 2.5rem;gap:8px;align-items:center;font-size:.9rem;margin:5px 0}
.row i{display:block;height:10px;border-radius:5px;background:var(--bar);min-width:2px}
.row em{font-style:normal;text-align:right;font-variant-numeric:tabular-nums}
.lbl{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
ol{margin:0;padding:0;list-style:none}
li{display:flex;gap:10px;align-items:baseline;padding:8px 0;border-top:1px solid var(--line)}
li:first-child{border-top:0}
.sc{font-weight:700;color:var(--acc);min-width:2.2rem;font-variant-numeric:tabular-nums}
.meta{color:var(--mut);font-size:.82rem}
.tag{font-size:.75rem;border:1px solid var(--line);border-radius:999px;padding:1px 8px;color:var(--mut);white-space:nowrap}
.empty{color:var(--mut)}
"""


def bars(counter, order=None):
    if not counter:
        return '<p class="empty">Aucune donnee.</p>'
    keys = order if order else [k for k, _ in counter.most_common()]
    top = max(counter.values())
    out = []
    for k in keys:
        n = counter.get(k, 0)
        w = round(100 * n / top) if top else 0
        out.append(f'<div class="row"><span class="lbl">{escape(str(k))}</span>'
                   f'<span><i style="width:{w}%"></i></span><em>{n}</em></div>')
    return "".join(out)


def load(path):
    rows = []
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build(rows):
    statuts = Counter(r.get("statut") or "?" for r in rows)
    depts = Counter(r.get("dept") or "?" for r in rows)
    scores = Counter()
    for r in rows:
        s = r.get("score", 0)
        scores[f"Prioritaire (>= {SEUIL_P})" if s >= SEUIL_P else f"Qualifie ({SEUIL_Q}-{SEUIL_P - 1})" if s >= SEUIL_Q else f"Faible (< {SEUIL_Q})"] += 1
    order_sc = [f"Prioritaire (>= {SEUIL_P})", f"Qualifie ({SEUIL_Q}-{SEUIL_P - 1})", f"Faible (< {SEUIL_Q})"]
    actifs = [r for r in rows if r.get("statut") not in ("gagne", "perdu", "exclu")]
    top = sorted(actifs, key=lambda r: (-r.get("score", 0), r.get("nom", "")))[:20]
    if top:
        items = "".join(
            f'<li><span class="sc">{int(r.get("score", 0))}</span><div style="flex:1;min-width:0">'
            f'<strong>{escape(r.get("nom") or "?")}</strong>'
            f'<div class="meta">{escape(r.get("ville") or "")} ({escape(r.get("dept") or "")}) &middot; {escape(r.get("secteur") or "")}</div></div>'
            f'<span class="tag">{escape(r.get("statut") or "?")}</span></li>' for r in top)
        liste = f"<ol>{items}</ol>"
    else:
        liste = '<p class="empty">Aucun prospect actif.</p>'
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    prio = sum(1 for r in rows if r.get("score", 0) >= SEUIL_P)
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>Pipeline agence</title><style>{CSS}</style></head>
<body><main>
<h1>Pipeline agence</h1>
<div class="sub">Genere le {now} &middot; source : data/prospects.ndjson</div>
<div class="card" style="margin-bottom:12px"><div class="kpis">
<div class="kpi"><b>{len(rows)}</b><span>prospects</span></div>
<div class="kpi"><b>{prio}</b><span>prioritaires</span></div>
<div class="kpi"><b>{statuts.get("gagne", 0)}</b><span>gagnes</span></div></div></div>
<div class="grid">
<section class="card"><h2>Par statut</h2>{bars(statuts, [s for s in STATUTS if s in statuts] + [s for s in statuts if s not in STATUTS])}</section>
<section class="card"><h2>Par score</h2>{bars(scores, order_sc)}</section>
<section class="card wide"><h2>Par departement</h2>{bars(depts)}</section>
<section class="card wide"><h2>20 prioritaires</h2>{liste}</section>
</div></main></body></html>
"""


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=os.path.join(ROOT, "data", "prospects.ndjson"))
    ap.add_argument("--out", default=os.path.join(ROOT, "dashboard", "index.html"))
    a = ap.parse_args()
    rows = load(a.db)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(build(rows))
    print(f"{len(rows)} prospects -> {a.out}")
