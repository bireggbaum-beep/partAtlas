"""Stände: Dateien nach dem Muster JJKW_Name_NN (gleicher Name, Format, Ordner) liegen als ein Stapel da, oben der zuletzt geänderte.
Nur Anzeige — geprüft wird, was still schiefgehen kann: eine Datei verschwindet im Stapel, der falsche Stand liegt oben, Fremdes rutscht hinein."""
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
TITEL = "[...document.querySelectorAll('.karte')].sort((a, b) => a.offsetTop - b.offsetTop || a.offsetLeft - b.offsetLeft).map((k) => k.querySelector('.name').title)"

if __name__ == "__main__":
    muster.zeitgrenze(120)
    from playwright.sync_api import sync_playwright
    tmp = tempfile.mkdtemp()
    samm = os.path.join(tmp, "3D")
    ordner = os.path.join(samm, "Peltierkühler")
    os.makedirs(ordner)
    os.makedirs(os.path.join(samm, "Anderes"))
    jetzt = time.time()
    # Zuletzt geändert ist _05, nicht die höchste Nummer _06: wer bei einem älteren Stand weitermachte, arbeitet an diesem.
    for i, (kw, n) in enumerate([("2644", 1), ("2644", 2), ("2645", 3), ("2646", 4), ("2647", 5), ("2647", 6)]):
        pfad = os.path.join(ordner, f"{kw}_Peltierhalter_{n:02d}.stl")
        muster.stl_binaer(pfad, 10 + n, 20, 30)          # verschiedene Masse: gleiche Bytes wären ein Modell an zwei Orten
        t = jetzt - 600 if n == 5 else jetzt - 86400 * (12 - i)
        os.utime(pfad, (t, t))
    muster.stl_binaer(os.path.join(ordner, "2641_Frontplatte_01.stl"), 40, 20, 30)
    muster.stl_binaer(os.path.join(ordner, "Deckel.stl"), 41, 20, 30)
    muster.stl_binaer(os.path.join(samm, "Anderes", "2647_Peltierhalter_07.stl"), 42, 20, 30)
    # Name vorn (Wunsch des Testers, 24.11.) und gemischt mit dem alten Schema; KW 99 ist keine Woche.
    for j, n in enumerate(["2646_Klemme_01", "Klemme_2647_02", "Klemme_2648_03"]):
        pfad = os.path.join(ordner, n + ".stl")
        muster.stl_binaer(pfad, 50 + j, 20, 30)
        t = jetzt - 86400 * (3 - j)
        os.utime(pfad, (t, t))
    for j, n in enumerate(["Buegel_2699_01", "Buegel_2699_02"]):
        muster.stl_binaer(os.path.join(ordner, n + ".stl"), 60 + j, 20, 30)
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
        warte(lambda: len(abfrage(port, "/api/modelle")) == 14)
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chromium())
            pg = b.new_context(viewport={"width": 1400, "height": 900}).new_page()
            fehler = []
            pg.on("pageerror", lambda e: fehler.append(str(e)))
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_selector(".karte")
            pg.wait_for_timeout(500)
            titel = pg.evaluate(TITEL)
            check("Sechs Stände eines Teils liegen als eine Kachel da (14 Dateien → 7 Kacheln)", len(titel) == 7)
            check("Oben liegt der zuletzt geänderte Stand, nicht die höchste Nummer",
                  "2647_Peltierhalter_05" in titel and "2647_Peltierhalter_06" not in titel)
            check("Gleicher Name in einem anderen Ordner gehört nicht in den Stapel", "2647_Peltierhalter_07" in titel)
            PELTIER = ".karte:has(.name[title='2647_Peltierhalter_05']) .stand-zeichen"
            check("Das Zeichen am Namen nennt die Zahl der Stände", pg.inner_text(PELTIER).strip() == "▸ 6")
            check("Die Leiste sagt, wie viele ältere Stände eingeklappt sind — niemand vermisst eine Datei",
                  pg.inner_text("#staende-auf").strip() == "7 ältere Stände eingeklappt")
            pg.click(PELTIER)
            pg.wait_for_function("document.querySelectorAll('.karte').length === 12")
            titel = pg.evaluate(TITEL)
            i = titel.index("2647_Peltierhalter_05")
            check("Aufgeklappt stehen die älteren Stände direkt dahinter, zuletzt geänderter zuerst",
                  titel[i + 1:i + 6] == ["2647_Peltierhalter_06", "2646_Peltierhalter_04", "2645_Peltierhalter_03",
                                         "2644_Peltierhalter_02", "2644_Peltierhalter_01"])
            pg.click(PELTIER)
            pg.wait_for_function("document.querySelectorAll('.karte').length === 7")
            pg.fill("#suche", "2645_Peltierhalter")
            pg.wait_for_function("document.querySelectorAll('.karte').length === 1")
            check("Ein Treffer der Suche verschwindet nicht in einem Stapel", pg.evaluate(TITEL) == ["2645_Peltierhalter_03"])
            pg.fill("#suche", "Klemme")
            pg.wait_for_selector(".karte .name[title^='Klemme']")
            pg.wait_for_timeout(300)
            check("Name vorn (Klemme_2648_03) ist ein Stand wie JJKW vorn — beide Schreibweisen desselben Namens sind ein Stapel",
                  pg.evaluate(TITEL) == ["Klemme_2648_03"] and pg.inner_text(".karte .stand-zeichen").strip() == "▸ 3")
            pg.fill("#suche", "Buegel")
            pg.wait_for_selector(".karte .name[title^='Buegel']")
            pg.wait_for_timeout(300)
            check("Eine Zahl, die keine Kalenderwoche sein kann (99), bündelt nicht",
                  len(pg.evaluate(TITEL)) == 2 and pg.locator(".stand-zeichen").count() == 0)
            pg.fill("#suche", "")
            # Entwürfe ausblenden wirkt in der Oberfläche, nicht beim Server: ist der oberste Stand ein ausgeblendeter Entwurf, rückt der
            # nächste nach — der Stapel darf mit ihm nicht verschwinden.
            kopf = next(m["id"] for m in abfrage(port, "/api/modelle") if m["name"] == "2647_Peltierhalter_05")
            abfrage(port, f"/api/modelle/{kopf}", {"entwurf": True}, "PATCH")
            pg.evaluate("localStorage.setItem('partatlas.ohneEntwuerfe', '1')")
            pg.reload()
            pg.wait_for_selector(".karte")
            pg.wait_for_timeout(500)
            titel = pg.evaluate(TITEL)
            check("Ist der oberste Stand als Entwurf ausgeblendet, liegt der nächste oben — der Stapel verschwindet nicht",
                  "2647_Peltierhalter_06" in titel
                  and pg.inner_text(".karte:has(.name[title='2647_Peltierhalter_06']) .stand-zeichen").strip() == "▸ 5")
            pg.evaluate("localStorage.setItem('partatlas.ohneEntwuerfe', '0')")
            pg.evaluate("localStorage.setItem('partatlas.staendeBuendeln', '0')")
            pg.reload()
            pg.wait_for_selector(".karte")
            pg.wait_for_timeout(500)
            check("Ausgeschaltet zeigt PartAtlas jede Datei wie bisher", len(pg.evaluate(TITEL)) == 14 and pg.locator(".stand-zeichen").count() == 0)
            check("Keine Fehler im Browser", not fehler)
            b.close()
    finally:
        server.terminate()
        server.wait(timeout=20)
    muster.ende()
