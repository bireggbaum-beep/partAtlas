"""Einstellungen › Programme: die Slicerliste. Alle erkannten Slicer stehen da, der Standard trägt die Marke und lässt sich wählen (auch mit
den Pfeiltasten), gleichnamige unterscheidet die Herkunft, × blendet aus bzw. entfernt (nicht den Standard), „＋ Hinzufügen“ nimmt den Pfad aus dem
Dateidialog des Rechners, und gespeichert wird erst mit „Speichern“. Gezielt, ohne test_ui: ein eigener Server mit Attrappen-Programmen."""
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
    muster.zeitgrenze(120)
    from playwright.sync_api import sync_playwright
    tmp = tempfile.mkdtemp()
    heim = os.path.join(tmp, "heim")
    attrappen = os.path.join(tmp, "bin")

    def attrappe(ordner, name):
        os.makedirs(ordner, exist_ok=True)
        pfad = os.path.join(ordner, name)
        with open(pfad, "w") as f:
            f.write("#!/bin/sh\nexit 0\n")
        os.chmod(pfad, 0o755)
        return pfad

    # Sechs bekannte Slicer, dazu ein zweiter OrcaSlicer als AppImage (gleicher Name) und ein FreeCAD.
    pfade = {n: attrappe(attrappen, n) for n in ("bambu-studio", "orca-slicer", "prusa-slicer", "superslicer", "cura", "AnycubicSlicerNext", "freecad")}
    orca_ai = attrappe(os.path.join(heim, "Applications"), "OrcaSlicer-2.3.0.AppImage")
    mein = attrappe(os.path.join(tmp, "selbst"), "mein-slicer")
    solid = attrappe(os.path.join(tmp, "solidcraft"), "SolidCraft")
    antwort = os.path.join(tmp, "antwort.txt")
    with open(os.path.join(attrappen, "zenity"), "w") as f:                    # der Dateidialog des Rechners
        f.write(f'#!/bin/sh\ncat "{antwort}"\n[ -s "{antwort}" ]\n')
    os.chmod(os.path.join(attrappen, "zenity"), 0o755)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    umgebung = {**os.environ, "PARTATLAS_BESTAND": os.path.join(tmp, "bestand"), "PARTATLAS_PORT": str(port), "PATH": attrappen + ":/usr/bin:/bin",
                "HOME": heim, "XDG_DATA_HOME": os.path.join(tmp, "daten"), "PYTHONPATH": os.environ.get("PARTATLAS_QUELLE") or os.path.join(HIER, "..")}
    server = subprocess.Popen([sys.executable, "-m", "partatlas"], env=umgebung, cwd=tmp, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        warte(lambda: abfrage(port, "/api/zaehler") is not None)
        abfrage(port, "/api/neuigkeiten/gesehen", {})
        liste = lambda: abfrage(port, "/api/programme")
        slicer = lambda: [p for p in liste()["programme"] if p["art"] == "slicer"]
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chromium())
            pg = b.new_page(viewport={"width": 1400, "height": 900})
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_selector("#einstellungen")
            pg.evaluate("localStorage.setItem('partatlas.einstellungen-abschnitt', 'slicer')")

            def oeffnen():
                pg.click("#einstellungen")
                pg.wait_for_selector("#prog-slicer .prog-zeile")

            def zeilen():
                return pg.eval_on_selector_all("#prog-slicer .prog-zeile", "l => l.map(z => ({name: z.querySelector('label').textContent, pfad: z.querySelector('code').title,"
                                               " ort: z.querySelector('.prog-ort')?.textContent || '', marke: z.querySelector('.prog-marke')?.textContent || '',"
                                               " gewaehlt: z.querySelector('input').checked, weg: z.querySelector('.prog-weg').getAttribute('aria-disabled') !== 'true'}))")

            def speichern():
                pg.evaluate("document.querySelector('#toast').textContent = ''")
                pg.click("dialog button.akzent")
                pg.wait_for_function("document.querySelector('#toast').textContent.includes('Gespeichert')")        # erst dann hat der Server geantwortet

            oeffnen()
            if os.environ.get("PARTATLAS_BILD"):
                pg.screenshot(path=os.environ["PARTATLAS_BILD"])
            z = zeilen()
            check(f"Alle erkannten Slicer stehen in der Liste ({[x['name'] for x in z]})", len(z) == 7 and {x["name"] for x in z} >=
                  {"Bambu Studio", "OrcaSlicer", "PrusaSlicer", "SuperSlicer", "UltiMaker Cura", "Anycubic Slicer"})
            check("Der bisherige Standard (erster Fund) ist gewählt und trägt die Marke „Standard (automatisch)“",
                  [x["name"] for x in z if x["gewaehlt"]] == ["Bambu Studio"] and z[0]["marke"] == "Standard (automatisch)" and not z[1]["marke"])
            orcas = [x for x in z if x["name"] == "OrcaSlicer"]
            check("Gleichnamige zeigen ihre Herkunft (System, AppImage), eindeutige keine",
                  sorted(x["ort"] for x in orcas) == ["AppImage", "System"] and all(not x["ort"] for x in z if x["name"] != "OrcaSlicer"))
            check("Radio-Gruppe mit Beschriftung (Leseprogramme), jeder Pfad ist der Beschreibung des Radios",
                  pg.eval_on_selector("#prog-slicer fieldset legend", "e => e.textContent") == "Slicer"
                  and pg.eval_on_selector_all("#prog-slicer input[name=prog-std-slicer]", "l => l.every(r => document.getElementById(r.getAttribute('aria-describedby')))"))
            check("Der Standard hat kein wirksames ×, die anderen schon", [x["weg"] for x in z] == [False] + [True] * 6)
            check("Slicer und CAD haben je einen Reiter; der Reiter Slicer ist offen, der des CADs verborgen",
                  pg.locator("[data-ein=slicer].aktiv").count() == 1 and pg.locator("[data-ein=cad]").count() == 1
                  and pg.is_visible("#prog-slicer") and not pg.is_visible("#prog-cad"))
            pg.click("[data-ein=cad]")
            check("CAD ist eine Liste wie der Slicer (#29): FreeCAD als Standard gewählt, mit ＋ Hinzufügen",
                  pg.locator("#prog-cad input[name=prog-std-cad]:checked").count() == 1 and "FreeCAD" in pg.inner_text("#prog-cad .prog-zeile.ist")
                  and pg.locator("#prog-cad [data-prog-neu=cad]").is_visible())
            check("… und sagt, welches FreeCAD Vorschaubilder und Masse rechnet — unabhängig vom Standard",
                  pfade["freecad"] in pg.inner_text("#prog-cad .prog-einlesen"))
            pg.click("[data-ein=slicer]")

            # Tastatur: Pfeil nach unten wählt den nächsten
            pg.focus("#prog-slicer input[name=prog-std-slicer]:checked")
            pg.keyboard.press("ArrowDown")
            z = zeilen()
            check("Mit der Pfeiltaste ist der nächste Slicer Standard, die Marke zieht mit, der Fokus bleibt im Radio",
                  z[1]["gewaehlt"] and z[1]["marke"] == "Standard" and not z[0]["marke"]
                  and pg.evaluate("document.activeElement?.name") == "prog-std-slicer")
            check("… gespeichert ist noch nichts", slicer()[0]["pfad"] == pfade["bambu-studio"])
            pg.click("dialog button[value=nein]")
            check("Abbrechen verwirft die Wahl", slicer()[0]["pfad"] == pfade["bambu-studio"])

            # Standard wählen und speichern
            oeffnen()
            pg.click("#prog-slicer label:text-is('PrusaSlicer')")
            z = zeilen()
            check("Per Klick gewählt: PrusaSlicer trägt die Marke ohne „automatisch“", [x["marke"] for x in z if x["name"] == "PrusaSlicer"] == ["Standard"])
            speichern()
            check("Gespeichert: PrusaSlicer führt die Liste und ist ausdrücklich der Standard",
                  slicer()[0]["pfad"] == pfade["prusa-slicer"] and slicer()[0]["standard"]
                  and abfrage(port, "/api/einstellungen")["programm"]["slicer"]["automatisch"] is False)

            # Ausblenden: erst mit Speichern
            oeffnen()
            check("Neu geöffnet: der Standard steht oben", zeilen()[0]["name"] == "PrusaSlicer" and zeilen()[0]["gewaehlt"])
            pg.click("#prog-slicer [aria-label='Ausblenden: SuperSlicer']")
            z = zeilen()
            check("× blendet aus: SuperSlicer fehlt, ein Weg zum Wiederanzeigen erscheint",
                  "SuperSlicer" not in [x["name"] for x in z] and pg.locator("#prog-slicer [data-prog-zeigen]").count() == 1)
            pg.click("#prog-slicer [aria-label='Ausblenden: UltiMaker Cura']")
            check("Zwei Ausgeblendete: der Weg nennt die Zahl", "2" in pg.inner_text("#prog-slicer [data-prog-zeigen]"))
            pg.click("#prog-slicer [data-prog-zeigen]")
            check("Wieder anzeigen (vor dem Speichern): beide sind zurück", {"SuperSlicer", "UltiMaker Cura"} <= {x["name"] for x in zeilen()}
                  and pg.locator("#prog-slicer [data-prog-zeigen]").count() == 0)
            pg.click("#prog-slicer [aria-label='Ausblenden: SuperSlicer']")
            pg.click("dialog button[value=nein]")
            check("Abbrechen: nichts ist ausgeblendet", liste()["ausgeblendet"] == [])
            oeffnen()
            pg.click("#prog-slicer [aria-label='Ausblenden: SuperSlicer']")
            speichern()
            check("Gespeichert: SuperSlicer ist ausgeblendet und fehlt in der Liste", [x["name"] for x in liste()["ausgeblendet"]] == ["SuperSlicer"]
                  and "SuperSlicer" not in [x["name"] for x in slicer()])
            oeffnen()
            check("Neu geöffnet: er bleibt weg, der Weg zum Wiederanzeigen ist da",
                  "SuperSlicer" not in [x["name"] for x in zeilen()] and pg.locator("#prog-slicer [data-prog-zeigen]").count() == 1)
            pg.click("#prog-slicer [data-prog-zeigen]")
            speichern()
            check("Wieder angezeigt und gespeichert", liste()["ausgeblendet"] == [] and "SuperSlicer" in [x["name"] for x in slicer()])

            # Hinzufügen und Entfernen
            oeffnen()
            open(antwort, "w").close()
            pg.click("#prog-slicer [data-prog-neu]")
            pg.wait_for_selector("#prog-slicer [data-prog-neu]:not([disabled])")
            check("Dateidialog abgebrochen: nichts kommt dazu", len(zeilen()) == 7)
            with open(antwort, "w") as f:
                f.write(mein + "\n")
            pg.click("#prog-slicer [data-prog-neu]")
            pg.wait_for_function("document.querySelectorAll('#prog-slicer .prog-zeile').length === 8")
            neu = zeilen()[-1]
            check("＋ Hinzufügen: der gewählte Slicer steht unten, als Herkunft nur bei Gleichnamigen, mit wirksamem ×",
                  neu["pfad"] == mein and neu["name"] == "mein-slicer" and neu["weg"] and not neu["gewaehlt"])
            pg.click("#prog-slicer [data-prog-neu]")
            pg.wait_for_selector("#prog-slicer [data-prog-neu]:not([disabled])")
            check("Denselben noch einmal: er steht nur einmal da", len(zeilen()) == 8)
            check("… gespeichert ist noch nichts", mein not in [x["pfad"] for x in slicer()])
            speichern()
            check("Gespeichert: der eigene Slicer ist in der Liste, der Standard bleibt PrusaSlicer",
                  mein in [x["pfad"] for x in slicer()] and slicer()[0]["name"] == "PrusaSlicer")
            oeffnen()
            pg.click("#prog-slicer [aria-label='Entfernen: mein-slicer']")
            check("× bei einem hinzugefügten: er ist weg und lässt sich nicht „wieder anzeigen“",
                  "mein-slicer" not in [x["name"] for x in zeilen()] and pg.locator("#prog-slicer [data-prog-zeigen]").count() == 0)
            speichern()
            check("Gespeichert: entfernt", mein not in [x["pfad"] for x in slicer()])

            # CAD: SolidCraft hinzufügen und zum Standard machen — das Einlesen bleibt bei FreeCAD
            oeffnen()
            pg.click("[data-ein=cad]")
            with open(antwort, "w") as f:
                f.write(solid + "\n")
            pg.click("#prog-cad [data-prog-neu]")
            pg.wait_for_function("document.querySelectorAll('#prog-cad .prog-zeile').length === 2")
            pg.click("[data-ein=slicer]")             # der Dialog merkt sich den Reiter; die übrigen Prüfungen öffnen ihn beim Slicer
            speichern()
            check("CAD: ein hinzugefügtes Programm bleibt nach dem Speichern in der Liste, auch ohne Standard zu sein",
                  [(p["name"], p["standard"]) for p in liste()["programme"] if p["art"] == "cad"] == [("FreeCAD", True), ("SolidCraft", False)])
            oeffnen()
            pg.click("[data-ein=cad]")
            pg.click("#prog-cad label:text-is('SolidCraft')")
            pg.click("[data-ein=slicer]")
            speichern()
            l = liste()
            check("CAD: SolidCraft hinzugefügt und als Standard gespeichert — STEP öffnet sich darin, FCStd weiter in FreeCAD",
                  [(p["name"], p["standard"]) for p in l["programme"] if p["art"] == "cad"] == [("SolidCraft", True), ("FreeCAD", False)]
                  and l["standard"]["step"] == solid and l["standard"]["fcstd"] == pfade["freecad"])
            check("… das Einlesen bleibt bei FreeCAD", l["einlesen_freecad"] == pfade["freecad"])
            oeffnen()
            pg.click("[data-ein=cad]")
            pg.click("#prog-cad [data-prog-auto=cad]")
            pg.click("#prog-cad [aria-label='Entfernen: SolidCraft']")
            pg.click("[data-ein=slicer]")
            speichern()
            check("CAD wieder automatisch, SolidCraft entfernt: FreeCAD allein und Standard",
                  [(p["name"], p["standard"]) for p in liste()["programme"] if p["art"] == "cad"] == [("FreeCAD", True)])

            # Der Standard lässt sich nicht entfernen
            oeffnen()
            pg.click("#prog-slicer [aria-label='Ausblenden: PrusaSlicer']", force=True)       # aria-disabled: Playwright hält es für gesperrt, ein Mensch kann klicken
            check("× beim Standard: nichts wird entfernt, ein Hinweis sagt warum", zeilen()[0]["name"] == "PrusaSlicer" and len(zeilen()) == 7
                  and "Standard" in pg.inner_text("#toast"))

            # Wieder automatisch
            pg.click("#prog-slicer [data-prog-auto=slicer]")
            check("„Wieder automatisch“: kein Radio mehr gewählt, der Hinweis erklärt es", not any(x["gewaehlt"] for x in zeilen())
                  and "Automatisch" in pg.inner_text("#prog-slicer"))
            speichern()
            check("Gespeichert: der erste Fund (Bambu Studio) ist wieder Standard, automatisch",
                  slicer()[0]["pfad"] == pfade["bambu-studio"] and abfrage(port, "/api/einstellungen")["programm"]["slicer"]["automatisch"])
            # Ein Sprung aus „Öffnen mit › Programme einstellen“ bzw. dem gedämpften Knopf: der Reiter der Art; der alte Reiter „programme“ führt zum Slicer
            for gemerkt, sichtbar in (("cad", "#prog-cad"), ("slicer", "#prog-slicer"), ("programme", "#prog-slicer")):
                pg.evaluate(f"localStorage.setItem('partatlas.einstellungen-abschnitt', '{gemerkt}')")
                pg.click("#einstellungen")
                pg.wait_for_selector(sichtbar, state="visible")
                check(f"Gemerkter Reiter „{gemerkt}“ öffnet {sichtbar}", pg.is_visible(sichtbar))
                pg.click("dialog button[value=nein]")
            b.close()
    finally:
        server.terminate()
        server.wait(10)
    muster.ende()
