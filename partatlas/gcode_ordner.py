"""G-Code aus den Wurzelordnern als regulärer Weg neben dem Hochladen (Anwender 30.10.2026).

Der Tester exportiert G-Code aus dem Slicer in den Ordner seiner Modelle. Das Einlesen liest ihn mit: das Quellmodell steht im Inhalt
(slicer.quellen_aus_gcode), der Slicer schreibt Sonderzeichen um („Testscheibe_45mm“ im Dateinamen, „Testscheibe_4_5mm“ im Inhalt) — verglichen
wird darum ohne Gross-/Kleinschreibung, Endung und alles ausser Buchstaben und Ziffern. Zugeordnet wird nur, was eindeutig ist; sonst bleibt die
Datei unberührt im Ordner und wird gezählt (`gcode_unklar`, `gcode_ohne_modell`). Der G-Code kommt über denselben Weg in den Bestand wie beim
Hochladen (Drucke.datei_anhaengen), an einen neuen Druck mit Ergebnis „offen“. Die Datei im Ordner bleibt liegen."""
import hashlib
import logging
import os
import re
import threading
import time
import unicodedata

from . import slicer
from .bestand import MODELL, GCODE
from .katalog import KatalogFehler

log = logging.getLogger("partatlas")

NAME_MIN = 5            # kürzere Modellnamen (Clip, Arm) kämen als Teil eines Dateinamens zu oft zufällig vor
GESEHEN = "gcode_gesehen"       # {"<Wurzel>/<rel>": [Grösse, mtime, Ausgang, [genannte Namen], Ausgang vor „ignoriert“]}
OFFEN = ("unklar", "ohne")
# Einlesen und Bereinigen schreiben denselben Schlüssel der Einstellungen: lesen-ändern-schreiben nur unter dieser Sperre, sonst überschriebe
# das Ende eines Einlesens eine Zuordnung, die der Anwender währenddessen gemacht hat.
_SPERRE = threading.Lock()


def vergleichsname(name):
    """Der Name, mit dem Modell und G-Code verglichen werden: ohne Endung, Gross-/Kleinschreibung, Umlaute und Satzzeichen."""
    name = re.sub(r"\.(stl|3mf|obj|step|stp|fcstd|gcode)$", "", (name or "").strip(), flags=re.I)
    name = unicodedata.normalize("NFKD", name)
    return re.sub(r"[\W_]+", "", "".join(c for c in name if not unicodedata.combining(c))).lower()


