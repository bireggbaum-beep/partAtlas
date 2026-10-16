"""
Backup als ZIP (KONZEPT §3.3a): Katalog und — einstellbar — Modelldateien und Bilder in einer Datei, in einem festen Zielordner, den das
eigene Backup-Programm des Anwenders (Sync, Cloud, NAS) ohnehin mitnimmt. Gegen Plattenschaden und Umzug; die automatische Sicherung
(sicherung.py) hilft gegen eigene Fehlgriffe und liegt auf derselben Platte.

Was hinein kommt, steht in ZEILEN. Regel (KONZEPT §3.3a): was der Anwender selbst hinzufügt, lässt sich nicht neu erzeugen → eigene Zeile,
Vorgabe an; was partAtlas erzeugt → Vorgabe aus oder ausgenommen. **Wer eine neue Art von Daten im Bestand ablegt, trägt sie hier ein**
— sonst fehlt sie im Backup, ohne dass es jemand merkt. `unbekannt()` findet solche Ordner (test_backup), und ein Backup nimmt sie
vorsichtshalber trotzdem mit (Zeile „sonstiges“), statt sie still zu übergehen.

Das ZIP: `partatlas-backup.json` (Inhaltsverzeichnis: Fassung, gewählte Zeilen, Anzahl und Grösse je Zeile, Wurzelordner, was sich nicht
lesen liess), die Teile des Bestands unter ihrem Pfad, die Modelldateien unter `dateien/<Wurzel-Kennung>/<Pfad im Ordner>`. Geschrieben
als Arbeitsdatei daneben, fsync, os.replace — eine abgebrochene liegt nie unter dem richtigen Namen. Die Datenbank wird unter der Sperre
von flatgraph gelesen (ein Stand, keine Mischung), die Dateien danach ohne Sperre: die Bedienung bleibt frei.
"""
import datetime
import json
import logging
import os
import re
import shutil
import threading
import time
import zipfile

from .bestand import DATEI, MODELL, WURZEL
from .version import VERSION

log = logging.getLogger("partatlas")

INHALT = "partatlas-backup.json"
FORMAT = 1
BEHALTEN = 2
NAME = re.compile(r"^partAtlas-Backup-(\d{4}-\d{2}-\d{2})(?:-(\d+))?\.zip$")

# Reihenfolge = Reihenfolge im Reiter. `teile`: Pfade im Bestand; `dateien`: die Modelldateien in den Ordnern des Anwenders.
ZEILEN = [
    {"id": "katalog", "titel": "Datenbank und Einstellungen", "immer": True, "vorgabe": True,
     "hinweis": "Modelle, Tags, Drucke, Baugruppen, Sammlungen, Notizen — klein, immer dabei.",
     "teile": ["datenbank", "vault_text", "einstellungen.json"]},
    {"id": "dateien", "titel": "Modelldateien", "vorgabe": True,
     "hinweis": "Die Dateien in deinen Ordnern, die im Katalog stehen — meist der grösste Teil. Andere Dateien in den Ordnern nicht.",
     "teile": []},
    {"id": "bilder", "titel": "Eigene Bilder, Druckfotos und Kaufteile", "vorgabe": True,
     "hinweis": "Lassen sich nicht neu erzeugen.", "teile": ["vault/bilder", "vault/komponenten"]},
    {"id": "anhaenge", "titel": "Anhänge", "vorgabe": True, "hinweis": "Zeichnungen, Anleitungen, Datenblätter an Modellen und Baugruppen.",
     "teile": ["vault/anhaenge"]},
    {"id": "gcode", "titel": "G-Code und Slicer-Projekte an Drucken", "vorgabe": True, "hinweis": "Lassen sich nicht neu erzeugen.",
     "teile": ["vault/gcode", "vault/quellen"]},
    {"id": "aufgehoben", "titel": "Aufgehobenes", "vorgabe": True,
     "hinweis": "Bilder und Anhänge, die du entfernt hast, und Dateien aus dem Papierkorb früherer Fassungen — partAtlas wirft nichts weg.",
     "teile": ["vault_archive", "papierkorb"]},
    {"id": "vorschau", "titel": "Vorschaubilder", "vorgabe": False,
     "hinweis": "partAtlas erzeugt sie nach dem Wiederherstellen neu.", "teile": ["vault/vorschau"]},
]
# Bewusst nicht im Backup — abgeleitet, vorübergehend oder schon enthalten. Mit Grund, damit niemand rätselt.
AUSGENOMMEN = {
    "arbeit": "Arbeitsdateien",
    "sicherungen": "automatische Sicherungen; die Datenbank ist im Backup",
    "netz": "Netze aus FreeCAD, neu erzeugbar",
    "thumbs": "kleine Bilder, neu erzeugbar",
    "cache": "Zwischenspeicher früherer Fassungen",
    "partatlas.log": "Protokoll",
}
# Was flatgraph neben die Datenbank legt (Sperrdatei u. ä.) und Dateien mit Punkt vorn gehören nicht dazu.
_FREMD = re.compile(r"^\.")
# Bereits gepackte Formate: noch einmal packen kostet Zeit und spart nichts.
_GEPACKT = (".3mf", ".png", ".jpg", ".jpeg", ".webp", ".zip", ".gz", ".7z", ".rar", ".fcstd", ".pdf", ".mp4")


