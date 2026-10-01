"""Die Oberfläche im echten Chromium: Raster, 3D-Ansicht, Ziehen auf
Sammlung und Warteschlange, Löschdialog. Startet den Server als eigenen
Prozess (wie im Betrieb) auf einem freien Port.

Braucht Playwright und Chromium; PARTATLAS_CHROMIUM zeigt auf ein anderes
Chromium als das von Playwright.
"""
import asyncio
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

WURZEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

# Ziehen per DragEvent: Playwrights Mausziehen scheitert an einer Seitenleiste,
# die erst gescrollt werden muss — das prüfte die Maus, nicht die App.
ZIEHEN = """([quelle, ziel]) => {
  const q = document.querySelector(quelle), z = document.querySelector(ziel);
  if (!q || !z) return false;
  const dt = new DataTransfer();
  q.dispatchEvent(new DragEvent('dragstart', {bubbles: true, dataTransfer: dt}));
  z.dispatchEvent(new DragEvent('dragover', {bubbles: true, cancelable: true, dataTransfer: dt}));
  z.dispatchEvent(new DragEvent('drop', {bubbles: true, cancelable: true, dataTransfer: dt}));
  q.dispatchEvent(new DragEvent('dragend', {bubbles: true, dataTransfer: dt}));
  return true;
}"""


