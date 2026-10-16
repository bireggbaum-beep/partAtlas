"""Ordner im Baum wie im Dateimanager: Umbenennen per Rechtsklick oder F2 direkt im Baum, Enter übernimmt, Esc bricht ab, eine Ablehnung
lässt das Feld offen; Rückgängig mit Strg+Z. Die Regeln selbst prüft test_ordner."""
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
    muster.zeitgrenze(120)
    from playwright.sync_api import sync_playwright
    tmp = tempfile.mkdtemp()
    samm = os.path.join(tmp, "3D")
    os.makedirs(os.path.join(samm, "Projekt"))
    muster.stl_binaer(os.path.join(samm, "Projekt", "Teil.stl"), 10, 20, 30)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    umgebung = {**os.environ, "PARTATLAS_BESTAND": os.path.join(tmp, "bestand"), "PARTATLAS_PORT": str(port),
                "PYTHONPATH": os.environ.get("PARTATLAS_QUELLE") or os.path.join(HIER, "..")}
    server = subprocess.Popen([sys.executable, "-m", "partatlas"], env=umgebung, cwd=tmp, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        warte(lambda: abfrage(port, "/api/zaehler") is not None)
        wid = abfrage(port, "/api/wurzeln", {"pfad": samm})["id"]
        warte(lambda: len(abfrage(port, "/api/modelle")) == 1)
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chromium())
            pg = b.new_page()
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_selector(f'.eintrag[data-wurzel="{wid}"]')
            if not pg.locator(f'.eintrag[data-ordner="{wid}/Projekt"]').count():
                pg.click(f'[data-klappe="{wid}"]')
            ordner = f'.eintrag[data-ordner="{wid}/Projekt"]'
            pg.wait_for_selector(ordner)

            pg.click(ordner, button="right")
            pg.click('[data-km="ordner-umbenennen"]')
            feld = pg.locator(".baum-name")
            check("Rechtsklick › Umbenennen: Feld im Baum, Name markiert", feld.count() == 1 and feld.input_value() == "Projekt"
                  and pg.evaluate("document.activeElement.selectionStart === 0 && document.activeElement.selectionEnd === 7"))
            feld.fill("Neu")
            feld.press("Enter")
            warte(lambda: os.path.isdir(os.path.join(samm, "Neu")), 10)
            pg.wait_for_selector(f'.eintrag[data-ordner="{wid}/Neu"]', timeout=10000)
            check("Enter übernimmt: auf der Platte umbenannt, im Baum der neue Name, Meldung mit „Rückgängig“",
                  os.path.isdir(os.path.join(samm, "Neu")) and "Rückgängig" in pg.inner_text("#toast"))

            pg.evaluate("document.activeElement?.blur()")        # Strg+Z ausserhalb eines Feldes, wie im Explorer
            pg.keyboard.press("Control+z")
            warte(lambda: os.path.isdir(os.path.join(samm, "Projekt")), 10)
            check("Strg+Z macht das Umbenennen rückgängig", os.path.isdir(os.path.join(samm, "Projekt")) and not os.path.exists(os.path.join(samm, "Neu")))

            pg.wait_for_selector(ordner, timeout=10000)
            pg.focus(ordner)
            pg.keyboard.press("F2")
            pg.wait_for_selector(".baum-name")
            pg.locator(".baum-name").fill("a:b")
            pg.locator(".baum-name").press("Enter")
            pg.wait_for_selector(".baum-name", timeout=5000)
            time.sleep(0.5)
            check("F2 auf dem Ordner; verbotenes Zeichen: Meldung, das Feld bleibt offen mit dem Getippten",
                  pg.locator(".baum-name").input_value() == "a:b" and "darf keines dieser Zeichen" in pg.inner_text("#toast")
                  and os.path.isdir(os.path.join(samm, "Projekt")))
            pg.locator(".baum-name").press("Escape")
            pg.wait_for_selector(ordner, timeout=5000)
            check("Esc bricht ab: nichts geändert", pg.locator(".baum-name").count() == 0 and os.path.isdir(os.path.join(samm, "Projekt")))
            b.close()
    finally:
        server.terminate()
        server.wait(10)
    muster.ende()
