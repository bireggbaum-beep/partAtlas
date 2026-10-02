"""
Wurzelordner einlesen.

Der Scan läuft im Hintergrund und rechnet in Arbeitsprozessen (Hash,
Analyse, Vorschau), geschrieben wird nur hier im Hauptprozess — flatgraph
hat einen Besitzer (KONZEPT §2).

Ablauf:
  1. Ordner ablaufen; eine Datei mit unveränderter Grösse und Zeit am
     bekannten Ort wird nicht neu gelesen. Das macht den zweiten Scan von
     5 700 Dateien billig.
  2. Neue oder geänderte Dateien hashen. Ist der Hash bekannt, bekommt
     die Datei nur einen Ort dazu (verschoben, umbenannt, kopiert).
  3. Unbekannte Hashes analysieren und in Gruppen je eine Transaktion
     anlegen — einzeln kostet jede Änderung ihren fsync (VERTRAG §5).
  4. Orte, die nicht mehr da sind, entfernen. Ein Modell ohne Ort „fehlt“
     und bleibt, mit Tags und Historie.
  5. Fehlende Vorschauen rendern, nach und nach.
"""
import logging
import multiprocessing
import os
import threading
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from concurrent.futures.process import BrokenProcessPool

from . import dateien, formate, vorschau

log = logging.getLogger("partatlas.scan")

GRUPPE = 100


# ---------------------------------------------------------------- Arbeitsprozesse

def _hash(pfad):
    try:
        return pfad, formate.datei_hash(pfad), None
    except OSError as e:
        return pfad, None, str(e)


def _analyse(pfad, vorschau_ziel):
    """Felder für den Graphen und den Vorschau-Status. Schreibt ein
    eingebettetes Bild gleich selbst in den Vault."""
    try:
        a = formate.analysiere(pfad)
    except formate.FormatFehler as e:
        return {"format": formate.format_von(pfad)}, "keine", str(e)
    status = "ausstehend" if a.format != "step" else "keine"
    if a.vorschau_png:
        dateien.schreibe_atomar(vorschau_ziel, a.vorschau_png)
        status = "eingebettet"
    return a.als_felder(), status, None


def _rendern(pfad, vorschau_ziel, farbe=None):
    try:
        a = formate.analysiere(pfad, mit_netz=True)
        png = vorschau.rendere(a.netz, farbe=farbe)
    except (formate.FormatFehler, MemoryError) as e:
        return "fehler", str(e)
    if not png:
        return "keine", None
    dateien.schreibe_atomar(vorschau_ziel, png)
    return "gerendert", None


# ---------------------------------------------------------------- Scanner

