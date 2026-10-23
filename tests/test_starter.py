"""Starter-Betrieb (PARTATLAS_STARTER=1, die gepackte Einzeldatei): öffnet den Standardbrowser, beendet sich, wenn keine Seite mehr offen ist,
und öffnet bei einem schon laufenden partAtlas nur den Browser. Ohne den Starter-Betrieb läuft der Server weiter (python -m partatlas)."""
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

import muster
from muster import check

HIER = os.path.dirname(os.path.abspath(__file__))
QUELLE = os.environ.get("PARTATLAS_QUELLE") or os.path.join(HIER, "..")


def freier_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def warte(bedingung, sekunden):
    ende = time.time() + sekunden
    while time.time() < ende:
        try:
            if bedingung():
                return True
        except OSError:
            pass
        time.sleep(0.2)
    return False


def starte(tmp, port, starter=True, **extra):
    umgebung = {**os.environ, "PARTATLAS_BESTAND": os.path.join(tmp, "bestand"), "PARTATLAS_PORT": str(port), "PYTHONPATH": QUELLE,
                "BROWSER": f"{tmp}/browser.sh %s", **extra}
    if starter:
        umgebung["PARTATLAS_STARTER"] = "1"
    return subprocess.Popen([sys.executable, "-m", "partatlas"], env=umgebung, cwd=tmp, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def da(port):
    return urllib.request.urlopen(f"http://127.0.0.1:{port}/api/stand", timeout=2).status == 200


if __name__ == "__main__":
    muster.zeitgrenze(150)
    tmp = tempfile.mkdtemp()
    aufrufe = os.path.join(tmp, "aufrufe.txt")
    with open(os.path.join(tmp, "browser.sh"), "w") as f:
        f.write(f'#!/bin/sh\necho "$1" >> {aufrufe}\n')
    os.chmod(os.path.join(tmp, "browser.sh"), 0o755)
    zeilen = lambda: open(aufrufe).read().split() if os.path.exists(aufrufe) else []
    prozesse = []
    try:
        # -- Server läuft, Browser wird geöffnet, mit Besucher bleibt er, ohne Besucher beendet er sich
        port = freier_port()
        p = starte(tmp, port, PARTATLAS_ERSTER_BESUCH="4", PARTATLAS_NACHFRIST="3")
        prozesse.append(p)
        check("Der Server startet", warte(lambda: da(port), 20))
        check("Der Standardbrowser wird mit der Adresse geöffnet", warte(lambda: zeilen() == [f"http://127.0.0.1:{port}/"], 5))
        live = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/live", timeout=5)
        live.read(1)
        time.sleep(8)                                   # länger als der erste Besuch und die Nachfrist zusammen
        check("Mit einer offenen Seite läuft der Server weiter", p.poll() is None)
        live.close()
        check("Die letzte Seite geht zu: der Server beendet sich nach der Nachfrist", warte(lambda: p.poll() is not None, 15))
        check("… und endet ohne Fehler", p.poll() == 0)

        # -- Kommt nie ein Browser, endet er nach dem ersten Besuch
        port = freier_port()
        p = starte(tmp, port, PARTATLAS_ERSTER_BESUCH="3", PARTATLAS_NACHFRIST="3")
        prozesse.append(p)
        check("Ohne jeden Besucher endet der Server nach der Wartezeit", warte(lambda: p.poll() is not None, 25))

        # -- Läuft schon einer, wird nur der Browser geöffnet
        port = freier_port()
        a = starte(tmp, port, PARTATLAS_ERSTER_BESUCH="60", PARTATLAS_NACHFRIST="60")
        prozesse.append(a)
        warte(lambda: da(port), 20)
        vorher = len(zeilen())
        b = starte(tmp, port, PARTATLAS_ERSTER_BESUCH="60", PARTATLAS_NACHFRIST="60")
        prozesse.append(b)
        check("Zweiter Start bei laufendem partAtlas: nur der Browser wird geöffnet, der Start endet gleich",
              warte(lambda: b.poll() == 0, 15) and len(zeilen()) == vorher + 1 and a.poll() is None)

        # -- Ohne Starter-Betrieb bleibt der Server (python -m partatlas)
        port = freier_port()
        c = starte(tmp, port, starter=False)
        prozesse.append(c)
        warte(lambda: da(port), 20)
        n = len(zeilen())
        time.sleep(6)
        check("Ohne Starter-Betrieb: kein Browser, kein Beenden", c.poll() is None and len(zeilen()) == n)
    finally:
        for p in prozesse:
            if p.poll() is None:
                p.terminate()
        for p in prozesse:
            try:
                p.wait(10)
            except subprocess.TimeoutExpired:
                p.kill()
    muster.ende()
