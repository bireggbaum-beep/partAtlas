"""Die Meldung unten verschwindet nie, während man sie benutzt: Maus darüber, Fokus auf einem Knopf darin oder Fenster im Hintergrund halten die
Zeit an; danach bleibt sie noch mindestens 2 s. Esc schliesst sie. Eine Meldung, die unter der Maus verschwand, hält die nächste nicht fest."""
import os
import socket
import subprocess
import sys
import tempfile
import time

import muster
from muster import check
from test_bereinigen_ui import abfrage, chromium, warte

HIER = os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    muster.zeitgrenze(90)
    from playwright.sync_api import sync_playwright
    tmp = tempfile.mkdtemp()
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    umgebung = {**os.environ, "PARTATLAS_BESTAND": os.path.join(tmp, "bestand"), "PARTATLAS_PORT": str(port),
                "PYTHONPATH": os.environ.get("PARTATLAS_QUELLE") or os.path.join(HIER, "..")}
    server = subprocess.Popen([sys.executable, "-m", "partatlas"], env=umgebung, cwd=tmp, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        warte(lambda: abfrage(port, "/api/zaehler") is not None)
        abfrage(port, "/api/neuigkeiten/gesehen", {})
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chromium())
            pg = b.new_page(viewport={"width": 1200, "height": 800})
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_selector("#toast", state="attached")
            time.sleep(1)
            sichtbar = lambda: pg.evaluate("!document.querySelector('#toast').hidden")
            zeige = lambda dauer, knopf=False: pg.evaluate(f"toast('Probe', {{ dauer: {dauer}, aktionen: {'[[\"Rückgängig\", () => { window.__zurueck = 1; }]]' if knopf else '[]'} }})")
            weg = lambda: pg.mouse.move(5, 5)

            weg(); zeige(600); time.sleep(1.2)
            check("Ohne Maus: die Meldung verschwindet pünktlich", not sichtbar())

            zeige(600, True)
            box = pg.locator("#toast").bounding_box()
            pg.mouse.move(box["x"] + 10, box["y"] + box["height"] / 2)
            time.sleep(1.5)
            check("Maus darüber: die Zeit hält an, die Meldung bleibt", sichtbar())
            weg(); time.sleep(1.3)
            check("… nach dem Wegfahren bleibt sie noch eine Weile (mindestens 2 s), statt sofort zu verschwinden", sichtbar())
            time.sleep(1.3)
            check("… und verschwindet dann", not sichtbar())

            zeige(600, True)
            pg.focus("#toast button")
            time.sleep(1.3)
            check("Fokus auf „Rückgängig“ (Tastatur): sie bleibt", sichtbar())
            pg.keyboard.press("Escape")
            check("Esc schliesst sie", not sichtbar())

            weg(); zeige(600)
            pg.evaluate("Object.defineProperty(document, 'hidden', { get: () => true, configurable: true }); document.dispatchEvent(new Event('visibilitychange'))")
            time.sleep(1.3)
            check("Fenster im Hintergrund (man ist kurz im Slicer): sie bleibt", sichtbar())
            pg.evaluate("Object.defineProperty(document, 'hidden', { get: () => false, configurable: true }); document.dispatchEvent(new Event('visibilitychange'))")
            time.sleep(2.6)
            check("… zurück im Fenster: sie verschwindet nach der Restzeit", not sichtbar())

            # Der Fallstrick: die Meldung verschwindet unter der Maus (Klick auf „Rückgängig“), ein „Maus verlässt“ kommt nicht in jedem Browser.
            # Nachgestellt ohne die Hilfe von Chromium: „Maus darüber“ von Hand, der Klick ohne Maus, dann eine neue Meldung abseits der Maus.
            weg(); zeige(5000, True)
            pg.evaluate("document.querySelector('#toast').dispatchEvent(new MouseEvent('mouseenter')); document.querySelector('#toast button').click()")
            zeige(600); time.sleep(1.2)
            check("Nach einem Klick in der Meldung hält die nächste nicht für immer fest", not sichtbar() and pg.evaluate("window.__zurueck") == 1)
            b.close()
    finally:
        server.terminate()
        server.wait(timeout=20)
    muster.ende()