def _zeile(zid):
    return next(z for z in ZEILEN if z["id"] == zid)


def _abgedeckt():
    teile = {t for z in ZEILEN for t in z["teile"]}
    return teile | set(AUSGENOMMEN)


def unbekannt(wurzel):
    """Pfade im Bestand, die weder zu einer Zeile gehören noch ausgenommen sind: oben und in vault/ (dort liegen die Arten von Daten)."""
    bekannt = _abgedeckt()
    aus = []
    for name in sorted(os.listdir(wurzel)) if os.path.isdir(wurzel) else []:
        if _FREMD.match(name) or name in bekannt:
            continue
        if name == "vault" and os.path.isdir(os.path.join(wurzel, name)):
            aus += [f"vault/{n}" for n in sorted(os.listdir(os.path.join(wurzel, name))) if f"vault/{n}" not in bekannt and not _FREMD.match(n)]
            continue
        aus.append(name)
    return aus


def _dateien_im_teil(wurzel, teil):
    """[(absoluter Pfad, Pfad im ZIP, Grösse)] eines Teils im Bestand; fehlt er, leer."""
    pfad = os.path.join(wurzel, *teil.split("/"))
    if os.path.isfile(pfad):
        return [(pfad, teil, os.path.getsize(pfad))]
    aus = []
    for d, ds, fs in os.walk(pfad):
        ds[:] = sorted(x for x in ds if not _FREMD.match(x))
        for f in sorted(fs):
            if _FREMD.match(f):
                continue
            p = os.path.join(d, f)
            try:
                aus.append((p, os.path.relpath(p, wurzel).replace(os.sep, "/"), os.path.getsize(p)))
            except OSError:
                pass
    return aus


def _modelldateien(katalog):
    """[(absoluter Pfad, Pfad im ZIP, Grösse)] aller Orte im Katalog — jede Kopie, auch von archivierten Modellen. Grösse aus der
    Datenbank, nicht von der Platte: die Zeile im Reiter soll sich ohne Tausende `stat` rechnen lassen."""
    db = katalog.db
    aus, gesehen = [], set()
    for d in db.list_nodes(DATEI, readonly=True).values():
        for o in d.get("orte") or []:
            ziel = f"dateien/{o['wurzel']}/{o['pfad']}"
            if ziel in gesehen:
                continue
            gesehen.add(ziel)
            aus.append((katalog.absoluter_pfad(o), ziel, o.get("groesse") or 0))
    return aus


def uebersicht(bestand, katalog):
    """Die Zeilen mit Anzahl und Grösse, für den Reiter (vor dem Erstellen die erwartete Grösse, KONZEPT §3.3a)."""
    e = bestand.einstellungen()
    gewaehlt = e.get("backup_zeilen") or {}
    zeilen = []
    for z in ZEILEN:
        liste = _modelldateien(katalog) if z["id"] == "dateien" else [x for t in z["teile"] for x in _dateien_im_teil(bestand.wurzel, t)]
        an = True if z.get("immer") else bool(gewaehlt.get(z["id"], z["vorgabe"]))
        zeilen.append({k: z[k] for k in ("id", "titel", "hinweis", "vorgabe")} | {"immer": bool(z.get("immer")), "an": an,
                                                                                   "dateien": len(liste), "bytes": sum(x[2] for x in liste)})
    fremd = unbekannt(bestand.wurzel)
    ziel = e.get("backup_ziel") or ""
    return {"zeilen": zeilen, "unbekannt": fremd, "ziel": ziel, "behalten": e.get("backup_behalten", BEHALTEN),
            "letztes": e.get("backup_letztes"), "vorhanden": vorhandene(ziel)}


