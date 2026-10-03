"""
Eigene Komponenten: Teile, die weder gedruckt noch gekauft sind — ein 60 Jahre altes Kugellager ohne Angaben, eine selbst gefräste
Platte, eine Schraube aus dem Fabriklager. Ein eigenes Objekt mit Name, Bild und Notiz, das man in eine Baugruppe stellt wie ein Kaufteil.

Bewusst schlicht (Entscheidung 03.10.2026): keine Bestandsverwaltung, kein Lagerort, keine Einkäufe. Die Menge in der Stückliste ist der
Bedarf, nicht der Bestand. Die freie Angabe `art` (Lagerteil, Eigenbau, Fundstück …) ist nur ein Etikett und füllt sich von selbst.

Zum Entfernen, falls es dem Anwender nichts taugt: diese Datei, `web/eigene.js`, `tests/test_eigene.py` und die mit „EIGENE“
markierten Stellen in baugruppen.py, stueckliste.py, main.py, web/baugruppen.js und index.html.
"""
import os

from .baugruppen import EIGEN
from .katalog import KatalogFehler, jetzt, ref

STANDARD_ARTEN = ["Lagerteil", "Eigenbau", "Fundstück"]
GRENZEN = {"art": 40, "masse": 60, "notiz": 500}


class Eigene:
    def __init__(self, katalog, baugruppen):
        self.k, self.bg, self.db = katalog, baugruppen, katalog.db

    def _knoten(self, eid):
        n = self.db.get_node(ref(EIGEN, eid), readonly=True)
        if n is None:
            raise KatalogFehler("Diese Komponente gibt es nicht.")
        return n

    def _kurz(self, eid, n):
        b = n.get("bild") or {}
        return {"id": eid, "name": n["name"], "art": n.get("art") or "", "masse": n.get("masse") or "", "notiz": n.get("notiz") or "",
                "bild": b.get("k"), "verwendet_in": [v["name"] for v in self.bg.verwendet_in(ref(EIGEN, eid))]}

    def liste(self, suche=None):
        woerter = [w.lower() for w in (suche or "").split() if w]
        aus = []
        for eid, n in self.db.list_nodes(EIGEN, readonly=True).items():
            text = f"{n['name']} {n.get('art') or ''} {n.get('masse') or ''} {n.get('notiz') or ''}".lower()
            if all(w in text for w in woerter):
                aus.append(self._kurz(eid, n))
        return sorted(aus, key=lambda x: x["name"].lower())

    def detail(self, eid):
        return self._kurz(eid, self._knoten(eid))

    def _felder(self, werte):
        neu = {}
        for k, v in werte.items():
            if k == "name":
                neu["name"] = self.k._name_pruefen(v)
            elif k in GRENZEN:
                v = (v or "").strip()
                if len(v) > GRENZEN[k]:
                    raise KatalogFehler(f"{k.capitalize()} ist zu lang (höchstens {GRENZEN[k]} Zeichen).")
                neu[k] = v
            else:
                raise KatalogFehler(f"Feld {k!r} lässt sich so nicht ändern.")
        return neu

    def anlegen(self, name, art="", masse="", notiz=""):
        felder = self._felder({"name": name, "art": art, "masse": masse, "notiz": notiz})
        with self.db.transaction():
            eid = self.db.next_id(EIGEN, "e_", 4)
            self.db.create_node(EIGEN, eid, {**felder, "angelegt": jetzt()})
        return eid

    def aendern(self, eid, werte):
        self._knoten(eid)
        self.db.update_node(EIGEN, eid, self._felder(werte))

    def bild_setzen(self, eid, daten):
        """Das Bild kommt wie die eigenen Bilder der Modelle in den Vault; ein ersetztes bleibt dort liegen (partAtlas löscht nichts)."""
        n = self._knoten(eid)
        k, rel = self.k.bild_ablegen(self.k.png_aus(daten), n["name"])
        self.db.update_node(EIGEN, eid, {"bild": {"k": k, "datei": rel}})
        return k

    def bild_pfad(self, eid):
        b = (self.db.get_node(ref(EIGEN, eid), readonly=True) or {}).get("bild")
        pfad = self.k.b.pfad(*b["datei"].split("/")) if b else None
        return pfad if pfad and os.path.exists(pfad) else None

    def loeschen(self, eid):
        """Nur, was in keiner Baugruppe steckt: sonst fehlte dort still eine Zeile."""
        self._knoten(eid)
        wo = self.bg.verwendet_in(ref(EIGEN, eid))
        if wo:
            raise KatalogFehler("Steckt noch in: " + ", ".join(v["name"] for v in wo) + ". Erst dort herausnehmen.")
        self.db.soft_delete(EIGEN, eid)

    def arten(self):
        """Die Angaben, die es schon gibt, vor den Vorschlägen — zum Vervollständigen."""
        vorhanden = sorted({n.get("art") for n in self.db.list_nodes(EIGEN, readonly=True).values() if n.get("art")})
        return vorhanden + [a for a in STANDARD_ARTEN if a not in vorhanden]
