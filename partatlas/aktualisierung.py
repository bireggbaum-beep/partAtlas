"""„Neue Fassung verfügbar“ für den Testzeitraum (Anwender 30.10.2026): Der Tester holt partAtlas mit `git pull` von `main`, es gibt keine Releases.

Läuft partAtlas aus einem Git-Ordner, holt es im Hintergrund `origin/main` (`git fetch` — verändert weder Arbeitsordner noch Zweig) und liest dort
`version.py` und `neuigkeiten.py`. Ist die Fassung dort höher, zeigt die Seite ein Zeichen neben der Fassung; ein Klick nennt, was in der neuen Fassung
steht. Geholt wird vom Git des Testers (seine Zugangsdaten, auch bei einem privaten Repo), kein Netzwerkcode von uns. Ohne Git-Ordner, ohne Netz oder
bei jedem Fehler bleibt es still: das Zeichen fehlt, nichts sonst. Die Quelle lässt sich mit PARTATLAS_KANAL ändern (Vorgabe `origin/main`)."""
import ast
import logging
import os
import re
import subprocess
import threading
import time

from .neuigkeiten import _nr

log = logging.getLogger("partatlas")

ABSTAND_S = 3 * 3600        # wie oft nachgesehen wird
FETCH_GRENZE_S = 30


def _git(ordner, *args, grenze=FETCH_GRENZE_S):
    r = subprocess.run(["git", "-C", ordner, *args], capture_output=True, text=True, timeout=grenze, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    if r.returncode != 0:
        raise OSError(r.stderr.strip()[:200] or f"git {args[0]} gescheitert")
    return r.stdout


def _neues_lesen(text):
    """NEUES aus dem Quelltext von neuigkeiten.py: eine Liste von (Fassung, [Zeilen]); gelesen wird der Text, nicht ausgeführt."""
    for knoten in ast.parse(text).body:
        if isinstance(knoten, ast.Assign) and any(getattr(t, "id", None) == "NEUES" for t in knoten.targets):
            return ast.literal_eval(knoten.value)
    return []


def pruefen(ordner, laufend, kanal="origin/main", holen=True):
    """{verfuegbar, version, neu: [{version, zeilen}]} — `neu` ab der laufenden Fassung (ausgenommen) bis zur neuesten, neueste zuerst."""
    if holen:
        remote, _, zweig = kanal.partition("/")
        _git(ordner, "fetch", "--quiet", remote, zweig)
    m = re.search(r'VERSION\s*=\s*"([\d.]+)"', _git(ordner, "show", f"{kanal}:partatlas/version.py"))
    if not m or _nr(m.group(1)) <= _nr(laufend):
        return {"verfuegbar": False, "version": laufend, "neu": []}
    neu = [{"version": v, "zeilen": z} for v, z in _neues_lesen(_git(ordner, "show", f"{kanal}:partatlas/neuigkeiten.py"))
           if _nr(laufend) < _nr(v) <= _nr(m.group(1))]
    return {"verfuegbar": True, "version": m.group(1), "neu": neu}


class Aktualisierung:
    """Hält das letzte Ergebnis und sieht im Hintergrund nach (beim Start, dann alle ABSTAND_S)."""

    def __init__(self, laufend, ordner=None, kanal=None):
        self.laufend = laufend
        self.ordner = ordner or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.kanal = kanal or os.environ.get("PARTATLAS_KANAL") or "origin/main"
        self.stand = {"verfuegbar": False, "version": laufend, "neu": []}
        self._beenden = threading.Event()

    def starten(self):
        if not os.path.isdir(os.path.join(self.ordner, ".git")):
            return          # kein Git-Ordner (Einzeldatei, Archiv): nichts zu vergleichen
        threading.Thread(target=self._schleife, name="Neue Fassung", daemon=True).start()

    def beenden(self):
        self._beenden.set()

    def _schleife(self):
        while not self._beenden.is_set():
            try:
                self.stand = pruefen(self.ordner, self.laufend, self.kanal)
            except (OSError, subprocess.SubprocessError, ValueError, SyntaxError) as e:
                log.info("Nach einer neuen Fassung gesehen, ohne Ergebnis: %s", e)
            self._beenden.wait(ABSTAND_S)
