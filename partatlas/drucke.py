"""
Drucke: ein einzelnes Mal, dass ein Modell auf dem Drucker lag (KONZEPT §4.6).

Ein Druck (`PRINT_JOB`) hängt an einem oder mehreren Modellen (Kante
`PRINTED_IN`) — mehrere, wenn eine Platte mehrere Bibliotheksmodelle trug.
Er trägt Datum, Dauer, Gewicht, Filament, Ergebnis, Notiz und Fotos.
„Gedruckt“ und der Zähler sind abgeleitet; damit die Kachelliste nicht bei
jedem Modell die Drucke nachschlagen muss, steht das Abgeleitete am Modell
(`drucke_n`, `gedruckt`, `ref_werte`) und wird bei jeder Änderung eines
Drucks nachgezogen.
"""
import re
import time

from .bestand import DRUCK, GEDRUCKT_IN, MODELL, REFERENZ
from .katalog import KatalogFehler, jetzt, ref

ERGEBNISSE = ("gut", "fehler", "abgebrochen")
ZAEHLT = ("gut", "fehler")      # ein Druck mit Fehlern hat stattgefunden; abgebrochen nicht
FELDER = ("datum", "dauer_s", "gewicht_g", "filament", "ergebnis", "notiz")


def _zahl(wert, name, hoechst):
    if wert in (None, ""):
        return None
    try:
        z = float(wert)
    except (TypeError, ValueError):
        raise KatalogFehler(f"{name}: keine Zahl.")
    if not 0 <= z <= hoechst:
        raise KatalogFehler(f"{name}: ausserhalb des Möglichen.")
    return z


def pruefen(felder, voll):
    """Eingaben prüfen und bereinigen. `voll`: ein neuer Druck bekommt Vorgaben."""
    neu = {}
    for k in felder:
        if k not in FELDER:
            raise KatalogFehler(f"Feld {k!r} gibt es am Druck nicht.")
    if "datum" in felder or voll:
        d = felder.get("datum") or (time.strftime("%Y-%m-%d") if voll else None)
        if d is not None and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
            raise KatalogFehler("Datum als JJJJ-MM-TT.")
        neu["datum"] = d
    if "dauer_s" in felder or voll:
        z = _zahl(felder.get("dauer_s"), "Dauer", 60 * 60 * 24 * 60)
        neu["dauer_s"] = int(z) if z is not None else None
    if "gewicht_g" in felder or voll:
        z = _zahl(felder.get("gewicht_g"), "Gewicht", 100000)
        neu["gewicht_g"] = round(z, 2) if z is not None else None
    if "filament" in felder or voll:
        f = felder.get("filament") or []
        if not isinstance(f, list) or len(f) > 8:
            raise KatalogFehler("Filament: höchstens acht Einträge.")
        sauber = []
        for e in f:
            if not isinstance(e, dict):
                raise KatalogFehler("Filament: Eintrag ungültig.")
            farbe = e.get("farbe") or None
            if farbe is not None and not re.fullmatch(r"#[0-9a-fA-F]{6}", farbe):
                raise KatalogFehler("Farbe als #rrggbb.")
            g = _zahl(e.get("g"), "Filament-Gewicht", 100000)
            sauber.append({"typ": str(e.get("typ") or "").strip()[:20] or None, "farbe": farbe,
                           "g": round(g, 2) if g is not None else None})
        neu["filament"] = sauber
    if "ergebnis" in felder or voll:
        e = felder.get("ergebnis") or "gut"
        if e not in ERGEBNISSE:
            raise KatalogFehler("Ergebnis: gut, fehler oder abgebrochen.")
        neu["ergebnis"] = e
    if "notiz" in felder or voll:
        n = (felder.get("notiz") or "").strip()
        if len(n) > 2000:
            raise KatalogFehler("Notiz länger als 2000 Zeichen.")
        neu["notiz"] = n or None
    return neu


def ist_leer(d):
    """Ein Druck ohne jede Angabe — das, was der Haken „gedruckt“ anlegt."""
    return not (d.get("dauer_s") or d.get("gewicht_g") or d.get("filament") or d.get("notiz") or d.get("bilder"))


