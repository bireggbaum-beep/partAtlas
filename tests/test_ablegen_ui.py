"""Ziehen auf Orte (Paket 2): 🗄 Archiv und 🗑 Papierkorb in der Leiste links (mit Zahl), zurück auf ▦ Bibliothek, Tag, ♥ Favoriten, ＋ neue Sammlung —
jeweils mit Hinweis am Zeiger und Rückgängig; ab 25 Modellen fragt der Papierkorb einmal nach."""
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
    muster.zeitgrenze(110)
    from playwright.sync_api import sync_playwright
    tmp = tempfile.mkdtemp()
    samm = os.path.join(tmp, "3D")
    os.makedirs(samm)
    namen = ["Alpha", "Beta", "Gamma", "Delta"] + [f"Teil_{i:02d}" for i in range(22)]
    for i, n in enumerate(namen):
        muster.stl_binaer(os.path.join(samm, n + ".stl"), 10 + i, 20, 30)
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
        warte(lambda: len(abfrage(port, "/api/modelle")) == 26)
        warte(lambda: not (abfrage(port, "/api/stand") or {}).get("scan", {}).get("laeuft"))
        ids = {m["name"]: m["id"] for m in abfrage(port, "/api/modelle")}
        abfrage(port, f"/api/modelle/{ids['Delta']}/tags", {"tag": "werkbank"})
        modell = lambda n: abfrage(port, f"/api/modelle/{ids[n]}")
        im_katalog = lambda n: any(m["name"] == n for m in abfrage(port, "/api/modelle"))
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chromium())
            pg = b.new_page(viewport={"width": 1400, "height": 900})
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_selector(".karte")
            pg.evaluate("window.__h = []; const o = ziehHinweis; window.ziehHinweis = (t, x, y) => { if (t) __h.push(t); return o(t, x, y); }")
            hinweise = lambda: pg.evaluate("__h")
            toast = lambda: pg.inner_text("#toast")
            rail = pg.eval_on_selector_all(".rail .rail-btn", "l => l.slice(0, 4).map((x) => x.textContent.trim().slice(0, 2))")
            check("Leiste links: ▦ Bibliothek, 🗄 Archiv, 🗑 Papierkorb, 🧹 Bereinigen", rail == ["▦", "🗄", "🗑", "🧹"])
            pg.click(".rail-btn[data-rail='bereinigen']")
            check("Unter Bereinigen stehen Archiv und Papierkorb nicht mehr (nichts doppelt)",
                  pg.locator(".sektion[data-sektion='bereinigen'] [data-ansicht='papierkorb'], .sektion[data-sektion='bereinigen'] [data-ansicht='archiv']").count() == 0)
            pg.click(".rail-btn[data-rail='katalog']")
            pg.wait_for_selector(".karte")

            # Papierkorb
            pg.drag_and_drop(".karte:has-text('Alpha')", ".rail [data-ansicht='papierkorb']")
            warte(lambda: not im_katalog("Alpha"))
            pg.wait_for_function("document.querySelector('#z-papierkorb')?.textContent === '1'")
            check("Auf 🗑 gezogen: entfernt, ohne Rückfrage; die Zahl am Papierkorb zeigt 1",
                  "„Alpha.stl“ in den Papierkorb" in hinweise() and not im_katalog("Alpha") and "Rückgängig" in toast())
            pg.click("#raster")
            pg.keyboard.press("Control+z")
            warte(lambda: im_katalog("Alpha"))
            pg.wait_for_function("document.querySelector('#z-papierkorb')?.textContent === ''")
            check("Strg+Z holt es zurück, der Papierkorb ist wieder ohne Zahl", im_katalog("Alpha"))

            # Ab 25: einmal nachfragen
            pg.click("#raster")
            pg.keyboard.press("Control+a")
            pg.drag_and_drop(".karte:has-text('Alpha')", ".rail [data-ansicht='papierkorb']")
            pg.wait_for_selector("#dialog[open]")
            check("26 Modelle auf 🗑: einmal Rückfrage (der Löschdialog), der Hinweis sagte es vorher", "26 Modelle in den Papierkorb — mit Rückfrage" in hinweise())
            pg.keyboard.press("Escape")
            check("… Abbrechen entfernt nichts", len(abfrage(port, "/api/modelle")) == 26)
            pg.keyboard.press("Escape")

            # Archiv und zurück auf ▦
            pg.drag_and_drop(".karte:has-text('Beta')", ".rail [data-ansicht='archiv']")
            warte(lambda: modell("Beta").get("archiv"))
            check("Auf 🗄 gezogen: im Archiv", bool(modell("Beta").get("archiv")) and not im_katalog("Beta"))
            pg.click(".rail [data-ansicht='archiv']")
            pg.wait_for_selector(".karte:has-text('Beta')")
            pg.drag_and_drop(".karte:has-text('Beta')", ".rail [data-rail='katalog']")
            warte(lambda: not modell("Beta").get("archiv"))
            check("Im Archiv auf ▦ Bibliothek gezogen: zurückgeholt", "„Beta.stl“ aus dem Archiv zurückholen" in hinweise() and im_katalog("Beta"))
            # Aus dem Papierkorb auf ▦ Bibliothek: wiederherstellen
            pg.click(".rail [data-rail='katalog']")
            pg.wait_for_selector(".karte:has-text('Alpha')")
            pg.drag_and_drop(".karte:has-text('Alpha')", ".rail [data-ansicht='papierkorb']")
            warte(lambda: not im_katalog("Alpha"))
            pg.click(".rail [data-ansicht='papierkorb']")
            pg.wait_for_selector(".karte:has-text('Alpha')")
            pg.drag_and_drop(".karte:has-text('Alpha')", ".rail [data-rail='katalog']")
            warte(lambda: im_katalog("Alpha"))
            check("Im Papierkorb auf ▦ Bibliothek gezogen: wiederhergestellt", "„Alpha.stl“ wiederherstellen" in hinweise() and im_katalog("Alpha"))
            pg.click(".rail [data-rail='katalog']")
            pg.wait_for_selector(".karte:has-text('Gamma')")

            # Tag
            if not pg.locator(".sektion[data-sektion='tags'] .eintrag[data-tag='werkbank']").is_visible():
                pg.click("[data-sk='tags']")
            pg.drag_and_drop(".karte:has-text('Gamma')", ".sektion[data-sektion='tags'] .eintrag[data-tag='werkbank']")
            warte(lambda: "werkbank" in modell("Gamma")["tags"])
            check("Auf einen Tag gezogen: gesetzt", "werkbank" in modell("Gamma")["tags"] and "#werkbank für „Gamma.stl“" in hinweise())
            pg.click("#toast button:has-text('Rückgängig')")
            warte(lambda: "werkbank" not in modell("Gamma")["tags"])
            check("… Rückgängig nimmt ihn wieder ab", "werkbank" not in modell("Gamma")["tags"])

            # Favoriten
            pg.drag_and_drop(".karte:has-text('Gamma')", ".ans-btn[data-ansicht='favoriten']")
            warte(lambda: modell("Gamma")["favorit"])
            check("Auf ♥ gezogen: Favorit", modell("Gamma")["favorit"])
            pg.click("#raster")
            pg.keyboard.press("Control+z")
            warte(lambda: not modell("Gamma")["favorit"])
            check("… Strg+Z nimmt es zurück", not modell("Gamma")["favorit"])

            # Neue Sammlung
            pg.drag_and_drop(".karte:has-text('Gamma')", "#sammlung-neu, #sammlung-neu-2")
            pg.wait_for_selector("#dialog[open] #s-name")
            check("Auf ＋ bei Sammlungen gezogen: der Name ist gleich zum Tippen", pg.evaluate("document.activeElement?.id") == "s-name")
            pg.keyboard.type("Probe")
            pg.keyboard.press("Enter")
            warte(lambda: any(x["name"] == "Probe" for x in abfrage(port, "/api/sammlungen")))
            sid = next(x["id"] for x in abfrage(port, "/api/sammlungen") if x["name"] == "Probe")
            check("… angelegt mit dem Modell darin", [m["name"] for m in abfrage(port, f"/api/modelle?sammlung={sid}")] == ["Gamma"])
            pg.click("#toast button:has-text('Rückgängig')")
            warte(lambda: not any(x["name"] == "Probe" for x in abfrage(port, "/api/sammlungen")))
            check("… Rückgängig löscht die Sammlung wieder", not any(x["name"] == "Probe" for x in abfrage(port, "/api/sammlungen")))
            b.close()
    finally:
        server.terminate()
        server.wait(timeout=20)
    muster.ende()
