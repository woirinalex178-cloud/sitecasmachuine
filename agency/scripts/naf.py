"""Classement sectoriel par code NAF, partage par sonde_api.py et prospects.py."""
import json, os

_C = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "config", "naf.json"), encoding="utf-8"))
SECTEURS = sorted(_C["secteurs"].items(), key=lambda kv: -len(kv[0]))
EXCLUS = sorted(_C["exclus"], key=len, reverse=True)
DEFAUT = _C.get("defaut", "services aux particuliers")


def secteur_de(naf):
    """Secteur de l'agence pour ce code NAF, ou None si le code est exclu de la cible."""
    naf = (naf or "").strip()
    if not naf:
        return DEFAUT
    for pref in EXCLUS:
        if naf.startswith(pref):
            return None
    for pref, sect in SECTEURS:
        if naf.startswith(pref):
            return sect
    return DEFAUT


def motif_exclusion(naf):
    naf = (naf or "").strip()
    for pref in EXCLUS:
        if naf.startswith(pref):
            return _C["exclus"][pref]
    return None
