"""
Die Bilder im Handbuch neu erzeugen — vor jeder Fassung, damit das Handbuch zeigt, was die Oberfläche heute ist.

    python werkzeuge/handbuch_bilder.py               alle Motive
    python werkzeuge/handbuch_bilder.py katalog ordner   nur diese

Baut die Demo-Sammlung (demo_sammlung.py, fester Samen) in einem frischen Ordner, startet partAtlas darauf, legt Drucke, Tags, eine
Sammlung und eine Baugruppe an und fotografiert je Motiv die Oberfläche in Hell und Dunkel (Chromium über Playwright). Ein roter
Rahmen zeigt, wovon der Text spricht. Ablage: partatlas/web/handbuch/bilder/<motiv>-hell.webp und -dunkel.webp; das Handbuch zeigt das
Bild passend zu seinem eigenen Hell/Dunkel.

Braucht die Pakete aus requirements-test.txt (Playwright) und ein Chromium (PARTATLAS_CHROMIUM, sonst das von Playwright).
"""
import glob
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

from PIL import Image

HIER = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HIER)
ZIEL = os.path.join(REPO, "partatlas", "web", "handbuch", "bilder")
BREITE, HOEHE = 1440, 860
ROT = "#e5484d"


def chromium():
    if os.environ.get("PARTATLAS_CHROMIUM"):
        return os.environ["PARTATLAS_CHROMIUM"]
    treffer = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
    return treffer[-1] if treffer else None


def api(port, pfad, daten=None, methode=None, roh=None):
    kopf = {"Content-Type": "application/json"} if daten is not None else {}
    r = urllib.request.Request(f"http://127.0.0.1:{port}{pfad}", method=methode or ("POST" if daten is not None or roh is not None else "GET"),
                               data=json.dumps(daten).encode() if daten is not None else roh, headers=kopf)
    return json.loads(urllib.request.urlopen(r, timeout=60).read() or b"null")


def warte(bedingung, sekunden=120):
    ende = time.time() + sekunden
    while time.time() < ende:
        try:
            if bedingung():
                return True
        except OSError:
            pass
        time.sleep(0.3)
    raise TimeoutError("Bedingung nicht erfüllt")


# ---------------------------------------------------------------- Vorbereitung: eine Sammlung, an der es etwas zu sehen gibt

def vorbereiten(port, samm):
    api(port, "/api/neuigkeiten/gesehen", {})               # das Fenster „Neu in dieser Fassung“ stört die Bilder
    api(port, "/api/wurzeln", {"pfad": samm})
    warte(lambda: not api(port, "/api/stand")["scan"].get("laeuft") and len(api(port, "/api/modelle")) > 40)
    warte(lambda: not api(port, "/api/stand")["worker"].get("laeuft"), 300)
    subprocess.run([sys.executable, os.path.join(HIER, "demo_drucke.py"), "--port", str(port)], check=True, stdout=subprocess.DEVNULL)
    m = {x["name"]: x["id"] for x in api(port, "/api/modelle")}
    drohne = [i for n, i in m.items() if n.startswith(("Arm_", "Top_Plate", "Bottom_Plate", "Kamerahalter", "Akkuhalter"))]
    api(port, "/api/stapel", {"aktion": "tag", "modelle": drohne, "wert": "drohne"})
    api(port, "/api/stapel", {"aktion": "favorit", "modelle": drohne[:2], "wert": True})
    werkstatt = [i for n, i in m.items() if n.startswith(("Bithalter", "Sortierbox", "Werkzeughalter", "Schraubenbox"))]
    sid = api(port, "/api/sammlungen", {"name": "Werkstatt", "modelle": werkstatt})["id"]
    api(port, "/api/sammlungen", {"name": "Drohnen-Teile", "regel": {"tags": ["drohne"]}})
    bid = api(port, "/api/baugruppen", {"name": "Quadrocopter 5 Zoll", "modelle": drohne})["id"]
    return {"modelle": m, "baugruppe": bid, "sammlung": sid, "port": port}


# ---------------------------------------------------------------- Motive
# Jedes Motiv bekommt die Seite und die Kennungen aus `vorbereiten`; es bringt die Oberfläche in den Zustand und gibt zurück, was
# fotografiert wird: {"clip": (x, y, b, h)}, {"element": Selektor} oder nichts (ganzes Fenster), dazu "rahmen": [CSS-Selektoren] für die
# roten Rahmen.

def baum_auf(pg):
    """Die Bibliothek aufklappen (ein frischer Browser hat sie zu)."""
    zu = pg.locator(".baum .eintrag[data-wurzel] .pfeil.zu")
    if zu.count():
        zu.first.click()
        pg.wait_for_timeout(500)


def katalog(pg, d):
    baum_auf(pg)
    pg.click(".karte >> nth=2")
    pg.wait_for_selector("#inspektor .i-name")
    return {"rahmen": []}


def einlesen(pg, d):
    return {"clip": (0, 0, 520, 420), "rahmen": ["#wurzel-neu-2", "#neu-einlesen-2"]}


