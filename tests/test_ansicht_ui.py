"""Wechsel der Ansicht (Bereinigen › Duplikate, Papierkorb …) holt nur die Liste neu, nicht Zähler, Ordnerbaum, Tags und Baugruppen-Vorschläge.

Die Vorschläge rechnen über alle Modelle; bei 8 600 Modellen unter Windows kostete jeder Klick dadurch mehrere Sekunden (Anwender, 12.10.2026)."""
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


def abfrage(port, pfad, daten=None):
    r = urllib.request.Request(f"http://127.0.0.1:{port}{pfad}", method="POST" if daten is not None else "GET",
                               data=json.dumps(daten).encode() if daten is not None else None, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r).read() or b"null")


if __name__ == "__main__":
    muster.zeitgrenze(90)
    from playwright.sync_api import sync_playwright
    tmp = tempfile.mkdtemp()
    samm = os.path.join(tmp, "3D")
    os.makedirs(samm)
    muster.stl_binaer(os.path.join(samm, "Halter.stl"), 10, 20, 30)
    muster.stl_binaer(os.path.join(samm, "Deckel.stl"), 12, 20, 30)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    umgebung = {**os.environ, "PARTATLAS_BESTAND": os.path.join(tmp, "bestand"), "PARTATLAS_PORT": str(port),
                "PYTHONPATH": os.environ.get("PARTATLAS_QUELLE") or os.path.join(HIER, "..")}
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
            if len(abfrage(port, "/api/modelle")) == 2:
                break
            time.sleep(0.2)
        mid = abfrage(port, "/api/modelle")[0]["id"]
        abfrage(port, f"/api/modelle/{mid}/loeschen", {})
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chromium())
            pg = b.new_page()
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_function("document.querySelector('#z-alle') && document.querySelector('#z-alle').textContent.trim() === '1'")
            pg.evaluate("""() => { window.__a = []; const o = window.fetch;
                window.fetch = (...a) => { window.__a.push(String(a[0]).split('?')[0]); return o(...a); }; }""")
            pg.evaluate("document.querySelector('[data-ansicht=\"papierkorb\"]').click()")
            pg.wait_for_selector(".pk-zeile", state="attached", timeout=10000)
            pg.wait_for_function("document.querySelectorAll('.karte').length === 1", timeout=10000)
            check("Papierkorb zeigt das entfernte Modell und die Hinweiszeile", pg.locator(".karte").count() == 1)
            pg.evaluate("document.querySelector('[data-ansicht=\"duplikate\"]').click()")
            pg.wait_for_function("document.querySelectorAll('.karte').length === 0", timeout=10000)
            time.sleep(1)
            geholt = set(pg.evaluate("window.__a"))
            # „Neu in dieser Fassung“ fragt einmal beim Start (0.95.6) und kommt zeitlich mal vor, mal nach dem Wechsel — kein Teil davon.
            geholt.discard("/api/neuigkeiten")
            check("Beim Wechsel wird nur die Liste geholt (kein Zähler, Ordnerbaum, Tags, keine Baugruppen-Vorschläge)",
                  geholt <= {"/api/modelle", "/api/papierkorb/weitere"})
            check("Die Hervorhebung wechselt mit", pg.evaluate("document.querySelector('[data-ansicht=\"duplikate\"]').classList.contains('aktiv')")
                  and not pg.evaluate("document.querySelector('[data-ansicht=\"papierkorb\"]').classList.contains('aktiv')"))
            b.close()
    finally:
        server.terminate()
        server.wait(10)
    muster.ende()
