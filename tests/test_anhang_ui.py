"""Ein Anhang, den der Browser nicht selbst zeigt (DXF, CorelDRAW …), startet beim Anklicken des Namens im Programm des Rechners — ohne Download
(Tester, 13.10.2026: zehn Klicks, zehn Dateien im Downloadordner). Was der Browser zeigt (PDF, Bilder, SVG, XHTML) geht in einen neuen Tab — SVG und
XHTML in der Sandbox: ein Skript darin läuft dort nicht."""
import glob
import json
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


def chromium():
    if os.environ.get("PARTATLAS_CHROMIUM"):
        return os.environ["PARTATLAS_CHROMIUM"]
    treffer = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
    return treffer[-1] if treffer else None


def abfrage(port, pfad, daten=None, roh=None, methode=None):
    r = urllib.request.Request(f"http://127.0.0.1:{port}{pfad}", method=methode or ("POST" if daten is not None or roh is not None else "GET"),
                               data=roh if roh is not None else (json.dumps(daten).encode() if daten is not None else None),
                               headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r).read() or b"null")


if __name__ == "__main__":
    muster.zeitgrenze(90)
    from playwright.sync_api import sync_playwright
    tmp = tempfile.mkdtemp()
    samm = os.path.join(tmp, "3D")
    os.makedirs(samm)
    muster.stl_binaer(os.path.join(samm, "Halter.stl"), 10, 20, 30)
    attrappen, protokoll = os.path.join(tmp, "bin"), os.path.join(tmp, "geoeffnet.txt")
    os.makedirs(attrappen)
    with open(os.path.join(attrappen, "xdg-open"), "w") as f:
        f.write(f'#!/bin/sh\necho "$1" >> "{protokoll}"\n')
    os.chmod(os.path.join(attrappen, "xdg-open"), 0o755)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    umgebung = {**os.environ, "PARTATLAS_BESTAND": os.path.join(tmp, "bestand"), "PARTATLAS_PORT": str(port),
                "PYTHONPATH": os.environ.get("PARTATLAS_QUELLE") or os.path.join(HIER, ".."), "PATH": attrappen + os.pathsep + os.environ["PATH"]}
    server = subprocess.Popen([sys.executable, "-m", "partatlas"], env=umgebung, cwd=tmp, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                abfrage(port, "/api/zaehler")
                break
            except OSError:
                time.sleep(0.1)
        abfrage(port, "/api/wurzeln", {"pfad": samm})
        for _ in range(200):
            if abfrage(port, "/api/modelle"):
                break
            time.sleep(0.2)
        mid = abfrage(port, "/api/modelle")[0]["id"]
        abfrage(port, f"/api/anhaenge/modell/{mid}?name=Zeichnung.dxf", roh=b"0\nSECTION\n")
        abfrage(port, f"/api/anhaenge/modell/{mid}?name=Logo.svg", roh=b'<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><rect width="40" height="40"/>'
                b'<script>window.__ausgefuehrt = 1; document.title = "skript lief";</script></svg>')
        abfrage(port, f"/api/anhaenge/modell/{mid}?name=Seite.xhtml", roh=b'<html xmlns="http://www.w3.org/1999/xhtml"><head><title>x</title></head><body><p>Hallo</p>'
                b'<script>window.__ausgefuehrt = 1;</script></body></html>')
        abfrage(port, f"/api/anhaenge/modell/{mid}?name=Anleitung.pdf", roh=b"%PDF-1.4\n%%EOF\n")
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chromium())
            pg = b.new_page()
            geladen = []
            pg.on("download", lambda d: geladen.append(d.suggested_filename))
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_selector(".karte", timeout=15000)
            pg.click(".karte")
            pg.wait_for_selector(".anh-zeile", timeout=10000)
            dxf = pg.locator(".anh-zeile", has_text="Zeichnung.dxf").locator(".anh-name")
            for _ in range(3):
                dxf.click()
                time.sleep(0.4)
            time.sleep(1)
            aufrufe = open(protokoll).read().split() if os.path.exists(protokoll) else []
            check("Der Name einer DXF-Datei startet sie im Programm des Rechners (dreimal angeklickt, dreimal gestartet)", len(aufrufe) == 3)
            check("…aus einer Kopie in arbeit/geoeffnet, jedes Mal dieselbe Datei", len(set(aufrufe)) == 1 and "geoeffnet" in aufrufe[0])
            check("Kein Download in den Downloadordner", geladen == [])
            pdf = pg.locator(".anh-zeile", has_text="Anleitung.pdf").locator(".anh-name")
            check("Ein PDF öffnet weiter in einem neuen Tab des Browsers", pdf.get_attribute("target") == "_blank")
            for name, was in (("Logo.svg", "SVG"), ("Seite.xhtml", "XHTML")):
                link = pg.locator(".anh-zeile", has_text=name).locator(".anh-name")
                with pg.context.expect_page() as neu:
                    link.click()
                tab = neu.value
                tab.wait_for_load_state()
                check(f"{was} öffnet im neuen Tab, wird gezeigt und kein Download", tab.url.startswith(f"http://127.0.0.1:{port}/api/anhaenge/") and geladen == [])
                check(f"{was}: ein Skript darin läuft nicht (Sandbox)", tab.evaluate("window.__ausgefuehrt") is None and tab.title() != "skript lief")
                tab.close()
            b.close()
    finally:
        server.terminate()
        server.wait(10)
    muster.ende()
