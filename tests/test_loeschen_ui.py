"""Nach dem Löschen: die Meldung bietet „Rückgängig“ und den Weg zum Papierkorb (Tester fand ein versehentlich gelöschtes Modell nicht wieder)."""
import os
import socket
import subprocess
import sys
import tempfile

import muster
from muster import check
from test_bereinigen_ui import abfrage, chromium, warte

HIER = os.path.dirname(os.path.abspath(__file__))


def loeschen(pg, name):
    pg.click(f".karte:has-text('{name}')")
    pg.wait_for_selector("#inspektor #mehr-knopf")
    pg.click("#inspektor #mehr-knopf")
    pg.click("#inspektor #loeschen")
    pg.wait_for_selector("#dialog[open] button[value='ja']")
    pg.click("#dialog[open] button[value='ja']")
    pg.wait_for_function("!document.querySelector('#toast').hidden && document.querySelector('#toast').textContent.includes('Aus dem Katalog entfernt')")


if __name__ == "__main__":
    muster.zeitgrenze(90)
    from playwright.sync_api import sync_playwright
    tmp = tempfile.mkdtemp()
    samm = os.path.join(tmp, "3D")
    os.makedirs(samm)
    muster.stl_binaer(os.path.join(samm, "Versehentlich.stl"), 10, 20, 30)
    muster.stl_binaer(os.path.join(samm, "Bleibt.stl"), 12, 20, 30)
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
        warte(lambda: len(abfrage(port, "/api/modelle")) == 2)
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chromium())
            pg = b.new_page(viewport={"width": 1400, "height": 800})
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_selector(".karte")
            loeschen(pg, "Versehentlich")
            knoepfe = pg.eval_on_selector_all("#toast button", "l => l.map((x) => x.textContent)")
            check("Die Meldung nach dem Löschen bietet „Rückgängig“ und „Papierkorb“", knoepfe == ["Rückgängig", "Papierkorb"])
            pg.click("#toast button:has-text('Rückgängig')")
            pg.wait_for_selector(".karte:has-text('Versehentlich')")
            check("„Rückgängig“ holt das Modell zurück in den Katalog", any(m["name"] == "Versehentlich" for m in abfrage(port, "/api/modelle")))
            loeschen(pg, "Versehentlich")
            pg.click("#toast button:has-text('Papierkorb')")
            pg.wait_for_selector(".karte:has-text('Versehentlich')")
            check("„Papierkorb“ führt zum Papierkorb, dort liegt das Modell",
                  pg.eval_on_selector("[data-ansicht='papierkorb']", "e => e.classList.contains('aktiv')") and pg.locator(".karte:has-text('Bleibt')").count() == 0)
            b.close()
    finally:
        server.terminate()
        server.wait(timeout=20)
    muster.ende()
