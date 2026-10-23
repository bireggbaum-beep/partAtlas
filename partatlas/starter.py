"""Starter-Betrieb (die einzelne Datei zum Anklicken): partAtlas öffnet nach dem Start den Standardbrowser und beendet sich, wenn
niemand mehr hinsieht. `python -m partatlas` bleibt unverändert: dort läuft der Server, bis man ihn beendet.

Wann „niemand mehr hinsieht“: jede offene Seite hält eine Live-Verbindung (/api/live). Ein Tab, der zugeht, beendet sie; ein Neuladen
braucht ein, zwei Sekunden und darf nichts beenden — darum die Nachfrist."""
import json
import logging
import socket
import threading
import time
import urllib.request
import webbrowser

log = logging.getLogger("partatlas")

ERSTER_BESUCH_S = 120      # so lange wartet der Server auf den ersten Browser
NACHFRIST_S = 45           # so lange darf nach dem letzten geschlossenen Tab niemand da sein


def laeuft_partatlas(port):
    """Antwortet unter dem Port schon ein partAtlas? Dann gibt es nichts zu starten, nur zu öffnen."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/stand", timeout=1.5) as r:
            return "version" in json.loads(r.read() or b"{}")
    except (OSError, ValueError):
        return False


def port_frei(port):
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def freier_port(wunsch):
    """Der gewünschte Port, sonst der nächste freie: ein anderes Programm darf partAtlas nicht den Start verderben."""
    for p in range(wunsch, wunsch + 20):
        if port_frei(p):
            return p
    return wunsch


def browser_oeffnen(url):
    """Standardbrowser des Systems (Linux: xdg-open bzw. $BROWSER, Windows: der Standardbrowser). Ohne Browser bleibt die Adresse im Protokoll."""
    try:
        if webbrowser.open(url):
            log.info("Browser geöffnet: %s", url)
            return True
    except Exception as e:
        log.warning("Browser liess sich nicht öffnen: %s", e)
    log.warning("Kein Browser gefunden — die Adresse im Browser selbst öffnen: %s", url)
    return False


def beenden_wenn_leer(server, app, erster_besuch=ERSTER_BESUCH_S, nachfrist=NACHFRIST_S):
    """Hintergrundfaden: beendet den Server, wenn keine Seite mehr verbunden ist. Solange das Einlesen oder die Hintergrundarbeit läuft,
    bleibt er — eine Arbeit, die der Anwender angestossen hat, bricht kein geschlossener Tab ab."""
    def beschaeftigt():
        try:
            s = app.state.zustand["scanner"]
            return bool(s.status.get("laeuft") or s.hat_offenes())
        except Exception:
            return False

    def schleife():
        t0 = time.monotonic()
        gesehen = False
        leer_seit = None
        while not server.should_exit:
            time.sleep(1)
            n = app.state.verteiler.verbunden()
            if n:
                gesehen, leer_seit = True, None
                continue
            if beschaeftigt():
                leer_seit = None
                continue
            if not gesehen:
                if time.monotonic() - t0 > erster_besuch:
                    log.info("Seit %d s hat sich kein Browser verbunden — partAtlas beendet sich.", erster_besuch)
                    break
                continue
            leer_seit = leer_seit or time.monotonic()
            if time.monotonic() - leer_seit > nachfrist:
                log.info("Keine Seite mehr offen (seit %d s) — partAtlas beendet sich.", nachfrist)
                break
        app.state.verteiler.beenden()
        server.should_exit = True

    threading.Thread(target=schleife, name="beenden-wenn-leer", daemon=True).start()