class Scanner:
    def __init__(self, bestand, katalog, melden=None, prozesse=None):
        self.b = bestand
        self.k = katalog
        self.melden = melden or (lambda status: None)
        self.prozesse = prozesse or max(1, (os.cpu_count() or 2) - 1)
        self._sperre = threading.Lock()
        self._faden = None
        self._nochmal = False
        self.status = {"laeuft": False}
        self._phasen, self._phase_name, self._phase_t = {}, None, 0.0
        self._pool = None

    def _neuer_pool(self):
        # spawn statt fork: der Server hat Threads und eine offene Datenbank; ein geforkter Kindprozess erbte beides halb.
        # Unter Windows gibt es ohnehin nur spawn.
        return ProcessPoolExecutor(self.prozesse, mp_context=multiprocessing.get_context("spawn"))

    def _pool_neu(self):
        """Nach einem harten Absturz eines Arbeiters (etwa vom Betriebssystem beendet, weil der Speicher ausging) ist der
        ganze Pool unbrauchbar: durch einen frischen ersetzen."""
        alt, self._pool = self._pool, self._neuer_pool()
        alt.shutdown(wait=False, cancel_futures=True)

    def _verteilen(self, aufgaben, arbeit):
        """Verteilt `aufgaben` [(Schlüssel, Argumente)] auf die Arbeiter und liefert (Schlüssel, Ergebnis, Fehler) nach und
        nach. Ein Fehler betrifft nur seine Datei; der Lauf geht weiter.

        Normalfall: alles auf einmal. Stirbt dabei ein Arbeiter, zerbrechen mit ihm alle laufenden Aufträge, und man weiss nicht,
        welche Datei es war. Dann geht es in Wellen von der Grösse der Arbeiterzahl weiter; zerbricht eine Welle, werden ihre
        offenen Aufträge einzeln wiederholt — so steht die Datei fest, die es war, und nur sie wird als Fehler gemeldet."""
        offen = list(aufgaben)
        welle = None
        while offen:
            stueck = offen if welle is None else offen[:welle]
            auftraege = {self._pool.submit(arbeit, *a): k for k, a in stueck}
            erledigt, zerbrochen = set(), False
            for f in as_completed(auftraege):
                k = auftraege[f]
                try:
                    erg = f.result()
                except BrokenProcessPool:
                    zerbrochen = True
                    continue
                except Exception as e:       # Unvorhergesehenes in einer Datei: sie meldet es, der Lauf geht weiter
                    erledigt.add(k)
                    yield k, None, f"{type(e).__name__}: {e}"
                    continue
                erledigt.add(k)
                yield k, erg, None
            if zerbrochen:
                self._pool_neu()
                if welle is None:
                    welle = self.prozesse
                else:
                    for k, a in [(k, a) for k, a in stueck if k not in erledigt]:
                        try:
                            erg, fehler = self._pool.submit(arbeit, *a).result(), None
                        except BrokenProcessPool:
                            self._pool_neu()
                            erg, fehler = None, "Arbeitsprozess beendet (vermutlich zu wenig Speicher für diese Datei)"
                        except Exception as e:
                            erg, fehler = None, f"{type(e).__name__}: {e}"
                        erledigt.add(k)
                        yield k, erg, fehler
            offen = [(k, a) for k, a in offen if k not in erledigt]

    def _setze(self, **werte):
        # Wie lange jede Phase dauerte (Suchen, Hashen, Analysieren, Vorschau): wer einen grossen Bestand einliest,
        # will wissen, wo die Zeit bleibt. Eine neue Phase schliesst die vorige.
        if "phase" in werte:
            jetzt = time.time()
            if werte["phase"] == "suchen":
                self._phasen, self._phase_name = {}, None
            if self._phase_name and self._phase_name != werte["phase"]:
                self._phasen[self._phase_name] = round(self._phasen.get(self._phase_name, 0) + jetzt - self._phase_t, 1)
            if self._phase_name != werte["phase"]:
                self._phase_name, self._phase_t = werte["phase"], jetzt
            werte["phasen"] = dict(self._phasen)
        self.status.update(werte)
        self.melden(dict(self.status))

    def starten(self):
        """Im Hintergrund. Kommt ein Auftrag während eines Laufs (Hochladen,
        Entpacken), läuft danach ein zweiter — der erste hat die neuen
        Dateien womöglich schon hinter sich gelassen."""
        with self._sperre:
            if self._faden and self._faden.is_alive():
                self._nochmal = True
                return False
            self._nochmal = False
            self._faden = threading.Thread(target=self._lauf_sicher, name="scan", daemon=True)
            self._faden.start()
            return True

    def warten(self, zeit=None):
        if self._faden:
            self._faden.join(zeit)

    def _lauf_sicher(self):
        while True:
            try:
                self.lauf()
            except Exception as e:                   # der Server soll weiterlaufen
                log.exception("Scan abgebrochen")
                self._setze(laeuft=False, abbruch=str(e))
            with self._sperre:
                if not self._nochmal:
                    return
                self._nochmal = False

    def lauf(self):
        t0 = time.time()
        self._setze(laeuft=True, phase="suchen", gefunden=0, neu=0, verschoben=0, entfernt=0,
                    unlesbar=0, im_papierkorb=0, vorschauen_offen=0, abbruch=None,
                    beginn=time.strftime("%H:%M:%S"))
        index = self.k.ort_index()
        wurzeln = self.k.wurzeln()
        gesehen, zu_hashen = set(), []
        for wid, w in wurzeln.items():
            for pfad, rel, st in self._ablaufen(w["pfad"]):
                schluessel = (wid, rel)
                gesehen.add(schluessel)
                alt = index.get(schluessel)
                if alt and alt[1] == st.st_size and alt[2] == st.st_mtime:
                    continue
                zu_hashen.append((schluessel, pfad, st))
        self._setze(gefunden=len(gesehen), phase="hashen", zu_pruefen=len(zu_hashen))

        self._pool = self._neuer_pool()
        try:
            pool = self._pool
            nach_pfad = {pfad: (s, st) for s, pfad, st in zu_hashen}
            neu_je_hash = {}                          # hash -> [(schluessel, pfad, st)]
            vorgaenger = {}                           # neuer hash -> hash, der vorher an diesem Ort lag
            ortwechsel = []                           # (hash, schluessel, st, alter_hash)
            for pfad, h, fehler in pool.map(_hash, list(nach_pfad), chunksize=8):
                if h is None:
                    log.warning("nicht lesbar: %s (%s)", pfad, fehler)
                    continue
                s, st = nach_pfad[pfad]
                alt = index.get(s)
                status = self.k.datei_status(h)
                if status == "lebt":
                    ortwechsel.append((h, s, st, alt[0] if alt and alt[0] != h else None))
                elif status == "papierkorb":
                    # Wer ein Modell löscht und die Datei zurücklegt, soll es
                    # im Papierkorb wiederherstellen — nicht still zurückbekommen.
                    self.status["im_papierkorb"] += 1
                else:
                    neu_je_hash.setdefault(h, []).append((s, pfad, st))
                    if alt and alt[0] != h:
                        ortwechsel.append((None, s, st, alt[0]))
                        vorgaenger[h] = alt[0]

            with self.b.db.transaction():
                for h, s, st, alter_hash in ortwechsel:
                    if alter_hash:
                        self.k.ort_entfernen(alter_hash, *s)
                    if h:
                        self.k.ort_setzen(h, s[0], s[1], st.st_size, st.st_mtime)
            self._setze(verschoben=sum(1 for o in ortwechsel if o[0]), phase="analysieren",
                        zu_analysieren=len(neu_je_hash), analysiert=0)

            aufgaben = [(h, (faelle[0][1], self.b.vorschau_pfad(h, "extrahiert"))) for h, faelle in neu_je_hash.items()]
            gruppe = []
            for h, erg, fehler in self._verteilen(aufgaben, _analyse):
                if fehler:      # die Datei liess sich nicht lesen oder riss ihren Arbeiter mit: sie bleibt als „unlesbar“ stehen
                    pfad = neu_je_hash[h][0][1]
                    log.warning("Analyse %s: %s", pfad, fehler)
                    erg = ({"format": formate.format_von(pfad)}, "keine", fehler)
                gruppe.append((h, *erg))
                if len(gruppe) >= GRUPPE:
                    self._anlegen(gruppe, neu_je_hash, vorgaenger)
                    gruppe = []
            self._anlegen(gruppe, neu_je_hash, vorgaenger)

            # Orte, die dieser Lauf nicht mehr gesehen hat.
            weg = [(v[0], s) for s, v in index.items() if s not in gesehen and s[0] in wurzeln]
            with self.b.db.transaction():
                for h, s in weg:
                    self.k.ort_entfernen(h, *s)
                self.k.namen_angleichen()
            self._setze(entfernt=len(weg), phase="vorschau")

            self._vorschauen()
        finally:
            self._pool.shutdown(wait=False, cancel_futures=True)
        self._setze(laeuft=False, phase="fertig", dauer_s=round(time.time() - t0, 1))

    def _anlegen(self, gruppe, neu_je_hash, vorgaenger):
        if not gruppe:
            return
        with self.b.db.transaction():
            for h, felder, vorschau_status, fehler in gruppe:
                orte = [{"wurzel": s[0], "pfad": s[1], "groesse": st.st_size, "mtime": st.st_mtime}
                        for s, _, st in neu_je_hash[h]]
                self.k.neue_datei(h, felder, orte, vorschau_status, fehler, vorgaenger.get(h))
        self._setze(neu=self.status["neu"] + len(gruppe),
                    unlesbar=self.status["unlesbar"] + sum(1 for g in gruppe if g[3]),
                    analysiert=self.status["analysiert"] + len(gruppe))

    def _vorschauen(self):
        offen = self.k.ausstehende_vorschauen()
        self._setze(vorschauen_offen=len(offen))
        aufgaben = []
        for h, d in offen:
            ort = next(iter(d.get("orte", [])), None)
            pfad = self.k.absoluter_pfad(ort) if ort else None
            # In der Farbe des ersten Filaments, wenn der Slicer eine kennt —
            # so sieht die Kachel aus wie der Druck.
            farbe = next((f.get("farbe") for p in d.get("platten") or [] for f in p.get("filamente", [])
                          if f.get("farbe")), None)
            if pfad:
                aufgaben.append((h, (pfad, self.b.vorschau_pfad(h, "berechnet"), farbe)))
        rest, stapel = len(aufgaben), []
        for h, erg, fehler in self._verteilen(aufgaben, _rendern):
            status, fehler = ("fehler", fehler) if fehler else erg
            if fehler:
                log.warning("Vorschau %s: %s", h[:12], fehler)
            stapel.append((h, status))
            rest -= 1
            if len(stapel) >= GRUPPE:
                self._vorschauen_speichern(stapel)
                stapel = []
                self._setze(vorschauen_offen=rest)
        self._vorschauen_speichern(stapel)

    def _vorschauen_speichern(self, stapel):
        """Gruppenweise in einer Transaktion: jede einzelne Änderung kostet ihren fsync (VERTRAG §5), bei tausenden Vorschauen
        war das ein grosser Teil der Zeit."""
        if not stapel:
            return
        with self.b.db.transaction():
            for h, status in stapel:
                self.k.vorschau_setzen(h, status)

    def _ablaufen(self, wurzel):
        """(absolut, relativ mit /, stat) je Modelldatei; versteckte Ordner
        und der eigene Bestand bleiben aussen vor."""
        bestand = os.path.abspath(self.b.wurzel)
        for ordner, unter, namen in os.walk(wurzel, followlinks=False):
            unter[:] = sorted(u for u in unter if not u.startswith(".")
                              and os.path.abspath(os.path.join(ordner, u)) != bestand)
            for n in namen:
                if n.startswith(".") or formate.format_von(n) is None:
                    continue
                pfad = os.path.join(ordner, n)
                try:
                    st = os.stat(pfad)
                except OSError:
                    continue
                rel = os.path.relpath(pfad, wurzel).replace(os.sep, "/")
                yield pfad, rel, st
