"""Ordner im Baum wie im Dateimanager: Umbenennen per Rechtsklick oder F2 direkt im Baum, Enter übernimmt, Esc bricht ab, eine Ablehnung
lässt das Feld offen; Rückgängig mit Strg+Z. Verschieben per Ziehen auf einen anderen Ordner oder Rechtsklick › Verschieben nach …
Die Regeln selbst prüft test_ordner. Am Ende: ein nicht erreichbarer Wurzelordner (Stick ab) bekommt nach dem Einlesen ein Zeichen im Baum,
ohne dass man die Seite neu lädt — und verliert es nach dem nächsten Einlesen mit eingestecktem Stick."""
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
    os.makedirs(os.path.join(samm, "Projekt"))
    muster.stl_binaer(os.path.join(samm, "Projekt", "Teil.stl"), 10, 20, 30)
    os.makedirs(os.path.join(samm, "Ziel"))
    muster.stl_binaer(os.path.join(samm, "Ziel", "Anderes.stl"), 12, 20, 30)
    stick = os.path.join(tmp, "Stick")
    os.makedirs(stick)
    muster.stl_binaer(os.path.join(stick, "Clip.stl"), 13, 20, 30)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    umgebung = {**os.environ, "PARTATLAS_BESTAND": os.path.join(tmp, "bestand"), "PARTATLAS_PORT": str(port),
                "PYTHONPATH": os.environ.get("PARTATLAS_QUELLE") or os.path.join(HIER, "..")}
    server = subprocess.Popen([sys.executable, "-m", "partatlas"], env=umgebung, cwd=tmp, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        warte(lambda: abfrage(port, "/api/zaehler") is not None)
        wid = abfrage(port, "/api/wurzeln", {"pfad": samm})["id"]
        warte(lambda: len(abfrage(port, "/api/modelle")) == 2)
        sw = abfrage(port, "/api/wurzeln", {"pfad": stick})["id"]
        warte(lambda: len(abfrage(port, "/api/modelle")) == 3)
        warte(lambda: not abfrage(port, "/api/scan")["laeuft"])
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chromium())
            pg = b.new_page()
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_selector(f'.eintrag[data-wurzel="{wid}"]')
            if not pg.locator(f'.eintrag[data-ordner="{wid}/Projekt"]').count():
                pg.click(f'[data-klappe="{wid}"]')
            ordner = f'.eintrag[data-ordner="{wid}/Projekt"]'
            pg.wait_for_selector(ordner)

            pg.click(ordner, button="right")
            pg.click('[data-km="ordner-umbenennen"]')
            feld = pg.locator(".baum-name")
            check("Rechtsklick › Umbenennen: Feld im Baum, Name markiert", feld.count() == 1 and feld.input_value() == "Projekt"
                  and pg.evaluate("document.activeElement.selectionStart === 0 && document.activeElement.selectionEnd === 7"))
            feld.fill("Neu")
            feld.press("Enter")
            warte(lambda: os.path.isdir(os.path.join(samm, "Neu")), 10)
            pg.wait_for_selector(f'.eintrag[data-ordner="{wid}/Neu"]', timeout=10000)
            check("Enter übernimmt: auf der Platte umbenannt, im Baum der neue Name, Meldung mit „Rückgängig“",
                  os.path.isdir(os.path.join(samm, "Neu")) and "Rückgängig" in pg.inner_text("#toast"))

            pg.evaluate("document.activeElement?.blur()")        # Strg+Z ausserhalb eines Feldes, wie im Explorer
            pg.keyboard.press("Control+z")
            warte(lambda: os.path.isdir(os.path.join(samm, "Projekt")), 10)
            check("Strg+Z macht das Umbenennen rückgängig", os.path.isdir(os.path.join(samm, "Projekt")) and not os.path.exists(os.path.join(samm, "Neu")))

            pg.wait_for_selector(ordner, timeout=10000)
            pg.focus(ordner)
            pg.keyboard.press("F2")
            pg.wait_for_selector(".baum-name")
            pg.locator(".baum-name").fill("a:b")
            pg.locator(".baum-name").press("Enter")
            pg.wait_for_selector(".baum-name", timeout=5000)
            time.sleep(0.5)
            check("F2 auf dem Ordner; verbotenes Zeichen: Meldung, das Feld bleibt offen mit dem Getippten",
                  pg.locator(".baum-name").input_value() == "a:b" and "darf keines dieser Zeichen" in pg.inner_text("#toast")
                  and os.path.isdir(os.path.join(samm, "Projekt")))
            pg.locator(".baum-name").press("Escape")
            pg.wait_for_selector(ordner, timeout=5000)
            check("Esc bricht ab: nichts geändert", pg.locator(".baum-name").count() == 0 and os.path.isdir(os.path.join(samm, "Projekt")))

            # -- Verschieben: Ziehen auf einen anderen Ordner
            pg.drag_and_drop(ordner, f'.eintrag[data-ordner="{wid}/Ziel"]')
            warte(lambda: os.path.isdir(os.path.join(samm, "Ziel", "Projekt")), 10)
            check("Ziehen auf einen Ordner verschiebt den Ordner dorthin, mit Meldung und „Rückgängig“",
                  os.path.isfile(os.path.join(samm, "Ziel", "Projekt", "Teil.stl")) and not os.path.exists(os.path.join(samm, "Projekt"))
                  and "verschoben nach „Ziel“" in pg.inner_text("#toast") and "Rückgängig" in pg.inner_text("#toast"))
            pg.click("#toast button")
            warte(lambda: os.path.isdir(os.path.join(samm, "Projekt")), 10)
            check("„Rückgängig“ in der Meldung: wieder am alten Ort", os.path.isfile(os.path.join(samm, "Projekt", "Teil.stl")))

            # -- Verschieben: Rechtsklick › Verschieben nach …
            pg.wait_for_selector(ordner, timeout=10000)
            pg.click(ordner, button="right")
            pg.click('[data-km="ordner-verschieben"]')
            pg.wait_for_selector("#ordner-ziel")
            ziele = pg.eval_on_selector_all("#ordner-ziel option", "l => l.map((o) => o.value)")
            check("Verschieben nach …: Auswahl ohne den Ordner selbst", f"{wid}/Ziel" in ziele and f"{wid}/Projekt" not in ziele)
            pg.select_option("#ordner-ziel", f"{wid}/Ziel")
            pg.click('#dialog button[value="ja"]')
            warte(lambda: os.path.isdir(os.path.join(samm, "Ziel", "Projekt")), 10)
            check("… und OK verschiebt", os.path.isfile(os.path.join(samm, "Ziel", "Projekt", "Teil.stl")))

            # -- Neuer Ordner: im Baum, mit offenem Namensfeld; ohne Modelle grau und ohne Zahl
            pg.click(f'.eintrag[data-ordner="{wid}"]', button="right")
            pg.click('[data-km="ordner-neu"]')
            pg.wait_for_selector(".baum-name", timeout=5000)
            check("Rechtsklick › Neuer Ordner: angelegt als „Neuer Ordner“, Name zum Umbenennen offen",
                  os.path.isdir(os.path.join(samm, "Neuer Ordner")) and pg.locator(".baum-name").input_value() == "Neuer Ordner")
            pg.locator(".baum-name").fill("Teile")
            pg.locator(".baum-name").press("Enter")
            neu = f'.eintrag[data-ordner="{wid}/Teile"]'
            pg.wait_for_selector(neu, timeout=10000)
            check("Umbenannt; im Baum grau und ohne Zahl, weil ohne Modelle", os.path.isdir(os.path.join(samm, "Teile"))
                  and "ohne-modelle" in pg.get_attribute(neu, "class") and pg.inner_text(f"{neu} em") == "")

            # -- Langsamer zweiter Klick auf den gewählten Ordner: Namensfeld; ein Doppelklick nicht
            teile = f'.eintrag[data-ordner="{wid}/Teile"]'
            pg.click(teile)
            pg.wait_for_selector(f"{teile}.aktiv", timeout=5000)
            time.sleep(0.8)
            pg.dblclick(teile)
            time.sleep(0.9)
            check("Doppelklick auf den gewählten Ordner öffnet kein Namensfeld", pg.locator(".baum-name").count() == 0)
            time.sleep(0.8)
            pg.click(teile)
            pg.wait_for_selector(".baum-name", timeout=3000)
            check("Langsamer zweiter Klick auf den gewählten Ordner öffnet das Namensfeld", pg.locator(".baum-name").input_value() == "Teile")
            pg.locator(".baum-name").press("Escape")
            pg.wait_for_selector(teile, timeout=5000)
            time.sleep(0.5)                        # der Baum zeichnet sich nach Esc neu; sonst träfe der nächste Klick noch „Teile“

            # -- Modell: langsamer zweiter Klick auf den Namen, Feld an Ort und Stelle, Endung bleibt; Rückgängig mit Strg+Z
            pg.click(f'.eintrag[data-ordner="{wid}/Ziel"]')
            karte = '.karte:has-text("Anderes")'
            pg.wait_for_selector(karte, timeout=10000)
            pg.click(f"{karte} .bild, {karte} .text >> nth=0")
            time.sleep(0.8)
            pg.click(f"{karte} .name")
            pg.wait_for_selector(".namens-feld", timeout=3000)
            feld = pg.locator(".namens-feld")
            check("Langsamer Klick auf den Namen eines gewählten Modells: Feld mit dem Namen ohne Endung, kein Fenster",
                  feld.input_value() == "Anderes" and not pg.evaluate("document.querySelector('#dialog').open"))
            # Die Seite erfährt die Antwort auf das Umbenennen erst 1,5 s später, der Server ist dann längst fertig. Strg+Z genau in dieser Lücke
            # nahm früher die Aktion davor zurück (den Ordner „Teile“) und meldete „Rückgängig gemacht.“ (nachgestellt 4.11.2026). Verzögert wird
            # in der Seite (fetch), nicht mit pg.route: dessen Handler hielte die Schleife von Playwright an, die Lücke wäre schon zu.
            pg.evaluate("""() => { const f = window.fetchEcht = window.fetch; window.fetch = async (...a) => { const r = await f(...a);
                if ((a[1]?.method || "") === "PATCH") await new Promise((ok) => setTimeout(ok, 1500)); return r; }; }""")
            feld.fill("Anderes v2")
            feld.press("Enter")
            warte(lambda: os.path.isfile(os.path.join(samm, "Ziel", "Anderes v2.stl")), 10)
            check("Enter: Datei auf der Platte umbenannt, Endung geblieben", os.path.isfile(os.path.join(samm, "Ziel", "Anderes v2.stl")))
            pg.evaluate("document.activeElement?.blur()")
            pg.keyboard.press("Control+z")          # die Antwort ist in der Seite noch nicht angekommen
            try:
                warte(lambda: os.path.isfile(os.path.join(samm, "Ziel", "Anderes.stl")), 20)
            except Exception:
                pass
            time.sleep(0.5)
            zustand_text = f"Meldung „{pg.inner_text('#toast')}“, Ordner {sorted(os.listdir(os.path.join(samm, 'Ziel')))}, Wurzel {sorted(os.listdir(samm))}"
            ok = os.path.isfile(os.path.join(samm, "Ziel", "Anderes.stl")) and os.path.isdir(os.path.join(samm, "Teile"))
            check("Strg+Z, während die Antwort aufs Umbenennen noch unterwegs ist: genau dieses Umbenennen zurück, der Ordner davor bleibt"
                  + ("" if ok else f" — {zustand_text}"), ok)
            pg.evaluate("window.fetch = window.fetchEcht")      # wieder ohne Verzögerung weiter
            try:                                    # Rückgängig lädt danach Liste und Inspektor neu: abwarten, sonst trifft F2 ein halb gezeichnetes Modell
                warte(lambda: "Rückgängig gemacht" in pg.inner_text("#toast"), 10)
            except Exception:
                pass
            time.sleep(1)

            # -- F2 auf dem gezeigten Modell; verbotenes Zeichen lässt das Feld offen
            time.sleep(0.5)
            pg.keyboard.press("F2")
            pg.wait_for_selector(".namens-feld", timeout=3000)
            pg.locator(".namens-feld").fill("a?b")
            pg.locator(".namens-feld").press("Enter")
            time.sleep(0.8)
            check("F2 auf dem Modell; verbotenes Zeichen: Meldung, Feld bleibt offen mit dem Getippten",
                  pg.locator(".namens-feld").count() == 1 and pg.locator(".namens-feld").input_value() == "a?b"
                  and "Dateiname darf keines dieser Zeichen" in pg.inner_text("#toast"))
            pg.locator(".namens-feld").press("Escape")
            check("Esc: Feld weg, Datei unverändert", pg.locator(".namens-feld").count() == 0 and os.path.isfile(os.path.join(samm, "Ziel", "Anderes.stl")))

            wurzel = f'.eintrag[data-wurzel="{sw}"]'
            check("Stick eingesteckt: kein Zeichen am Wurzelordner", pg.locator(f"{wurzel}.unerreichbar").count() == 0)
            os.rename(stick, stick + "-ab")
            abfrage(port, "/api/scan", {})
            pg.wait_for_selector(f"{wurzel}.unerreichbar", timeout=20000)
            check("Stick ab und eingelesen: „nicht erreichbar“ am Wurzelordner, ohne die Seite neu zu laden, das Modell bleibt gezählt",
                  "nicht erreichbar" in pg.inner_text(wurzel) and pg.inner_text(f"{wurzel} em").strip() == "1")
            os.rename(stick + "-ab", stick)
            abfrage(port, "/api/scan", {})
            pg.wait_for_selector(f"{wurzel}:not(.unerreichbar)", timeout=20000)
            check("Wieder eingesteckt und eingelesen: das Zeichen ist weg", "nicht erreichbar" not in pg.inner_text(wurzel))
            b.close()
    finally:
        server.terminate()
        server.wait(10)
    muster.ende()
