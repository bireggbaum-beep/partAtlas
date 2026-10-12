"""Der Papierkorb für alles ausser Modellen: Sammlungen, Baugruppen, Drucke, Tags, eigene Kaufteile.

Gelöscht wurden sie schon immer nur weich (`soft_delete`, KONZEPT §3.3) — im Graph und in den Sicherungen also noch da, aber die
Oberfläche bot keinen Weg zurück. Das holt dieses Modul nach: zeigen, was dort liegt, und einzeln zurückholen.

Nicht gezeigt wird, was zurückgeholt nichts brächte: Tags ohne Zuordnung (aufgegangen in einem anderen oder nach „Alle automatischen
entfernen“) und leere Drucke, die der Haken „gedruckt“ angelegt und wieder entfernt hat.
"""
import os

from . import dateien
from .baugruppen import BAUGRUPPE, EIGEN, ENTHAELT
from .bestand import DRUCK, GEDRUCKT_IN, HAT_TAG, IN_SAMMLUNG, MODELL, SAMMLUNG, TAG
from .drucke import ist_leer
from .katalog import KatalogFehler, ref

ARTEN = {"sammlung": SAMMLUNG, "baugruppe": BAUGRUPPE, "druck": DRUCK, "tag": TAG, "kaufteil": EIGEN}


def _geloeschte(db, sammlung):
    """{kennung: roher Knoten} für alles im Papierkorb."""
    return {k: v for k, v in db.list_nodes(sammlung, include_deleted=True, readonly=True).items() if v.get("_deletion_flag")}


def _lebende_quellen(db, r, kantenart):
    """Wie viele lebende Knoten zeigen über `kantenart` hierher — `get_connected` sähe vom gelöschten Ziel aus nichts."""
    return sum(1 for _, k in db.get_connected_edges(r, direction="in", rel_type=kantenart)
               if db.get_node(k["source"], readonly=True) is not None)


def weitere(k):
    """Was ausser Modellen im Papierkorb liegt, je Art neueste zuerst: {art: [{id, name, geloescht, info}]}."""
    db = k.db
    erg = {a: [] for a in ARTEN}
    for sid, v in _geloeschte(db, SAMMLUNG).items():
        n = _lebende_quellen(db, ref(SAMMLUNG, sid), IN_SAMMLUNG)
        erg["sammlung"].append({"id": sid, "name": v.get("name"), "geloescht": v["_deletion_flag"],
                                "info": f"{n} Modell{'' if n == 1 else 'e'}"})
    for bid, v in _geloeschte(db, BAUGRUPPE).items():
        n = len(db.get_connected_edges(ref(BAUGRUPPE, bid), rel_type=ENTHAELT))
        erg["baugruppe"].append({"id": bid, "name": v.get("name"), "geloescht": v["_deletion_flag"],
                                 "info": f"{n} Position{'' if n == 1 else 'en'}"})
    for did, v in _geloeschte(db, DRUCK).items():
        if ist_leer(v):
            continue
        namen = [(db.get_node_raw(r) or {}).get("name") or r for r in
                 db.get_connected(ref(DRUCK, did), direction="in", rel_type=GEDRUCKT_IN, include_deleted=True)]
        erg["druck"].append({"id": did, "name": ", ".join(namen) or "ohne Modell", "geloescht": v["_deletion_flag"],
                             "info": " · ".join(x for x in (v.get("datum"), v.get("ergebnis")) if x)})
    for name, v in _geloeschte(db, TAG).items():
        n = _lebende_quellen(db, ref(TAG, name), HAT_TAG)
        if n:
            erg["tag"].append({"id": name, "name": "#" + name, "geloescht": v["_deletion_flag"],
                               "info": f"an {n} Modell{'' if n == 1 else 'en'}"})
    for eid, v in _geloeschte(db, EIGEN).items():
        erg["kaufteil"].append({"id": eid, "name": v.get("name"), "geloescht": v["_deletion_flag"], "info": v.get("art") or ""})
    for liste in erg.values():
        liste.sort(key=lambda x: x["geloescht"] or "", reverse=True)
    return erg


def zurueckholen(k, art, kennung):
    sammlung = ARTEN.get(art)
    if sammlung is None:
        raise KatalogFehler(f"Unbekannte Art: {art}")
    db = k.db
    roh = db.get_node_raw(ref(sammlung, kennung))
    if roh is None or db.get_node(ref(sammlung, kennung), readonly=True) is not None:
        raise KatalogFehler("Das liegt nicht im Papierkorb.")
    with db.transaction():
        db.restore_node(sammlung, kennung)
        if art == "druck":
            _fotos_zurueck(k, roh)
            k.drucke.nachziehen([r.split("/", 1)[1] for r in
                                 db.get_connected(ref(DRUCK, kennung), direction="in", rel_type=GEDRUCKT_IN)])
    if art == "tag":
        # Wer einen Tag zurückholt, will ihn wieder — auch als Vorschlag beim Einlesen.
        k.auto_sperre_aufheben([kennung])
    return {"art": art, "id": kennung}


def _fotos_zurueck(k, druck):
    """Bis 0.55 gingen die Fotos eines gelöschten Drucks gleich nach vault_archive/. Liegt eines dort unter seinem Namen, kommt es an
    seinen Platz zurück — nie überschreibend; sonst bleibt der Verweis, und die Oberfläche zeigt das Foto als fehlend."""
    for b in druck.get("bilder") or []:
        ziel = k.b.pfad(*b["datei"].split("/"))
        quelle = k.b.pfad("vault_archive", os.path.basename(b["datei"]))
        if not os.path.exists(ziel) and os.path.exists(quelle):
            os.makedirs(os.path.dirname(ziel), exist_ok=True)
            dateien.verschiebe(quelle, ziel)
