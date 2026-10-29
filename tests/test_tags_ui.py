"""Tags in der Seitenleiste: „Eigene“ blendet die nur automatischen aus, „Alle“ zeigt sie; die Wahl bleibt nach dem Neuladen;
ohne eigene Tags ein Hinweis mit Weg zu „Alle“."""
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
    muster.stl_binaer(os.path.join(samm, "Schraube_M3.stl"), 10, 20, 30)
    muster.stl_binaer(os.path.join(samm, "Schraube_M4.stl"), 12, 20, 30)
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
        ids = {m["name"]: m["id"] for m in abfrage(port, "/api/modelle")}
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chromium())
            pg = b.new_page(viewport={"width": 1400, "height": 800})
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_selector(".karte")
            pg.click(".sk-kopf[data-sk='tags']")
            pg.wait_for_selector("#tag-liste .tag-leer")
            check("Nur automatische Tags: unter „Eigene“ keine Liste, aber ein Hinweis mit dem Weg zu „Alle“",
                  pg.locator("#tag-liste [data-tag]").count() == 0 and "Alle" in pg.inner_text("#tag-liste .tag-leer"))
            pg.click("#tag-liste .tag-leer [data-tags-zeigen='alle']")
            pg.wait_for_selector("#tag-liste [data-tag='schraube']")
            check("„Alle“ zeigt die automatischen, leiser gesetzt", pg.locator("#tag-liste .eintrag.auto[data-tag='schraube']").count() == 1)
            abfrage(port, f"/api/modelle/{ids['Schraube_M3']}/tags", {"tag": "Werkstatt"})
            pg.reload()
            pg.wait_for_selector("#tag-liste [data-tag='werkstatt']")
            check("Die Wahl „Alle“ bleibt nach dem Neuladen", pg.locator("#tag-liste [data-tag='schraube']").count() == 1)
            pg.click("#tag-liste .tag-wahl [data-tags-zeigen='eigene']")
            pg.wait_for_function("!document.querySelector(\"#tag-liste [data-tag='schraube']\")")
            check("„Eigene“: nur der von Hand gesetzte Tag", pg.locator("#tag-liste [data-tag]").count() == 1
                  and pg.locator("#tag-liste [data-tag='werkstatt']").count() == 1)
            # Ein Filter ändert nichts an Zählern, Ordnerbaum und Tags: der Klick holt nur die Liste. Sonst kamen acht Anfragen über alle Modelle
            # mit (bei 9 000 Modellen über eine Sekunde Serverarbeit), die die Liste ausbremsten.
            # Erst wenn Einlesen und Vorschaubilder ruhen: deren Ende lädt zu Recht alles neu und gehört nicht zum Klick.
            warte(lambda: not any(abfrage(port, "/api/stand")[k]["laeuft"] for k in ("scan", "worker")), 60)
            pg.wait_for_timeout(1500)
            seite = []
            pg.on("request", lambda r: seite.append(r.url) if any(x in r.url for x in ("/api/zaehler", "/api/tags", "/api/ordner", "/api/baugruppen")) else None)
            with pg.expect_response(lambda r: "/api/modelle?" in r.url):
                pg.click("#tag-liste [data-tag='werkstatt']")
            pg.wait_for_timeout(500)
            check("Ein Tag-Filter holt nur die Liste, nicht Zähler, Ordnerbaum, Tags und Baugruppen neu",
                  not seite and pg.locator("#tag-liste [data-tag='werkstatt'].aktiv").count() == 1)
            b.close()
    finally:
        server.terminate()
        server.wait(10)
    muster.ende()
