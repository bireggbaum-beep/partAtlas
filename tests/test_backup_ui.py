"""Backup im Reiter „Backup & Wiederherstellung“: Zeilen mit Grösse, Umschalten wirkt, „Backup erstellen“ legt das ZIP an und der Stand
zeigt es. Die Logik prüft test_backup; hier nur, dass die Oberfläche sie erreicht."""
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
    muster.stl_binaer(os.path.join(samm, "Halter.stl"), 10, 20, 30)
    ziel = os.path.join(tmp, "Backups")
    os.makedirs(ziel)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    umgebung = {**os.environ, "PARTATLAS_BESTAND": os.path.join(tmp, "bestand"), "PARTATLAS_PORT": str(port),
                "PYTHONPATH": os.environ.get("PARTATLAS_QUELLE") or os.path.join(HIER, "..")}
    server = subprocess.Popen([sys.executable, "-m", "partatlas"], env=umgebung, cwd=tmp, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        warte(lambda: abfrage(port, "/api/zaehler") is not None)
        abfrage(port, "/api/wurzeln", {"pfad": samm})
        warte(lambda: len(abfrage(port, "/api/modelle")) == 1)
        abfrage(port, "/api/backup", {"ziel": ziel}, "PUT")
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chromium())
            pg = b.new_page()
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_selector("#einstellungen")
            pg.click("#einstellungen")
            pg.click('[data-ein="sicherung"]')
            pg.wait_for_selector("[data-bk-zeile]")
            check("Reiter zeigt Stand, Zielordner und je Zeile die Grösse; die Datenbank ist nicht abwählbar",
                  "Noch kein Backup" in pg.inner_text("#ein-backup") and ziel in pg.inner_text(".bk-ziel")
                  and pg.locator("[data-bk-zeile]").count() >= 6 and pg.is_disabled('[data-bk-zeile="katalog"]'))
            pg.uncheck('[data-bk-zeile="dateien"]')
            warte(lambda: abfrage(port, "/api/backup")["zeilen"][1]["an"] is False, 5)
            check("Eine Zeile abwählen wirkt beim Server", next(z for z in abfrage(port, "/api/backup")["zeilen"] if z["id"] == "dateien")["an"] is False)
            pg.click("[data-bk-start]")
            try:
                pg.wait_for_function("document.querySelector('#ein-backup')?.innerText.includes('Letztes Backup')", timeout=30000)
            except Exception:
                pass                       # dann fällt die Prüfung unten
            check("„Backup erstellen“: ZIP im Zielordner, der Stand zeigt es", [n for n in os.listdir(ziel) if n.endswith(".zip")]
                  and "heute" in pg.inner_text(".bk-stand"))
            b.close()
    finally:
        server.terminate()
        server.wait(10)
    muster.ende()
