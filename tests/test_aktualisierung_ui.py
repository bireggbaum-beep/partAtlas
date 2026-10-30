"""Das Zeichen „↑ Fassung“ neben der Fassung, wenn auf main eine höhere liegt; ein Klick zeigt, was darin neu ist. Echter Server aus einem Git-Klon."""
import os
import shutil
import socket
import subprocess
import sys
import tempfile

import muster
from muster import check
from test_bereinigen_ui import abfrage, chromium, warte

HIER = os.path.dirname(os.path.abspath(__file__))
QUELLE = os.path.abspath(os.environ.get("PARTATLAS_QUELLE") or os.path.join(HIER, ".."))


def git(ordner, *a):
    subprocess.run(["git", "-C", ordner, "-c", "user.email=t@t", "-c", "user.name=t", *a], check=True, capture_output=True)


if __name__ == "__main__":
    muster.zeitgrenze(120)
    from playwright.sync_api import sync_playwright
    tmp = tempfile.mkdtemp()
    ursprung, entwickler, tester = (os.path.join(tmp, n) for n in ("ursprung.git", "entwickler", "tester"))
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", ursprung], check=True)
    subprocess.run(["git", "clone", "-q", ursprung, entwickler], check=True, capture_output=True)
    git(entwickler, "checkout", "-q", "-b", "main")
    shutil.copytree(os.path.join(QUELLE, "partatlas"), os.path.join(entwickler, "partatlas"), ignore=shutil.ignore_patterns("__pycache__"))
    git(entwickler, "add", "-A")
    git(entwickler, "commit", "-qm", "laufende Fassung")
    git(entwickler, "push", "-q", "origin", "main")
    subprocess.run(["git", "clone", "-q", ursprung, tester], check=True, capture_output=True)
    # main bekommt eine höhere Fassung mit einem Eintrag
    v = os.path.join(entwickler, "partatlas", "version.py")
    open(v, "w").write('VERSION = "9.0.0"\n')
    n = os.path.join(entwickler, "partatlas", "neuigkeiten.py")
    t = open(n, encoding="utf-8").read().replace("NEUES = [\n", 'NEUES = [\n    ("9.0.0", ["Etwas ganz Neues zum Ausprobieren."]),\n', 1)
    open(n, "w", encoding="utf-8").write(t)
    git(entwickler, "commit", "-qam", "Fassung 9.0.0")
    git(entwickler, "push", "-q", "origin", "main")

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    umgebung = {**os.environ, "PARTATLAS_BESTAND": os.path.join(tmp, "bestand"), "PARTATLAS_PORT": str(port), "PYTHONPATH": tester}
    server = subprocess.Popen([sys.executable, "-m", "partatlas"], env=umgebung, cwd=tester, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        warte(lambda: abfrage(port, "/api/zaehler") is not None)
        abfrage(port, "/api/neuigkeiten/gesehen", {})
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chromium())
            pg = b.new_page(viewport={"width": 1400, "height": 800})
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_selector("#version")
            check("Ohne neuere Fassung ist das Zeichen weg, solange nichts bekannt ist", pg.locator("#neue-fassung").is_hidden())
            pg.wait_for_selector("#neue-fassung:not([hidden])", timeout=60000)
            check("Auf main liegt eine höhere Fassung: das Zeichen steht neben der Fassung und nennt sie",
                  pg.inner_text("#neue-fassung") == "↑ 9.0.0"
                  and pg.eval_on_selector("#neue-fassung", "e => e.getBoundingClientRect().left") >= pg.eval_on_selector("#version", "e => e.getBoundingClientRect().right") - 1)
            pg.click("#neue-fassung")
            pg.wait_for_selector("#dialog[open]")
            text = pg.inner_text("#dialog")
            check("Ein Klick zeigt, was in der neuen Fassung steht, und wie man sie holt",
                  "Neue Fassung 9.0.0" in text and "Etwas ganz Neues zum Ausprobieren." in text and "git pull" in text)
            b.close()
    finally:
        server.terminate()
        server.wait(timeout=20)
    muster.ende()
