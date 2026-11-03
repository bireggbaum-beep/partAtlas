"""Ziehen und Ablegen (ZIELE in app.js): am Zeiger steht vor dem Loslassen, was geschieht; Sammlung und Baugruppe melden mit „Rückgängig“ und
nehmen nur zurück, was dieses Ablegen geändert hat (was schon drin war, bleibt; in der Baugruppe die alte Menge)."""
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
    os.makedirs(samm)
    for i, n in enumerate(["Alpha", "Beta", "Gamma"]):
        muster.stl_binaer(os.path.join(samm, n + ".stl"), 10 + i, 20, 30)
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
        ids = {m["name"]: m["id"] for m in abfrage(port, "/api/modelle")}
        sid = abfrage(port, "/api/sammlungen", {"name": "Werkbank", "modelle": [ids["Alpha"]]})["id"]
        bid = abfrage(port, "/api/baugruppen", {"name": "Gestell", "modelle": [ids["Beta"]]})["id"]
        in_sammlung = lambda: {m["name"] for m in abfrage(port, f"/api/modelle?sammlung={sid}")}
        menge = lambda n: next((p["menge"] for p in abfrage(port, f"/api/baugruppen/{bid}")["positionen"] if p["ref"] == f"MODEL_ASSET/{ids[n]}"), 0)
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chromium())
            pg = b.new_page(viewport={"width": 1400, "height": 800})
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_selector(".karte")
            # Was am Zeiger stand, mitschreiben (der Hinweis verschwindet beim Loslassen)
            pg.evaluate("window.__h = []; const o = ziehHinweis; window.ziehHinweis = (t, x, y) => { if (t) __h.push(t); return o(t, x, y); }")

            # Sammlung: Alpha (schon drin) und Gamma gewählt, auf die Sammlung gezogen
            pg.click(".karte:has-text('Alpha')", modifiers=["Control"])
            pg.click(".karte:has-text('Gamma')", modifiers=["Control"])
            pg.drag_and_drop(".karte:has-text('Gamma')", f"[data-sammlung='{sid}']")
            pg.wait_for_function("!document.querySelector('#toast').hidden && document.querySelector('#toast').textContent.includes('Sammlung')")
            check("Am Zeiger stand vor dem Loslassen, was geschieht", "2 Modelle in die Sammlung „Werkbank“" in pg.evaluate("__h"))
            check("Die Meldung nennt nur, was neu dazukam, und hat „Rückgängig“",
                  "„Gamma.stl“ in die Sammlung „Werkbank“ gelegt." in pg.inner_text("#toast") and in_sammlung() == {"Alpha", "Gamma"})
            pg.click("#toast button:has-text('Rückgängig')")
            warte(lambda: in_sammlung() == {"Alpha"})
            check("Rückgängig nimmt nur Gamma wieder heraus — Alpha war schon drin und bleibt", in_sammlung() == {"Alpha"})
            check("Nach dem Loslassen ist der Hinweis am Zeiger weg", pg.evaluate("!document.querySelector('#ziehhinweis') || document.querySelector('#ziehhinweis').hidden"))

            # Baugruppe: Beta (schon drin, Menge 1) auf die Baugruppe → Menge 2; Strg+Z → wieder 1, nicht entfernt
            pg.keyboard.press("Escape")
            if not pg.locator(f"#baugruppen [data-baugruppe='{bid}']").is_visible():
                pg.click("[data-sk='baugruppen']")
            pg.drag_and_drop(".karte:has-text('Beta')", f"#baugruppen [data-baugruppe='{bid}']")
            warte(lambda: menge("Beta") == 2)
            check("In die Baugruppe gezogen: ein vorhandenes Teil zählt eins hoch", menge("Beta") == 2)
            pg.click("#raster")
            pg.keyboard.press("Control+z")
            warte(lambda: menge("Beta") == 1)
            check("Strg+Z: die alte Menge, das Teil bleibt in der Baugruppe", menge("Beta") == 1)
            b.close()
    finally:
        server.terminate()
        server.wait(timeout=20)
    muster.ende()
