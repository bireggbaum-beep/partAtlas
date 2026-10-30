"""G-Code aus den Wurzelordnern als regulärer Weg neben dem Hochladen (Anwender 30.10.2026).

Der Tester exportiert G-Code aus dem Slicer in den Ordner seiner Modelle. Das Einlesen liest ihn mit: das Quellmodell steht im Inhalt
(slicer.quellen_aus_gcode), der Slicer schreibt Sonderzeichen um („Testscheibe_45mm“ im Dateinamen, „Testscheibe_4_5mm“ im Inhalt) — verglichen
wird darum ohne Gross-/Kleinschreibung, Endung und alles ausser Buchstaben und Ziffern. Zugeordnet wird nur, was eindeutig ist; sonst bleibt die
Datei unberührt im Ordner und wird gezählt (`gcode_unklar`, `gcode_ohne_modell`). Der G-Code kommt über denselben Weg in den Bestand wie beim
Hochladen (Drucke.datei_anhaengen), an einen neuen Druck mit Ergebnis „offen“. Die Datei im Ordner bleibt liegen."""
import logging
import os
import re
import time
import unicodedata

from . import slicer
from .bestand import MODELL, GCODE

log = logging.getLogger("partatlas")

NAME_MIN = 5            # kürzere Modellnamen (Clip, Arm) kämen als Teil eines Dateinamens zu oft zufällig vor
GESEHEN = "gcode_gesehen"


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
        """('ok', [Modell …]) | ('unklar', Namen) | ('ohne', Namen): die Modelle, aus denen dieser G-Code gesliced wurde."""
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
            return "ok", gefunden
        if unklar or gefunden:
            return "unklar", unklar or namen          # ein Teil eindeutig, ein Teil nicht: lieber nichts als halb
        return "ohne", ohne

    def einlesen(self, wurzeln, neue_modelle, stopp=None):
        """Alle `.gcode` unter den Wurzelordnern. `neue_modelle`: in diesem Lauf kamen Modelle dazu — dann werden auch die früher unklaren und
        unbekannten noch einmal angesehen. Gibt die Zahlen zurück."""
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
                        return z
                    pfad = os.path.join(ordner, n)
                    try:
                        st = os.stat(pfad)
                    except OSError:
                        continue
                    schluessel = f"{wid}/{os.path.relpath(pfad, w['pfad']).replace(os.sep, '/')}"
                    alt = gesehen.get(schluessel)
                    if alt and alt[0] == st.st_size and alt[1] == st.st_mtime and (alt[2] == "ok" or not neue_modelle):
                        neu_gesehen[schluessel] = alt
                        if alt[2] != "ok":
                            z["gcode_unklar" if alt[2] == "unklar" else "gcode_ohne_modell"] += 1
                        continue
                    if je_name is None:
                        je_name = self._modelle_nach_name()
                    try:
                        art, was = self.zuordnen(pfad, je_name)
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
                    neu_gesehen[schluessel] = [st.st_size, st.st_mtime, art]
        if neu_gesehen != gesehen:
            self.b.einstellungen_setzen(**{GESEHEN: neu_gesehen})
        return z

    def _anhaengen(self, mids, name, daten, mtime):
        import hashlib
        h = hashlib.sha256(daten).hexdigest()
        # Derselbe Inhalt hängt schon an einem Druck (hochgeladen oder früher gelesen): nichts doppelt anlegen.
        if self.db.get_node(f"{GCODE}/{h}", readonly=True) is not None and self.db.get_connected(f"{GCODE}/{h}", direction="in"):
            return
        self.k.drucke.aus_ordner(mids, name, daten, time.strftime("%Y-%m-%d", time.localtime(mtime)))
