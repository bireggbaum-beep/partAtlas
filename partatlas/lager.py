"""
Filamentlager: die Spulen, die der Anwender hat (nach dem 3MF Katalog Manager, dort „Material Manager“).

Eine Spule (`MATERIAL_SPOOL`) trägt Material, Hersteller, Farbe, Durchmesser, Start- und Restgewicht, Preis, Lagerort und Notiz.
Das Restgewicht stimmt, soweit der Anwender es pflegt; abgezogen wird erst, wenn ein Druck die Spule nennt (drucke.py).
Eine leere Spule wird archiviert, nicht gelöscht: partAtlas löscht hier nichts, und der Verbrauch alter Drucke bleibt nachvollziehbar.
"""
import re

from .bestand import SPULE
from .katalog import KatalogFehler, jetzt, ref

FELDER = ("material", "hersteller", "farbname", "farbe", "ort", "durchmesser", "start_g", "rest_g", "preis", "notiz", "archiviert")
MAX_ANZAHL = 20
VORGABE_START_G = 1000.0


def _text(wert, name, laenge, pflicht=False):
    t = (wert or "").strip() if isinstance(wert, str) or wert is None else str(wert).strip()
    if pflicht and not t:
        raise KatalogFehler(f"{name}: bitte ausfüllen.")
    if len(t) > laenge:
        raise KatalogFehler(f"{name}: höchstens {laenge} Zeichen.")
    return t


def _zahl(wert, name, klein, gross, einheit=""):
    try:
        z = float(str(wert).replace(",", "."))
    except (TypeError, ValueError):
        raise KatalogFehler(f"{name}: keine Zahl.")
    if not klein <= z <= gross:
        raise KatalogFehler(f"{name}: zwischen {klein:g} und {gross:g}{einheit}.")
    return z


def pruefen(felder):
    """Eingaben prüfen und bereinigen; nur die genannten Felder, ohne Vorgaben (die setzt `anlegen`)."""
    neu = {}
    for k in felder:
        if k not in FELDER:
            raise KatalogFehler(f"Feld {k!r} gibt es an der Spule nicht.")
    if "material" in felder:
        neu["material"] = _text(felder["material"], "Material", 30, pflicht=True)
    for k, name, n in (("hersteller", "Hersteller", 60), ("farbname", "Farbname", 40), ("ort", "Lagerort", 60), ("notiz", "Notiz", 500)):
        if k in felder:
            neu[k] = _text(felder[k], name, n)
    if "farbe" in felder:
        f = _text(felder["farbe"], "Farbe", 7)
        if f and not re.fullmatch(r"#[0-9a-fA-F]{6}", f):
            raise KatalogFehler("Farbe: ein Farbwert wie #1a1a1a.")
        neu["farbe"] = f.lower()
    if "durchmesser" in felder:
        neu["durchmesser"] = _zahl(felder["durchmesser"], "Durchmesser", 1.0, 3.5, " mm")
    if "start_g" in felder:
        neu["start_g"] = _zahl(felder["start_g"], "Gewicht der vollen Spule", 1, 20000, " g")
    if "rest_g" in felder:
        neu["rest_g"] = round(_zahl(felder["rest_g"], "Rest", 0, 20000, " g"), 1)
    if "preis" in felder:
        neu["preis"] = None if felder["preis"] in (None, "") else round(_zahl(felder["preis"], "Preis", 0, 10000), 2)
    if "archiviert" in felder:
        neu["archiviert"] = bool(felder["archiviert"])
    return neu


class Lager:
    def __init__(self, katalog):
        self.k = katalog
        self.db = katalog.db

    def liste(self):
        """Alle Spulen, nach Material und Farbe sortiert; die archivierten stehen mit `archiviert` dabei."""
        aus = [{"id": sid, **d} for sid, d in self.db.list_nodes(SPULE, readonly=True).items()]
        aus.sort(key=lambda s: (bool(s.get("archiviert")), s.get("material", ""), s.get("farbname", ""), s["id"]))
        return aus

    def _spule(self, sid):
        d = self.db.get_node(ref(SPULE, sid), readonly=True)
        if d is None:
            raise KatalogFehler("Diese Spule gibt es nicht.")
        return d

    def anlegen(self, felder, anzahl=1):
        """Legt `anzahl` gleiche Spulen an (jede mit eigenem Rest). Ohne Restgewicht ist die Spule voll."""
        try:
            anzahl = int(anzahl)
        except (TypeError, ValueError):
            raise KatalogFehler("Anzahl: keine Zahl.")
        if not 1 <= anzahl <= MAX_ANZAHL:
            raise KatalogFehler(f"Anzahl: zwischen 1 und {MAX_ANZAHL}.")
        felder = felder or {}
        if "material" not in felder:
            raise KatalogFehler("Material: bitte ausfüllen.")
        daten = pruefen(felder)
        daten.setdefault("durchmesser", 1.75)
        daten.setdefault("start_g", VORGABE_START_G)
        daten.setdefault("rest_g", daten["start_g"])
        for k in ("hersteller", "farbname", "farbe", "ort", "notiz"):
            daten.setdefault(k, "")
        daten.setdefault("preis", None)
        daten.setdefault("archiviert", False)
        if daten["rest_g"] > daten["start_g"]:
            raise KatalogFehler("Der Rest kann nicht grösser sein als die volle Spule.")
        ids = []
        with self.db.transaction():
            for _ in range(anzahl):
                sid = self.db.next_id(SPULE, "sp_", 5)
                self.db.create_node(SPULE, sid, {**daten, "angelegt": jetzt()})
                ids.append(sid)
        return ids

    def aendern(self, sid, felder):
        alt = self._spule(sid)
        neu = pruefen(felder)
        start, rest = neu.get("start_g", alt.get("start_g")), neu.get("rest_g", alt.get("rest_g"))
        if rest is not None and start is not None and rest > start:
            raise KatalogFehler("Der Rest kann nicht grösser sein als die volle Spule.")
        if neu:
            with self.db.transaction():
                self.db.update_node(SPULE, sid, neu)
