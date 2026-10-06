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
from datetime import datetime
import multiprocessing
import os
import sys
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, ProcessPoolExecutor, wait
from concurrent.futures import TimeoutError as FutZeit      # vor 3.11 nicht dasselbe wie das eingebaute
from concurrent.futures.process import BrokenProcessPool

from . import cad, dateien, formate, programme, vorschau
from .bestand import DATEI, KLEIN_BYTES, MODELL

log = logging.getLogger("partatlas.scan")

GRUPPE = 100
SPEICHERN_ALLE_S = 2.0   # Ergebnisse der Vorschauen spätestens so oft festhalten, damit die Bilder nach und nach erscheinen, nicht erst nach 100 Stück
ZEITGRENZE = 180      # Sekunden ohne ein einziges fertiges Ergebnis, bevor eine Datei als hängend gilt (wie bei FreeCAD, cad.py)


# ---------------------------------------------------------------- Arbeitsprozesse

def _niedrig():
    """Beim Start jedes Arbeiters: Hintergrundarbeit läuft mit niedriger Priorität. Sonst konkurrieren alle Arbeiter gleichberechtigt
    mit dem Server um die Kerne, und auf einem älteren Rechner braucht ein Klick Sekunden bis Minuten, solange eingelesen wird.
    Gibt ein Rechner Kerne frei, nehmen die Arbeiter sie trotzdem; nur wenn jemand klickt, gewinnt der Server."""
    try:
        if sys.platform.startswith("win"):
            import ctypes
            ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00004000)   # BELOW_NORMAL_PRIORITY_CLASS
        else:
            os.nice(10)
    except Exception:
        pass            # keine Berechtigung oder nicht unterstützt: dann eben mit normaler Priorität

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
    def __init__(self, bestand, katalog, melden=None, prozesse=None, cad_befehl=None, zeitgrenze=None):
        self.b = bestand
        self.cad_befehl = cad_befehl        # Aufruf von FreeCAD ohne Fenster; None: aus den installierten Programmen ermitteln
        self.k = katalog
        self.zeitgrenze = zeitgrenze or ZEITGRENZE
        self.melden = melden or (lambda status: None)
        # Höchstens die Hälfte der Threads (mindestens einer, nie alle bis auf einen): die Oberfläche braucht auch etwas.
        self.prozesse = prozesse or max(1, min((os.cpu_count() or 2) - 1, ((os.cpu_count() or 2) + 1) // 2))
        self._sperre = threading.Lock()
        self._faden = None
        self._nochmal = False               # Folgelauf nach dem laufenden: False, "cad" (nur FreeCAD) oder True (ganz)
        self.status = {"laeuft": False, "lauf": 0}
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
        return ProcessPoolExecutor(self.prozesse, mp_context=multiprocessing.get_context("spawn"), initializer=_niedrig)

    def _pool_neu(self):
        """Nach einem harten Absturz eines Arbeiters (etwa vom Betriebssystem beendet, weil der Speicher ausging) ist der
        ganze Pool unbrauchbar: durch einen frischen ersetzen."""
        alt, self._pool = self._pool, self._neuer_pool()
        # Ein hängender Arbeiter lässt sich nicht bitten aufzuhören; ohne terminate() lebte er weiter und hielte die CPU.
        for p in list((getattr(alt, "_processes", None) or {}).values()):
            try:
                p.terminate()
            except Exception:
                pass
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
            warten = set(auftraege)
            while warten:
                # Zeitgrenze = Stillstand: solange irgendeine Datei fertig wird, läuft der Lauf; kommt `zeitgrenze` Sekunden lang
                # nichts, hängt mindestens eine. Welche, zeigt das Wellen-Verfahren unten (Pool beenden, Rest einzeln).
                fertig, warten = wait(warten, timeout=self.zeitgrenze, return_when=FIRST_COMPLETED)
                if not fertig:
                    zerbrochen = True
                    break
                for f in fertig:
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
                            erg, fehler = self._pool.submit(arbeit, *a).result(timeout=self.zeitgrenze), None
                        except BrokenProcessPool:
                            self._pool_neu()
                            erg, fehler = None, "Arbeitsprozess beendet (vermutlich zu wenig Speicher für diese Datei)"
                        except FutZeit:
                            self._pool_neu()
                            erg, fehler = None, f"Zeitgrenze von {self.zeitgrenze} s überschritten (Datei hängt oder ist zu gross)"
                        except Exception as e:
                            erg, fehler = None, f"{type(e).__name__}: {e}"
                        erledigt.add(k)
                        yield k, erg, fehler
            offen = [(k, a) for k, a in offen if k not in erledigt]

    def _setze(self, **werte):
        # Wie lange jede Phase dauerte (Suchen, Hashen, Analysieren, Vorschau): wer einen grossen Bestand einliest,
        # will wissen, wo die Zeit bleibt. Eine neue Phase schliesst die vorige.
        if "phase" in werte:
            jetzt = time.monotonic()
            if werte["phase"] == "suchen":
                self._phasen, self._phase_name = {}, None
            if self._phase_name and self._phase_name != werte["phase"]:
                self._phasen[self._phase_name] = round(self._phasen.get(self._phase_name, 0) + jetzt - self._phase_t, 1)
            if self._phase_name != werte["phase"]:
                self._phase_name, self._phase_t = werte["phase"], jetzt
            werte["phasen"] = dict(self._phasen)
        if self._phase_name:
            werte["phase_s"] = round(time.monotonic() - self._phase_t, 1)     # für die Restzeit-Schätzung der Oberfläche
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

    def naechster_lauf(self):
        """Die Nummer des Laufs, der die Änderung von eben sieht — VOR `starten` lesen: läuft einer, ist es sein Folgelauf, sonst der
        neue. Danach gelesen könnte der neue Lauf schon mitgezählt sein."""
        return self.status.get("lauf", 0) + 1

    def warten(self, zeit=None):
        if self._faden:
            self._faden.join(zeit)

    def _kette_buchen(self, kette):
        """Mehrere Läufe hintereinander (Hochladen, Entpacken: jeder Auftrag, der während eines Laufs eintrifft, bekommt einen Folgelauf) sind
        für den Anwender ein Einlesen. Die Zeile oben rechts zeigte nur den letzten Lauf: „219 Dateien, 1 neu in unter 1 s“ nach 121 Dateien
        in 20 s. Hier werden die Läufe einer Kette zusammengezählt; ein einzelner Lauf bleibt unverändert."""
        st = self.status
        if st.get("phase") != "fertig" or st.get("nur_cad"):
            return
        kette["laeufe"] += 1
        for f in ("neu", "verschoben", "entfernt", "zurueckgeholt", "aufgeraeumt", "kopien", "aus_datei"):
            kette["summe"][f] = kette["summe"].get(f, 0) + (st.get(f) or 0)
        kette["summe"]["einlesen_s"] = round(kette["summe"].get("einlesen_s", 0) + (st.get("einlesen_s") or 0), 1)
        for name, sek in (st.get("phasen") or {}).items():
            kette["phasen"][name] = round(kette["phasen"].get(name, 0) + sek, 1)
        for fm, n in (st.get("je_format") or {}).items():
            kette["je_format"][fm] = kette["je_format"].get(fm, 0) + n
        if kette["laeufe"] > 1:
            self._setze(**kette["summe"], phasen=dict(kette["phasen"]), je_format=dict(kette["je_format"]),
                        dauer_s=round(time.monotonic() - kette["t0"], 1))

    def _lauf_sicher(self):
        kette = {"t0": time.monotonic(), "laeufe": 0, "summe": {}, "phasen": {}, "je_format": {}}
        while True:
            try:
                nur, self._nur_cad = self._nur_cad, False      # ein Folgelauf ist wieder ein ganzer
                self.lauf(nur_cad=True) if nur else self.lauf()
                self._kette_buchen(kette)
            except Exception as e:                   # der Server soll weiterlaufen
                log.exception("Scan abgebrochen")
                self._setze(laeuft=False, abbruch=str(e))
            with self._sperre:
                if not self._nochmal:
                    return
                self._nur_cad = self._nochmal == "cad"
                self._nochmal = False

    def lauf(self, nur_cad=False):
        t0 = time.monotonic()
        self._stopp.clear()
        self._setze(fcstd_frage=0, cad_ohne_freecad=0)
        if nur_cad:
            return self._lauf_nur_cad(t0)
        # `lauf` zählt die Läufe: der Einlesen-Dialog weiss so, welcher Lauf seiner ist. `geprueft`, `je_format`, `aus_datei`,
        # `einlesen_s`, `vorschauen_gesamt`, `cad_gesamt`: was der Dialog und die Anzeige am Zahnrad zeigen (Fortschritt, Bilanz).
        self._setze(lauf=self.status["lauf"] + 1, geprueft=0, je_format={}, aus_datei=0, einlesen_s=None, vorschauen_gesamt=0,
                    cad_gesamt=0, zu_pruefen=0, zu_analysieren=0, analysiert=0, kopien=0, aufgeraeumt=0)
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
            for i, (pfad, h, fehler) in enumerate(pool.map(_hash, list(nach_pfad), chunksize=8), 1):
                if self._stopp.is_set():      # map holt die übrigen Aufträge beim Verlassen der Schleife zurück
                    break
                if i % 20 == 0 or i == len(nach_pfad):
                    self._setze(geprueft=i)
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
            # Inhaltsgleiche Kopien werden ein Modell mit mehreren Orten: die Bilanz nennt sie, sonst fehlen scheinbar Dateien.
            self._setze(phase="analysieren", zu_analysieren=len(neu_je_hash), analysiert=0,
                        kopien=sum(len(f) - 1 for f in neu_je_hash.values()))

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
            # Ein Entwurf, dessen Datei der Anwender gelöscht hat, ist aufgeräumt, nicht „fehlt“: still in den Papierkorb (dort
            # zurückholbar), die Bilanz nennt ihn. Ein nicht erreichbarer Ordner steht nicht in `weg`, dort geht nichts.
            aufgeraeumt = set()
            for h, _ in weg:
                d = self.b.db.get_node(f"{DATEI}/{h}", readonly=True)
                mid = self.k.modell_von(h) if d is not None and not d.get("orte") else None
                if mid and (self.b.db.get_node(f"{MODELL}/{mid}", readonly=True) or {}).get("entwurf"):
                    aufgeraeumt.add(mid)
            for mid in sorted(aufgeraeumt):
                self.k.loeschen(mid)
            if aufgeraeumt:
                self._setze(aufgeraeumt=len(aufgeraeumt))
            # Gleich hier fragen, sobald die FCStd-Dateien bekannt sind — nicht erst am Ende des Laufs. Vorher kam die Frage nach der
            # STEP-Umwandlung, und das Vorschaubild aus der FCStd-Datei (liest partAtlas ohne FreeCAD) sah aus, als sei sie schon geladen.
            # Wer antwortet, solange der Lauf noch nicht bei FreeCAD ist, bekommt die FCStd im selben Lauf; sonst folgt „nur FreeCAD“.
            self._setze(entfernt=len(weg), phase="vorschau", cad_voraus=self._cad_anzahl(), fcstd_frage=self._fcstd_offen(), einlesen_s=round(time.monotonic() - t0, 1))

            self._vorschauen()
            if self._stopp.is_set():
                return self._abgebrochen(t0)
            # Die kleinen Bilder vor FreeCAD: das braucht bei einer grossen Library Stunden, und bis dahin sollen die Kacheln schon stehen.
            self._thumbs()
            if self._stopp.is_set():
                return self._abgebrochen(t0)
            self._cad()
            if self._stopp.is_set():
                return self._abgebrochen(t0)
            self._thumbs()
            if self._stopp.is_set():
                return self._abgebrochen(t0)
        finally:
            self._pool.shutdown(wait=False, cancel_futures=True)
        # Wann zuletzt vollständig eingelesen wurde: steht neben „Bibliothek“, damit man bei „nur auf Knopfdruck“ sieht, wie alt der Stand ist.
        # Fehlt der Platz zum Schreiben, ist das keine Sache, die das Einlesen scheitern lässt.
        jetzt = datetime.now().astimezone().isoformat(timespec="seconds")
        try:
            self.b.einstellungen_setzen(zuletzt_eingelesen=jetzt)
        except OSError as e:
            log.warning("Zeitpunkt des Einlesens nicht gespeichert: %s", e)
        self._setze(laeuft=False, abbricht=False, phase="fertig", dauer_s=round(time.monotonic() - t0, 1), zuletzt_eingelesen=jetzt)

    def hat_offenes(self):
        """Wartet im Hintergrund noch Arbeit — ein Vorschaubild, das fehlt, oder eine FreeCAD-Umwandlung, die jetzt möglich ist?
        Die Warteschlange ist der Zustand „ausstehend“ an den Dateien im Bestand; sie übersteht einen Neustart. Dateien ohne bekannten Ort
        zählen nicht (es gibt nichts zu rechnen) und halten sonst bei jedem Start einen leeren Lauf in Gang."""
        if any(d.get("orte") for _, d in self.k.ausstehende_vorschauen()):
            return True
        if self._cad_anzahl() == 0:
            return False
        prog = programme.programm_fuer(programme.CAD, self.b.einstellungen()) or {}
        return bool(self.cad_befehl or cad.konsole_befehl(prog.get("pfad")))

    def _lauf_nur_cad(self, t0):
        """Der Hintergrundlauf, ohne Suchen und Hashen: Vorschaubilder, kleine Bilder, FreeCAD — alles, was im Bestand als „ausstehend“ steht.
        Heisst aus Gewohnheit `nur_cad` (so kam er zuerst, nach der Zusage für FCStd). Zähler von Suchen und Hashen bleiben vom letzten Lauf
        stehen: es wurde nichts neu eingelesen. Setzt nach einem Abbruch oder Neustart genau dort fort, wo es aufhörte."""
        self._setze(lauf=self.status["lauf"] + 1, einlesen_s=None)
        self._setze(laeuft=True, phase="vorschau", nur_cad=True, bearbeitet=0, abbruch=None, abbricht=False, abgebrochen=False,
                    vorschauen_gesamt=0, cad_gesamt=0, cad_voraus=self._cad_anzahl(), beginn=time.strftime("%H:%M:%S"))
        self._pool = self._neuer_pool()
        try:
            self._vorschauen()
            if self._stopp.is_set():
                return self._abgebrochen(t0)
            self._thumbs()
            if self._stopp.is_set():
                return self._abgebrochen(t0)
            self._cad()
            if self._stopp.is_set():
                return self._abgebrochen(t0)
            self._thumbs()
            if self._stopp.is_set():
                return self._abgebrochen(t0)
        finally:
            self._pool.shutdown(wait=False, cancel_futures=True)
        self._setze(laeuft=False, abbricht=False, phase="fertig", dauer_s=round(time.monotonic() - t0, 1))

    def _abgebrochen(self, t0):
        self._setze(laeuft=False, abbricht=False, abgebrochen=True, phase="abgebrochen", dauer_s=round(time.monotonic() - t0, 1))

    def _anlegen(self, gruppe, neu_je_hash, vorgaenger):
        if not gruppe:
            return
        with self.b.db.transaction():
            for h, felder, vorschau_status, fehler in gruppe:
                orte = [{"wurzel": s[0], "pfad": s[1], "groesse": st.st_size, "mtime": st.st_mtime}
                        for s, _, st in neu_je_hash[h]]
                self.k.neue_datei(h, felder, orte, vorschau_status, fehler, vorgaenger.get(h))
        je_format = dict(self.status["je_format"])
        for _, felder, _, _ in gruppe:
            f = felder.get("format") or "?"
            je_format[f] = je_format.get(f, 0) + 1
        self._setze(neu=self.status["neu"] + len(gruppe), je_format=je_format,
                    aus_datei=self.status["aus_datei"] + sum(1 for g in gruppe if g[2] == "eingebettet"),
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
        rest, stapel, zuletzt = len(aufgaben), [], time.monotonic()
        self._setze(vorschauen_gesamt=len(aufgaben), vorschauen_offen=rest)
        for h, erg, fehler in self._verteilen(aufgaben, _rendern):
            status, fehler = ("fehler", fehler) if fehler else erg
            if fehler:
                log.warning("Vorschau %s: %s", h[:12], fehler)
            stapel.append((h, status))
            rest -= 1
            if len(stapel) >= GRUPPE or time.monotonic() - zuletzt >= SPEICHERN_ALLE_S:
                self._vorschauen_speichern(stapel)
                stapel, zuletzt = [], time.monotonic()
            if rest % 10 == 0:
                self._setze(vorschauen_offen=rest)      # die Anzeige beim Zahnrad zählt mit, nicht nur alle hundert
        self._vorschauen_speichern(stapel)
        self._setze(vorschauen_offen=0)

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
        # Kleine zuerst: die ersten Bilder erscheinen früh, die Schätzung der Restzeit wird nicht von einer frühen Riesenbaugruppe verzerrt,
        # und was hängen könnte (die grossen Dateien), kommt ans Ende.
        aufgaben.sort(key=lambda a: os.path.getsize(a[1]))
        self._setze(phase="cad", cad_offen=len(aufgaben), cad_gesamt=len(aufgaben))
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

    def _cad_anzahl(self):
        """Wie viele Dateien FreeCAD voraussichtlich bekommt — schon vor den Vorschauen bekannt, damit man früh weiss, was kommt."""
        offen = self.k.ausstehende_cad()
        if self.b.einstellungen().get("fcstd_freecad") != "ja":
            offen = [x for x in offen if x[1].get("format") != "fcstd"]
        return len(offen)

    def _fcstd_offen(self):
        """Wie viele FCStd-Dateien auf die Zusage für FreeCAD warten; 0, wenn der Anwender schon geantwortet hat."""
        if self.b.einstellungen().get("fcstd_freecad") is not None:
            return 0
        return sum(1 for _, d in self.k.ausstehende_cad() if d.get("format") == "fcstd")

    def _thumbs(self):
        """Die kleinen Fassungen aller Bilder im Vault vorbauen (?t=1: Kacheln, Zeilen, Karten). Sonst erzeugt sie der erste Abruf,
        und das erste Scrollen durch einen frischen Bestand wartet auf tausend Verkleinerungen. Vorhandene werden übersprungen
        (`Bestand.thumb` ist wiederholbar); ein Bild, das sich nicht verkleinern lässt, schadet nicht — es bleibt beim Original.
        Threads statt Prozessen: Pillow gibt beim Lesen und Verkleinern die Sperre frei, und es gibt nichts zu übergeben."""
        bilder = []
        for teil in ("vorschau", "bilder"):
            ordner = self.b.pfad("vault", teil)
            if not os.path.isdir(ordner):
                continue
            for e in sorted(os.scandir(ordner), key=lambda e: e.name):
                n = e.name.lower()
                if not n.endswith((".png", ".jpg", ".jpeg", ".webp")):
                    continue
                # Kleine PNGs (die Vorschauen von partAtlas selbst: 320 px, ca. 11 KB) braucht es nicht zu verkleinern; `Bestand.thumb` liefert
                # sie direkt aus. Sie hier zu öffnen kostete bei 9 000 Bildern bei JEDEM Lauf ca. 3 s, auch ohne etwas Neues (gemessen am 6.10.2026,
                # Rückmeldung des Testers: „beim Aktualisieren unveränderter Ordner immer 3 Sekunden“); nur die Grösse abzufragen kostet 0,03 s.
                if n.endswith(".png") and e.stat().st_size <= KLEIN_BYTES:
                    continue
                bilder.append(e.path)
        self._setze(phase="thumbs", thumbs_gesamt=len(bilder), thumbs_fertig=0)
        if not bilder:
            return
        fertig = 0
        with ThreadPoolExecutor(min(2, self.prozesse)) as pool:      # wenige: die Threads teilen sich den Server-Prozess mit der Oberfläche
            for _ in pool.map(self._thumb_eins, bilder):
                fertig += 1
                if fertig % 25 == 0:
                    self._setze(thumbs_fertig=fertig)
                if self._stopp.is_set():
                    break
        self._setze(thumbs_fertig=fertig)

    def _thumb_eins(self, pfad):
        if self._stopp.is_set():
            return
        try:
            self.b.thumb(pfad)
        except Exception as e:            # ein kaputtes Bild hält den Lauf nicht auf
            log.warning("Thumbnail %s: %s", os.path.basename(pfad), e)

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