def ordner(pg, d):
    baum_auf(pg)
    eintrag = ".baum .eintrag[data-ordner$='/Drohne']"
    pg.click(eintrag, button="right")
    pg.wait_for_selector("#kontext:not([hidden])")
    return {"clip": (0, 0, 620, 460), "rahmen": ["#kontext"]}


def bereinigen(pg, d):
    pg.click('[data-rail="bereinigen"]')
    pg.click('[data-ansicht="duplikate"]')
    pg.wait_for_timeout(1200)
    return {"clip": (0, 0, 1060, 420), "rahmen": ['.sektion[data-sektion="bereinigen"] .sk-inhalt', "#pk-leiste"]}


def karte(pg, name):
    """Die Kachel eines Modells (genauer Name, nicht nur ein Teil davon)."""
    return pg.locator(".karte", has=pg.locator(".name", has_text=name)).first


def ansichten(pg, d):
    pg.click('[data-layout="liste"]')
    pg.wait_for_timeout(800)
    return {"clip": (288, 0, 780, 520), "rahmen": ["#ansicht-wahl", "#listenkopf"]}


def auswahl(pg, d):
    karte(pg, "Adapter").click()
    karte(pg, "Akkuhalter").click(modifiers=["Control"])
    karte(pg, "Arm_Hinten_v1").click(modifiers=["Control"])
    pg.wait_for_selector("#stapel:not([hidden])")
    return {"rahmen": ["#stapel"]}


def suche(pg, d):
    pg.fill("#suche", "tag:drohne arm")
    pg.wait_for_timeout(1200)
    return {"clip": (0, 0, 1060, 520), "rahmen": [".suche-feld", "#tagleiste"]}


def inspektor(pg, d):
    karte(pg, "Arm_Front").click()
    pg.wait_for_selector("#inspektor .i-reiter")
    return {"element": "#inspektor", "rahmen": ["#inspektor .i-reiter"]}


def drucke(pg, d):
    karte(pg, "Arm_Front").click()
    pg.click('#inspektor [data-reiter="drucke"]')
    pg.wait_for_timeout(800)
    return {"element": "#inspektor"}


def baugruppe(pg, d):
    pg.click(f'.eintrag[data-baugruppe="{d["baugruppe"]}"]')
    pg.wait_for_timeout(1500)
    return {}


def umbenennen(pg, d):
    k = karte(pg, "Adapter")
    k.click()
    pg.wait_for_timeout(300)
    pg.keyboard.press("F2")
    pg.wait_for_selector(".namens-feld")
    return {"clip": (288, 40, 620, 380), "rahmen": [".namens-feld"]}


def einstellungen(pg, d):
    pg.click("#einstellungen")
    pg.click('[data-ein="sicherung"]')
    pg.wait_for_timeout(1200)
    # Der Bestand dieses Laufs liegt in einem Arbeitsordner mit Zufallsnamen; im Bild steht ein gewöhnlicher Ort.
    pg.evaluate("""() => document.querySelectorAll('#dialog .bk-ziel code').forEach((c) => { c.textContent = '/home/anna/.local/share/partatlas'; })""")
    return {"rahmen": []}


def tags_verwalten(pg, d):
    pg.locator("[data-tags-verwalten]").first.click()
    pg.wait_for_timeout(1200)
    return {}


SPULEN = [("PLA", "Prusament", "Galaxy Black", "#1a1a1a", 812, "Regal B2", 24.9), ("PLA", "Filamentwerk Süd", "Petrol", "#1a8a99", 1000, "Regal B1", 24.9),
          ("PETG", "Nordfaser", "Signalorange", "#e67e22", 380, "Regal A3", 29.9), ("PLA", "PolyWerk", "Gold", "#f1c40f", 150, "Regal A3", 22.9),
          ("PETG", "KunststoffKontor", "Transparent", "#f2f2f2", 0, "Trockenbox", 26.9), ("ASA", "KunststoffKontor", "Hellgrau", "#c0c0c0", 890, "Regal B2", 29.9)]


def _spulen_anlegen(d):
    if api(d["port"], "/api/spulen")["spulen"]:
        return
    for mat, her, farbname, farbe, rest, ort, preis in SPULEN:
        api(d["port"], "/api/spulen", {"felder": {"material": mat, "hersteller": her, "farbname": farbname, "farbe": farbe, "start_g": 1000,
                                                  "rest_g": rest, "ort": ort, "preis": preis}})


def lager(pg, d):
    _spulen_anlegen(d)
    pg.click("#lager")
    pg.wait_for_selector(".lg-karte")
    pg.wait_for_timeout(600)
    return {"rahmen": [".lg-zahlen"]}


def lager_formular(pg, d):
    _spulen_anlegen(d)
    pg.click("#lager")
    pg.wait_for_selector(".lg-karte")
    pg.click(".lg-karte >> nth=0 >> [data-lg-bearbeiten]")
    pg.wait_for_selector("#lf-material")
    pg.wait_for_timeout(400)
    return {}


