"""Gibt es eine neue Fassung auf `main`? Vorübergehend, für den Tester, der per `git pull` aktualisiert (Anwender, 29.10.2026).

Nur lesen: `git fetch` holt, was auf GitHub liegt, und ändert an den Dateien nichts; gezogen wird nie von selbst. Mit Zeitgrenze und ohne
Rückfrage (kein Passwort-Prompt), damit nichts hängt. Ohne git, ohne Netz oder ohne Clone (ZIP) gibt es einfach keine Meldung."""
import ast
import os
import subprocess
import threading
import time

from .neuigkeiten import _nr
from .version import VERSION

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLE_S = 6 * 3600                 # so oft nachsehen; der Tester startet ohnehin meist neu
ZEITGRENZE_S = 20
_stand = {"laeuft": VERSION, "auf_platte": None, "verfuegbar": None, "neu": []}


def _git(*args):
    umgebung = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "true", "SSH_ASKPASS": "true", "GCM_INTERACTIVE": "never"}
    r = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True, timeout=ZEITGRENZE_S, env=umgebung,
                       stdin=subprocess.DEVNULL)
    return r.stdout if r.returncode == 0 else None


def _wert(quelltext, name):
    """Eine Zuweisung `name = <Literal>` aus Quelltext lesen, ohne ihn auszuführen."""
    for knoten in ast.parse(quelltext).body:
        if isinstance(knoten, ast.Assign) and any(getattr(z, "id", None) == name for z in knoten.targets):
            return ast.literal_eval(knoten.value)
    return None


def pruefen():
    """Einmal nachsehen; Fehler jeder Art heissen „nichts bekannt“."""
    try:
        with open(os.path.join(REPO, "partatlas", "version.py"), encoding="utf-8") as f:
            _stand["auf_platte"] = _wert(f.read(), "VERSION")
    except (OSError, SyntaxError, ValueError):
        pass
    if not os.path.isdir(os.path.join(REPO, ".git")):
        return dict(_stand)
    try:
        if _git("fetch", "--quiet", "origin", "main") is None:
            return dict(_stand)
        v = _git("show", "origin/main:partatlas/version.py")
        n = _git("show", "origin/main:partatlas/neuigkeiten.py")
        verfuegbar = _wert(v, "VERSION") if v else None
        neues = (_wert(n, "NEUES") or []) if n else []
        _stand["verfuegbar"] = verfuegbar
        _stand["neu"] = [{"version": ver, "zeilen": z} for ver, z in neues if _nr(ver) > _nr(VERSION)] if verfuegbar else []
    except (OSError, subprocess.SubprocessError, SyntaxError, ValueError):
        pass
    return dict(_stand)


def stand():
    """Was die Oberfläche zeigt: `neu` = auf `main` liegt eine neuere Fassung; `neustart` = sie liegt schon auf der Platte, läuft aber noch nicht."""
    s = dict(_stand)
    s["neustart"] = bool(s["auf_platte"] and _nr(s["auf_platte"]) > _nr(VERSION))
    s["neuer"] = bool(s["verfuegbar"] and _nr(s["verfuegbar"]) > _nr(s["auf_platte"] or VERSION))
    return s


def im_hintergrund():
    """Beim Start und dann alle paar Stunden. Abgeschaltet mit PARTATLAS_KEIN_NETZ=1 (die Tests setzen es)."""
    if os.environ.get("PARTATLAS_KEIN_NETZ") == "1":
        return
    def schleife():
        while True:
            pruefen()
            time.sleep(ALLE_S)
    threading.Thread(target=schleife, name="Neue Fassung?", daemon=True).start()
