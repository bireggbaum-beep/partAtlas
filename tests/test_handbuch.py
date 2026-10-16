"""Das Handbuch: aus partAtlas erreichbar (Knopf „?“, F1 — beim Kapitel zur Ansicht), jedes Bild da (hell und dunkel), jeder Verweis
auf ein Kapitel trifft. Ein Handbuch, das man nicht findet oder in dem Bilder fehlen, merkt sonst niemand."""
import os
import re
import socket
import subprocess
import sys
import tempfile

import muster
from muster import check
from test_bereinigen_ui import abfrage, chromium, warte

HIER = os.path.dirname(os.path.abspath(__file__))
QUELLE = os.environ.get("PARTATLAS_QUELLE") or os.path.join(HIER, "..")
HANDBUCH = os.path.join(QUELLE, "partatlas", "web", "handbuch")

if __name__ == "__main__":
    muster.zeitgrenze(120)
    html = open(os.path.join(HANDBUCH, "index.html"), encoding="utf-8").read()
    bilder = re.findall(r'src="(bilder/[^"]+)"', html)
    fehlen = [b for b in bilder if not os.path.isfile(os.path.join(HANDBUCH, b))]
    paare = {b.rsplit("-", 1)[0] for b in bilder}
    ohne_paar = [p for p in paare if not (f"{p}-hell.webp" in bilder and f"{p}-dunkel.webp" in bilder)]
    check(f"Jedes Bild im Handbuch liegt da, je hell und dunkel (fehlen: {fehlen or 'keine'}, ohne Paar: {ohne_paar or 'keine'})",
          not fehlen and not ohne_paar)
    ids = set(re.findall(r'id="([^"]+)"', html))
    tote = [a for a in re.findall(r'href="#([^"]+)"', html) if a not in ids]
    check(f"Jeder Verweis auf ein Kapitel trifft (tot: {tote or 'keine'})", not tote)

    from playwright.sync_api import sync_playwright
    tmp = tempfile.mkdtemp()
    samm = os.path.join(tmp, "3D")
    os.makedirs(samm)
    muster.stl_binaer(os.path.join(samm, "Teil.stl"))
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    umgebung = {**os.environ, "PARTATLAS_BESTAND": os.path.join(tmp, "bestand"), "PARTATLAS_PORT": str(port), "PYTHONPATH": QUELLE}
    server = subprocess.Popen([sys.executable, "-m", "partatlas"], env=umgebung, cwd=tmp, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        warte(lambda: abfrage(port, "/api/zaehler") is not None)
        abfrage(port, "/api/wurzeln", {"pfad": samm})
        warte(lambda: len(abfrage(port, "/api/modelle")) == 1)
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chromium())
            ctx = b.new_context()
            pg = ctx.new_page()
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_selector(".karte")
            with ctx.expect_page() as neu:
                pg.click("#handbuch")
            hb = neu.value
            hb.wait_for_load_state()
            try:
                hb.wait_for_function("document.getElementById('fassung').textContent.includes('Fassung')", timeout=5000)
            except Exception:
                pass                               # dann fällt die Prüfung
            check("Knopf „?“ öffnet das Handbuch in einem neuen Tab, mit der laufenden Fassung",
                  "/web/handbuch/index.html" in hb.url and hb.title() == "partAtlas Handbuch"
                  and hb.inner_text("#fassung").endswith(abfrage(port, "/api/stand")["version"]))
            hb.close()
            pg.click('[data-rail="bereinigen"]')
            pg.wait_for_timeout(500)
            with ctx.expect_page() as neu:
                pg.keyboard.press("F1")
            hb = neu.value
            hb.wait_for_load_state()
            check("F1 in Bereinigen öffnet das Handbuch beim Kapitel „Bereinigen“", hb.url.endswith("/web/handbuch/index.html#bereinigen"))
            b.close()
    finally:
        server.terminate()
        server.wait(10)
    muster.ende()
