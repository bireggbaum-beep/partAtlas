"""Ein Bestand, ein partAtlas: ein zweiter Start öffnet den laufenden im Browser und beendet sich (Vorbild: 3MF Katalog Manager 0.16, „a second
launch brings its window to the front“; Anwender 2.11.2026).

Die Sperre von flatgraph (VERTRAG §3.2) lässt ohnehin nur einen Prozess an den Bestand. Ohne diese Datei blieb ein zweiter Start auf einem anderen
Port aber als leere Seite mit „BestandBelegt …“ stehen (Abschusstest Doppelstart, 30.10.2026). `laeuft.json` im Bestand sagt, wo der laufende
antwortet; geglaubt wird ihr nur, wenn dort wirklich ein partAtlas mit demselben Bestand antwortet — eine liegengebliebene Datei (kill -9, Absturz)
schadet so nicht. start.sh und start.bat prüfen den gleichen Port schon selbst; dies hier gilt für jeden Starter und jeden Port."""
import json
import logging
import os
import urllib.request
import webbrowser

from .dateien import schreibe_atomar

log = logging.getLogger("partatlas")
DATEI = "laeuft.json"


def _gleich(a, b):
    return os.path.realpath(a) == os.path.realpath(b)


def laufender(ort):
    """Die Adresse des partAtlas, der diesen Bestand gerade offen hat, oder None."""
    try:
        with open(os.path.join(ort, DATEI), encoding="utf-8") as f:
            port = int(json.load(f)["port"])
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/stand", timeout=3) as r:
            stand = json.load(r)
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return f"http://127.0.0.1:{port}" if _gleich(stand.get("bestand") or "", ort) else None


def eintragen(ort, port, version):
    try:
        schreibe_atomar(os.path.join(ort, DATEI), json.dumps({"port": port, "pid": os.getpid(), "version": version}).encode("utf-8"))
    except OSError as e:
        log.warning("Nicht vermerkt, wo partAtlas läuft (%s): ein zweiter Start findet es dann nicht", e)


def austragen(ort):
    """Nur die eigene Eintragung entfernen — ein anderer Prozess könnte sie inzwischen überschrieben haben."""
    pfad = os.path.join(ort, DATEI)
    try:
        with open(pfad, encoding="utf-8") as f:
            if json.load(f).get("pid") == os.getpid():
                os.remove(pfad)
    except (OSError, ValueError):
        pass


def dorthin(url):
    """Den laufenden partAtlas zeigen. PARTATLAS_KEIN_BROWSER (Tests): nur melden."""
    print(f"partAtlas läuft schon mit diesem Bestand: {url}")
    log.info("Zweiter Start: partAtlas läuft schon mit diesem Bestand (%s); dieser Start endet", url)
    if not os.environ.get("PARTATLAS_KEIN_BROWSER"):
        try:
            webbrowser.open(url)
        except Exception:           # ohne Desktop kein Browser — die Zeile oben sagt, wohin
            pass
