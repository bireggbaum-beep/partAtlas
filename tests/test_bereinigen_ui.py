"""Bereinigen: jede Ansicht sagt oben, was man sieht und was die Aktionen tun (Anwender, 16.10.2026: „damit man klar weiss, was man sieht
und tut“). Geprüft über alle Einträge der Seitenleiste — kommt eine neue Ansicht ohne Beschreibung dazu, fällt die Prüfung.
Dazu: bei gleicher Datei an mehreren Orten zeigt der Inspektor je Ort den Weg in den Ordner (dort löscht man eine Kopie)."""
import glob
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

import muster
from muster import check

HIER = os.path.dirname(os.path.abspath(__file__))


def chromium():
    if os.environ.get("PARTATLAS_CHROMIUM"):
        return os.environ["PARTATLAS_CHROMIUM"]
    treffer = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
    return treffer[-1] if treffer else None


def abfrage(port, pfad, daten=None, methode=None):
    r = urllib.request.Request(f"http://127.0.0.1:{port}{pfad}", method=methode or ("POST" if daten is not None else "GET"),
                               data=json.dumps(daten).encode() if daten is not None else None, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r).read() or b"null")


def warte(bedingung, sekunden=20):
    ende = time.time() + sekunden
    while time.time() < ende:
        try:
            if bedingung():
                return True
        except OSError:                            # Server noch nicht offen
            pass
        time.sleep(0.2)
    return False


if __name__ == "__main__":
    muster.zeitgrenze(120)
    from playwright.sync_api import sync_playwright
    tmp = tempfile.mkdtemp()
    samm = os.path.join(tmp, "3D")
    for d in ("A", "B"):
        os.makedirs(os.path.join(samm, d))
    muster.stl_binaer(os.path.join(samm, "A", "Halter.stl"), 10, 20, 30)
    shutil.copy(os.path.join(samm, "A", "Halter.stl"), os.path.join(samm, "B", "Halter.stl"))      # gleiche Datei, zwei Orte
    muster.stl_binaer(os.path.join(samm, "Arm.stl"), 12, 20, 30)
    with open(os.path.join(samm, "kaputt.3mf"), "wb") as f:
        f.write(b"kein zip")
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    umgebung = {**os.environ, "PARTATLAS_BESTAND": os.path.join(tmp, "bestand"), "PARTATLAS_PORT": str(port),
                "PYTHONPATH": os.environ.get("PARTATLAS_QUELLE") or os.path.join(HIER, "..")}
    server = subprocess.Popen([sys.executable, "-m", "partatlas"], env=umgebung, cwd=tmp, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        warte(lambda: abfrage(port, "/api/zaehler") is not None)
        abfrage(port, "/api/wurzeln", {"pfad": samm})
        warte(lambda: abfrage(port, "/api/zaehler").get("unlesbar") == 1 and abfrage(port, "/api/zaehler").get("duplikate") == 1)
        arm = next(x["id"] for x in abfrage(port, "/api/modelle") if x["name"] == "Arm")
        abfrage(port, f"/api/modelle/{arm}", {"archiv": True}, "PATCH")
        halter = next(x["id"] for x in abfrage(port, "/api/modelle") if x["name"] == "Halter")
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chromium())
            pg = b.new_page()
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_selector('[data-rail="bereinigen"]')
            pg.click('[data-rail="bereinigen"]')
            ohne = []
            ansichten = pg.eval_on_selector_all('.sektion[data-sektion="bereinigen"] [data-ansicht]', "l => l.map((x) => x.dataset.ansicht)")
            for a in ansichten:
                pg.click(f'[data-ansicht="{a}"]')
                time.sleep(1.2)                    # Liste geholt und gezeichnet; die Live-Verbindung lässt kein „networkidle“ zu
                text = pg.evaluate("""() => ['#pk-leiste', '#leer', '#aufraeumen .af-kopf']
                    .map((s) => document.querySelector(s)).filter((e) => e && e.offsetParent !== null)
                    .map((e) => e.innerText.trim()).join(' ')""")
                if len(text) < 30:
                    ohne.append(a)
            check(f"Jede Ansicht unter Bereinigen ({len(ansichten)}) erklärt oben, was man sieht — ohne: {ohne or 'keine'}",
                  len(ansichten) >= 6 and not ohne)
            pg.click('[data-ansicht="duplikate"]')
            pg.wait_for_selector(f'.karte[data-id="{halter}"]', timeout=10000)
            pg.click(f'.karte[data-id="{halter}"]')
            pg.wait_for_function(f"document.querySelector('#inspektor')?.dataset.id === '{halter}'", timeout=10000)
            orte = pg.eval_on_selector_all("[data-ort-zeigen]", "l => l.map((x) => x.dataset.ortZeigen)")
            check("Gleiche Datei: der Inspektor zeigt beide Orte, je mit dem Weg in den Ordner",
                  sorted(os.path.basename(os.path.dirname(o)) for o in orte) == ["A", "B"])
            b.close()
    finally:
        server.terminate()
        server.wait(10)
    muster.ende()
