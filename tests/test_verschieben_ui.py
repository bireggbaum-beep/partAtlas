"""Modelle verschieben: die Meldung nennt das Ziel und hat „Rückgängig“, Strg+Z geht ebenso; beim Ziehen mehrerer sagt das Ziehbild, wie viele mitgehen."""
import os
import socket
import subprocess
import sys
import tempfile

import muster
from muster import check
from test_bereinigen_ui import abfrage, chromium, warte

HIER = os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    muster.zeitgrenze(90)
    from playwright.sync_api import sync_playwright
    tmp = tempfile.mkdtemp()
    samm = os.path.join(tmp, "3D")
    os.makedirs(os.path.join(samm, "Ziel"))
    muster.stl_binaer(os.path.join(samm, "Alpha.stl"), 10, 20, 30)
    muster.stl_binaer(os.path.join(samm, "Beta.stl"), 11, 20, 30)
    muster.stl_binaer(os.path.join(samm, "Ziel", "Gamma.stl"), 12, 20, 30)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    umgebung = {**os.environ, "PARTATLAS_BESTAND": os.path.join(tmp, "bestand"), "PARTATLAS_PORT": str(port),
                "PYTHONPATH": os.environ.get("PARTATLAS_QUELLE") or os.path.join(HIER, "..")}
    server = subprocess.Popen([sys.executable, "-m", "partatlas"], env=umgebung, cwd=tmp, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        warte(lambda: abfrage(port, "/api/zaehler") is not None)
        abfrage(port, "/api/neuigkeiten/gesehen", {})
        abfrage(port, "/api/wurzeln", {"pfad": samm})
        warte(lambda: len(abfrage(port, "/api/modelle")) == 3)
        im_ziel = lambda n: os.path.exists(os.path.join(samm, "Ziel", n + ".stl"))
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chromium())
            pg = b.new_page(viewport={"width": 1400, "height": 800})
            # Was das Ziehbild zeigt, festhalten (es verschwindet gleich nach dem Ziehbeginn wieder)
            pg.add_init_script("""(() => { const o = DataTransfer.prototype.setDragImage;
              DataTransfer.prototype.setDragImage = function (el, x, y) { window.__ziehbild = el.textContent; return o.call(this, el, x, y); }; })()""")
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_selector(".karte")
            toast = lambda: pg.inner_text("#toast")

            # Menü: ein Modell
            pg.click(".karte:has-text('Alpha')")
            pg.click("#inspektor #mehr-knopf")
            pg.click("#inspektor #verschieben")
            pg.wait_for_selector("#dialog[open] #ordner-ziel")
            wert = pg.eval_on_selector("#ordner-ziel", "s => [...s.options].find((o) => o.textContent.includes('Ziel')).value")
            pg.select_option("#ordner-ziel", wert)
            pg.click("#dialog[open] button[value='ja']")
            pg.wait_for_function("!document.querySelector('#toast').hidden && document.querySelector('#toast').textContent.includes('verschoben nach')")
            check("Verschieben über das Menü: die Meldung nennt Modell und Ziel und hat „Rückgängig“",
                  "„Alpha.stl“ verschoben nach „Ziel“" in toast() and pg.locator("#toast button", has_text="Rückgängig").count() == 1 and im_ziel("Alpha"))
            pg.click("#toast button:has-text('Rückgängig')")
            warte(lambda: os.path.exists(os.path.join(samm, "Alpha.stl")))
            check("„Rückgängig“ legt die Datei zurück an ihren alten Ort", os.path.exists(os.path.join(samm, "Alpha.stl")) and not im_ziel("Alpha"))

            # Ziehen: zwei gewählte auf den Ordner
            pg.wait_for_selector(".karte:has-text('Alpha')")
            pg.click(".karte:has-text('Alpha')")
            pg.click(".karte:has-text('Beta')", modifiers=["Control"])
            if not pg.locator(".eintrag[data-ordner$='/Ziel']").count():
                pg.click("[data-wurzel] [data-klappe]")          # den Bibliotheksordner aufklappen, wie ein Anwender
            pg.wait_for_selector(".eintrag[data-ordner$='/Ziel']")
            pg.drag_and_drop(".karte:has-text('Alpha')", ".eintrag[data-ordner$='/Ziel']")
            pg.wait_for_function("!document.querySelector('#toast').hidden && document.querySelector('#toast').textContent.includes('2 Modelle verschoben')")
            check("Beim Ziehen mehrerer sagt das Ziehbild, wie viele mitgehen", pg.evaluate("window.__ziehbild") == "2 Modelle")
            check("Beide gehen mit, die Meldung nennt die Anzahl und das Ziel", "2 Modelle verschoben nach „Ziel“" in toast() and im_ziel("Alpha") and im_ziel("Beta"))
            pg.click("#raster")                               # Fokus weg vom Baum, wie nach einem echten Ziehen
            pg.keyboard.press("Control+z")
            warte(lambda: os.path.exists(os.path.join(samm, "Alpha.stl")) and os.path.exists(os.path.join(samm, "Beta.stl")))
            check("Strg+Z holt beide an ihren alten Ort zurück", not im_ziel("Alpha") and not im_ziel("Beta"))
            b.close()
    finally:
        server.terminate()
        server.wait(timeout=20)
    muster.ende()