def vorhandene(ziel):
    """Die Backups im Zielordner, neueste zuerst — nur Dateien mit unserem Namen."""
    if not ziel or not os.path.isdir(ziel):
        return []
    aus = []
    for n in os.listdir(ziel):
        m = NAME.match(n)
        if m and os.path.isfile(os.path.join(ziel, n)):
            aus.append({"name": n, "bytes": os.path.getsize(os.path.join(ziel, n)), "_sort": (m.group(1), int(m.group(2) or 1))})
    aus.sort(key=lambda x: x.pop("_sort"), reverse=True)
    return aus


def ziel_pruefen(bestand, katalog, ziel):
    """Der Zielordner: vorhanden, beschreibbar, nicht im Bestand und nicht in einem Ordner mit Modellen (dort läse partAtlas das ZIP
    beim Einlesen als Archiv mit). Gibt den bereinigten Pfad zurück oder wirft ValueError mit einem Satz für den Anwender."""
    if not ziel:
        raise ValueError("Wähle zuerst einen Zielordner für das Backup.")
    ziel = os.path.abspath(os.path.expanduser(ziel))
    if not os.path.isdir(ziel):
        raise ValueError("Diesen Ordner gibt es nicht.")
    real = os.path.realpath(ziel)

    def innen(a, b):
        return a == b or a.startswith(b.rstrip(os.sep) + os.sep)
    if innen(real, os.path.realpath(bestand.wurzel)):
        raise ValueError("Das Backup gehört nicht in den Bestand von partAtlas — wähle einen Ordner ausserhalb.")
    for w in katalog.db.list_nodes(WURZEL, readonly=True).values():
        if w.get("pfad") and innen(real, os.path.realpath(w["pfad"])):
            raise ValueError(f"Das ist ein Ordner mit Modellen ({w.get('name') or w['pfad']}). Wähle einen Ordner ausserhalb.")
    if not os.access(ziel, os.W_OK):
        raise ValueError("In diesen Ordner darf partAtlas nicht schreiben.")
    return ziel


