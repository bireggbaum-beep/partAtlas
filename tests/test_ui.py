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
muster.zeitgrenze(900)       # startet Chromium und einen Server: mehrere Minuten
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

        await pg.goto(f"http://127.0.0.1:{port}/?phase=2")
        # -- Erster Start: Willkommenskarte, Ordner wählen durch Klicken statt Tippen
        await pg.wait_for_selector(".willkommen")
        check("Erster Start: Willkommenskarte, leere Rubriken der Seitenleiste ausgeblendet",
              "Wurzelordner wählen" in await pg.inner_text(".willkommen") and not await pg.locator("text=SAMMLUNGEN").is_visible())
        await pg.click("#wurzel-neu-3")                    # der Ordnerdialog des Rechners (Attrappe) wählt die Sammlung
        await pg.wait_for_selector("#dialog[open]")
        text = await pg.inner_text("#dialog")
        check("Vor dem Einlesen eine Übersicht: wie viele Modelldateien, je Format, mit Einlesen oder Abbrechen",
              "Modelldateien" in text and "STL" in text and await pg.locator('#dialog button[value="nein"]').count() == 1)
        await pg.evaluate("""() => { window.__gedreht = false; new MutationObserver(() => {
            if ($("#neu-einlesen-2").classList.contains("dreht")) window.__gedreht = true; }).observe($("#neu-einlesen-2"), { attributes: true }); }""")
        await pg.click('#dialog button[value="ja"]')
        await pg.wait_for_function("!document.querySelector('#toast').hidden && document.querySelector('#toast').innerText.includes('neue Modelle')", timeout=60000)
        text = await pg.inner_text("#toast")
        check("Einlesen ohne Fenster: ⟳ dreht sich, am Ende eine Meldung mit der Zahl der neuen Modelle und „Zeigen“",
              await pg.evaluate("window.__gedreht") and "3 neue Modelle" in text and "Zeigen" in text
              and await pg.locator("dialog[open]").count() == 0)
        await pg.wait_for_function("!document.querySelector('#neu-einlesen-2').classList.contains('dreht')")
        check("Nach dem Einlesen steht das Ergebnis neben „Bibliothek“", "3 neu" in await pg.inner_text("#zuletzt-eingelesen"))
        fehlerbild = await pg.evaluate("""() => {
            const g = einlesen.gemeldet;
            einlesenZeichnen({ lauf: 98, laeuft: false, phase: "fehler", abbruch: "No space left on device" });
            const r = { text: $("#toast").innerText, sichtbar: !$("#toast").hidden, zeile: $("#zuletzt-eingelesen").innerText,
                        offen: !!document.querySelector("dialog[open]") };
            einlesen.gemeldet = g; einlesenZeichnen(zustand.scan || {}); $("#toast").hidden = true;
            return r;
        }""")
        check("Einlesen an einem Fehler gescheitert: eine Meldung nennt den Grund, neben „Bibliothek“ steht „gescheitert“, kein Fenster wartet",
              fehlerbild["sichtbar"] and "No space left" in fehlerbild["text"] and "gescheitert" in fehlerbild["zeile"] and not fehlerbild["offen"])
        await pg.wait_for_selector(".karte", timeout=60000)
        check("Ordner über den Dialog des Rechners gewählt: es wird eingelesen, die Kacheln kommen, die Seitenleiste ist vollständig",
              await pg.locator("text=SAMMLUNGEN").is_visible())
        while api(port, "/api/stand")["scan"].get("laeuft"):
            await asyncio.sleep(0.3)
        await pg.wait_for_timeout(500)
        # -- Bedienbarkeit während des Einlesens: nicht bei jeder Änderung die ganze Liste neu holen
        rl = await pg.evaluate("""async () => {
            // In einer Ansicht, die ganz lädt („Neu“); in den anderen wird nachgereicht (geprüft weiter unten).
            const orig = window.neuLaden, alt = zustand.scan, ansicht = zustand.ansicht; let n = 0;
            window.neuLaden = () => { n++; }; zustand.ansicht = "neu";
            clearTimeout(liveZeit); liveZeit = null; letztesLiveLaden = 0;       // ein Zeitgeber vom echten Einlesen davor ist noch offen
            LIVE_SCAN_MS = 400; zustand.scan = { laeuft: true };
            for (let i = 0; i < 20; i++) { liveAenderung({ ref: "x" }); await new Promise((r) => setTimeout(r, 50)); }   // eine Änderung alle 50 ms, 1 s lang
            const waehrend = n;
            n = 0; clearTimeout(liveZeit); liveZeit = null; letztesLiveLaden = 0; liveAenderung({ ref: "y" });
            await new Promise((r) => setTimeout(r, 60));
            const sofort = n;           // die erste Änderung nach einer Ruhepause lädt gleich, nicht erst nach LIVE_SCAN_MS
            await new Promise((r) => setTimeout(r, 600));
            const mit = zustand.modelle.length;
            const g = einlesen.gemeldet;
            const ohne = (() => { n = 0; liveScan({ art: "scan", laeuft: false, phase: "fertig", neu: 0, gefunden: mit, dauer_s: 1, einlesen_s: 1, lauf: 99 }); return n; })();
            const mitFunden = (() => { n = 0; liveScan({ art: "scan", laeuft: false, phase: "fertig", neu: 5, gefunden: mit, dauer_s: 1, einlesen_s: 1, lauf: 100 }); return n; })();
            window.neuLaden = orig; zustand.scan = alt; zustand.ansicht = ansicht; LIVE_SCAN_MS = 5000; einlesen.gemeldet = g; einlesenZeichnen(alt || {}); $("#toast").hidden = true;
            return [waehrend, ohne, mitFunden, mit, sofort];
        }""")
        check("Beim Einlesen wird die Liste höchstens alle paar Sekunden neu geholt, nicht bei jeder Änderung (20 Änderungen in 1 s → 2 Neuladen bei 400 ms)",
              1 <= rl[0] <= 4)
        check("Die erste Änderung nach einer Ruhepause lädt sofort (kleiner Import: die Modelle erscheinen gleich, nicht erst nach 5 s)", rl[4] == 1)
        check("Ein Einlesen ohne Funde lädt am Ende nichts neu, eines mit Funden einmal", rl[3] > 0 and rl[1] == 0 and rl[2] == 1)
        # -- Nur die neueste Listenantwort zählt (bei 9 000 Modellen dauert eine Liste Sekunden; eine ältere kam sonst über eine neuere)
        n_alt = await pg.evaluate("""async () => {
            const echt = api; let erste = true;
            api = async (pfad, o) => {
                if (erste && pfad.startsWith("/api/modelle?")) {
                    erste = false; const r = await echt(pfad, o);
                    await new Promise((z) => setTimeout(z, 800));
                    return { modelle: [], leiste: r.leiste };        // die langsame, ältere Antwort: ein anderer Stand (keine Kacheln)
                }
                return echt(pfad, o);
            };
            try { await Promise.all([ladeModelle(), ladeModelle()]); } finally { api = echt; }
            return zustand.modelle.length;
        }""")
        check("Kommt eine ältere Listenantwort nach einer neueren an, zeigt die Liste den Stand der neueren", n_alt > 0)
        # -- Während des Einlesens holt eine geänderte Kachel nur sich selbst (nachgereicht, auch aus einer Sammelmeldung des Servers)
        wege = await pg.evaluate("""async () => {
            const echt = api, wege = [], alt = zustand.scan;
            api = async (p, o) => { wege.push(p.split("?")[0]); return echt(p, o); };
            zustand.scan = { laeuft: true };
            clearTimeout(liveZeit); liveZeit = null;
            const m = zustand.modelle.find((x) => x.hash);
            liveAenderung({ ereignis: "update_node", ref: `PART_GEOMETRY/${m.hash}` });
            liveAenderung({ ereignis: "update_node", ref: `MODEL_ASSET/${m.id}` });
            await new Promise((r) => setTimeout(r, 900));
            const einzeln = wege.splice(0);
            liveMeldung({ art: "graph", stapel: [{ ereignis: "update_node", ref: `MODEL_ASSET/${m.id}` }] });
            await new Promise((r) => setTimeout(r, 900));
            api = echt; zustand.scan = alt; clearTimeout(liveZeit); liveZeit = null;
            return [einzeln, wege];
        }""")
        check("Während des Einlesens holt eine geänderte Kachel (Vorschaubild, FreeCAD) nur sich selbst, nicht die ganze Liste — "
              "auch aus einer Sammelmeldung des Servers",
              wege[0] == ["/api/modelle/aenderungen"] and wege[1] == ["/api/modelle/aenderungen"])

        # -- Listenkopf: Klick sortiert, ein zweiter Klick dreht die Richtung; das Auswahlfeld oben folgt
        await pg.click('[data-layout="liste"]')
        reihen = []
        for kopf in ("gewicht", "gewicht", "name", "name"):
            await pg.click(f'#listenkopf [data-sortiere="{kopf}"]')
            await pg.wait_for_timeout(300)
            reihen.append(await pg.evaluate("""() => [zustand.modelle.map((m) => [m.name, m.gewicht_g || 0]), $("#sortierung").value,
                                                      $("#listenkopf .an").innerText]"""))
        gew = lambda r: [g for _, g in r[0]]
        nam = lambda r: [n.lower() for n, _ in r[0]]
        check("Listenkopf: Gewicht schwerste zuerst, noch ein Klick leichteste zuerst; Name A–Z, dann Z–A; Auswahlfeld und Pfeil folgen",
              gew(reihen[0]) == sorted(gew(reihen[0]), reverse=True) and gew(reihen[1]) == sorted(gew(reihen[1]))
              and nam(reihen[2])[0] < nam(reihen[2])[-1] and nam(reihen[3])[0] > nam(reihen[3])[-1]
              and reihen[1][1] == "gewicht" and reihen[3][1] == "name" and reihen[0][2].endswith("▼") and reihen[1][2].endswith("▲"))
        await pg.click('[data-layout="raster"]')

        await suche("Vase")
        await pg.locator(".karte").first.click()
        await pg.wait_for_selector("#i-bild canvas", timeout=20000)
        check("Klick auf eine Kachel: 3D-Ansicht im Inspektor", await pg.locator("#i-bild canvas").count() == 1)

        # Tag setzen: die 3D-Ansicht bleibt stehen (kein neues Netz).
        canvas = await pg.locator("#i-bild canvas").element_handle()
        await pg.fill("#tag-neu", "deko")
        await pg.press("#tag-neu", "Enter")
        await pg.wait_for_timeout(1200)
        check("Tag im Inspektor gesetzt, Chip sichtbar", "#deko" in await pg.inner_text(".i-tags"))
        check("… und die 3D-Ansicht wurde dabei nicht neu aufgebaut",
              await pg.evaluate("(c) => c.isConnected", canvas))

        # Zwei Fotos für den Druck weiter unten
        from PIL import Image
        fotos = []
        for i, farbe in enumerate([(200, 40, 40), (40, 40, 200)]):
            fotos.append(os.path.join(os.path.dirname(SAMMLUNG), f"foto{i}.png"))
            Image.new("RGB", (64, 48), farbe).save(fotos[-1])

        # -- Öffnen in …: Hauptknopf mit dem Standard, in den Einstellungen umstellbar
        check("Hauptknopf nennt den Standard fürs Format (STL → Slicer), daneben der CAD-Knopf",
              "PrusaSlicer" in await pg.inner_text("#oeffnen")
              and "FreeCAD" in await pg.inner_text(".i-haupt"))
        await pg.click("#oeffnen")
        await pg.wait_for_timeout(1000)
        check("… und startet ihn mit der Datei des Modells",
              os.path.exists(PROTOKOLL) and "prusa-slicer " in open(PROTOKOLL).read() and "Vase.stl" in open(PROTOKOLL).read())
        await pg.click("#einstellungen")
        await pg.click('[data-ein="programme"]')
        await pg.wait_for_selector('[data-prog-aendern="slicer"]')
        check("Einstellungen › Programme: Slicer und CAD stehen schon drin, ohne Textfeld",
              "PrusaSlicer" in await pg.inner_text(".prog-wahl >> nth=0") and "FreeCAD" in await pg.inner_text(".prog-wahl >> nth=1")
              and await pg.locator("#prog-teil input").count() == 0)
        await pg.click('[data-prog-aendern="slicer"]')                 # der Dateidialog (Attrappe) wählt FreeCAD
        await pg.wait_for_function("document.querySelector('.prog-wahl').innerText.includes('FreeCAD')")
        await pg.click('dialog button[value="ja"]')
        await pg.wait_for_timeout(1000)
        check("Einstellungen: FreeCAD als Slicer gewählt, der Hauptknopf für STL folgt",
              "FreeCAD" in await pg.inner_text("#oeffnen"))

        global WID
        WID = api(port, "/api/wurzeln")[0]["id"]
        sid = api(port, "/api/sammlungen", {"name": "Drohne V2"})["id"]
        await pg.wait_for_timeout(800)
        await suche("Arm")
        await pg.evaluate(ZIEHEN, [".karte", f'[data-sammlung="{sid}"]'])
        await pg.wait_for_timeout(800)
        check("Kachel auf Sammlung gezogen: Modell ist in der Sammlung", [m["name"] for m in api(port, f"/api/modelle?sammlung={sid}")] == ["Arm"])

        # -- Reiter „Verwendet“: jede Zeile führt dorthin; Vor und Zurück bringen wieder zurück
        await pg.locator(".karte").first.click()
        await pg.click('.i-reiter [data-reiter="verwendet"]')
        check("Verwendet: der Reiter nennt die Sammlung, in der das Modell liegt, und den Ordner",
              "Drohne V2" in await pg.inner_text('.i-tafel[data-reiter="verwendet"]') and await pg.locator('.v-zeile[data-springe="ordner"]').count() >= 1)
        await pg.click('.v-zeile[data-springe="sammlung"]')
        await pg.wait_for_timeout(700)
        check("Verwendet: ein Klick auf die Sammlung springt hin (Seitenleiste zeigt sie als gewählt)",
              await pg.locator(f'[data-sammlung="{sid}"].aktiv').count() == 1)
        await pg.click("#nav-zurueck")
        await pg.wait_for_timeout(700)
        check("Zurück: die Sammlung ist nicht mehr gewählt, Vor ist möglich",
              await pg.locator(f'[data-sammlung="{sid}"].aktiv').count() == 0 and await pg.locator("#nav-vor").is_enabled())
        await pg.click('[data-ansicht="alle"]')
        await pg.click('.i-reiter [data-reiter="uebersicht"]')
        await pg.wait_for_timeout(500)

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
            await pg.wait_for_function("(e) => [...document.querySelectorAll('#ws-liste li > span')]"
                                       ".map((x) => x.textContent).join('|') === e.join('|')", arg=erwartet, timeout=5000)
        except Exception:
            pass
        check("Drei Kacheln in die Warteschlange gezogen, Liste links nummeriert",
              await pg.locator("#ws-liste li > span").all_inner_texts() == erwartet
              and await pg.locator("#ws-liste li b").all_inner_texts() == ["1", "2", "3"])
        await pg.evaluate(ZIEHEN, ["#ws-liste li:last-child", "#ws-liste li:first-child"])
        await pg.wait_for_timeout(800)
        check("Warteschlange per Ziehen umsortiert",
              [m["name"] for m in api(port, "/api/warteschlange")] == ["Vase", "Haken", "Arm"])

        # -- Mehrfachauswahl und Aktionsleiste
        await suche("")
        oben = (await pg.locator(".karte").nth(2).bounding_box())["y"]
        await pg.locator(".karte .wahl").nth(0).click()
        await pg.wait_for_selector("#stapel:not([hidden])")
        leiste, mitte = await pg.locator("#stapel").bounding_box(), await pg.locator(".mitte").bounding_box()
        check("Erstes Häkchen: die Liste bleibt stehen, die Leiste erscheint unten (der nächste Klick trifft)",
              (await pg.locator(".karte").nth(2).bounding_box())["y"] == oben
              and leiste["y"] > mitte["y"] + mitte["height"] / 2)
        await pg.locator(".karte .wahl").nth(2).click(modifiers=["Shift"])
        check("Kästchen und Umschalt-Klick: Bereich von drei gewählt, Leiste zeigt es",
              "3 ausgewählt" in await pg.inner_text("#stapel"))
        # Alle vier Zuordnungen (Tag, Material, Sammlung, Baugruppe) laufen über dasselbe Fenster: Suchfeld, Liste mit Stand, Neu anlegen.
        await pg.click('[data-stapel="tag"]')
        await pg.wait_for_selector("#zuordnen:not([hidden]) .zw-suche")
        await pg.wait_for_selector("#zuordnen .zw-zeile")
        box, leiste = await pg.locator("#zuordnen").bounding_box(), await pg.locator("#stapel").bounding_box()
        check("Zuordnen-Fenster steht über der Leiste und verdeckt nichts davon (auch nicht „n ausgewählt“), Suchfeld hat den Fokus, es nennt die Zahl der Modelle",
              box["y"] + box["height"] <= leiste["y"] and await pg.evaluate("document.activeElement.className") == "zw-suche"
              and "für 3 Modelle" in await pg.inner_text(".zw-kopf"))
        await pg.keyboard.type("Stapel")
        check("Unbekannter Name: die Liste bietet an, ihn neu anzulegen", "Neuer Tag „Stapel“ anlegen" in await pg.inner_text("#zuordnen .zw-zeile.neu"))
        await pg.keyboard.press("Enter")
        await pg.wait_for_selector(".zw-zeile:has-text('#stapel') .zw-stand.voll", timeout=5000)
        check("Enter legt an und vergibt für alle drei; das Fenster bleibt offen, der Stand der Zeile zeigt „alle“",
              len(api(port, "/api/modelle?tag=stapel")) == 3 and await pg.locator("#zuordnen").is_visible()
              and "angelegt" in await pg.inner_text(".zw-status"))
        await pg.keyboard.press("Escape")
        check("Esc schliesst das Fenster, die Auswahl bleibt", await pg.locator("#zuordnen").is_hidden() and "3 ausgewählt" in await pg.inner_text("#stapel"))
        await pg.click('[data-stapel="tag"]')
        await pg.wait_for_selector("#zuordnen:not([hidden]) .zw-suche")
        await pg.wait_for_selector("#zuordnen .zw-zeile")
        await pg.keyboard.type("stap")
        zeilen = await pg.locator("#zuordnen .zw-zeile").all_inner_texts()
        await pg.keyboard.press("Enter")
        await pg.wait_for_timeout(500)
        check("Teil eines vorhandenen Namens tippen und Enter: nimmt den vorhandenen, legt keinen neuen Tag „stap“ an",
              "#stapel" in zeilen[0] and "anlegen" in zeilen[-1] and not any(t["name"] == "stap" for t in api(port, "/api/tags")))
        await pg.keyboard.press("Escape")
        await pg.click('[data-stapel="sammlung"]')
        await pg.wait_for_selector("#zuordnen:not([hidden]) .zw-suche")
        await pg.keyboard.type("Auswahl-Sammlung")
        await pg.keyboard.press("Enter")
        await pg.wait_for_selector(".zw-zeile:has-text('Auswahl-Sammlung') .zw-stand.voll", timeout=5000)
        check("Dasselbe Fenster für Sammlungen: neu angelegt mit den drei Gewählten",
              any(x["name"] == "Auswahl-Sammlung" and x["anzahl"] == 3 for x in api(port, "/api/sammlungen")))
        await pg.click('[data-stapel="sammlung"]')                      # derselbe Knopf schliesst wieder
        check("Derselbe Knopf schaltet das Fenster wieder aus", await pg.locator("#zuordnen").is_hidden())
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
        # Oben ist FreeCAD als Slicer gewählt worden: beide Plätze zeigen es, getrennt als zwei Einträge; PrusaSlicer ist es nicht mehr.
        check("Rechtsklick: Slicer und CAD als zwei Einträge, mit den in den Einstellungen gewählten Programmen",
              menu.count("In FreeCAD öffnen") == 2 and "PrusaSlicer" not in menu)
        check("Rechtsklick: Öffnen, Im Ordner zeigen, Löschen im Menü; Favorit umschalten wirkt",
              "Im Ordner zeigen" in menu and "Löschen" in menu
              and next(m for m in api(port, "/api/modelle") if m["id"] == mid)["favorit"] != vorher
              and await pg.locator("#kontext").is_hidden())

        # -- Quelle als Link
        await pg.locator(".karte").first.click()
        await pg.wait_for_selector(".i-reiter")
        await pg.click('.i-reiter [data-reiter="datei"]')
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
        await pg.click('[data-bg-aktion="kaufteile"]')
        await pg.wait_for_selector("#w-liste .w-zeile")
        await pg.fill("#w-suche", "m3x10")
        await pg.wait_for_timeout(600)
        await pg.fill('[data-w-menge="PURCHASED_PART/din912-m3x10"]', "6")
        await pg.click('[data-w-plus="PURCHASED_PART/din912-m3x10"]')
        await pg.wait_for_timeout(600)
        drin = lambda: any(p["ref"] == "PURCHASED_PART/din912-m3x10" for p in api(port, f"/api/baugruppen/{bid}")["positionen"])
        check("Kaufteil im Wähler hinzugefügt", drin())
        await pg.click('dialog button[value="fertig"]')
        await pg.wait_for_timeout(800)
        check("Kaufteil aus dem Katalog mit Menge, erscheint in der Einkaufsliste",
              "KAUFTEILE" in await pg.inner_text("#inspektor") and "6×" in await pg.inner_text("#inspektor"))
        await pg.click('[data-ansicht="alle"]')
        await pg.wait_for_timeout(600)

        # -- Neue Sammlung: Enter legt an, statt den Dialog wegzuwerfen
        await pg.click("#sammlung-neu")
        await pg.fill("#s-name", "Per Enter")
        await pg.press("#s-name", "Enter")
        await pg.wait_for_timeout(800)
        check("Neue Sammlung: Name, Enter — angelegt, Dialog zu",
              any(x["name"] == "Per Enter" for x in api(port, "/api/sammlungen")) and await pg.locator("dialog[open]").count() == 0)

        # -- Schnell hintereinander klicken: keine Auswahl geht verloren
        await suche("")
        await pg.wait_for_selector(".karte")
        for runde in range(2):
            await pg.locator(".karte").nth(0).click()
            await pg.locator(".karte").nth(1).click()
            await pg.locator(".karte").nth(2).click()
            await pg.wait_for_timeout(700 if runde == 0 else 1500)
            ids = [await pg.locator(".karte").nth(i).get_attribute("data-id") for i in range(3)]
            check(f"Drei Kacheln schnell nacheinander angeklickt (Runde {runde + 1}): die letzte ist gewählt",
                  await pg.locator(".karte.gewaehlt").count() == 1 and await pg.locator("#inspektor").get_attribute("data-id") == ids[2])
        if await pg.locator('.sektion[data-sektion="tags"][data-zu="1"]').count():
            await pg.click('.sektion[data-sektion="tags"] .sk-kopf')
        for tag in [t["name"] for t in api(port, "/api/tags")][:3]:
            await pg.click(f'#tag-liste [data-tag="{tag}"]', no_wait_after=True)
        await pg.wait_for_timeout(800)
        check("Mehrere Tags schnell nacheinander gewählt: alle angenommen",
              await pg.locator("#tagleiste .chip.aktiv[data-tag]:not([data-tag=''])").count() == min(3, len(api(port, "/api/tags"))))
        await pg.click("#filter-weg")
        await pg.wait_for_timeout(500)

        # -- Datei im Dateimanager gelöscht: Kachel bleibt, deutlich markiert
        os.remove(os.path.join(SAMMLUNG, "Technik", "Arm.stl"))
        api(port, "/api/scan", {})
        while api(port, "/api/stand")["scan"].get("laeuft"):
            time.sleep(0.3)
        await suche("Arm")
        await pg.wait_for_selector(".karte.fehlt .fehlt-band", timeout=5000)
        check("Datei fehlt: Kachel bleibt im Raster, mit Band „Datei fehlt“",
              "Datei fehlt" in await pg.inner_text(".karte.fehlt .fehlt-band"))
        await pg.click('[data-rail="bereinigen"]')
        await pg.wait_for_selector('[data-sektion="bereinigen"]', state="visible", timeout=5000)
        check("Bereinigen: die Seitenleiste wechselt, „Datei fehlt“ zählt 1, Tags sind weg",
              await pg.locator('[data-sektion="bereinigen"]').is_visible()
              and (await pg.inner_text('[data-ansicht="fehlt"] em')).strip() == "1"
              and await pg.locator('[data-sektion="tags"]').is_hidden())
        await pg.click('[data-rail="katalog"]')
        await suche("Arm")
        await pg.locator(".karte").first.click()
        await pg.wait_for_selector("#ohne-datei")
        text = await pg.inner_text(".fehlt-teil")
        check("Datei fehlt im Inspektor: drei Wege (Suchen, Ohne Datei behalten, Entfernen) und wo sie zuletzt lag",
              await pg.locator("#datei-suchen").is_visible() and await pg.locator("#fehlt-entfernen").is_visible()
              and "Arm.stl" in text)
        await pg.click("#ohne-datei")
        await pg.wait_for_selector(".karte .badge.ohne", timeout=5000)
        check("Ohne Datei behalten: ruhiges Zeichen statt Band, das Abzeichen am Besen verschwindet",
              await pg.locator(".fehlt-band").count() == 0 and await pg.locator("#abz-bereinigen").is_hidden()
              and await pg.locator("#ohne-datei-aus").is_visible())

        await suche("Haken")
        await pg.locator(".karte").first.click()
        await pg.wait_for_selector("#mehr-knopf")
        await pg.click("#mehr-knopf")
        await pg.click("#loeschen")
        await pg.wait_for_selector("dialog[open]")
        text = await pg.inner_text("dialog")
        check("Löschdialog in Klartext: Datei, Warteschlange, Tags — kein Technikwort",
              "Haken.stl" in text and "Warteschlange" in text and "Tags:" in text and "HAS_TAG" not in text)
        await pg.click('dialog button[value="ja"]')
        await pg.wait_for_timeout(1000)
        # -- Phase 1 (Vorgabe): keine Warteschlange, Baugruppen bleiben
        await pg.goto(f"http://127.0.0.1:{port}/")
        await pg.wait_for_selector(".karte")
        await pg.locator(".karte").first.click()
        await pg.wait_for_selector(".i-reiter")

        # -- Drucke: Reiter, Formular, Karte, Referenz, Foto, Zähler auf der Kachel
        await pg.click('.i-reiter [data-reiter="drucke"]')
        await pg.click("[data-druck-neu]")
        await pg.wait_for_selector("#df-g")
        await pg.fill("#df-g", "12.5")
        await pg.fill("#df-h", "1")
        await pg.fill("#df-min", "30")
        await pg.select_option("#df-typ", "PETG")
        await pg.fill("#df-notiz", "Brim an, Düse 240")
        await pg.click('dialog button[value="ja"]')
        await pg.wait_for_selector(".druck")
        karte = await pg.inner_text(".druck")
        check("Druck anlegen: Karte mit Gewicht, Dauer, Material und Notiz; Zähler auf dem Reiter",
              "12,5 g" in karte and "1 h 30 min" in karte and "PETG" in karte and "Brim an" in karte
              and "1" in await pg.inner_text('.i-reiter [data-reiter="drucke"]'))
        await pg.click("[data-druck-ref]")
        await pg.wait_for_selector(".druck.ref")
        async with pg.expect_file_chooser() as wahl:
            await pg.click("[data-druck-foto]")
        await (await wahl.value).set_files(fotos[0])
        await pg.wait_for_selector(".d-foto img")
        await pg.click('.i-reiter [data-reiter="uebersicht"]')
        uebersicht = await pg.inner_text('.i-tafel[data-reiter="uebersicht"]')
        check("Referenzdruck liefert Gewicht und Zeit der Übersicht, mit Herkunft; „1× gedruckt“ statt „Nicht gedruckt“",
              "12,5" in uebersicht and "Referenzdruck" in uebersicht and "1× gedruckt" in uebersicht)
        try:
            await pg.wait_for_function("document.querySelector('.karte.gewaehlt')?.innerText.includes('12,5 g')", timeout=6000)
        except Exception:
            pass
        check("Die Kachel zeigt das Gewicht des Referenzdrucks",
              "12,5 g" in await pg.locator(".karte.gewaehlt").inner_text())
        await pg.click('.i-reiter [data-reiter="drucke"]')
        await pg.click("[data-druck-weg]")
        await pg.click('dialog button[value="ja"]')
        await pg.wait_for_selector(".d-leer")
        check("Druck entfernen: der Reiter ist wieder leer, das Modell wieder „noch nicht gedruckt“",
              "Noch nicht gedruckt" in await pg.inner_text(".d-oben"))
        await pg.click('.i-reiter [data-reiter="uebersicht"]')
        await pg.wait_for_selector("#gedruckt")

        # -- Endgültig entfernen: je Modell im Papierkorb, erst nach Eintippen
        im_korb = api(port, "/api/zaehler")["papierkorb"]
        await pg.click('[data-rail="bereinigen"]')
        await pg.locator(".karte", has_text="Haken").first.click()
        await pg.click("#endgueltig")
        await pg.wait_for_selector("dialog[open] #endgueltig-wort")
        text = await pg.inner_text("dialog")
        gesperrt = await pg.locator("#endgueltig-ja").is_disabled()
        await pg.fill("#endgueltig-wort", "entfernen")
        check("Endgültig entfernen: Knopf erst nach Eintippen von „entfernen“; der Dialog sagt, dass die Datei im Ordner bleibt und wiederkommt",
              gesperrt and await pg.locator("#endgueltig-ja").is_enabled() and "bleibt in ihrem Ordner" in text and "neues" in text)
        await pg.keyboard.press("Enter")
        await pg.wait_for_selector("dialog[open]", state="detached")
        await pg.wait_for_timeout(500)
        check("… Enter entfernt genau dieses Modell aus dem Papierkorb",
              api(port, "/api/zaehler")["papierkorb"] == im_korb - 1
              and await pg.locator(".karte", has_text="Haken").count() == 0)
        # -- Entwurf: im Inspektor setzen, ruhiges Zeichen auf der Kachel, ausblenden mit Zahl, gemerkt
        await pg.click('[data-rail="katalog"]')
        await suche("Vase")
        await pg.locator(".karte").first.click()
        await pg.wait_for_selector("#entwurf")
        await pg.click("#entwurf")
        await pg.wait_for_selector(".karte .badge.entwurf", timeout=5000)
        await pg.wait_for_selector("#entwuerfe-aus")
        await pg.click("#entwuerfe-aus")
        await pg.wait_for_timeout(600)
        check("Entwurf: Zeichen auf der Kachel; „Entwürfe ausblenden“ nimmt ihn aus der Liste und sagt, wie viele fehlen",
              await pg.locator(".karte").count() == 0 and "1 Entwurf ausgeblendet" in await pg.inner_text("#entwuerfe-aus")
              and await pg.evaluate("localStorage.getItem('partatlas.ohneEntwuerfe')") == "1")
        await pg.click("#entwuerfe-aus")
        await pg.wait_for_selector(".karte .badge.entwurf", timeout=5000)
        await pg.locator(".karte").first.click()
        await pg.wait_for_selector("#entwurf.an")
        await pg.click("#entwurf")
        await pg.wait_for_selector(".karte .badge.entwurf", state="detached", timeout=5000)
        await suche("")

        # Ein Entwurf für das Aufräumen (früher kam er übers Hochladen, das es seit 0.50 nicht mehr gibt)
        muster.stl_binaer(os.path.join(SAMMLUNG, "Nimm.stl"), 51, 12, 13)
        api(port, "/api/scan", {})
        ende = time.time() + 60
        while time.time() < ende and not any(x["name"] == "Nimm" for x in api(port, "/api/modelle")):
            time.sleep(0.3)
        # -- Aufräumen: eigene Fläche unter Bereinigen, Gruppen mit Grund und Grösse, Auswahl mit Summe, Behalten
        nimm = next(x["id"] for x in api(port, "/api/modelle") if x["name"] == "Nimm")
        api(port, f"/api/modelle/{nimm}", {"entwurf": True}, "PATCH")
        await pg.click('[data-rail="bereinigen"]')
        await pg.click('[data-ansicht="aufraeumen"]')
        await pg.wait_for_selector('#aufraeumen:not([hidden]) .af-gruppe')
        zeile = pg.locator(".af-zeile", has_text="Nimm")
        await pg.wait_for_timeout(500)
        check("Aufräumen: eigene Fläche statt Kacheln (kein Leer-Hinweis), der Entwurf steht mit Grund, Grösse und Pfad da",
              await pg.locator("#raster").is_hidden() and await pg.locator("#leer").is_hidden() and await zeile.count() == 1
              and "als Entwurf markiert" in await zeile.inner_text() and "Nimm.stl" in await zeile.inner_text())
        await zeile.locator("input").check()
        await pg.wait_for_selector(".af-leiste:not([hidden])")
        check("Auswahl: Leiste mit Anzahl und Summe, Pfade als CSV speicherbar", (await pg.inner_text(".af-leiste")).startswith("1 gewählt")
              and await pg.locator("[data-af-csv]").count() == 1)
        await zeile.locator("[data-af-behalten]").click()
        await pg.wait_for_selector(".af-zeile:has-text('Nimm')", state="detached")
        check("Behalten: nicht mehr vorgeschlagen, als Ausnahme gezählt", "1 Ausnahme" in await pg.inner_text(".af-kopf"))
        await pg.click('[data-rail="katalog"]')
        check("Zurück im Katalog: die Kacheln sind wieder da", await pg.locator("#raster").is_visible())
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
    # Der Dateidialog des Rechners: Ordner → die Sammlung, Programm → die FreeCAD-Attrappe.
    with open(os.path.join(attrappen, "zenity"), "w") as f:
        f.write(f'#!/bin/sh\ncase "$*" in *--directory*) echo "{sammlung}";; *) echo "{os.path.join(attrappen, "freecad")}";; esac\n')
    os.chmod(os.path.join(attrappen, "zenity"), 0o755)
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
