"""Feld „＋ Tag“ im Inspektor: Vorschläge aus den vorhandenen Tags, Enter nimmt den markierten, Fokus bleibt im Feld, „neu anlegen“ nur ohne genauen Treffer."""
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
    for i, n in enumerate(["Halter_Arm", "Halter_Kabel", "Deckel"]):
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
        abfrage(port, f"/api/modelle/{ids['Deckel']}/tags", {"tag": "werkbank"})
        tags_von = lambda n: set(abfrage(port, f"/api/modelle/{ids[n]}")["tags"])
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chromium())
            pg = b.new_page(viewport={"width": 1400, "height": 800})
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_selector(".karte")
            pg.click(".karte:has-text('Halter_Kabel')")
            pg.wait_for_selector("#tag-neu")
            pg.click("#tag-neu")
            vorschlaege = lambda: pg.evaluate("[...document.querySelectorAll('#tag-vorschlaege:not([hidden]) li')].map((l) => [l.innerText.replace(/\\s+/g, ' ').trim(), l.classList.contains('markiert')])")
            pg.keyboard.type("werk")
            pg.wait_for_selector("#tag-vorschlaege:not([hidden])")
            v = vorschlaege()
            check("Beim Tippen: der vorhandene Tag, mit Anzahl, vorbelegt (fängt so an); dazu „neu anlegen“",
                  v[0][0] == "#werkbank 1" and v[0][1] and "neu anlegen" in v[-1][0])
            pg.keyboard.press("Enter")
            pg.wait_for_function("[...document.querySelectorAll('.i-tags .chip')].some((c) => c.innerText.includes('werkbank'))")
            check("Enter nimmt den Vorschlag, und der Fokus bleibt im Feld (der nächste Tag gleich hinterher)",
                  "werkbank" in tags_von("Halter_Kabel") and pg.evaluate("document.activeElement?.id") == "tag-neu")
            pg.keyboard.type("halt")
            pg.wait_for_selector("#tag-vorschlaege:not([hidden])")
            check("Was das Modell schon hat, wird nicht vorgeschlagen", not any("#halter " in x[0] for x in vorschlaege()))
            pg.fill("#tag-neu", "")
            pg.keyboard.type("Arm")
            pg.wait_for_function("document.querySelector('#tag-vorschlaege li')?.innerText.includes('#arm')")
            v = vorschlaege()
            check("Genauer Treffer (auch mit anderer Gross-/Kleinschreibung): vorbelegt, kein „neu anlegen“",
                  v[0][1] and v[0][0].startswith("#arm") and not any("neu anlegen" in x[0] for x in v))
            pg.fill("#tag-neu", "")
            pg.keyboard.type("ckel")
            pg.wait_for_function("document.querySelector('#tag-vorschlaege li')?.innerText.includes('#deckel')")
            v = vorschlaege()
            check("Treffer nur mitten im Wort: angeboten, aber vorbelegt ist „neu anlegen“ (ein neuer Tag wird nie aus Versehen ein anderer)",
                  v[0][0].startswith("#deckel") and not v[0][1] and v[-1][1] and "neu anlegen" in v[-1][0])
            pg.fill("#tag-neu", "")
            pg.keyboard.type("de")
            pg.wait_for_function("document.querySelector('#tag-vorschlaege li')?.innerText.includes('#deckel')")
            pg.keyboard.press("ArrowDown")
            v = vorschlaege()
            check("↓ markiert die nächste Zeile", not v[0][1] and v[1][1])
            pg.keyboard.press("Escape")
            check("Esc schliesst die Liste, der Text bleibt", pg.locator("#tag-vorschlaege").is_hidden() and pg.input_value("#tag-neu") == "de"
                  and pg.evaluate("document.activeElement?.id") == "tag-neu")
            pg.keyboard.press("Escape")
            check("… ein zweites Esc leert das Feld und verlässt es", pg.evaluate("document.activeElement?.id") != "tag-neu")
            pg.click("#tag-neu")
            pg.keyboard.type("drohne")
            pg.wait_for_selector("#tag-vorschlaege:not([hidden])")
            check("Kein Treffer: „neu anlegen“ ist vorbelegt", vorschlaege() == [["„drohne“ neu anlegen Enter", True]])
            pg.keyboard.press("Enter")
            pg.wait_for_function("[...document.querySelectorAll('.i-tags .chip')].some((c) => c.innerText.includes('drohne'))")
            check("… Enter legt ihn an", "drohne" in tags_von("Halter_Kabel"))
            b.close()
    finally:
        server.terminate()
        server.wait(timeout=20)
    muster.ende()