class Backup:
    """Ein Backup zur Zeit, im Hintergrund. `status` liest die Oberfläche; `melden(status)` geht als Live-Meldung hinaus."""

    def __init__(self, bestand, katalog, melden=None):
        self.b, self.k = bestand, katalog
        self.melden = melden or (lambda s: None)
        self.status = {"laeuft": False}
        self._sperre = threading.Lock()
        self._stopp = threading.Event()
        self._thread = None

    def starten(self, ziel=None):
        """Prüft Ziel und Platz und startet; ValueError mit einem Satz für den Anwender, wenn es nicht geht."""
        with self._sperre:
            if self.status.get("laeuft"):
                raise ValueError("Es läuft schon ein Backup.")
            e = self.b.einstellungen()
            ziel = ziel_pruefen(self.b, self.k, ziel or e.get("backup_ziel"))
            plan = self._plan(e)
            gesamt = sum(x[2] for _, liste in plan for x in liste)
            frei = shutil.disk_usage(ziel).free
            # Erst schreiben, wenn die Platte es aufnehmen kann (Grösse ohne Packen gerechnet, dazu 5 % und 50 MB Luft).
            if frei < gesamt * 1.05 + 50 * 1024 * 1024:
                raise ValueError(f"Im Zielordner ist zu wenig Platz: nötig etwa {_mb(gesamt)}, frei {_mb(frei)}.")
            self._stopp.clear()
            self.status = {"laeuft": True, "ziel": ziel, "fertig": 0, "gesamt": sum(len(l) for _, l in plan), "bytes": 0,
                           "bytes_gesamt": gesamt, "beginn": time.time()}
            self._thread = threading.Thread(target=self._lauf, args=(ziel, plan, e), name="backup", daemon=True)
            self._thread.start()
        self.melden(self.status)
        return dict(self.status)

    def abbrechen(self):
        self._stopp.set()

    def warten(self, sekunden=None):
        t = self._thread
        if t:
            t.join(sekunden)
        return not (t and t.is_alive())

    def _plan(self, e):
        """[(zeile, [(quelle, ziel, grösse)])] der gewählten Zeilen, dazu „sonstiges“ für Unbekanntes im Bestand."""
        gewaehlt = e.get("backup_zeilen") or {}
        plan = []
        for z in ZEILEN:
            if z["id"] == "katalog":
                continue                     # die Datenbank kopiert der Lauf unter der Sperre, nicht nach diesem Plan
            if not (gewaehlt.get(z["id"], z["vorgabe"])):
                continue
            liste = _modelldateien(self.k) if z["id"] == "dateien" else [x for t in z["teile"] for x in _dateien_im_teil(self.b.wurzel, t)]
            plan.append((z["id"], liste))
        fremd = [x for t in unbekannt(self.b.wurzel) for x in _dateien_im_teil(self.b.wurzel, t)]
        if fremd:
            log.warning("Backup: unbekannte Teile im Bestand mitgenommen: %s", ", ".join(unbekannt(self.b.wurzel)))
            plan.append(("sonstiges", fremd))
        katalog = [x for t in _zeile("katalog")["teile"] for x in _dateien_im_teil(self.b.wurzel, t)]
        return [("katalog", katalog)] + plan

    def _lauf(self, ziel, plan, e):
        heute = datetime.date.today().isoformat()
        name = _freier_name(ziel, heute)
        arbeit = os.path.join(ziel, f".{name}.arbeit")
        t0 = time.monotonic()
        zaehler = {zid: {"dateien": 0, "bytes": 0} for zid, _ in plan}
        nicht_lesbar = []
        try:
            with zipfile.ZipFile(arbeit, "w", allowZip64=True) as z:
                # Die Datenbank unter der Sperre: kein anderer Thread schreibt, das ZIP enthält einen Stand und keine Mischung.
                with self.b.db.transaction():
                    # Die Liste erst hier: flatgraph ersetzt Dateien über os.replace, eine vorher gelesene Liste wäre schon veraltet.
                    katalog = [x for t in _zeile("katalog")["teile"] for x in _dateien_im_teil(self.b.wurzel, t)]
                    self.status["gesamt"] += len(katalog) - len(plan[0][1])
                    for quelle, rel, groesse in katalog:
                        self._eine(z, quelle, rel, groesse, zaehler["katalog"], nicht_lesbar)
                modelle = len(self.b.db.list_nodes(MODELL, readonly=True))
                wurzeln = [{"id": wid, "name": w.get("name"), "pfad": w.get("pfad")}
                           for wid, w in self.b.db.list_nodes(WURZEL, readonly=True).items()]
                for zid, liste in plan[1:]:
                    for quelle, rel, groesse in liste:
                        if self._stopp.is_set():
                            raise _Abbruch()
                        self._eine(z, quelle, rel, groesse, zaehler[zid], nicht_lesbar)
                inhalt = {"format": FORMAT, "partatlas": VERSION, "erstellt": datetime.datetime.now().isoformat(timespec="seconds"),
                          "modelle": modelle, "zeilen": zaehler, "ausgelassen": [x["id"] for x in ZEILEN if x["id"] not in zaehler],
                          "wurzeln": wurzeln, "nicht_lesbar": nicht_lesbar[:1000], "nicht_lesbar_n": len(nicht_lesbar)}
                z.writestr(INHALT, json.dumps(inhalt, ensure_ascii=False, indent=1))
            with open(arbeit, "rb+") as f:
                os.fsync(f.fileno())
            if os.path.exists(os.path.join(ziel, name)):        # nie überschreiben, auch wenn jemand den Namen inzwischen belegt hat
                name = _freier_name(ziel, heute)
            os.replace(arbeit, os.path.join(ziel, name))
            _ordner_fsync(ziel)
            bytes_zip = os.path.getsize(os.path.join(ziel, name))
            letztes = {"name": name, "ziel": ziel, "zeit": inhalt["erstellt"], "modelle": modelle, "bytes": bytes_zip,
                       "dateien": sum(x["dateien"] for x in zaehler.values()), "nicht_lesbar": len(nicht_lesbar)}
            self.b.einstellungen_setzen(backup_letztes=letztes)
            weg = _aufraeumen(ziel, e.get("backup_behalten", BEHALTEN), name)
            log.info("Backup %s: %d Dateien, %s in %.1f s%s", name, letztes["dateien"], _mb(bytes_zip), time.monotonic() - t0,
                     f", {len(nicht_lesbar)} nicht lesbar" if nicht_lesbar else "")
            self.status = {"laeuft": False, "ergebnis": "fertig", "letztes": letztes, "weggeraeumt": weg}
        except _Abbruch:
            _weg(arbeit)
            log.info("Backup abgebrochen")
            self.status = {"laeuft": False, "ergebnis": "abgebrochen"}
        except Exception as ex:          # Platte voll, Ordner weg …: melden, Arbeitsdatei weg, partAtlas läuft weiter
            _weg(arbeit)
            log.exception("Backup gescheitert")
            self.status = {"laeuft": False, "ergebnis": "fehler", "fehler": f"{type(ex).__name__}: {ex}"}
        self.melden(self.status)

    def _eine(self, z, quelle, rel, groesse, zaehler, nicht_lesbar):
        try:
            if not quelle:
                raise FileNotFoundError(rel)      # Ort ohne eingetragenen Ordner
            art = zipfile.ZIP_STORED if rel.lower().endswith(_GEPACKT) else zipfile.ZIP_DEFLATED
            z.write(quelle, rel, compress_type=art, compresslevel=1 if art == zipfile.ZIP_DEFLATED else None)
            zaehler["dateien"] += 1
            zaehler["bytes"] += groesse
        except OSError:                 # verschoben, gesperrt, Datei fehlt: weiter, im Inhaltsverzeichnis vermerkt
            nicht_lesbar.append(rel)
        s = self.status
        s["fertig"] += 1
        s["bytes"] += groesse
        jetzt = time.monotonic()
        if jetzt - s.get("_gemeldet", 0) > 0.3 or s["fertig"] == s["gesamt"]:
            s["_gemeldet"] = jetzt
            self.melden(s)


