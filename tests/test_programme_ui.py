"""Öffnen-Knöpfe im Inspektor: für ein Format, das kein Programm einer Art je öffnet (FCStd im Slicer), gibt es keinen Knopf dieser Art —
auch keinen gedämpften „noch kein Slicer eingerichtet“. Ohne erkannte Programme (leerer PATH) bleibt er für STL, wo er hilft.
Ein geslictes 3MF (Platten mit G-Code) geht nur in den Slicer: kein CAD-Knopf, kein CAD im Menü „Öffnen mit“, und sobald ein Slicer da ist
auch kein „Mit dem System öffnen“ (Tester 4.11.2026: FreeCAD und das Standardprogramm des Rechners scheiterten an einem G-Code-3MF)."""
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
    muster.dreimf(os.path.join(samm, "Geslict.3mf"), slice_info=True)
    muster.dreimf(os.path.join(samm, "Roh.3mf"), slice_info=False)
    # Zwei „Programme“: ausführbare Skripte, die nichts tun — nur damit Slicer und CAD eingerichtet sind.
    slicer, cad = os.path.join(tmp, "meinslicer"), os.path.join(tmp, "meincad")
    for pfad in (slicer, cad):
        with open(pfad, "w") as f:
            f.write("#!/bin/sh\nexit 0\n")
        os.chmod(pfad, 0o755)
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
        warte(lambda: len(abfrage(port, "/api/modelle")) == 4)
        warte(lambda: any(m["gcode"] == "3mf" for m in abfrage(port, "/api/modelle")))
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
            def menue():
                pg.click("#mehr-knopf")
                pg.wait_for_selector("#mehr-menu:not([hidden])")
                e = pg.eval_on_selector_all("#mehr-menu button", "l => l.map((x) => x.id || x.dataset.oeffnePfad || x.textContent)")
                pg.keyboard.press("Escape")
                return e
            stl = knoepfe("Teil")
            fc = knoepfe("Konstruktion")
            check(f"STL ohne Programme: Hinweisknöpfe für Slicer und CAD, damit man weiss, was fehlt ({stl})", sorted(stl) == ["cad", "slicer"])
            check(f"FCStd ohne Programme: nur der Hinweisknopf fürs CAD, keiner für den Slicer ({fc})", fc == ["cad"])
            ge = knoepfe("Geslict")
            check(f"Geslictes 3MF ohne Programme: nur der Hinweisknopf für den Slicer, keiner fürs CAD ({ge})", ge == ["slicer"])
            check("Geslictes 3MF ohne Slicer: „Mit dem System öffnen“ bleibt — der einzige Weg nach draussen", "oeffnen-system" in menue())
            check(f"Rohes 3MF ohne Programme: Hinweisknöpfe für beide ({knoepfe('Roh')})", sorted(knoepfe("Roh")) == ["cad", "slicer"])

            abfrage(port, "/api/einstellungen", {"programm": {"slicer": slicer, "cad": cad}}, "PUT")
            pg.reload()
            pg.wait_for_selector(".karte")
            roh = knoepfe("Roh")
            check(f"Rohes 3MF mit Slicer und CAD: beide Knöpfe ({roh})", sorted(roh) == ["cad", "slicer"])
            m = menue()
            check("Rohes 3MF: CAD und „Mit dem System öffnen“ im Menü", cad in m and "oeffnen-system" in m)
            ge = knoepfe("Geslict")
            check(f"Geslictes 3MF mit Slicer und CAD: nur der Slicer-Knopf ({ge})", ge == ["slicer"])
            m = menue()
            check(f"Geslictes 3MF: Slicer im Menü, kein CAD, kein „Mit dem System öffnen“ ({m})", slicer in m and cad not in m and "oeffnen-system" not in m)
            b.close()
    finally:
        server.terminate()
        server.wait(10)
    muster.ende()
