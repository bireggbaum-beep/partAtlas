"""Unerwartete Fehler auf dem Server: der Anwender bekommt einen Satz, mit dem er etwas anfangen kann, statt „Fehler 500“."""
import errno
import os
import tempfile

import muster
from muster import check
from fastapi.testclient import TestClient
from partatlas.main import erstelle_app

if __name__ == "__main__":
    tmp = tempfile.mkdtemp()
    samm = os.path.join(tmp, "3D")
    os.makedirs(os.path.join(samm, "Projekt"))
    muster.stl_binaer(os.path.join(samm, "Projekt", "Teil.stl"))
    # Wie im Betrieb: ein unerwarteter Fehler wird zur Antwort, statt im Test hochzukommen.
    with TestClient(erstelle_app(os.path.join(tmp, "bestand"), prozesse=1), raise_server_exceptions=False) as c:
        z = c.app.state.zustand
        wid = c.post("/api/wurzeln", json={"pfad": samm}).json()["id"]
        z["scanner"].warten(60)
        k = z["katalog"]
        echt = k.ordner_bewegen

        def mit(fehler):
            def wirf(*a, **kw):
                raise fehler
            k.ordner_bewegen = wirf
            try:
                return c.post("/api/ordner/bewegen", json={"id": f"{wid}/Projekt", "name": "X"})
            finally:
                k.ordner_bewegen = echt
        r = mit(OSError(errno.ENOSPC, "No space left on device"))
        check("Platte voll: Status 500 mit einem Satz und dem Hinweis aufs Protokoll",
              r.status_code == 500 and r.json()["fehler"].startswith("Die Platte ist voll") and "Protokoll" in r.json()["fehler"])
        r = mit(PermissionError(13, "Zugriff verweigert"))
        check("Keine Berechtigung / Datei gesperrt: Satz statt Fehlernummer", "in einem anderen Programm geöffnet" in r.json()["fehler"])
        r = mit(FileNotFoundError(2, "weg"))
        check("Datei verschwunden: Hinweis auf Einlesen", "Einlesen" in r.json()["fehler"])
        r = mit(RuntimeError("etwas Unerwartetes"))
        check("Sonst: Art und Text des Fehlers, Hinweis aufs Protokoll", r.status_code == 500
              and "RuntimeError: etwas Unerwartetes" in r.json()["fehler"] and "Protokoll" in r.json()["fehler"])
    muster.ende()
