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
    return {"modelle": m, "baugruppe": bid, "sammlung": sid}


# ---------------------------------------------------------------- Motive
# Jedes Motiv bekommt die Seite und die Kennungen aus `vorbereiten`; es bringt die Oberfläche in den Zustand und gibt zurück, was
# fotografiert wird: {"clip": (x, y, b, h)} oder nichts (ganzes Fenster), dazu "rahmen": [CSS-Selektoren] für die roten Rahmen.

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
    return {"clip": (0, 0, BREITE - 520, 520), "rahmen": ['.sektion[data-sektion="bereinigen"]', "#pk-leiste"]}


MOTIVE = {"katalog": katalog, "einlesen": einlesen, "ordner": ordner, "bereinigen": bereinigen}


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
    x, y, b, h = was.get("clip") or (0, 0, BREITE, HOEHE)
    png = pg.screenshot(clip={"x": x, "y": y, "width": b, "height": h})
    ctx.close()
    pfad = os.path.join(ZIEL, f"{name}-{thema}.webp")
    Image.open(io.BytesIO(png)).save(pfad, "WEBP", quality=82, method=6)
    return pfad


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


if __name__ == "__main__":
    main(sys.argv[1:])
