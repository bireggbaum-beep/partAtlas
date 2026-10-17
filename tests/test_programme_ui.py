"""Öffnen-Knöpfe im Inspektor: für ein Format, das kein Programm einer Art je öffnet (FCStd im Slicer), gibt es keinen Knopf dieser Art —
auch keinen gedämpften „noch kein Slicer eingerichtet“. Ohne erkannte Programme (leerer PATH) bleibt er für STL, wo er hilft."""
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
    muster.zeitgrenze(120)
    from playwright.sync_api import sync_playwright
    tmp = tempfile.mkdtemp()
    samm = os.path.join(tmp, "3D")
    os.makedirs(samm)
    muster.stl_binaer(os.path.join(samm, "Teil.stl"))
    muster.fcstd(os.path.join(samm, "Konstruktion.fcstd"))
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    # Leerer Bestand und leerer PATH: es gibt weder Slicer noch CAD zu erkennen.
    umgebung = {**os.environ, "PARTATLAS_BESTAND": os.path.join(tmp, "bestand"), "PARTATLAS_PORT": str(port), "PATH": "/nonexistent",
                "HOME": tmp, "XDG_DATA_HOME": os.path.join(tmp, "daten"), "PYTHONPATH": os.environ.get("PARTATLAS_QUELLE") or os.path.join(HIER, "..")}
    server = subprocess.Popen([sys.executable, "-m", "partatlas"], env=umgebung, cwd=tmp, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        warte(lambda: abfrage(port, "/api/zaehler") is not None)
        abfrage(port, "/api/neuigkeiten/gesehen", {})          # das Fenster „Neu in dieser Fassung“ verdeckte sonst die Kacheln
        abfrage(port, "/api/einstellungen", {"fcstd_freecad": "nein"}, "PUT")           # ebenso die Frage „FCStd über FreeCAD einlesen?“
        abfrage(port, "/api/wurzeln", {"pfad": samm})
        warte(lambda: len(abfrage(port, "/api/modelle")) == 2)
        prog = abfrage(port, "/api/programme")
        check("Ohne erkannte Programme: keine Programme in der Liste", prog["programme"] == [])
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chromium())
            pg = b.new_page()
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_selector(".karte")

            def knoepfe(name):
                pg.locator(".karte", has=pg.locator(".name", has_text=name)).first.click(timeout=5000)
                pg.wait_for_selector("#inspektor .i-name")
                pg.wait_for_function(f"document.querySelector('#inspektor .i-name')?.textContent.startsWith('{name}')")
                time.sleep(0.5)
                return pg.eval_on_selector_all("#inspektor .i-aktionen .hv-btn[data-hv-art]", "l => l.map((x) => x.dataset.hvArt)")
            stl = knoepfe("Teil")
            fc = knoepfe("Konstruktion")
            check(f"STL ohne Programme: Hinweisknöpfe für Slicer und CAD, damit man weiss, was fehlt ({stl})", sorted(stl) == ["cad", "slicer"])
            check(f"FCStd ohne Programme: nur der Hinweisknopf fürs CAD, keiner für den Slicer ({fc})", fc == ["cad"])
            b.close()
    finally:
        server.terminate()
        server.wait(10)
    muster.ende()
