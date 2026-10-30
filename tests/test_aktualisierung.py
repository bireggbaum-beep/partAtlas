"""„Neue Fassung verfügbar“: git fetch von origin/main, Fassung und Neuigkeiten von dort lesen. Echte Git-Ordner (Ursprung, Klon des Testers)."""
import os
import shutil
import subprocess
import tempfile
import threading
import time

import muster
from muster import check
from fastapi.testclient import TestClient
from partatlas import aktualisierung
from partatlas.main import erstelle_app

NEUES = '''NEUES = [
    ("{v}", ["Zeile zu {v}",
             "zweite Zeile zu {v}"]),
{alt}]
'''


def git(ordner, *a):
    subprocess.run(["git", "-C", ordner, "-c", "user.email=t@t", "-c", "user.name=t", *a], check=True, capture_output=True)


def stand(ordner, version, eintraege):
    """version.py und neuigkeiten.py auf diesen Stand bringen und committen."""
    os.makedirs(os.path.join(ordner, "partatlas"), exist_ok=True)
    with open(os.path.join(ordner, "partatlas", "version.py"), "w") as f:
        f.write(f'VERSION = "{version}"\n')
    with open(os.path.join(ordner, "partatlas", "neuigkeiten.py"), "w") as f:
        f.write("NEUES = [\n" + "".join(f'    ("{v}", ["Zeile zu {v}", "zweite Zeile zu {v}"]),\n' for v in eintraege) + "]\n")
    git(ordner, "add", "-A")
    git(ordner, "commit", "-qm", f"Fassung {version}")


if __name__ == "__main__":
    tmp = tempfile.mkdtemp()
    ursprung, tester, entwickler = (os.path.join(tmp, n) for n in ("ursprung.git", "tester", "entwickler"))
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", ursprung], check=True)
    subprocess.run(["git", "clone", "-q", ursprung, entwickler], check=True, capture_output=True)
    git(entwickler, "checkout", "-q", "-b", "main")
    stand(entwickler, "1.0.1", ["1.0.1", "1.0.0"])
    git(entwickler, "push", "-q", "origin", "main")
    subprocess.run(["git", "clone", "-q", ursprung, tester], check=True, capture_output=True)

    a = aktualisierung.pruefen(tester, "1.0.1")
    check("Gleiche Fassung auf main: nichts verfügbar", a == {"verfuegbar": False, "version": "1.0.1", "neu": []})

    stand(entwickler, "1.0.3", ["1.0.3", "1.0.2", "1.0.1", "1.0.0"])
    git(entwickler, "push", "-q", "origin", "main")
    a = aktualisierung.pruefen(tester, "1.0.1")
    check("Höhere Fassung auf main: verfügbar, mit Nummer", a["verfuegbar"] and a["version"] == "1.0.3")
    check("… und genau die Einträge dazwischen, neueste zuerst (nicht die schon laufende)", [e["version"] for e in a["neu"]] == ["1.0.3", "1.0.2"])
    check("… mit den Zeilen aus neuigkeiten.py", a["neu"][0]["zeilen"] == ["Zeile zu 1.0.3", "zweite Zeile zu 1.0.3"])
    check("Das Nachsehen ändert den Arbeitsordner des Testers nicht",
          open(os.path.join(tester, "partatlas", "version.py")).read().strip() == 'VERSION = "1.0.1"')
    check("Ist die laufende Fassung neuer als main (Entwicklung), meldet es nichts", not aktualisierung.pruefen(tester, "1.0.9", holen=False)["verfuegbar"])
    check("Zehn ist grösser als neun (Nummern, nicht Text)", aktualisierung.pruefen(tester, "1.0.9", holen=False)["verfuegbar"] is False
          and aktualisierung._nr("1.0.10") > aktualisierung._nr("1.0.9"))

    # -- kein Netz / Ursprung weg: Ausnahme, die die Schleife auffängt
    shutil.rmtree(ursprung)
    try:
        aktualisierung.pruefen(tester, "1.0.1")
        gescheitert = False
    except OSError:
        gescheitert = True
    check("Ursprung nicht erreichbar: OSError (die Schleife schluckt ihn, das Zeichen fehlt einfach)", gescheitert)
    class EinMal(threading.Event):
        def wait(self, t=None):          # nach dem ersten Durchgang beenden, statt drei Stunden zu schlafen
            self.set()

    obj = aktualisierung.Aktualisierung("1.0.1", ordner=tester)
    obj._beenden = EinMal()
    try:
        obj._schleife()                  # pruefen() scheitert hier (Ursprung weg) — die Schleife darf nicht fallen
        ok = True
    except Exception:
        ok = False
    check("Die Schleife übersteht einen Fehler beim Nachsehen und lässt den alten Stand stehen", ok and obj.stand["verfuegbar"] is False)
    kein_git = aktualisierung.Aktualisierung("1.0.1", ordner=tmp)
    kein_git.starten()
    check("Ohne Git-Ordner startet gar kein Nachsehen", not any(t.name == "Neue Fassung" for t in threading.enumerate()))

    # -- die Schnittstelle
    with TestClient(erstelle_app(os.path.join(tmp, "bestand"), prozesse=1)) as c:
        check("/api/aktualisierung: in Tests wird nicht nachgesehen, die Antwort ist leer", c.get("/api/aktualisierung").json()["verfuegbar"] is False)
        c.app.state.zustand["aktualisierung"].stand = {"verfuegbar": True, "version": "9.9.9", "neu": [{"version": "9.9.9", "zeilen": ["x"]}]}
        check("… und gibt den gemerkten Stand heraus", c.get("/api/aktualisierung").json()["version"] == "9.9.9")
    muster.ende()
