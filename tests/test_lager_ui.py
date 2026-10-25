"""Filamentlager in der Oberfläche: Knopf in der Leiste, Spule anlegen (auch mehrere), bearbeiten, ablegen und wieder holen; Fehler als Satz."""
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
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    umgebung = {**os.environ, "PARTATLAS_BESTAND": os.path.join(tmp, "bestand"), "PARTATLAS_PORT": str(port),
                "PYTHONPATH": os.environ.get("PARTATLAS_QUELLE") or os.path.join(HIER, "..")}
    server = subprocess.Popen([sys.executable, "-m", "partatlas"], env=umgebung, cwd=tmp, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        warte(lambda: abfrage(port, "/api/zaehler") is not None)
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chromium())
            pg = b.new_page(viewport={"width": 1300, "height": 800})
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_selector("#lager")
            pg.click("#lager")
            pg.wait_for_selector("[data-lg-neu]")
            check("Der Knopf in der Leiste öffnet das Lager; ohne Spulen steht ein Hinweis da", "Noch keine Spulen" in pg.inner_text("#dialog"))
            pg.click("[data-lg-neu]")
            pg.select_option("#lg-material", "PETG")
            pg.fill("#lg-hersteller", "Prusament")
            pg.fill("#lg-farbname", "Galaxy Black")
            pg.click('[data-lg-farbe="#1a1a1a"]')
            pg.fill("#lg-preis", "24,90")
            pg.fill("#lg-ort", "Regal 2")
            pg.fill("#lg-anzahl", "2")
            check("Formular: gewählte Farbe bleibt nach dem Klick erhalten, Eingaben auch",
                  pg.locator('[data-lg-farbe="#1a1a1a"].aktiv').count() == 1 and pg.input_value("#lg-hersteller") == "Prusament" and pg.input_value("#lg-ort") == "Regal 2")
            pg.click("[data-lg-speichern]")
            pg.wait_for_selector(".lg-zeile")
            check("Zwei gleiche Spulen angelegt, in der Liste mit Material, Name und Rest",
                  pg.locator(".lg-zeile").count() == 2 and "PETG" in pg.inner_text(".lg-zeile >> nth=0") and "Galaxy Black" in pg.inner_text(".lg-zeile >> nth=0")
                  and "1.000 g" in pg.inner_text(".lg-zeile >> nth=0"))
            check("Die Summe oben stimmt: 2 Spulen, 2 kg, Wert 49,80 €", "2 Spulen" in pg.inner_text(".lg > p") and "2 kg" in pg.inner_text(".lg > p") and "49,8" in pg.inner_text(".lg > p"))
            pg.click(".lg-zeile >> nth=0 >> [data-lg-bearbeiten]")
            pg.fill("#lg-rest", "80")
            pg.click("[data-lg-speichern]")
            pg.wait_for_selector(".lg-zeile")
            check("Rest geändert: 80 g, der Balken ist knapp (gelb), die zweite Spule bleibt voll",
                  "80 g" in pg.inner_text(".lg-zeile >> nth=0") and pg.locator(".lg-zeile >> nth=0 >> .lg-rest.knapp").count() == 1
                  and "1.000 g" in pg.inner_text(".lg-zeile >> nth=1"))
            pg.click(".lg-zeile >> nth=0 >> [data-lg-bearbeiten]")
            pg.fill("#lg-rest", "5000")
            pg.click("[data-lg-speichern]")
            pg.wait_for_timeout(500)
            check("Rest über der vollen Spule: Meldung, das Formular bleibt offen", "grösser" in pg.inner_text("#toast") and pg.locator("#lg-rest").count() == 1)
            pg.click("[data-lg-zurueck]")
            pg.click(".lg-zeile >> nth=0 >> [data-lg-archiv]")
            pg.wait_for_selector("[data-lg-leere]")
            check("Als leer abgelegt: sie verschwindet aus der Liste, ein Schalter „Abgelegte zeigen (1)“ erscheint",
                  pg.locator(".lg-zeile").count() == 1 and "(1)" in pg.inner_text(".lg-leiste"))
            pg.check("[data-lg-leere]")
            check("Abgelegte zeigen: wieder zwei Zeilen, die abgelegte gedämpft", pg.locator(".lg-zeile").count() == 2 and pg.locator(".lg-zeile.archiv").count() == 1)
            pg.screenshot(path="/tmp/claude-0/-home-user/a87771ce-acd8-5417-a6e2-9a56023b0bc8/scratchpad/lager.png")
            pg.click(".lg-zeile.archiv [data-lg-archiv]")
            pg.wait_for_function("document.querySelectorAll('.lg-zeile.archiv').length === 0", timeout=5000)
            check("Wieder aktiviert", pg.locator(".lg-zeile.archiv").count() == 0 and pg.locator(".lg-zeile").count() == 2)
            pg.click("#dialog .knoepfe .knopf")
            check("Schliessen beendet das Fenster", not pg.evaluate("document.querySelector('#dialog').open"))
            b.close()
    finally:
        server.terminate()
        server.wait(10)
    muster.ende()
