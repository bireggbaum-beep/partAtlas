"""
Eigene Komponenten: Teile, die weder gedruckt noch gekauft sind — ein 60 Jahre altes Kugellager ohne Angaben, eine selbst gefräste
Platte, eine Schraube aus dem Fabriklager. Ein eigenes Objekt mit Name, Bild und Notiz, das man in eine Baugruppe stellt wie ein Kaufteil.

Bewusst schlicht (Entscheidung 03.10.2026): keine Bestandsverwaltung, kein Lagerort, keine Einkäufe. Die Menge in der Stückliste ist der
Bedarf, nicht der Bestand. Die freie Angabe `art` (Lagerteil, Eigenbau, Fundstück …) ist nur ein Etikett und füllt sich von selbst.
"""
import hashlib
import os
import re
import threading

from . import cad, dateien, formate, programme, vorschau
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
        d = n.get("datei") or {}
        return {"id": eid, "name": n["name"], "datei": d.get("name"), "datei_format": d.get("format"), "art": n.get("art") or "", "masse": n.get("masse") or "", "notiz": n.get("notiz") or "",
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
        self.db.update_node(EIGEN, eid, {"bild": {"k": k, "datei": rel}, "bild_aus_datei": False})
        return k

    def datei_setzen(self, eid, name, daten):
        """Eine Konstruktionsdatei (FCStd, STEP, 3MF, STL, OBJ) an die Komponente hängen. Sie läuft durch dieselbe Vorschau wie ein Modell,
        wird aber nie in den Katalog eingelesen: eine Kopie im Vault, kein Wurzelordner, den der Scanner sähe.
        Gibt zurück, ob dabei ein Bild entstand."""
        n = self._knoten(eid)
        name = os.path.basename((name or "").replace("\\", "/"))
        fmt = formate.format_von(name)
        if fmt is None:
            raise KatalogFehler("Hier gehen 3MF, STL, OBJ, STEP und FCStd.")
        h = hashlib.sha256(daten).hexdigest()[:12]
        sicher = re.sub(r"[^\w.-]+", "_", name)[:80]
        rel = f"vault/komponenten/{h}__{sicher}"
        pfad = self.k.b.pfad(*rel.split("/"))
        if not os.path.exists(pfad):
            dateien.schreibe_atomar(pfad, daten)
        png, masse = self._vorschau(pfad, fmt, h)
        neu = {"datei": {"name": name, "datei": rel, "format": fmt}}
        # Ein eigenes Bild des Anwenders bleibt; nur ein Bild aus einer früheren Datei wird ersetzt.
        if png and not (n.get("bild") and not n.get("bild_aus_datei")):
            try:
                k, brel = self.k.bild_ablegen(self.k.png_aus(png), n["name"])
                neu.update(bild={"k": k, "datei": brel}, bild_aus_datei=True)
            except KatalogFehler:
                png = None      # ein unlesbares eingebettetes Bild verdirbt nicht das Speichern der Datei
        if masse and not n.get("masse"):
            neu["masse"] = " × ".join(f"{x:g}" for x in masse) + " mm"
        self.db.update_node(EIGEN, eid, neu)
        return "bild" in neu

    def _vorschau(self, pfad, fmt, h):
        """(PNG | None, Maße | None): eingebettetes Bild, sonst gerendert; STEP/FCStd ohne Bild über FreeCAD, wenn es da ist
        (FCStd nur nach der Zusage des Anwenders, wie beim Einlesen)."""
        try:
            a = formate.analysiere(pfad, mit_netz=fmt not in formate.OHNE_NETZ)
            if a.vorschau_png:
                return a.vorschau_png, a.masse_mm
            if a.netz is not None:
                return vorschau.rendere(a.netz), a.masse_mm
            einst = self.k.b.einstellungen()
            if fmt == "fcstd" and einst.get("fcstd_freecad") != "ja":
                return None, a.masse_mm
            prog = programme.programm_fuer(programme.CAD, einst) or {}
            befehl = cad.konsole_befehl(prog.get("pfad"))
            if not befehl:
                return None, a.masse_mm
            ziel = self.k.b.pfad("arbeit", "cad", f"komp_{h}.stl")
            os.makedirs(os.path.dirname(ziel), exist_ok=True)
            for _, ok, _ in cad.umwandeln(befehl, [(h, pfad, ziel)], threading.Event(), os.path.dirname(ziel)):
                if ok:
                    b = formate.analysiere(ziel, mit_netz=True)
                    self.k.b.entfernen(ziel)
                    return vorschau.rendere(b.netz), b.masse_mm
            return None, a.masse_mm
        except (formate.FormatFehler, MemoryError):
            return None, None

    def datei_pfad(self, eid):
        d = (self.db.get_node(ref(EIGEN, eid), readonly=True) or {}).get("datei")
        pfad = self.k.b.pfad(*d["datei"].split("/")) if d else None
        return (pfad, d["name"]) if pfad and os.path.exists(pfad) else (None, None)

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
