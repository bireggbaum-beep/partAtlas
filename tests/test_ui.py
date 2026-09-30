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
        await pg.wait_for_selector(".karte")
        check("Raster zeigt Kacheln mit Namen und Endung",
              "Vase.stl" in await pg.locator(".karte .name").all_inner_texts())

        await suche("Vase")
        await pg.locator(".karte").first.click()
        await pg.wait_for_selector("#i-bild canvas", timeout=20000)
        check("Klick auf eine Kachel: 3D-Ansicht im Inspektor", await pg.locator("#i-bild canvas").count() == 1)
        await pg.click('[data-ansicht3d="bild"]')
        await pg.wait_for_timeout(500)
        check("Umschalten auf Bild: gerenderte Vorschau statt 3D",
              await pg.locator("#i-bild img").count() == 1 and await pg.locator("#i-bild canvas").count() == 0)
        await pg.reload()
        await pg.wait_for_selector(".karte")
        await suche("Vase")
        await pg.locator(".karte").first.click()
        await pg.wait_for_timeout(1000)
        check("Die Wahl „Bild“ bleibt nach dem Neuladen", await pg.locator("#i-bild img").count() == 1)
        await pg.click('[data-ansicht3d="3d"]')
        await pg.wait_for_selector("#i-bild canvas", timeout=20000)

        # Tag setzen: die 3D-Ansicht bleibt stehen (kein neues Netz).
        canvas = await pg.locator("#i-bild canvas").element_handle()
        await pg.fill("#tag-neu", "deko")
        await pg.press("#tag-neu", "Enter")
        await pg.wait_for_timeout(1200)
        check("Tag im Inspektor gesetzt, Chip sichtbar", "#deko" in await pg.inner_text(".i-tags"))
        check("… und die 3D-Ansicht wurde dabei nicht neu aufgebaut",
              await pg.evaluate("(c) => c.isConnected", canvas))

        global WID
        WID = api(port, "/api/wurzeln")[0]["id"]
        sid = api(port, "/api/sammlungen", {"name": "Drohne V2"})["id"]
        await pg.wait_for_timeout(800)
        await suche("Arm")
        check("Kachel auf Sammlung ziehen", await pg.evaluate(ZIEHEN, [".karte", f'[data-sammlung="{sid}"]']))
        await pg.wait_for_timeout(800)
        check("… Modell ist in der Sammlung", [m["name"] for m in api(port, f"/api/modelle?sammlung={sid}")] == ["Arm"])

        for name in ["Haken", "Arm", "Vase"]:
            await suche(name)
            await pg.evaluate(ZIEHEN, [".karte", '[data-ansicht="warteschlange"]'])
            await pg.wait_for_timeout(600)
        await suche("")
        check("Drei Kacheln in die Warteschlange gezogen, Liste links nummeriert",
              [x.split("\n")[1] for x in await pg.locator("#ws-liste li").all_inner_texts()] == ["Haken.stl", "Arm.stl", "Vase.stl"])
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
        await pg.keyboard.press("Escape")
        await pg.wait_for_timeout(300)
        check("Escape hebt die Auswahl auf", await pg.locator("#stapel").is_hidden())

        # -- Liste
        await pg.click('[data-layout="liste"]')
        await pg.wait_for_timeout(500)
        check("Listenansicht: Zeilen mit Spaltenkopf", await pg.locator(".zeile-l").count() == 3
              and "GEWICHT" in await pg.inner_text("#listenkopf"))
        await pg.click('[data-layout="raster"]')
        await pg.wait_for_timeout(500)

        # -- Kachel auf einen Ordner ziehen: Datei wird verschoben
        await pg.click(f'[data-klappe="{WID}"]')
        await pg.wait_for_selector(f'[data-ordner="{WID}/Technik"]')
        await suche("Arm")
        ok = await pg.evaluate(ZIEHEN, [".karte", f'[data-ordner="{WID}/Technik"]'])
        await pg.wait_for_timeout(1200)
        check("Kachel auf Ordner gezogen: Datei auf der Platte verschoben",
              ok and os.path.exists(os.path.join(SAMMLUNG, "Technik", "Arm.stl")) and not os.path.exists(os.path.join(SAMMLUNG, "Arm.stl")))

        # -- Quelle als Link
        await pg.locator(".karte").first.click()
        await pg.wait_for_selector("#quelle-aendern")
        await pg.click("#quelle-aendern")
        await pg.fill("#quelle-url", "https://www.printables.com/model/42")
        await pg.click('dialog button[value="ja"]')
        await pg.wait_for_timeout(1000)
        link = pg.locator(".quelle a")
        check("Quelle im Inspektor als Link, öffnet in neuem Tab ohne Zugriff auf partAtlas",
              await link.get_attribute("href") == "https://www.printables.com/model/42"
              and "noopener" in (await link.get_attribute("rel")))

        await suche("Haken")
        await pg.locator(".karte").first.click()
        await pg.wait_for_selector("#loeschen")
        await pg.click("#loeschen")
        await pg.wait_for_selector("dialog[open]")
        text = await pg.inner_text("dialog")
        check("Löschdialog nennt Datei und Verknüpfungen (loeschfolgen)", "Haken.stl" in text and "HAS_TAG" in text)
        await pg.click('dialog button[value="ja"]')
        await pg.wait_for_timeout(1000)
        check("Nach dem Löschen: im Papierkorb und nicht mehr in der Warteschlange",
              api(port, "/api/zaehler")["papierkorb"] == 1
              and [m["name"] for m in api(port, "/api/warteschlange")] == ["Vase", "Arm"])
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
    umgebung = {**os.environ, "PARTATLAS_BESTAND": os.path.join(tmp, "bestand"), "PARTATLAS_PORT": str(port),
                "PYTHONPATH": os.environ.get("PARTATLAS_QUELLE") or WURZEL}
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
        api(port, "/api/wurzeln", {"pfad": sammlung})
        while api(port, "/api/stand")["scan"].get("laeuft"):
            time.sleep(0.3)
        asyncio.run(oberflaeche(port))
    finally:
        server.terminate()
        server.wait(10)
    muster.ende()