def api(port, pfad, daten=None, methode=None):
    anfrage = urllib.request.Request(f"http://127.0.0.1:{port}{pfad}", method=methode or ("POST" if daten is not None else "GET"),
                                     data=json.dumps(daten).encode() if daten is not None else None,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(anfrage) as r:
        return json.loads(r.read() or b"null")


def chromium():
    if os.environ.get("PARTATLAS_CHROMIUM"):
        return os.environ["PARTATLAS_CHROMIUM"]
    treffer = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
    return treffer[-1] if treffer else None


async def oberflaeche(port):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=chromium(),
                                    args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        pg = await b.new_page(viewport={"width": 1400, "height": 900})
        fehler = []
        pg.on("pageerror", lambda e: fehler.append(str(e)))
        pg.on("console", lambda m: fehler.append(m.text) if m.type == "error" else None)

        async def suche(t):
            await pg.fill("#suche", t)
            await pg.wait_for_timeout(700)

        await pg.goto(f"http://127.0.0.1:{port}/")
        # -- Erster Start: Willkommenskarte, Ordner wählen durch Klicken statt Tippen
        await pg.wait_for_selector(".willkommen")
        check("Erster Start: Willkommenskarte, leere Rubriken der Seitenleiste ausgeblendet",
              "Wurzelordner wählen" in await pg.inner_text(".willkommen") and not await pg.locator("text=SAMMLUNGEN").is_visible())
        await pg.click("#wurzel-neu-3")
        await pg.wait_for_selector(".ow-ordner")
        await pg.click(".ow-tippen summary")
        await pg.fill("#ow-pfad", os.path.dirname(SAMMLUNG))
        await pg.click("[data-ow-gehe]")
        await pg.click(f'[data-ow-pfad="{SAMMLUNG}"]')
        await pg.wait_for_function("document.querySelector('.ow-fuss')?.textContent.includes('3 Modelldateien')", timeout=5000)
        check("Ordner-Wähler: hineinklicken, vor dem Bestätigen steht, wie viele Modelldateien drin liegen",
              "3 Modelldateien" in await pg.inner_text(".ow-fuss"))
        await pg.click("#ow-ok")
        await pg.wait_for_selector(".karte", timeout=60000)
        check("Nach dem Bestätigen wird eingelesen, die Kacheln kommen, die Seitenleiste ist vollständig",
              await pg.locator("text=SAMMLUNGEN").is_visible())
        while api(port, "/api/stand")["scan"].get("laeuft"):
            await asyncio.sleep(0.3)
        await pg.wait_for_timeout(500)
        check("Seitenleiste: „Aufräumen“ fehlt, solange es nichts aufzuräumen gibt",
              await pg.locator('[data-sektion="aufraeumen"]').is_hidden())
        await pg.click('[data-sk="tags"]')
        check("Abschnitt per Überschrift aufklappen (Tags standardmässig zu)", await pg.locator("#tag-liste").is_visible())
        await pg.click('[data-sk="tags"]')

        await suche("Vase")
        await pg.locator(".karte").first.click()
        await pg.wait_for_selector("#i-bild canvas", timeout=20000)
        check("Klick auf eine Kachel: 3D-Ansicht im Inspektor", await pg.locator("#i-bild canvas").count() == 1)
        await pg.click('.gal-mini[data-art="berechnet"]')
        await pg.wait_for_timeout(500)
        check("Galerie: Kachel „Vorschau“ zeigt das gerenderte Bild statt 3D",
              await pg.locator("#i-bild img").count() == 1 and await pg.locator("#i-bild canvas").count() == 0)
        await pg.click('.gal-mini[data-art="3d"]')
        await pg.wait_for_selector("#i-bild canvas", timeout=20000)

        # Tag setzen: die 3D-Ansicht bleibt stehen (kein neues Netz).
        canvas = await pg.locator("#i-bild canvas").element_handle()
        await pg.fill("#tag-neu", "deko")
        await pg.press("#tag-neu", "Enter")
        await pg.wait_for_timeout(1200)
        check("Tag im Inspektor gesetzt, Chip sichtbar", "#deko" in await pg.inner_text(".i-tags"))
        check("… und die 3D-Ansicht wurde dabei nicht neu aufgebaut",
              await pg.evaluate("(c) => c.isConnected", canvas))

        # -- Eigene Bilder: zwei auf einmal hinzufügen, das zuletzt geladene wird gezeigt, blättern
        from PIL import Image
        fotos = []
        for i, farbe in enumerate([(200, 40, 40), (40, 40, 200)]):
            fotos.append(os.path.join(os.path.dirname(SAMMLUNG), f"foto{i}.png"))
            Image.new("RGB", (64, 48), farbe).save(fotos[-1])
        await pg.set_input_files("#bild-wahl", fotos)
        await pg.wait_for_function("document.querySelectorAll('.gal-mini[data-art=eigen]').length === 2", timeout=10000)
        await pg.wait_for_timeout(500)
        etikett = await pg.inner_text(".gal-etikett")
        check("Zwei eigene Bilder: vorn in der Leiste, das zuletzt geladene ist zu sehen (2 / 4)",
              etikett.startswith("Eigenes Bild") and "2 / 4" in etikett and await pg.locator("#i-bild img").count() == 1)
        await pg.hover("#i-bild")
        await pg.keyboard.press("ArrowLeft")
        await pg.wait_for_timeout(300)
        await pg.click(".gal-pfeil.links")
        await pg.wait_for_timeout(300)
        check("Blättern mit Pfeiltaste und Pfeil: vom Titelbild rückwärts ans Ende (Vorschau, 4 / 4)",
              (await pg.inner_text(".gal-etikett")).startswith("Vorschau · 4 / 4"))

        # -- Öffnen in …: Hauptknopf mit dem Standard, in den Einstellungen umstellbar
        check("Hauptknopf nennt den Standard fürs Format (STL → Slicer), daneben der CAD-Knopf",
              "PrusaSlicer" in await pg.inner_text("#oeffnen")
              and "FreeCAD" in await pg.inner_text(".i-haupt"))
        await pg.click("#oeffnen")
        await pg.wait_for_timeout(1000)
        check("… und startet ihn mit der Datei des Modells",
              os.path.exists(PROTOKOLL) and "prusa-slicer " in open(PROTOKOLL).read() and "Vase.stl" in open(PROTOKOLL).read())
        await pg.click("#einstellungen")
        await pg.wait_for_selector('[data-prog-std="stl"]')
        freecad = await pg.locator('[data-prog-std="stl"] option', has_text="FreeCAD").get_attribute("value")
        await pg.select_option('[data-prog-std="stl"]', freecad)
        await pg.click('dialog button[value="ja"]')
        await pg.wait_for_timeout(1000)
        check("Einstellungen: STL auf FreeCAD umgestellt, der Hauptknopf folgt",
              "FreeCAD" in await pg.inner_text("#oeffnen"))

        global WID
        WID = api(port, "/api/wurzeln")[0]["id"]
        sid = api(port, "/api/sammlungen", {"name": "Drohne V2"})["id"]
        await pg.wait_for_timeout(800)
        await suche("Arm")
        await pg.evaluate(ZIEHEN, [".karte", f'[data-sammlung="{sid}"]'])
        await pg.wait_for_timeout(800)
        check("Kachel auf Sammlung gezogen: Modell ist in der Sammlung", [m["name"] for m in api(port, f"/api/modelle?sammlung={sid}")] == ["Arm"])

        for name in ["Haken", "Arm", "Vase"]:
            await suche(name)
            await pg.evaluate(ZIEHEN, [".karte", '[data-ansicht="warteschlange"]'])
            await pg.wait_for_timeout(600)
        await suche("")
        # Auf den Zustand warten statt Text zu zerlegen: die Live-Aktualisierung
        # zeichnet die Liste neu, und ein halb gezeichneter Stand warf vorher
        # einen IndexError statt eines FAIL.
        erwartet = ["Haken.stl", "Arm.stl", "Vase.stl"]
        try:
            await pg.wait_for_function("(e) => [...document.querySelectorAll('#ws-liste [data-ws-waehle]')]"
                                       ".map((x) => x.textContent).join('|') === e.join('|')", arg=erwartet, timeout=5000)
        except Exception:
            pass
        check("Drei Kacheln in die Warteschlange gezogen, Liste links nummeriert",
              await pg.locator("#ws-liste [data-ws-waehle]").all_inner_texts() == erwartet
              and await pg.locator("#ws-liste li b").all_inner_texts() == ["1", "2", "3"])
        await pg.evaluate(ZIEHEN, ["#ws-liste li:last-child", "#ws-liste li:first-child"])
        await pg.wait_for_timeout(800)
        check("Warteschlange per Ziehen umsortiert",
              [m["name"] for m in api(port, "/api/warteschlange")] == ["Vase", "Haken", "Arm"])

        # -- Mehrfachauswahl und Aktionsleiste
        await suche("")
        await pg.locator(".karte .wahl").nth(0).click()
        await pg.locator(".karte .wahl").nth(2).click(modifiers=["Shift"])
        check("Kästchen und Umschalt-Klick: Bereich von drei gewählt, Leiste zeigt es",
              "3 ausgewählt" in await pg.inner_text("#stapel"))
        await pg.click('[data-stapel="tag"]')
        await pg.fill("#s-name", "Stapel")
        await pg.click('dialog button[value="ja"]')
        await pg.wait_for_timeout(1000)
        check("Tag für alle Gewählten", len(api(port, "/api/modelle?tag=stapel")) == 3)
        await pg.locator(".karte").nth(1).click(button="right")
        await pg.wait_for_selector("#kontext:not([hidden])")
        check("Rechtsklick in eine Auswahl: Menü für alle drei", "3 MODELLE" in (await pg.inner_text("#kontext")).upper())
        await pg.keyboard.press("Escape")
        await pg.keyboard.press("Escape")
        await pg.wait_for_timeout(300)


        # -- Kachel auf einen Ordner ziehen: Datei wird verschoben
        await pg.click(f'[data-klappe="{WID}"]')
        await pg.wait_for_selector(f'[data-ordner="{WID}/Technik"]')
        await suche("Arm")
        ok = await pg.evaluate(ZIEHEN, [".karte", f'[data-ordner="{WID}/Technik"]'])
        await pg.wait_for_timeout(1200)
        check("Kachel auf Ordner gezogen: Datei auf der Platte verschoben",
              ok and os.path.exists(os.path.join(SAMMLUNG, "Technik", "Arm.stl")) and not os.path.exists(os.path.join(SAMMLUNG, "Arm.stl")))

        # -- Rechtsklick auf eine Kachel
        await pg.locator(".karte").first.click(button="right")
        await pg.wait_for_selector("#kontext:not([hidden])")
        menu = await pg.inner_text("#kontext")
        mid = await pg.locator(".karte").first.get_attribute("data-id")
        vorher = next(m for m in api(port, "/api/modelle") if m["id"] == mid)["favorit"]
        await pg.click('[data-km="favorit1"]')
        await pg.wait_for_timeout(600)
        check("Rechtsklick: Slicer und CAD getrennt, je mit dem Programm, das das Format kann",
              "In PrusaSlicer öffnen" in menu and "In FreeCAD öffnen" in menu)
        check("Rechtsklick: Öffnen, Im Ordner zeigen, Löschen im Menü; Favorit umschalten wirkt",
              "Im Ordner zeigen" in menu and "Löschen" in menu
              and next(m for m in api(port, "/api/modelle") if m["id"] == mid)["favorit"] != vorher
              and await pg.locator("#kontext").is_hidden())

        # -- Quelle als Link
        await pg.locator(".karte").first.click()
        await pg.wait_for_selector("#i-details summary")
        await pg.click("#i-details summary")
        await pg.click("#quelle-aendern")
        await pg.fill("#quelle-url", "https://www.printables.com/model/42")
        await pg.click('dialog button[value="ja"]')
        await pg.wait_for_timeout(1000)
        link = pg.locator(".quelle a")
        check("Quelle im Inspektor als Link, öffnet in neuem Tab ohne Zugriff auf partAtlas",
              await link.get_attribute("href") == "https://www.printables.com/model/42"
              and "noopener" in (await link.get_attribute("rel")))

        # -- Baugruppe: öffnen, zählen, Kaufteil aus dem Katalog
        bid = api(port, "/api/baugruppen", {"name": "Testaufbau", "modelle": [m["id"] for m in api(port, "/api/modelle")][:2]})["id"]
        await suche("")
        await pg.wait_for_selector(f'#baugruppen [data-baugruppe="{bid}"]')
        await pg.click(f'#baugruppen [data-baugruppe="{bid}"]')
        await pg.wait_for_selector(".bg-titel")
        check("Baugruppe öffnet ihre eigene Ansicht statt des Rasters",
              await pg.locator("#raster").is_hidden() and "Testaufbau" in await pg.inner_text(".bg-titel"))
        rechts = await pg.inner_text("#inspektor")
        check("Übersicht steht rechts: Filament, Druckzeit, PDF — die Mitte bleibt der Stückliste",
              "FILAMENT" in rechts and "DRUCKZEIT" in rechts and "PDF" in rechts
              and await pg.locator("#bg-ansicht .mischung").count() == 0)
        await pg.locator("#bg-ansicht .pos .name").first.click()
        await pg.wait_for_selector("#bg-zurueck")
        await pg.click("#bg-zurueck")
        await pg.wait_for_timeout(300)
        check("Klick auf ein Teil zeigt das Modell, „← Baugruppe“ führt zur Übersicht zurück",
              "DRUCKZEIT" in await pg.inner_text("#inspektor"))
        await pg.click('[data-bg-aktion="kaufteile"]')
        await pg.wait_for_selector("#w-liste .w-zeile")
        await pg.fill("#w-suche", "m3x10")
        await pg.wait_for_timeout(600)
        await pg.fill('[data-w-menge="PURCHASED_PART/din912-m3x10"]', "6")
        await pg.click('[data-w-plus="PURCHASED_PART/din912-m3x10"]')
        await pg.wait_for_timeout(600)
        await pg.click('dialog button[value="fertig"]')
        await pg.wait_for_timeout(800)
        check("Kaufteil aus dem Katalog mit Menge, erscheint in der Einkaufsliste",
              "KAUFTEILE" in await pg.inner_text("#inspektor") and "6×" in await pg.inner_text("#inspektor"))
        await pg.click('[data-ansicht="alle"]')
        await pg.wait_for_timeout(600)

        # -- Datei im Dateimanager gelöscht: Kachel bleibt, deutlich markiert
        os.remove(os.path.join(SAMMLUNG, "Technik", "Arm.stl"))
        api(port, "/api/scan", {})
        while api(port, "/api/stand")["scan"].get("laeuft"):
            time.sleep(0.3)
        await suche("Arm")
        await pg.wait_for_selector(".karte.fehlt .fehlt-band", timeout=5000)
        check("Datei fehlt: Kachel bleibt im Raster, mit Band „Datei fehlt“",
              "Datei fehlt" in await pg.inner_text(".karte.fehlt .fehlt-band"))
        check("… und „Aufräumen“ erscheint mit „Datei fehlt 1“",
              "Datei fehlt" in await pg.inner_text('[data-sektion="aufraeumen"]')
              and await pg.locator('[data-sektion="aufraeumen"] [data-ansicht="duplikate"]').is_hidden())

        await suche("Haken")
        await pg.locator(".karte").first.click()
        await pg.wait_for_selector("#mehr-knopf")
        check("Inspektor: Hauptaktion oben, seltene im Menü — Löschen erst nach „⋯“",
              await pg.locator("#oeffnen").is_visible() and not await pg.locator("#loeschen").is_visible())
        await pg.click("#mehr-knopf")
        await pg.click("#loeschen")
        await pg.wait_for_selector("dialog[open]")
        text = await pg.inner_text("dialog")
        check("Löschdialog in Klartext: Datei, Warteschlange, Tags — kein Technikwort",
              "Haken.stl" in text and "Warteschlange" in text and "Tags:" in text and "HAS_TAG" not in text)
        await pg.click('dialog button[value="ja"]')
        await pg.wait_for_timeout(1000)
        check("Keine Fehler in der Browser-Konsole", fehler == [])
        if fehler:
            print("   ", fehler)
        await b.close()


if __name__ == "__main__":
    if not chromium():
        print("Kein Chromium gefunden (PARTATLAS_CHROMIUM setzen).")
        sys.exit(1)
    tmp = tempfile.mkdtemp()
    sammlung = os.path.join(tmp, "3D-Druck")
    os.makedirs(sammlung)
    SAMMLUNG = sammlung
    os.makedirs(os.path.join(sammlung, "Technik"))
    muster.stl_binaer(os.path.join(sammlung, "Arm.stl"), 120, 20, 6)
    muster.stl_binaer(os.path.join(sammlung, "Technik", "Haken.stl"), 10, 30, 40)
    sys.path.insert(0, os.path.join(WURZEL, "werkzeuge"))
    import demo_sammlung
    demo_sammlung.stl(os.path.join(sammlung, "Vase.stl"),
                      demo_sammlung.drehkoerper([(0.01, 0), (20, 0.5), (26, 30), (18, 60), (0.01, 60)], 64, drall=0.03))

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    # Attrappen für Slicer und CAD: schreiben nur auf, womit sie gestartet wurden.
    global PROTOKOLL
    attrappen, PROTOKOLL = os.path.join(tmp, "bin"), os.path.join(tmp, "gestartet.txt")
    os.makedirs(attrappen)
    for name in ("freecad", "prusa-slicer"):
        with open(os.path.join(attrappen, name), "w") as f:
            f.write(f'#!/bin/sh\necho "{name} $*" >> "{PROTOKOLL}"\n')
        os.chmod(os.path.join(attrappen, name), 0o755)
    umgebung = {**os.environ, "PARTATLAS_BESTAND": os.path.join(tmp, "bestand"), "PARTATLAS_PORT": str(port),
                "PYTHONPATH": os.environ.get("PARTATLAS_QUELLE") or WURZEL,
                "PATH": attrappen + os.pathsep + os.environ["PATH"]}
    # cwd nicht im Repo: `python -m` setzt das Arbeitsverzeichnis vor
    # PYTHONPATH, und die Gegenprobe prüfte sonst das echte Paket.
    server = subprocess.Popen([sys.executable, "-m", "partatlas"], env=umgebung, cwd=tmp,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                api(port, "/api/stand")
                break
            except OSError:
                time.sleep(0.1)
        asyncio.run(oberflaeche(port))
    finally:
        server.terminate()
        server.wait(10)
    muster.ende()