class _Abbruch(Exception):
    pass


def _freier_name(ziel, tag):
    """Hinter der höchsten Nummer des Tages, nie in einer Lücke: ein frei geräumter Name ohne Nummer sortierte das neue Backup als ältestes,
    und das Aufräumen gleich danach hielte die älteren (wie bei den Sicherungen)."""
    belegt = [int(m.group(2) or 1) for n in os.listdir(ziel) for m in [NAME.match(n.lstrip(".").removesuffix(".arbeit"))]
              if m and m.group(1) == tag]
    n = max(belegt, default=0) + 1
    return f"partAtlas-Backup-{tag}.zip" if n == 1 else f"partAtlas-Backup-{tag}-{n}.zip"


def _aufraeumen(ziel, behalten, neu):
    """Ältere Backups gehen, die `behalten` neuesten bleiben (bei mehreren GB je ZIP soll der Ordner nicht volllaufen). Nur Dateien mit
    unserem Namen, nie das eben geschriebene, nie weniger als eines."""
    weg = []
    for x in vorhandene(ziel)[max(1, int(behalten)):]:
        if x["name"] != neu:
            os.remove(os.path.join(ziel, x["name"]))
            weg.append(x["name"])
    return weg


def _weg(pfad):
    try:
        os.remove(pfad)
    except OSError:
        pass


def _ordner_fsync(pfad):
    try:
        fd = os.open(pfad, os.O_RDONLY)
    except OSError:
        return                          # Windows: Verzeichnisse lassen sich so nicht öffnen (flatgraph VERTRAG §2.2)
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _mb(n):
    return f"{n / 1e9:.1f} GB".replace(".", ",") if n >= 1e9 else f"{n / 1e6:.0f} MB" if n >= 1e6 else f"{max(n, 0) / 1e3:.0f} KB"