class Drucke:
    def __init__(self, katalog):
        self.k = katalog
        self.db = katalog.db
        self._alte_haken_umziehen()

    # ------------------------------------------------------------ Lesen

    def _modelle_von(self, did):
        return [r.split("/", 1)[1] for r in self.db.get_connected(ref(DRUCK, did), direction="in", rel_type=GEDRUCKT_IN)]

    def _druck(self, did):
        d = self.db.get_node(ref(DRUCK, did), readonly=True)
        if d is None:
            raise KatalogFehler("Diesen Druck gibt es nicht.")
        return d

    def _ids_von(self, mid):
        return [r.split("/", 1)[1] for r in self.db.get_connected(ref(MODELL, mid), rel_type=GEDRUCKT_IN)]

    def _referenz_von(self, mid):
        r = self.db.get_connected(ref(MODELL, mid), rel_type=REFERENZ)
        return r[0].split("/", 1)[1] if r else None

    def liste(self, mid):
        """Die Drucke eines Modells, neueste zuerst; der Referenzdruck steht vorn."""
        referenz = self._referenz_von(mid)
        aus = []
        for did in self._ids_von(mid):
            d = self.db.get_node(ref(DRUCK, did), readonly=True)
            if d is None:
                continue
            gefaehrten = [x for x in self._modelle_von(did) if x != mid]
            aus.append({
                "id": did, **{f: d.get(f) for f in FELDER}, "filament": d.get("filament") or [],
                "bilder": [{"k": b["k"], "url": f"/api/drucke/{did}/bilder/{b['k']}"} for b in d.get("bilder") or []],
                "zusammen_mit": [{"id": x, "name": (self.db.get_node(ref(MODELL, x), readonly=True) or {}).get("name")}
                                 for x in gefaehrten],
                "referenz": did == referenz, "leer": ist_leer(d), "angelegt": d.get("angelegt"),
            })
        aus.sort(key=lambda x: (x["datum"] or "", x["angelegt"] or ""), reverse=True)
        aus.sort(key=lambda x: not x["referenz"])
        return aus

    # ------------------------------------------------------------ Schreiben

    def nachziehen(self, mids):
        """Zähler, Haken und Referenzwerte am Modell neu aus den Drucken ableiten."""
        for mid in mids:
            m = self.db.get_node(ref(MODELL, mid), readonly=True)
            if m is None:
                continue
            drucke = [self.db.get_node(ref(DRUCK, i), readonly=True) for i in self._ids_von(mid)]
            drucke = [d for d in drucke if d]
            referenz = self._referenz_von(mid)
            rd = self.db.get_node(ref(DRUCK, referenz), readonly=True) if referenz else None
            ref_werte = ({"druck": referenz, "gewicht_g": rd.get("gewicht_g"), "dauer_s": rd.get("dauer_s"),
                          "filament": rd.get("filament") or []} if rd else None)
            neu = {"drucke_n": sum(1 for d in drucke if d.get("ergebnis") in ZAEHLT),
                   "gedruckt": any(d.get("ergebnis") == "gut" for d in drucke), "ref_werte": ref_werte}
            if any(m.get(k) != v for k, v in neu.items()):
                self.db.update_node(MODELL, mid, neu)

    def anlegen(self, modelle, felder=None):
        modelle = list(dict.fromkeys(modelle or []))
        if not modelle:
            raise KatalogFehler("Ein Druck braucht mindestens ein Modell.")
        for mid in modelle:
            if self.db.get_node(ref(MODELL, mid), readonly=True) is None:
                raise KatalogFehler(f"Modell {mid} gibt es nicht.")
        daten = pruefen(felder or {}, voll=True)
        with self.db.transaction():
            did = self.db.next_id(DRUCK, "d_", 6)
            self.db.create_node(DRUCK, did, {**daten, "bilder": [], "herkunft": "hand", "angelegt": jetzt()})
            for mid in modelle:
                self.db.create_edge(ref(MODELL, mid), ref(DRUCK, did), GEDRUCKT_IN)
            self.nachziehen(modelle)
        return did

    def aendern(self, did, felder):
        self._druck(did)
        neu = pruefen(felder, voll=False)
        with self.db.transaction():
            if neu:
                self.db.update_node(DRUCK, did, neu)
            self.nachziehen(self._modelle_von(did))

    def loeschen(self, did):
        d = self._druck(did)
        modelle = self._modelle_von(did)
        with self.db.transaction():
            self.db.soft_delete(DRUCK, did)
            for b in d.get("bilder") or []:
                self.k._archivieren(b["datei"])
            self.nachziehen(modelle)

    def referenz(self, did, mid, an=True):
        self._druck(did)
        if mid not in self._modelle_von(did):
            raise KatalogFehler("Dieser Druck gehört nicht zu diesem Modell.")
        with self.db.transaction():
            for kante, _ in self.db.verwendungen(ref(MODELL, mid), direction="out").get(REFERENZ, []):
                self.db.delete_edge(kante)
            if an:
                self.db.create_edge(ref(MODELL, mid), ref(DRUCK, did), REFERENZ)
            self.nachziehen([mid])

    def markieren(self, mid, gesetzt):
        """Der Haken „gedruckt“: setzen legt einen leeren Druck an, zurücknehmen
        entfernt leere Drucke — und weigert sich, wenn einer Angaben trägt."""
        m = self.db.get_node(ref(MODELL, mid), readonly=True)
        if m is None:
            raise KatalogFehler(f"Modell {mid} gibt es nicht.")
        if gesetzt:
            if not m.get("gedruckt"):
                self.anlegen([mid], {})
            return
        ids = self._ids_von(mid)
        mit = [i for i in ids if not ist_leer(self.db.get_node(ref(DRUCK, i), readonly=True) or {})]
        if mit:
            raise KatalogFehler(f"Dieses Modell hat {len(mit)} Druck{'e' if len(mit) > 1 else ''} mit Angaben — "
                                "entferne sie im Reiter „Drucke“.")
        with self.db.transaction():
            for i in ids:
                self.db.soft_delete(DRUCK, i)
            self.nachziehen([mid])

    # ------------------------------------------------------------ Fotos

    def bild_hinzufuegen(self, did, daten):
        d = self._druck(did)
        k, rel = self.k.bild_ablegen(self.k.png_aus(daten), f"druck_{did}")
        bilder = list(d.get("bilder") or [])
        if not any(b["k"] == k for b in bilder):
            self.db.update_node(DRUCK, did, {"bilder": bilder + [{"k": k, "datei": rel, "angelegt": jetzt()}]})
            self.nachziehen(self._modelle_von(did))
        return k

    def bild_entfernen(self, did, k):
        d = self._druck(did)
        weg = [b for b in d.get("bilder") or [] if b["k"] == k]
        if not weg:
            raise KatalogFehler("Dieses Bild gibt es nicht.")
        self.db.update_node(DRUCK, did, {"bilder": [b for b in d["bilder"] if b["k"] != k]})
        self.k._archivieren(weg[0]["datei"])

    def bild_pfad(self, did, k):
        d = self.db.get_node(ref(DRUCK, did), readonly=True) or self.db.get_node_raw(ref(DRUCK, did)) or {}
        b = next((b for b in d.get("bilder") or [] if b["k"] == k), None)
        return self.k.b.pfad(*b["datei"].split("/")) if b else None

    # ------------------------------------------------------------ Umzug

    def _alte_haken_umziehen(self):
        """Bestände vor 0.19: der Haken „gedruckt“ war ein Feld. Jeder wird zu
        einem leeren Druck ohne Datum; die Modelle bekommen `drucke_n`. Schreibt
        nur, wenn so ein Modell da ist."""
        alt = [mid for mid, m in self.db.list_nodes(MODELL, readonly=True).items()
               if m.get("gedruckt") and m.get("drucke_n") is None]
        if not alt:
            return
        with self.db.transaction():
            for mid in alt:
                did = self.db.next_id(DRUCK, "d_", 6)
                self.db.create_node(DRUCK, did, {"datum": None, "dauer_s": None, "gewicht_g": None, "filament": [],
                                                 "ergebnis": "gut", "notiz": None, "bilder": [],
                                                 "herkunft": "hand", "angelegt": jetzt()})
                self.db.create_edge(ref(MODELL, mid), ref(DRUCK, did), GEDRUCKT_IN)
            self.nachziehen(alt)
