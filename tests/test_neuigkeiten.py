"""„Neu in dieser Fassung“: einmal nach einem Update, gemerkt im Bestand; ein ganz neuer Bestand sieht nichts; jede Fassung hat einen Text."""
import glob
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

import muster
from muster import check
from fastapi.testclient import TestClient
from partatlas import neuigkeiten
from partatlas.main import erstelle_app
from partatlas.version import VERSION

HIER = os.path.dirname(os.path.abspath(__file__))


def chromium():
    if os.environ.get("PARTATLAS_CHROMIUM"):
        return os.environ["PARTATLAS_CHROMIUM"]
    treffer = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
    return treffer[-1] if treffer else None


if __name__ == "__main__":
    muster.zeitgrenze(90)
    check("Zur aktuellen Fassung steht ein Text (neueste zuerst) — sonst zeigt sie nichts an", neuigkeiten.NEUES[0][0] == VERSION
          and all(z for _, z in neuigkeiten.NEUES))
    check("seit(): nur die Fassungen nach der gesehenen bis zur aktuellen",
          [e["version"] for e in neuigkeiten.seit("0.95.3", "0.95.5")] == ["0.95.5", "0.95.4"]
          and neuigkeiten.seit("0.95.6", "0.95.6") == [] and neuigkeiten.seit("0.99.0", "0.95.6") == [])

    tmp = tempfile.mkdtemp()
    samm = os.path.join(tmp, "3D")
    os.makedirs(samm)
    muster.stl_binaer(os.path.join(samm, "Halter.stl"), 10, 20, 30)
    with TestClient(erstelle_app(os.path.join(tmp, "leer"), prozesse=2)) as c:
        check("Ein ganz neuer Bestand hat nichts verpasst: keine Neuigkeiten", c.get("/api/neuigkeiten").json()["neu"] == []
              and c.app.state.zustand["bestand"].einstellungen().get("neuigkeiten_gesehen") == VERSION)
    alt = os.path.join(tmp, "alt")
    with TestClient(erstelle_app(alt, prozesse=2)) as c:
        c.post("/api/wurzeln", json={"pfad": samm})
        c.app.state.zustand["scanner"].warten(60)
    with open(os.path.join(alt, "einstellungen.json"), "w") as f:
        f.write("{}")                       # ein Bestand von vor diesem Fenster: Inhalt, aber nichts über „gesehen“
    with TestClient(erstelle_app(alt, prozesse=2)) as c:
        n = c.get("/api/neuigkeiten").json()
        check("Ein Bestand mit Inhalt, der das Fenster noch nicht kannte, sieht alles ab 0.95.1", n["version"] == VERSION
              and [e["version"] for e in n["neu"]][-1] == "0.95.1" and n["neu"][0]["version"] == VERSION)
        c.post("/api/neuigkeiten/gesehen")
        check("Nach „gesehen“ kommt nichts mehr", c.get("/api/neuigkeiten").json()["neu"] == [])
        check("Ein Klick auf die Fassung zeigt trotzdem die letzten Einträge", 1 <= len(c.get("/api/neuigkeiten?alle=1").json()["neu"]) <= 5)

    # -- im Browser
    bestand = os.path.join(tmp, "browser")
    os.makedirs(bestand)
    with open(os.path.join(bestand, "einstellungen.json"), "w") as f:
        json.dump({"neuigkeiten_gesehen": "0.95.4"}, f)
    from playwright.sync_api import sync_playwright
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    umgebung = {**os.environ, "PARTATLAS_BESTAND": bestand, "PARTATLAS_PORT": str(port),
                "PYTHONPATH": os.environ.get("PARTATLAS_QUELLE") or os.path.join(HIER, "..")}
    server = subprocess.Popen([sys.executable, "-m", "partatlas"], env=umgebung, cwd=tmp, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/api/zaehler")
                break
            except OSError:
                time.sleep(0.1)
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chromium())
            pg = b.new_page()
            pg.goto(f"http://127.0.0.1:{port}/")
            try:
                pg.wait_for_selector("#dialog[open]", timeout=8000)
                text = pg.inner_text("#dialog")
            except Exception:
                text = ""
            check("Nach einem Update erscheint das Fenster mit den Neuerungen seit der gesehenen Fassung",
                  VERSION in text and "0.95.5" in text and "0.95.4" not in text)
            pg.click("#dialog button[value=ok]")
            time.sleep(0.5)
            pg.reload()
            time.sleep(3)
            check("Nach dem Schliessen kommt es nicht wieder", not pg.evaluate("document.querySelector('#dialog').open"))
            pg.click("#version")
            pg.wait_for_selector("#dialog[open]", timeout=5000)
            check("Ein Klick auf die Fassung zeigt es auf Wunsch wieder", "Zuletzt dazugekommen" in pg.inner_text("#dialog"))
            b.close()
    finally:
        server.terminate()
        server.wait(10)
    muster.ende()
