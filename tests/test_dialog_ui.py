"""Ordnerdialog des Rechners, der sich nicht zeigt (Windows: hinter dem Browser): „+“ darf nicht tot aussehen.

Ein Dialog, der nie antwortet (Attrappe), lässt nach 3 s einen Hinweis erscheinen; dessen Knopf schliesst den Dialog und öffnet den
eigenen Ordnerbaum."""
import glob
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

import muster
from muster import check

HIER = os.path.dirname(os.path.abspath(__file__))


def chromium():
    if os.environ.get("PARTATLAS_CHROMIUM"):
        return os.environ["PARTATLAS_CHROMIUM"]
    treffer = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
    return treffer[-1] if treffer else None


if __name__ == "__main__":
    muster.zeitgrenze(90)
    from playwright.sync_api import sync_playwright
    tmp = tempfile.mkdtemp()
    attrappen = os.path.join(tmp, "bin")
    os.makedirs(attrappen)
    with open(os.path.join(attrappen, "zenity"), "w") as f:
        f.write("#!/bin/sh\nexec sleep 120\n")        # exec: beim Schliessen endet der Dialog wirklich (kein Kindprozess hält die Leitung)
    os.chmod(os.path.join(attrappen, "zenity"), 0o755)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    umgebung = {**os.environ, "PARTATLAS_BESTAND": os.path.join(tmp, "bestand"), "PARTATLAS_PORT": str(port),
                "PYTHONPATH": os.environ.get("PARTATLAS_QUELLE") or os.path.join(HIER, ".."), "PATH": attrappen + os.pathsep + os.environ["PATH"]}
    server = subprocess.Popen([sys.executable, "-m", "partatlas"], env=umgebung, cwd=tmp, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/api/stand")
                break
            except OSError:
                time.sleep(0.1)
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chromium())
            pg = b.new_page()
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.click("#wurzel-neu-2")
            check("Gleich nach „+“ noch kein Hinweis", not pg.locator("#dialog-hinweis").is_visible())
            try:
                pg.wait_for_selector("#dialog-hinweis", state="visible", timeout=6000)
                kommt = True
            except Exception:
                kommt = False
            check("Antwortet der Dialog des Rechners nicht, erscheint nach wenigen Sekunden der Hinweis", kommt)
            if kommt:
                pg.click("#dialog-hinweis button")
                try:
                    pg.wait_for_selector("#ow", state="visible", timeout=6000)
                    offen = True
                except Exception:
                    offen = False
                check("Der Knopf öffnet den eigenen Ordnerbaum", offen)
                check("Der Hinweis verschwindet danach", pg.locator("#dialog-hinweis").count() == 0)
            b.close()
    finally:
        server.terminate()
        server.wait(10)
    muster.ende()
