"""Die Seite „Lager“ (lager.js), nach dem Material Manager des 3MF Katalogs: Kennzahlen, Suche, Filter, Dashboard und Liste, Formular als Seitenfenster,
Nachkaufen, Ablegen. Der Server (Prüfung der Eingaben, Nachkaufen) steht in test_lager."""
import os
import socket
import subprocess
import sys
import tempfile

import muster
from muster import check
from test_bereinigen_ui import abfrage, chromium, warte

HIER = os.path.dirname(os.path.abspath(__file__))
BILD = "/tmp/claude-0/-home-user/a87771ce-acd8-5417-a6e2-9a56023b0bc8/scratchpad/lager.png"

if __name__ == "__main__":
    muster.zeitgrenze(120)
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
        samm = os.path.join(tmp, "3D")
        os.makedirs(samm)
        muster.dreimf(os.path.join(samm, "Paar.3mf"))
        abfrage(port, "/api/wurzeln", {"pfad": samm})
        warte(lambda: len(abfrage(port, "/api/modelle")) == 1)
        mid = abfrage(port, "/api/modelle")[0]["id"]
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chromium())
            pg = b.new_page(viewport={"width": 1500, "height": 850})
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_selector("#lager")
            pg.click("#lager")
            pg.wait_for_selector(".lg-zahlen")
            zahlen = lambda: [pg.inner_text(f".lg-zahl:nth-child({i}) b") for i in (1, 2, 3, 4)]
            check("Der Knopf in der Leiste öffnet die Seite Lager: vier Kennzahlen, leer; Hinweis statt Karten",
                  zahlen() == ["0", "0 g", "0", "0"] and "Noch keine Spulen" in pg.inner_text("#lager-seite")
                  and pg.evaluate("document.querySelector('#raster').hidden") and pg.locator("#lager.aktiv").count() == 1)

            pg.click("[data-lg-neu]")
            pg.wait_for_selector("#lf-material")
            pg.fill("#lf-material", "PETG")
            pg.fill("#lf-hersteller", "Filamentwerk Süd")
            pg.fill("#lf-farbname", "Petrol")
            pg.fill("#lf-hex", "#1A8A99")
            pg.fill("#lf-ort", "Regal B1")
            pg.fill("#lf-preis", "24,90")
            pg.click('[data-lg-anzahl="1"]')
            check("Formular als Seitenfenster: Farbwert per Hex, Anzahl mit +, der Balken zeigt 100 %",
                  pg.input_value("#lf-anzahl") == "2" and pg.inner_text("#lf-prozent") == "100 %" and not pg.evaluate("document.querySelector('#lager-form').hidden"))
            pg.click("[data-lg-speichern]")
            pg.wait_for_selector(".lg-karte")
            check("Hinzufügen: zwei Karten, das Seitenfenster ist zu, die neuen sind hervorgehoben",
                  pg.locator(".lg-karte").count() == 2 and pg.evaluate("document.querySelector('#lager-form').hidden") and pg.locator(".lg-karte.neu").count() == 2)
            check("Kennzahlen: 2 Spulen, 2.000 g, 1 Lagerplatz, nichts niedrig", zahlen() == ["2", "2.000 g", "1", "0"])
            check("Karte: Material, Hersteller · Farbname, Lagerort, Status Vorrätig, 100 %, Durchmesser und Preis",
                  all(w in pg.inner_text(".lg-karte >> nth=0") for w in ("PETG", "Filamentwerk Süd · Petrol", "Regal B1", "VORRÄTIG", "100 %", "1,75 mm", "24,90")))

            pg.dblclick(".lg-karte >> nth=0 >> .lg-kopf")
            pg.wait_for_selector("#lf-rest")
            pg.fill("#lf-rest", "140")
            check("Doppelklick bearbeitet: Restgewicht 140 von 1000 = 14 %", pg.inner_text("#lf-prozent") == "14 %" and pg.input_value("#lf-material") == "PETG")
            pg.click("[data-lg-speichern]")
            pg.wait_for_function("document.querySelectorAll('.lg-marke.niedrig').length === 1")
            check("Nach dem Speichern: eine Karte „Niedrig“, Kennzahl Niedrig/leer = 1", zahlen()[3] == "1")
            pg.click('[data-lg-filter="niedrig"]')
            check("Filter „Niedrig“ zeigt nur die eine Karte", pg.locator(".lg-karte").count() == 1)
            pg.click('[data-lg-filter="niedrig"]')
            pg.fill("#lg-suche", "petrol")
            n1 = pg.locator(".lg-karte").count()
            pg.fill("#lg-suche", "gibtsnicht")
            check("Suche nach Farbname findet beide, bei Unbekanntem kommt ein Hinweis",
                  n1 == 2 and pg.locator(".lg-karte").count() == 0 and "Keine Spulen für diese Auswahl" in pg.inner_text("#lager-seite"))
            pg.fill("#lg-suche", "")

            pg.click('[data-lg-nachkaufen] >> nth=0')
            pg.wait_for_selector("#nk-anzahl")
            pg.fill("#nk-anzahl", "2")
            pg.fill("#nk-preis", "22,50")
            pg.click("#dialog .knopf.akzent")
            pg.wait_for_function("document.querySelectorAll('.lg-karte').length === 4")
            check("Nachkaufen: zwei neue Spulen, voll, mit Material und Hersteller der Vorlage und dem neuen Preis",
                  pg.locator(".lg-karte", has_text="22,50").count() == 2 and pg.locator(".lg-karte", has_text="Filamentwerk Süd").count() == 4)

            pg.click('[data-lg-ansicht="liste"]')
            pg.wait_for_selector(".lg-tabelle")
            pg.click('[data-lg-sort="rest_g"]')
            ersteZeile = pg.inner_text(".lg-tabelle tbody tr >> nth=0")
            pg.click('[data-lg-sort="rest_g"]')
            check("Liste: sortierbar nach Bestand — aufsteigend steht die knappe Spule oben, absteigend eine volle",
                  "140" in ersteZeile and "140" not in pg.inner_text(".lg-tabelle tbody tr >> nth=0"))
            pg.screenshot(path=BILD)
            pg.click('[data-lg-ansicht="dashboard"]')

            pg.click(".lg-karte >> nth=0 >> [data-lg-loeschen]")
            pg.wait_for_function("document.querySelectorAll('.lg-karte').length === 3")
            check("Löschen: die Spule ist weg, die Meldung bietet „Rückgängig“", "Rückgängig" in pg.inner_text("#toast"))
            pg.click("#toast button")
            pg.wait_for_function("document.querySelectorAll('.lg-karte').length === 4")
            check("Rückgängig: alle vier Spulen sind wieder da", pg.locator(".lg-karte").count() == 4)

            # -- Bild an der Spule
            import io
            from PIL import Image
            png = io.BytesIO()
            Image.new("RGB", (60, 60), "#cc3333").save(png, "PNG")
            pg.click(".lg-karte >> nth=0 >> [data-lg-bearbeiten]")
            pg.wait_for_selector("#lf-bilddatei", state="attached")
            pg.set_input_files("#lf-bilddatei", {"name": "spule.txt", "mimeType": "text/plain", "buffer": b"kein bild"})
            check("Eine Textdatei als Bild: Hinweis unter dem Bildfeld, kein Bild gewählt", "Nur PNG, JPG oder WebP" in pg.inner_text("#lf-bildhinweis") and pg.locator("#lf-bild img").count() == 0)
            pg.set_input_files("#lf-bilddatei", {"name": "gross.png", "mimeType": "image/png", "buffer": b"0" * (5 * 1024 * 1024 + 1)})
            check("Über 5 MB: Hinweis, kein Bild gewählt", "5 MB" in pg.inner_text("#lf-bildhinweis") and pg.locator("#lf-bild img").count() == 0)
            pg.set_input_files("#lf-bilddatei", {"name": "spule.png", "mimeType": "image/png", "buffer": png.getvalue()})
            check("Ein PNG: Vorschau im Bildfeld, der Hinweis ist weg", pg.locator("#lf-bild img").count() == 1 and pg.evaluate("document.querySelector('#lf-bildhinweis').hidden"))
            pg.click("[data-lg-speichern]")
            pg.wait_for_selector(".lg-karte .lg-bild")
            check("Gespeichert: die Karte zeigt das Foto statt des Kürzels", pg.locator(".lg-karte .lg-bild").count() == 1)
            pg.click(".lg-karte:has(.lg-bild) [data-lg-bearbeiten]")
            pg.click("[data-lg-bildweg]")
            pg.keyboard.press("Escape")
            check("Bild entfernen, dann Escape: nichts ändert sich, das Foto bleibt", pg.locator(".lg-karte .lg-bild").count() == 1)
            pg.click(".lg-karte:has(.lg-bild) [data-lg-bearbeiten]")
            pg.click("[data-lg-bildweg]")
            pg.click("[data-lg-speichern]")
            pg.wait_for_function("document.querySelectorAll('.lg-karte .lg-bild').length === 0")
            check("Bild entfernen und speichern: wieder das Kürzel", pg.locator(".lg-karte .lg-bild").count() == 0)

            pg.click("[data-lg-neu]")
            pg.fill("#lf-material", "PLA")
            pg.fill("#lf-rest", "5000")
            pg.click("[data-lg-speichern]")
            pg.wait_for_timeout(500)
            check("Rest über der vollen Spule: Meldung, das Seitenfenster bleibt offen", "grösser" in pg.inner_text("#toast") and pg.locator("#lf-rest").count() == 1)
            pg.keyboard.press("Escape")
            check("Escape schliesst das Seitenfenster", pg.evaluate("document.querySelector('#lager-form').hidden"))
            pg.click('[data-rail="katalog"]')
            pg.wait_for_selector("#raster:not([hidden])")
            check("Zurück in den Katalog: das Lager ist weg, der Knopf nicht mehr aktiv", pg.evaluate("document.querySelector('#lager-seite').hidden") and pg.locator("#lager.aktiv").count() == 0)

            # -- Reicht das Filament? im Inspektor und in der Warteschlange (das 3MF braucht PETG schwarz 12,5 g und PLA weiss 3,25 g)
            for x in abfrage(port, "/api/spulen")["spulen"]:
                abfrage(port, f"/api/spulen/{x['id']}", methode="DELETE")
            abfrage(port, "/api/spulen", {"felder": {"material": "PETG", "farbe": "#000000", "start_g": 1000, "hersteller": "Prusament", "ort": "Regal 1"}})
            abfrage(port, "/api/warteschlange", {"modelle": [mid]})
            pg.goto(f"http://127.0.0.1:{port}/?phase=2")
            pg.wait_for_selector(".karte")
            pg.click(".karte >> nth=0")
            pg.wait_for_selector(".rf")
            check("Inspektor „Reicht das Filament?“: PETG reicht mit Spule und Ort, PLA ist unklar (keine passende Spule)",
                  "reicht" in pg.inner_text(".rf-zeile >> nth=0").lower() and "Prusament" in pg.inner_text(".rf") and "Regal 1" in pg.inner_text(".rf")
                  and "Keine passende Spule" in pg.inner_text(".rf") and pg.locator(".rf-marke.reicht").count() == 1 and pg.locator(".rf-marke.unklar").count() == 1)
            pg.screenshot(path=BILD.replace("lager.png", "reicht.png"))
            pg.wait_for_selector("#ws-liste li")
            check("Warteschlange: der Punkt vor dem Modell ist unklar (grau), weil das PLA fehlt", pg.locator("#ws-liste .ws-reicht").count() == 1
                  and "unklar" in pg.get_attribute("#ws-liste .ws-reicht", "title"))
            abfrage(port, "/api/spulen", {"felder": {"material": "PLA", "farbe": "#ffffff", "start_g": 1000}})
            pg.goto(f"http://127.0.0.1:{port}/?phase=2")
            pg.wait_for_selector("#ws-liste .ws-reicht")
            check("Mit weisser PLA-Spule: der Punkt in der Warteschlange wird grün", "reicht" in pg.get_attribute("#ws-liste .ws-reicht", "title") and "ws-reicht reicht" in pg.get_attribute("#ws-liste .ws-reicht", "class"))

            # -- Abbuchen beim Anlegen eines Drucks, Materialkosten
            for x in abfrage(port, "/api/spulen")["spulen"]:
                abfrage(port, f"/api/spulen/{x['id']}", {"preis": 30}, methode="PATCH")
            pg.click(".karte >> nth=0")
            pg.wait_for_selector(".rf")
            pg.click('[data-reiter="drucke"]')
            pg.click("[data-druck-neu]")
            pg.wait_for_selector("#df-typ")
            pg.select_option("#df-typ", "PETG")
            pg.fill("#df-fg", "12.5")
            pg.dispatch_event("#df-fg", "change")
            pg.wait_for_function("document.querySelector('#df-spule').value !== ''")
            check("Druck anlegen: die PETG-Spule ist vorgewählt, der Hinweis nennt, was abgezogen wird",
                  "PETG" in pg.eval_on_selector("#df-spule", "e => e.selectedOptions[0].textContent") and "Zieht 12,5 g ab" in pg.inner_text("#df-spulehinweis"))
            pg.click("#df-ok")
            pg.wait_for_selector(".druck .chip:has-text('von PETG')")
            petg = next(x for x in abfrage(port, "/api/spulen")["spulen"] if x["material"] == "PETG")
            check("Gespeichert: der Rest der Spule sank um 12,5 g, der Druck zeigt „↓ 12,5 g von PETG · 0,38 €“",
                  petg["rest_g"] == 987.5 and "0,38" in pg.inner_text(".druck .chip:has-text('von PETG')"))
            pg.click('[data-reiter="uebersicht"]')
            check("Der Inspektor nennt die Materialkosten des Projekts: 12,5 g PETG und 3,25 g PLA zu je 30 € je kg = 0,47 €",
                  "Materialkosten ca. 0,47" in pg.inner_text(".rf") and "ohne die Filamente" not in pg.inner_text(".rf"))
            b.close()
    finally:
        server.terminate()
        server.wait(10)
    muster.ende()