class GcodeOrdner:
    def __init__(self, katalog, bestand):
        self.k, self.b, self.db = katalog, bestand, katalog.db

    def _modelle_nach_name(self):
        je_name = {}
        for mid, m in self.db.list_nodes(MODELL, readonly=True).items():
            n = vergleichsname(m.get("name"))
            if n:
                je_name.setdefault(n, []).append(mid)
        return je_name

    def zuordnen(self, pfad, je_name):
        """('ok', [Modell …], Namen) | ('unklar', Namen, Namen) | ('ohne', Namen, Namen): die Modelle, aus denen dieser G-Code gesliced wurde;
        zuletzt immer die Namen, die der G-Code nennt (oder die aus dem Dateinamen)."""
        namen = slicer.quellen_aus_gcode(pfad)
        if not namen:
            # Der Inhalt nennt nichts: der Dateiname, genau ein längster Treffer.
            datei = vergleichsname(os.path.basename(pfad))
            treffer = {n: m for n, m in je_name.items() if len(n) >= NAME_MIN and n in datei}
            if treffer:
                laengster = max(len(n) for n in treffer)
                beste = {n: m for n, m in treffer.items() if len(n) == laengster}
                namen = list(beste)
        gefunden, unklar, ohne = [], [], []
        for n in namen:
            mids = je_name.get(vergleichsname(n), [])
            if len(mids) == 1:
                gefunden.append(mids[0])
            elif mids:
                unklar.append(n)
            else:
                ohne.append(n)
        gefunden = list(dict.fromkeys(gefunden))
        if gefunden and not unklar:
            return "ok", gefunden, namen
        if unklar or gefunden:
            return "unklar", unklar or namen, namen   # ein Teil eindeutig, ein Teil nicht: lieber nichts als halb
        return "ohne", ohne, namen

    def einlesen(self, wurzeln, neue_modelle, stopp=None):
        """Alle `.gcode` unter den Wurzelordnern. `neue_modelle`: in diesem Lauf kamen Modelle dazu — dann werden auch die früher unklaren und
        unbekannten noch einmal angesehen. Zugeordnete und ausgeblendete bleiben, wie sie sind. Gibt die Zahlen zurück."""
        z = {"gcode_neu": 0, "gcode_unklar": 0, "gcode_ohne_modell": 0, "gcode_fehler": 0}
        gesehen = dict(self.b.einstellungen().get(GESEHEN) or {})
        neu_gesehen, je_name = {}, None
        for wid, w in wurzeln.items():
            for ordner, unter, dateien in os.walk(w["pfad"], followlinks=False):
                unter[:] = sorted(u for u in unter if not u.startswith(".") and os.path.abspath(os.path.join(ordner, u)) != os.path.abspath(self.b.wurzel))
                for n in dateien:
                    if n.startswith(".") or not n.lower().endswith(".gcode"):
                        continue
                    if stopp is not None and stopp.is_set():
                        self._merken(gesehen, neu_gesehen, vollstaendig=False)
                        return z
                    pfad = os.path.join(ordner, n)
                    try:
                        st = os.stat(pfad)
                    except OSError:
                        continue
                    schluessel = f"{wid}/{os.path.relpath(pfad, w['pfad']).replace(os.sep, '/')}"
                    alt = gesehen.get(schluessel)
                    if alt and alt[0] == st.st_size and alt[1] == st.st_mtime and (alt[2] in ("ok", "ignoriert") or not neue_modelle):
                        neu_gesehen[schluessel] = alt
                        if alt[2] in OFFEN:
                            z["gcode_unklar" if alt[2] == "unklar" else "gcode_ohne_modell"] += 1
                        continue
                    if je_name is None:
                        je_name = self._modelle_nach_name()
                    try:
                        art, was, namen = self.zuordnen(pfad, je_name)
                        if art == "ok":
                            with open(pfad, "rb") as f:
                                daten = f.read()
                            self._anhaengen(was, n, daten, st.st_mtime)
                            z["gcode_neu"] += 1
                        else:
                            z["gcode_unklar" if art == "unklar" else "gcode_ohne_modell"] += 1
                            log.info("G-Code nicht zugeordnet (%s): %s — %s", art, pfad, ", ".join(was) or "der Inhalt nennt kein Modell")
                    except Exception:
                        log.exception("G-Code aus dem Ordner nicht gelesen: %s", pfad)
                        z["gcode_fehler"] += 1
                        continue            # nicht merken: beim nächsten Einlesen noch einmal versuchen
                    neu_gesehen[schluessel] = [st.st_size, st.st_mtime, art, namen]
        self._merken(gesehen, neu_gesehen, vollstaendig=True)
        return z

    def _merken(self, vorher, neu, vollstaendig):
        """Das Ergebnis des Laufs festhalten, ohne zu überschreiben, was der Anwender während des Laufs entschieden hat (zuordnen, ausblenden).
        `vollstaendig`: alle Ordner gesehen — dann fallen verschwundene Dateien weg; nach einem Abbruch bleiben sie."""
        with _SPERRE:
            jetzt = dict(self.b.einstellungen().get(GESEHEN) or {})
            erg = {} if vollstaendig else dict(jetzt)
            for k, v in neu.items():
                erg[k] = jetzt[k] if k in jetzt and jetzt[k] != vorher.get(k) else v
            if erg != jetzt:
                self.b.einstellungen_setzen(**{GESEHEN: erg})

    # ------------------------------------------------------------ Bereinigen: G-Code ohne Modell

    def _pfad(self, schluessel):
        wid, _, rel = schluessel.partition("/")
        w = self.k.wurzeln().get(wid)
        return (os.path.join(w["pfad"], *rel.split("/")), w) if w else (None, None)

    def offene(self):
        """{eintraege: [{id, name, ordner, pfad, art, namen, kandidaten: [{id, name, ordner}]}], ausgeblendet: n} — G-Codes, die das Einlesen nicht
        zuordnen konnte und deren Datei noch da ist. Kandidaten: die Modelle, deren Name zu einem genannten passt (bei „unklar“ mehrere)."""
        gesehen = self.b.einstellungen().get(GESEHEN) or {}
        je_name, modelle, aus = None, None, []
        ausgeblendet = 0
        for k, v in sorted(gesehen.items()):
            if v[2] == "ignoriert":
                ausgeblendet += 1
                continue
            if v[2] not in OFFEN:
                continue
            pfad, w = self._pfad(k)
            if not pfad or not os.path.isfile(pfad):
                continue
            if je_name is None:
                je_name = self._modelle_nach_name()
                modelle = {m["id"]: m for m in self.k.modelle()}
                wnamen = {wid: x["name"] for wid, x in self.k.wurzeln().items()}
            kand = []
            for n in (v[3] if len(v) > 3 else []):
                for mid in je_name.get(vergleichsname(n), []):
                    m = modelle.get(mid)
                    if m and mid not in [x["id"] for x in kand]:
                        o = (m.get("ordner") or [""])[0]
                        owid, _, orel = o.partition("/")
                        kand.append({"id": mid, "name": m["name"], "format": m.get("format"), "ordner": "/".join(x for x in (wnamen.get(owid, owid), orel) if x)})
            rel = k.partition("/")[2]
            aus.append({"id": k, "name": rel.rsplit("/", 1)[-1], "ordner": "/".join(x for x in (w["name"], rel.rpartition("/")[0]) if x), "pfad": pfad,
                        "art": v[2], "namen": v[3] if len(v) > 3 else [], "kandidaten": kand})
        return {"eintraege": aus, "ausgeblendet": ausgeblendet}

    def anzahl_offen(self):
        """Für die Zahl in der Seitenleiste: ohne die Platte anzusehen (eine verschwundene Datei zählt bis zum nächsten Einlesen mit)."""
        return sum(1 for v in (self.b.einstellungen().get(GESEHEN) or {}).values() if v[2] in OFFEN)

    def von_hand(self, schluessel, mids):
        """Einen offenen G-Code den gewählten Modellen zuordnen — derselbe Weg wie beim Einlesen (Druck „offen“ mit dem G-Code)."""
        mids = list(dict.fromkeys(mids or []))
        if not mids:
            raise KatalogFehler("Wähle mindestens ein Modell.")
        for mid in mids:
            if self.db.get_node(f"{MODELL}/{mid}", readonly=True) is None:
                raise KatalogFehler("Dieses Modell gibt es nicht (mehr).")
        with _SPERRE:
            gesehen = dict(self.b.einstellungen().get(GESEHEN) or {})
            v = gesehen.get(schluessel)
            pfad, _ = self._pfad(schluessel)
            if v is None or not pfad or not os.path.isfile(pfad):
                raise KatalogFehler("Diesen G-Code gibt es im Ordner nicht mehr. Lies neu ein.")
            with open(pfad, "rb") as f:
                daten = f.read()
            st = os.stat(pfad)
            self._anhaengen(mids, os.path.basename(pfad), daten, st.st_mtime)
            gesehen[schluessel] = [st.st_size, st.st_mtime, "ok", v[3] if len(v) > 3 else []]
            self.b.einstellungen_setzen(**{GESEHEN: gesehen})

    def ausblenden(self, schluessel, an=True):
        """„Nicht zuordnen“: nicht mehr unter Bereinigen zeigen und beim Einlesen nicht mehr anfassen; `an=False` holt ihn zurück."""
        with _SPERRE:
            gesehen = dict(self.b.einstellungen().get(GESEHEN) or {})
            v = gesehen.get(schluessel)
            if v is None:
                raise KatalogFehler("Diesen G-Code kennt partAtlas nicht.")
            v = list(v) + [None] * (5 - len(v))
            if an and v[2] in OFFEN:
                v[4], v[2] = v[2], "ignoriert"
            elif not an and v[2] == "ignoriert":
                v[2] = v[4] or "ohne"
            gesehen[schluessel] = v
            self.b.einstellungen_setzen(**{GESEHEN: gesehen})

    def ausgeblendete(self):
        gesehen = self.b.einstellungen().get(GESEHEN) or {}
        return [{"id": k, "name": k.rpartition("/")[2]} for k, v in sorted(gesehen.items()) if v[2] == "ignoriert"]

    def _anhaengen(self, mids, name, daten, mtime):
        h = hashlib.sha256(daten).hexdigest()
        # Derselbe Inhalt hängt schon an einem Druck (hochgeladen oder früher gelesen): nichts doppelt anlegen.
        if self.db.get_node(f"{GCODE}/{h}", readonly=True) is not None and self.db.get_connected(f"{GCODE}/{h}", direction="in"):
            return
        self.k.drucke.aus_ordner(mids, name, daten, time.strftime("%Y-%m-%d", time.localtime(mtime)))
