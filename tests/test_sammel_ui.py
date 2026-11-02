"""Sammel-Haken: oben über dem Raster (in der Liste im Spaltenkopf), je Gruppe, oben in Häkchen-Listen der Fenster — mit „−“ für eine Teilauswahl."""
import os
import socket
import subprocess
import sys
import tempfile
import zipfile

import muster
from muster import check
from test_bereinigen_ui import abfrage, chromium, warte

HIER = os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    muster.zeitgrenze(90)
    from playwright.sync_api import sync_playwright
    tmp = tempfile.mkdtemp()
    samm = os.path.join(tmp, "3D")
    os.makedirs(os.path.join(samm, "Unter"))
    for i, n in enumerate(["Alpha", "Beta"]):
        muster.stl_binaer(os.path.join(samm, n + ".stl"), 10 + i, 20, 30)
    for i, n in enumerate(["Gamma", "Delta"]):
        muster.stl_binaer(os.path.join(samm, "Unter", n + ".stl"), 20 + i, 20, 30)
    for n in ("eins", "zwei"):
        with zipfile.ZipFile(os.path.join(samm, f"{n}.zip"), "w") as z:
            z.writestr(f"{n}.txt", "x")
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
        warte(lambda: len(abfrage(port, "/api/modelle")) == 4)
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chromium())
            pg = b.new_page(viewport={"width": 1400, "height": 800})
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_selector(".karte")
            zustand = lambda sel: pg.eval_on_selector(sel, "e => e.indeterminate ? 'teil' : e.checked ? 'an' : 'aus'")
            gewaehlt = lambda: pg.evaluate("document.querySelectorAll('.karte.markiert').length")

            pg.wait_for_selector("#leiste-alle")
            pg.click("#leiste-alle")
            pg.wait_for_function("document.querySelectorAll('.karte.markiert').length === 4")
            check("Raster: der Sammel-Haken oben wählt alle Gezeigten", zustand("#leiste-alle") == "an")
            pg.click("#leiste-alle")
            pg.wait_for_function("document.querySelectorAll('.karte.markiert').length === 0")
            check("… ein zweiter Klick hebt die Auswahl auf", zustand("#leiste-alle") == "aus")
            pg.click(".karte:has-text('Alpha')", modifiers=["Control"])
            pg.click(".karte:has-text('Gamma')", modifiers=["Control"])
            pg.wait_for_function("document.querySelectorAll('.karte.markiert').length === 2")
            check("Ein Teil gewählt: der Sammel-Haken zeigt „−“", zustand("#leiste-alle") == "teil")

            pg.select_option("#gruppierung", "ordner")
            pg.wait_for_selector("[data-gruppe-wahl]")
            check("Gruppen: auch ihr Haken zeigt „−“, wenn nur ein Teil der Gruppe gewählt ist",
                  all(zustand(f"[data-gruppe-wahl='{k}']") == "teil" for k in pg.eval_on_selector_all("[data-gruppe-wahl]", "l => l.map((x) => x.dataset.gruppeWahl)")))
            pg.click("[data-gruppe-wahl]")
            pg.wait_for_function("document.querySelectorAll('.karte.markiert').length === 3")
            check("Klick auf den „−“ einer Gruppe wählt die ganze Gruppe", gewaehlt() == 3)
            pg.select_option("#gruppierung", "keine")
            pg.keyboard.press("Escape")

            pg.click("[data-layout='liste']")
            pg.wait_for_selector("#kopf-alle")
            check("Liste: der Sammel-Haken steht im Spaltenkopf, nicht doppelt in der Leiste", pg.locator("#leiste-alle").count() == 0)
            pg.click("[data-layout='raster']")

            pg.click("#import-knopf")
            pg.click("#archive-knopf")
            pg.wait_for_selector("#dialog[open] [data-sammel='archive']")
            check("Fenster „Archive entpacken“: oben „Alle“, an, weil alle vorgewählt sind", zustand("[data-sammel='archive']") == "an")
            pg.locator("[data-archiv]").first.uncheck()
            check("Einer abgewählt: „−“ und „1 von 2“", zustand("[data-sammel='archive']") == "teil" and "1 von 2" in pg.inner_text(".sammel"))
            pg.click("[data-sammel='archive']")
            check("Klick auf „Alle“ wählt wieder alle", pg.eval_on_selector_all("[data-archiv]", "l => l.every((x) => x.checked)"))
            pg.click("[data-sammel='archive']")
            check("… und noch einmal keinen", pg.eval_on_selector_all("[data-archiv]", "l => l.every((x) => !x.checked)"))
            pg.keyboard.press("Escape")
            b.close()
    finally:
        server.terminate()
        server.wait(timeout=20)
    muster.ende()
