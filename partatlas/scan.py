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
  6. STEP-Dateien über FreeCAD (ohne Fenster) in ein Netz umwandeln; daraus kommen Vorschau, Maße und die 3D-Ansicht.
     Ohne FreeCAD bleiben sie „ausstehend“ und kommen beim nächsten Lauf dran.

Abbrechen (`abbrechen()`): ein Ereignis, das jede Phase je Ergebnis prüft,
nie innerhalb einer Transaktion. Was fertig ist, steht schon in der
Datenbank; der Rest bleibt unangetastet und der nächste Lauf macht dort
weiter (bekannte Dateien über Ort, Grösse und Zeit, ausstehende Vorschauen
bleiben „ausstehend“). Bei Abbruch wird nichts entfernt: die Liste der
gesehenen Orte ist dann unvollständig.
"""
import logging
import multiprocessing
import os
import threading
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from concurrent.futures.process import BrokenProcessPool

from . import cad, dateien, formate, programme, vorschau

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
    status = "keine" if a.format in formate.OHNE_NETZ else "ausstehend"
    if a.vorschau_png:
        dateien.schreibe_atomar(vorschau_ziel, a.vorschau_png)
        status = "eingebettet"
    felder = a.als_felder()
    if a.format in ("step", "fcstd"):
        felder["cad"] = "ausstehend"     # Netz kommt später von FreeCAD (Phase 6), wenn es da ist
    return felder, status, None


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


def _cad_bild(stl, vorschau_ziel):
    """Aus dem Netz, das FreeCAD geschrieben hat: Maße (wie bei einer STL) und das berechnete Vorschaubild."""
    try:
        a = formate.analysiere(stl, mit_netz=True)
        felder = {k: v for k, v in a.als_felder().items() if k in ("masse_mm", "volumen_cm3", "flaeche_cm2", "dreiecke")}
        png = vorschau.rendere(a.netz)
    except (formate.FormatFehler, MemoryError) as e:
        return {}, "fehler", str(e)
    if not png:
        return felder, "keine", None
    dateien.schreibe_atomar(vorschau_ziel, png)
    return felder, "gerendert", None


# ---------------------------------------------------------------- Scanner

class Scanner:
    def __init__(self, bestand, katalog, melden=None, prozesse=None, cad_befehl=None):
        self.b = bestand
        self.cad_befehl = cad_befehl        # Aufruf von FreeCAD ohne Fenster; None: aus den installierten Programmen ermitteln
        self.k = katalog
        self.melden = melden or (lambda status: None)
        self.prozesse = prozesse or max(1, (os.cpu_count() or 2) - 1)
        self._sperre = threading.Lock()
        self._faden = None
        self._nochmal = False               # Folgelauf nach dem laufenden: False, "cad" (nur FreeCAD) oder True (ganz)
        self.status = {"laeuft": False}
        self._phasen, self._phase_name, self._phase_t = {}, None, 0.0
        self._pool = None
        self._stopp = threading.Event()
        self._nur_cad = False

    def abbrechen(self):
        """Bittet den laufenden Lauf, aufzuhören. Wahr, wenn einer lief. Ein wartender Folgelauf entfällt: wer abbricht,
        will Ruhe, nicht den nächsten Durchgang."""
        with self._sperre:
            if not self.status.get("laeuft"):
                return False
            self._nochmal = False
            self._stopp.set()
        self._setze(abbricht=True)
        return True

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
            if self._stopp.is_set():
                return
            stueck = offen if welle is None else offen[:welle]
            auftraege = {self._pool.submit(arbeit, *a): k for k, a in stueck}
            erledigt, zerbrochen = set(), False
            for f in as_completed(auftraege):
                if self._stopp.is_set():
                    for g in auftraege:
                        g.cancel()
                    return
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

    def starten(self, nur_cad=False):
        """Im Hintergrund. Kommt ein Auftrag während eines Laufs (Hochladen,
        Entpacken), läuft danach ein zweiter — der erste hat die neuen
        Dateien womöglich schon hinter sich gelassen.

        Mit `nur_cad`: nur die Umwandlung über FreeCAD, ohne Suchen und Hashen — etwa nachdem der Anwender FCStd erlaubt hat."""
        with self._sperre:
            if self._faden and self._faden.is_alive():
                # Den Wunsch merken, nicht nur „nochmal“: vorher wurde aus „nur FreeCAD“ (nach der FCStd-Zusage) ein ganzer
                # Lauf, der alles neu einlas. Ein ganzer Folgelauf schliesst die Umwandlung ein.
                self._nochmal = True if not nur_cad or self._nochmal is True else "cad"
                return False
            self._nochmal = False
            self._nur_cad = nur_cad
            self._faden = threading.Thread(target=self._lauf_sicher, name="scan", daemon=True)
            self._faden.start()
            return True

    def warten(self, zeit=None):
        if self._faden:
            self._faden.join(zeit)

    def _lauf_sicher(self):
        while True:
            try:
                nur, self._nur_cad = self._nur_cad, False      # ein Folgelauf ist wieder ein ganzer
                self.lauf(nur_cad=True) if nur else self.lauf()
            except Exception as e:                   # der Server soll weiterlaufen
                log.exception("Scan abgebrochen")
                self._setze(laeuft=False, abbruch=str(e))
            with self._sperre:
                if not self._nochmal:
                    return
                self._nur_cad = self._nochmal == "cad"
                self._nochmal = False

    def lauf(self, nur_cad=False):
        t0 = time.time()
        self._stopp.clear()
        self._setze(fcstd_frage=0, cad_ohne_freecad=0)
        if nur_cad:
            return self._lauf_nur_cad(t0)
        self._setze(laeuft=True, phase="suchen", nur_cad=False, nicht_erreichbar=[], gefunden=0, neu=0, verschoben=0, entfernt=0, bearbeitet=0,
                    unlesbar=0, zurueckgeholt=0, im_papierkorb=0, vorschauen_offen=0, abbruch=None, abbricht=False, abgebrochen=False,
                    beginn=time.strftime("%H:%M:%S"))
        index = self.k.ort_index()
        ignoriert = self.k.ignorierte_orte()
        wurzeln = self.k.wurzeln()
        gesehen, zu_hashen = set(), []
        # Ein Wurzelordner, der fehlt oder plötzlich keine einzige Modelldatei mehr hat, obwohl der Katalog welche kennt, ist mit grosser
        # Wahrscheinlichkeit nicht erreichbar (Stick ab, Netzlaufwerk weg, leerer Einhängepunkt) — nicht geleert. Seine Orte bleiben dann
        # stehen; sonst stünde nach jedem Stecker-Ziehen der halbe Katalog als „Datei fehlt“ da.
        bekannt_je_wurzel = {}
        for wid, _ in index:
            bekannt_je_wurzel[wid] = bekannt_je_wurzel.get(wid, 0) + 1
        unerreichbar = []
        for wid, w in wurzeln.items():
            gefunden_hier = 0
            for pfad, rel, st in self._ablaufen(w["pfad"]):
                gefunden_hier += 1
                if self._stopp.is_set():
                    return self._abgebrochen(t0)
                schluessel = (wid, rel)
                gesehen.add(schluessel)
                alt = index.get(schluessel)
                if alt and alt[1] == st.st_size and alt[2] == st.st_mtime:
                    continue
                ign = ignoriert.get(schluessel)
                if ign and ign[1] == st.st_size and ign[2] == st.st_mtime:
                    self.status["im_papierkorb"] += 1     # aus dem Katalog entfernt, die Datei liegt noch im Ordner: so lassen
                    continue
                zu_hashen.append((schluessel, pfad, st))
            if gefunden_hier == 0 and (bekannt_je_wurzel.get(wid) or not os.path.isdir(w["pfad"])):
                unerreichbar.append(wid)
                log.warning("Wurzelordner nicht erreichbar oder leer, seine Orte bleiben: %s", w["pfad"])
        if self._stopp.is_set():
            return self._abgebrochen(t0)
        self._setze(gefunden=len(gesehen), phase="hashen", zu_pruefen=len(zu_hashen),
                    nicht_erreichbar=[wurzeln[w]["name"] for w in unerreichbar])

        self._pool = self._neuer_pool()
        try:
            pool = self._pool
            nach_pfad = {pfad: (s, st) for s, pfad, st in zu_hashen}
            neu_je_hash = {}                          # hash -> [(schluessel, pfad, st)]
            vorgaenger = {}                           # neuer hash -> hash, der vorher an diesem Ort lag
            ortwechsel = []                           # (hash, schluessel, st, alter_hash)
            zurueck = []                              # (hash, schluessel, st): Dateien, deren Modell im Papierkorb liegt
            for pfad, h, fehler in pool.map(_hash, list(nach_pfad), chunksize=8):
                if self._stopp.is_set():      # map holt die übrigen Aufträge beim Verlassen der Schleife zurück
                    break
                if h is None:
                    log.warning("nicht lesbar: %s (%s)", pfad, fehler)
                    continue
                s, st = nach_pfad[pfad]
                alt = index.get(s)
                status = self.k.datei_status(h)
                if status == "lebt":
                    ortwechsel.append((h, s, st, alt[0] if alt and alt[0] != h else None))
                elif status == "papierkorb":
                    # Der Inhalt ist die Kennung: ein Modell im Papierkorb, dessen Datei der Anwender wieder in den Ordner legt, kommt
                    # zurück, wenn frühere Fassungen die Datei verschoben hatten; sonst bleibt es im Papierkorb (Datei und Modell sind
                    # beide noch da, der Anwender hat nur den Katalogeintrag entfernt).
                    zurueck.append((h, s, st))
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
            for h, s, st in zurueck:
                if self.k.aus_papierkorb_zurueck(h, s[0], s[1], st):
                    self._setze(zurueckgeholt=self.status["zurueckgeholt"] + 1)
                else:
                    self.status["im_papierkorb"] += 1
            verschoben = sum(1 for o in ortwechsel if o[0])
            self._setze(verschoben=verschoben, bearbeitet=verschoben)
            if self._stopp.is_set():          # gehasht ist nur ein Teil: nichts Neues anlegen, nichts entfernen
                return self._abgebrochen(t0)
            self._setze(phase="analysieren", zu_analysieren=len(neu_je_hash), analysiert=0)

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
            self._anlegen(gruppe, neu_je_hash, vorgaenger)    # auch beim Abbruch: was schon analysiert ist, geht nicht verloren
            if self._stopp.is_set():
                return self._abgebrochen(t0)

            # Orte, die dieser Lauf nicht mehr gesehen hat.
            weg = [(v[0], s) for s, v in index.items() if s not in gesehen and s[0] in wurzeln and s[0] not in unerreichbar]
            with self.b.db.transaction():
                for h, s in weg:
                    self.k.ort_entfernen(h, *s)
                self.k.namen_angleichen()
            # Gleich hier fragen, sobald die FCStd-Dateien bekannt sind — nicht erst am Ende des Laufs. Vorher kam die Frage nach der
            # STEP-Umwandlung, und das Vorschaubild aus der FCStd-Datei (liest partAtlas ohne FreeCAD) sah aus, als sei sie schon geladen.
            # Wer antwortet, solange der Lauf noch nicht bei FreeCAD ist, bekommt die FCStd im selben Lauf; sonst folgt „nur FreeCAD“.
            self._setze(entfernt=len(weg), phase="vorschau", fcstd_frage=self._fcstd_offen())

            self._vorschauen()
            if self._stopp.is_set():
                return self._abgebrochen(t0)
            self._cad()
            if self._stopp.is_set():
                return self._abgebrochen(t0)
        finally:
            self._pool.shutdown(wait=False, cancel_futures=True)
        self._setze(laeuft=False, abbricht=False, phase="fertig", dauer_s=round(time.time() - t0, 1))

    def _lauf_nur_cad(self, t0):
        """Nur Phase 6. Zähler von Suchen und Hashen bleiben vom letzten Lauf stehen: es wurde nichts neu eingelesen."""
        self._setze(laeuft=True, phase="cad", nur_cad=True, bearbeitet=0, abbruch=None, abbricht=False, abgebrochen=False,
                    beginn=time.strftime("%H:%M:%S"))
        self._pool = self._neuer_pool()
        try:
            self._cad()
            if self._stopp.is_set():
                return self._abgebrochen(t0)
        finally:
            self._pool.shutdown(wait=False, cancel_futures=True)
        self._setze(laeuft=False, abbricht=False, phase="fertig", dauer_s=round(time.time() - t0, 1))

    def _abgebrochen(self, t0):
        self._setze(laeuft=False, abbricht=False, abgebrochen=True, phase="abgebrochen", dauer_s=round(time.time() - t0, 1))

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
                    analysiert=self.status["analysiert"] + len(gruppe),
                    bearbeitet=self.status["bearbeitet"] + len(gruppe))

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

    def _cad(self):
        """STEP-Dateien ohne Netz über FreeCAD umwandeln. Das Netz liegt abgeleitet in `netz/<hash>.stl` (nicht gesichert,
        jederzeit neu berechenbar). Ein Fehler oder eine Zeitüberschreitung betrifft nur seine Datei und wird nicht bei
        jedem Lauf wiederholt: sonst hielte dieselbe Datei jeden Scan um die Zeitgrenze auf."""
        offen = self.k.ausstehende_cad()
        if not offen:
            return
        prog = programme.programm_fuer(programme.CAD, self.b.einstellungen()) or {}
        befehl = self.cad_befehl or cad.konsole_befehl(prog.get("pfad"))
        if not befehl:
            # Ins Protokoll und in den Status: sonst weiss niemand, ob FreeCAD fehlt oder nur nicht als solches erkannt wurde.
            log.warning("CAD: kein FreeCAD-Aufruf gefunden, %d Dateien warten (erkanntes CAD-Programm: %s)", len(offen),
                        prog.get("pfad") or "keines")
            self._setze(cad_ohne_freecad=len(offen), cad_programm=prog.get("pfad") or "")
            return
        log.info("CAD: FreeCAD-Aufruf %s, %d Dateien offen", befehl, len(offen))
        # FCStd lädt FreeCAD wie beim Doppelklick, und ein Dokument kann Programmcode mitbringen: das tut partAtlas nur nach
        # ausdrücklicher Zusage des Anwenders. Solange er nicht geantwortet hat, fragt die Oberfläche (`fcstd_frage`).
        if self.b.einstellungen().get("fcstd_freecad") != "ja":
            offen = [x for x in offen if x[1].get("format") != "fcstd"]
            self._setze(fcstd_frage=self._fcstd_offen())
            if not offen:
                return
        aufgaben = []
        for h, d in offen:
            ort = next((o for o in d.get("orte", []) if self.k.absoluter_pfad(o)), None)
            pfad = self.k.absoluter_pfad(ort) if ort else None
            if pfad and os.path.exists(pfad):
                aufgaben.append((h, pfad, self.b.pfad("arbeit", "cad", f"{h}.stl")))
        self._setze(phase="cad", cad_offen=len(aufgaben))
        rest = len(aufgaben)
        for h, ok, info in cad.umwandeln(befehl, aufgaben, self._stopp, self.b.pfad("arbeit", "cad")):
            rest -= 1
            if not ok:
                log.warning("CAD %s: %s", h[:12], info)
                with self.b.db.transaction():
                    self.k.cad_fehler(h, str(info))
            else:
                ziel = self.b.netz_pfad(h)
                os.makedirs(os.path.dirname(ziel), exist_ok=True)
                os.replace(self.b.pfad("arbeit", "cad", f"{h}.stl"), ziel)
                felder, status, fehler = {}, "fehler", "Vorschau nicht berechnet"
                for _, erg, ausnahme in self._verteilen([(h, (ziel, self.b.vorschau_pfad(h, "berechnet")))], _cad_bild):
                    felder, status, fehler = ({}, "fehler", ausnahme) if ausnahme else erg
                if self._stopp.is_set():
                    break                  # abgebrochen: die Datei bleibt ausstehend, das Netz liegt schon da
                with self.b.db.transaction():
                    self.k.cad_ergebnis(h, felder, status, fehler)
            self._setze(cad_offen=rest, bearbeitet=self.status["bearbeitet"] + 1)

    def _fcstd_offen(self):
        """Wie viele FCStd-Dateien auf die Zusage für FreeCAD warten; 0, wenn der Anwender schon geantwortet hat."""
        if self.b.einstellungen().get("fcstd_freecad") is not None:
            return 0
        return sum(1 for _, d in self.k.ausstehende_cad() if d.get("format") == "fcstd")

    def _vorschauen_speichern(self, stapel):
        """Gruppenweise in einer Transaktion: jede einzelne Änderung kostet ihren fsync (VERTRAG §5), bei tausenden Vorschauen
        war das ein grosser Teil der Zeit."""
        if not stapel:
            return
        with self.b.db.transaction():
            for h, status in stapel:
                self.k.vorschau_setzen(h, status)
        self._setze(bearbeitet=self.status["bearbeitet"] + len(stapel))

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
