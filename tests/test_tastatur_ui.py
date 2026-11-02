"""Bedienung nur mit der Tastatur: Suchfeld ↔ Treffer, Entf beim einzelnen Modell (Enter bestätigt, Wahl springt aufs nächste), Strg+Z holt zurück,
„?“ zeigt die Tastenkürzel."""
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
    for i, n in enumerate(["Alpha", "Beta", "Gamma", "Delta"]):
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
        warte(lambda: len(abfrage(port, "/api/modelle")) == 4)
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chromium())
            pg = b.new_page(viewport={"width": 1400, "height": 800})
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_selector(".karte")
            gewaehlt = lambda: pg.evaluate("(document.querySelector('.karte.gewaehlt')?.innerText.split('\\n').find((z) => z.endsWith('.stl')) || '').replace('.stl', '') || null")
            im_suchfeld = lambda: pg.evaluate("document.activeElement?.id === 'suche'")
            pg.keyboard.press("/")
            pg.keyboard.type("Gam")
            pg.keyboard.press("ArrowDown")                  # sofort, vor der Tipp-Pause: die wartende Suche gilt
            pg.wait_for_function("document.querySelector('.karte.gewaehlt')")
            check("Im Suchfeld: ↓ führt zu den Treffern, der erste ist gewählt (auch vor Ablauf der Tipp-Pause)",
                  gewaehlt() == "Gamma" and not im_suchfeld())
            pg.keyboard.press("ArrowUp")
            check("↑ in der ersten Reihe führt zurück ins Suchfeld, der Text ist markiert",
                  im_suchfeld() and pg.evaluate("(() => { const s = document.querySelector('#suche'); return s.selectionStart === 0 && s.selectionEnd === s.value.length; })()"))
            pg.keyboard.press("Escape")                     # Suche leeren
            pg.wait_for_function("document.querySelectorAll('.karte').length === 4")
            pg.keyboard.press("Enter")
            pg.wait_for_function("document.querySelector('.karte.gewaehlt')")
            erstes = gewaehlt()
            pg.keyboard.press("ArrowRight")
            zweites = gewaehlt()
            check("Enter im leeren Suchfeld wählt das erste Modell, → das nächste", erstes != zweites and zweites is not None)
            pg.keyboard.press("Delete")
            pg.wait_for_selector("#dialog[open]")
            check("Entf beim einzelnen angeklickten Modell fragt nach; der Fokus steht auf „Aus dem Katalog entfernen“",
                  pg.evaluate("document.activeElement?.value") == "ja")
            pg.keyboard.press("Enter")
            pg.wait_for_function(f"!document.querySelector('#dialog').open && ![...document.querySelectorAll('.karte')].some((k) => k.innerText.includes({zweites!r} + '.stl'))")
            pg.wait_for_function("document.querySelector('.karte.gewaehlt')")
            check("Enter entfernt; danach ist das Modell gewählt, das jetzt an derselben Stelle steht", gewaehlt() not in (None, zweites))
            pg.keyboard.press("Control+z")
            pg.wait_for_function(f"[...document.querySelectorAll('.karte')].some((k) => k.innerText.includes({zweites!r} + '.stl'))")
            check("Strg+Z holt das entfernte Modell zurück", any(m["name"] == zweites for m in abfrage(port, "/api/modelle")))
            pg.keyboard.press("?")
            pg.wait_for_selector("#dialog[open] .kuerzel")
            text = pg.inner_text("#dialog")
            check("„?“ zeigt die Tastenkürzel, mit den Tasten dieses Rechners", "Tastenkürzel" in text and "Strg" in text and "Entf" in text)
            pg.keyboard.press("Escape")
            check("… und Esc schliesst sie", not pg.evaluate("document.querySelector('#dialog').open"))
            b.close()
    finally:
        server.terminate()
        server.wait(timeout=20)
    muster.ende()
