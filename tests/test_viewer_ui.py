"""3D-Ansicht: zeichnet nur, wenn sich etwas ändert (eine ruhende Ansicht kostet nichts), senkt bei langsamen Bildern die Auflösung und
stellt sie scharf, sobald nichts mehr bewegt wird; glättet grosse Modelle und Prozessor-WebGL nicht. Die Prüfung nimmt die Ansicht direkt
aus /web/viewer.js — die Seite drumherum prüft test_ui."""
import os
import socket
import subprocess
import sys
import tempfile

import muster
from muster import check
from test_bereinigen_ui import abfrage, chromium, warte

HIER = os.path.dirname(os.path.abspath(__file__))

SKRIPT = """
async ({dreiecke}) => {
  const v = await import('/web/viewer.js');
  const roh = new Float32Array(dreiecke * 9);
  let z = 12345;
  const zufall = () => { z = (z * 1103515245 + 12345) & 0x7fffffff; return z / 0x7fffffff; };
  for (let i = 0; i < dreiecke; i++) {
    const x = zufall() * 40, y = zufall() * 40, h = zufall() * 40;
    roh.set([x, y, h, x + 1, y, h, x, y + 1, h + 0.5], i * 9);
  }
  const feld = document.createElement('div');
  feld.style.cssText = 'position:fixed;left:0;top:0;width:900px;height:700px;background:#222;z-index:99999';
  document.body.appendChild(feld);
  window.__rahmen = 0;
  const echt = window.requestAnimationFrame.bind(window);
  window.requestAnimationFrame = (f) => echt((t) => { window.__rahmen++; f(t); });
  window.__v = v.zeige(feld, roh.buffer, null);
  return true;
}
"""

if __name__ == "__main__":
    muster.zeitgrenze(150)
    from playwright.sync_api import sync_playwright
    tmp = tempfile.mkdtemp()
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    umgebung = {**os.environ, "PARTATLAS_BESTAND": os.path.join(tmp, "bestand"), "PARTATLAS_PORT": str(port),
                "PYTHONPATH": os.environ.get("PARTATLAS_QUELLE") or os.path.join(HIER, "..")}
    server = subprocess.Popen([sys.executable, "-m", "partatlas"], env=umgebung, cwd=tmp, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        warte(lambda: abfrage(port, "/api/zaehler") is not None)
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chromium())
            pg = b.new_page(viewport={"width": 1200, "height": 800})
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_selector("#raster")

            # -- kleines Modell: ruhende Ansicht zeichnet nichts
            pg.evaluate(SKRIPT, {"dreiecke": 2000})
            pg.evaluate("__v.drehen(false)")
            pg.wait_for_timeout(1500)
            pg.evaluate("window.__rahmen = 0")
            pg.wait_for_timeout(1200)
            ruhe = pg.evaluate("window.__rahmen")
            check(f"Ruhende Ansicht (nichts bewegt sich): keine Dauerschleife, {ruhe} Bilder in 1,2 s", ruhe <= 1)
            pg.evaluate("__v.drehen(true)")
            pg.wait_for_timeout(300)
            pg.evaluate("window.__rahmen = 0")
            pg.wait_for_timeout(1000)
            lauf = pg.evaluate("window.__rahmen")
            check(f"Beim automatischen Drehen wird gezeichnet ({lauf} Bilder in 1 s)", lauf >= 3)
            pg.evaluate("__v.drehen(false)")
            pg.wait_for_timeout(3000)                    # die Trägheit der Drehung klingt in etwa einer Sekunde ab
            pg.evaluate("window.__rahmen = 0")
            pg.wait_for_timeout(1000)
            check("Nach dem Anhalten und Ausklingen ist wieder Ruhe", pg.evaluate("window.__rahmen") <= 1)
            check("Ein kleines Modell bleibt in voller Auflösung", pg.evaluate("__v.qualitaet()") == 1)

            # -- grosses Modell: langsame Bilder senken die Auflösung, Stillstand stellt sie wieder scharf
            pg.evaluate(SKRIPT, {"dreiecke": 400000})
            pg.evaluate("__v.drehen(true)")
            warte(lambda: pg.evaluate("__v.qualitaet()") < 1, 40)
            aufgenommen = pg.evaluate("[__v.bild().slice(0, 22), __v.qualitaet()]")
            tief = pg.evaluate("__v.qualitaet()")
            check(f"Grosses Modell, langsame Bilder: die Auflösung sinkt (Faktor {tief:.2f})", tief < 1)
            check("Bild aufnehmen mitten in der Bewegung liefert ein PNG, ohne die laufende Auflösung zu ändern",
                  aufgenommen[0] == "data:image/png;base64," and aufgenommen[1] == tief)
            pg.evaluate("__v.drehen(false)")
            warte(lambda: pg.evaluate("__v.qualitaet()") == 1, 20)
            check("Nichts bewegt sich mehr: wieder volle Auflösung", pg.evaluate("__v.qualitaet()") == 1)
            b.close()
    finally:
        server.terminate()
        server.wait(10)
    muster.ende()