MOTIVE = {"katalog": katalog, "einlesen": einlesen, "ansichten": ansichten, "auswahl": auswahl, "suche": suche, "inspektor": inspektor,
          "drucke": drucke, "baugruppe": baugruppe, "ordner": ordner, "umbenennen": umbenennen, "bereinigen": bereinigen,
          "einstellungen": einstellungen, "tags_verwalten": tags_verwalten, "lager": lager, "lager_formular": lager_formular}


# ---------------------------------------------------------------- Fotografieren

RAHMEN_JS = """(sel) => {
  for (const s of sel) {
    const el = document.querySelector(s);
    if (!el) continue;
    const b = el.getBoundingClientRect(), r = document.createElement("div");
    r.className = "handbuch-rahmen";
    Object.assign(r.style, { position: "fixed", left: (b.left - 4) + "px", top: (b.top - 4) + "px", width: (b.width + 8) + "px",
      height: (b.height + 8) + "px", border: "3px solid %s", borderRadius: "7px", zIndex: 99999, pointerEvents: "none",
      boxSizing: "border-box" });
    document.body.append(r);
  }
}""" % ROT


def foto(browser, port, name, motiv, d, thema):
    ctx = browser.new_context(viewport={"width": BREITE, "height": HOEHE}, color_scheme="dark" if thema == "dunkel" else "light")
    ctx.add_init_script(f"try {{ localStorage.setItem('partatlas.thema', '{'dark' if thema == 'dunkel' else 'light'}'); }} catch (e) {{}}")
    pg = ctx.new_page()
    pg.goto(f"http://127.0.0.1:{port}/")
    pg.wait_for_selector(".karte")
    pg.wait_for_timeout(1500)                  # Vorschaubilder und Seitenleiste fertig
    was = motiv(pg, d) or {}
    pg.wait_for_timeout(400)
    pg.evaluate(RAHMEN_JS, was.get("rahmen") or [])
    if was.get("element"):
        k = pg.locator(was["element"]).bounding_box()
        was["clip"] = (k["x"], k["y"], k["width"], min(k["height"], HOEHE - k["y"]))
    x, y, b, h = was.get("clip") or (0, 0, BREITE, HOEHE)
    png = pg.screenshot(clip={"x": x, "y": y, "width": b, "height": h})
    ctx.close()
    pfad = os.path.join(ZIEL, f"{name}-{thema}.webp")
    Image.open(io.BytesIO(png)).save(pfad, "WEBP", quality=82, method=6)
    return pfad


def groessen_eintragen():
    """Breite und Höhe jedes Bildes im Handbuch nachziehen: sie halten den Platz frei, solange ein Bild noch lädt (sonst verrutscht
    ein Sprung zu einem Kapitel, test_handbuch). Ändert sich ein Motiv in der Grösse, stimmt das Handbuch danach wieder."""
    import re
    datei = os.path.join(os.path.dirname(ZIEL), "index.html")
    html = open(datei, encoding="utf-8").read()

    def setzen(m):
        pfad = os.path.join(os.path.dirname(ZIEL), m.group(1))
        if not os.path.isfile(pfad):
            return m.group(0)
        b, h = Image.open(pfad).size
        return re.sub(r'width="\d+" height="\d+"', f'width="{b}" height="{h}"', m.group(0))
    neu = re.sub(r'<img [^>]*src="(bilder/[^"]+)"[^>]*>', setzen, html)
    if neu != html:
        open(datei, "w", encoding="utf-8").write(neu)


def main(namen):
    from playwright.sync_api import sync_playwright
    unbekannt = [n for n in namen if n not in MOTIVE]
    if unbekannt:
        sys.exit(f"Unbekannte Motive: {', '.join(unbekannt)} (es gibt: {', '.join(MOTIVE)})")
    os.makedirs(ZIEL, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="partatlas-handbuch-")
    samm = os.path.join(tmp, "3D-Druck")
    subprocess.run([sys.executable, os.path.join(HIER, "demo_sammlung.py"), samm, "--anzahl", "60"], check=True, stdout=subprocess.DEVNULL)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    umgebung = {**os.environ, "PARTATLAS_BESTAND": os.path.join(tmp, "bestand"), "PARTATLAS_PORT": str(port), "PYTHONPATH": REPO}
    server = subprocess.Popen([sys.executable, "-m", "partatlas"], env=umgebung, cwd=tmp, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        warte(lambda: api(port, "/api/zaehler") is not None, 60)
        d = vorbereiten(port, samm)
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=chromium())
            for name in namen or MOTIVE:
                for thema in ("hell", "dunkel"):
                    print(foto(browser, port, name, MOTIVE[name], d, thema))
            browser.close()
    finally:
        server.terminate()
        server.wait(10)
        shutil.rmtree(tmp, ignore_errors=True)
    groessen_eintragen()


if __name__ == "__main__":
    main(sys.argv[1:])
