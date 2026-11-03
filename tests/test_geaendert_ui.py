"""Kachelzeile „Geändert“ (Datum und Uhrzeit der Datei wie im Explorer), Sortierung „Zuletzt geändert“, Inspektor mit dem Datum von der Platte;
wer schon eigene Kachelzeilen gewählt hatte, bekommt „Geändert“ einmal dazu."""
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
    samm = os.path.join(tmp, "3D")
    os.makedirs(samm)
    zeiten = {"Halter_v1": (2026, 10, 1, 9, 5), "Halter_v3": (2026, 11, 2, 18, 47), "Halter_v2": (2026, 10, 20, 7, 30)}
    for i, (n, z) in enumerate(zeiten.items()):
        pfad = os.path.join(samm, n + ".stl")
        muster.stl_binaer(pfad, 10 + i, 20, 30)
        t = time.mktime((*z, 0, 0, 0, -1))
        os.utime(pfad, (t, t))
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    umgebung = {**os.environ, "PARTATLAS_BESTAND": os.path.join(tmp, "bestand"), "PARTATLAS_PORT": str(port), "TZ": os.environ.get("TZ", "UTC"),
                "PYTHONPATH": os.environ.get("PARTATLAS_QUELLE") or os.path.join(HIER, "..")}
    server = subprocess.Popen([sys.executable, "-m", "partatlas"], env=umgebung, cwd=tmp, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        warte(lambda: abfrage(port, "/api/zaehler") is not None)
        abfrage(port, "/api/neuigkeiten/gesehen", {})
        abfrage(port, "/api/wurzeln", {"pfad": samm})
        warte(lambda: len(abfrage(port, "/api/modelle")) == 3)
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chromium())
            ctx = b.new_context(viewport={"width": 1400, "height": 800}, timezone_id=os.environ.get("TZ", "UTC"))
            # Wie beim Tester: er hat schon eigene Kachelzeilen gewählt (vor 1.0.10, ohne „Geändert“)
            ctx.add_init_script("if (!localStorage.getItem('partatlas.kachelGeaendertDazu')) localStorage.setItem('partatlas.kachelZeilen', JSON.stringify(['masse']))")
            pg = ctx.new_page()
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_selector(".karte")
            text = pg.inner_text(".karte:has-text('Halter_v3')")
            check("Die Kachel zeigt, wann die Datei zuletzt geändert wurde — Datum und Uhrzeit wie im Explorer", "02.11.2026 18:47" in text)
            check("… auch wer schon eigene Kachelzeilen gewählt hatte, bekommt sie einmal dazu",
                  pg.evaluate("JSON.parse(localStorage.getItem('partatlas.kachelZeilen'))") == ["masse", "geaendert"])
            pg.select_option("#sortierung", "geaendert")
            pg.wait_for_function("document.querySelector('.karte')?.innerText.includes('Halter_v3')")
            reihe = pg.evaluate("[...document.querySelectorAll('.karte')].sort((a, b) => a.offsetTop - b.offsetTop || a.offsetLeft - b.offsetLeft).map((k) => k.innerText.match(/Halter_v\\d/)[0])")
            check("„Zuletzt geändert“ stellt den neuesten Stand nach vorn", reihe == ["Halter_v3", "Halter_v2", "Halter_v1"])
            # Eben in FreeCAD gespeichert (hier: Zeit gesetzt), noch nicht neu eingelesen: der Inspektor liest das Datum von der Platte
            t = time.mktime((2026, 11, 3, 8, 15, 0, 0, 0, -1))
            os.utime(os.path.join(samm, "Halter_v1.stl"), (t, t))
            pg.click(".karte:has-text('Halter_v1')")
            pg.wait_for_selector("#inspektor .i-reiter")
            pg.click("#inspektor [data-reiter='datei']") if pg.locator("#inspektor [data-reiter='datei']").count() else None
            pg.wait_for_function("document.querySelector('#inspektor').innerText.includes('Geändert')")
            check("Inspektor: das Datum kommt von der Platte — ein eben gespeicherter Stand zeigt es sofort, ohne neues Einlesen",
                  "03.11.2026" in pg.inner_text("#inspektor") and "08:15" in pg.inner_text("#inspektor"))
            pg.click("[data-layout='liste']")
            pg.wait_for_selector("#listenkopf")
            check("Liste: Spalte „Geändert“ lässt sich wählen", pg.locator("[data-spalte='geaendert']").count() == 1)
            b.close()
    finally:
        server.terminate()
        server.wait(timeout=20)
    muster.ende()
