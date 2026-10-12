"""Dateien, die auf der Platte verschwunden sind: das Einlesen nennt am Ende, was bei diesem Lauf neu fehlt, mit dem, was daran hängt;
der Anwender entscheidet für jede oder alle: ins Archiv (Vorgabe), ohne Datei behalten, löschen (Papierkorb)."""
import os
import shutil
import tempfile

import muster
from muster import check
from fastapi.testclient import TestClient
from partatlas.main import erstelle_app

if __name__ == "__main__":
    tmp = tempfile.mkdtemp()
    samm = os.path.join(tmp, "3D")
    os.makedirs(os.path.join(samm, "Drohne"))
    for i, n in enumerate(("Arm", "Rumpf", "Kufe", "Propeller")):
        muster.stl_binaer(os.path.join(samm, "Drohne", f"{n}.stl"), 10 + i, 20, 30)
    muster.stl_binaer(os.path.join(samm, "Haken.stl"), 40, 20, 30)
    muster.stl_binaer(os.path.join(samm, "Altes.stl"), 41, 20, 30)

    with TestClient(erstelle_app(os.path.join(tmp, "bestand"), prozesse=2)) as c:
        z = c.app.state.zustand
        c.post("/api/wurzeln", json={"pfad": samm})
        z["scanner"].warten(120)
        ids = {m["name"]: m["id"] for m in c.get("/api/modelle").json()}
        c.post("/api/drucke", json={"modelle": [ids["Arm"]], "felder": {"ergebnis": "gut"}})
        bid = c.post("/api/baugruppen", json={"name": "Drohne", "modelle": [ids["Arm"], ids["Rumpf"]]}).json()["id"]

        # Vorher schon fehlend (früherer Lauf): gehört nicht ins Fenster dieses Laufs.
        os.remove(os.path.join(samm, "Altes.stl"))
        z["scanner"].starten(); z["scanner"].warten(120)
        check("Ein Lauf mit einer fehlenden Datei meldet sie", z["scanner"].status["fehlt_neu"] == 1)

        shutil.rmtree(os.path.join(samm, "Drohne"))            # ganzer Ordner im Dateimanager gelöscht
        z["scanner"].starten(); z["scanner"].warten(120)
        st = z["scanner"].status
        neu = c.get("/api/fehlende", params={"neu": 1}).json()
        check("Am Ende des Laufs: genau die vier, die jetzt verschwunden sind, nach Ordner, mit dem, was daran hängt",
              st["fehlt_neu"] == 4 and [x["name"] for x in neu] == ["Arm", "Kufe", "Propeller", "Rumpf"]
              and all(x["ordner"] == "3D/Drohne" for x in neu)
              and {k: v for k, v in next(x for x in neu if x["name"] == "Arm")["haengt"].items() if k != "tags"}
              == {"drucke": 1, "anhaenge": 0, "bilder": 0, "sammlungen": 0, "baugruppen": 1})
        check("Ohne „neu“: alle, über die noch nicht entschieden ist (auch die von früher)", len(c.get("/api/fehlende").json()) == 5)

        r = c.post("/api/fehlende/entscheiden", json={"archiv": [ids["Arm"], ids["Rumpf"]], "behalten": [ids["Kufe"]],
                                                       "loeschen": [ids["Propeller"]]}).json()
        namen = lambda **p: {m["name"] for m in c.get("/api/modelle", params=p).json()}
        check("Entscheiden: Archiv, Behalten, Löschen — jedes an seinem Platz",
              r == {"archiv": 2, "behalten": 1, "geloescht": 1, "fehler": []} and namen(ansicht="archiv") == {"Arm", "Rumpf"}
              and c.get(f"/api/modelle/{ids['Kufe']}").json()["ohne_datei"] and namen(ansicht="papierkorb") == {"Propeller"})
        check("Im Archiv bleibt die Baugruppe vollständig", len(c.get(f"/api/baugruppen/{bid}").json()["positionen"]) == 2)
        check("Danach steht nur noch das von früher offen", [x["name"] for x in c.get("/api/fehlende").json()] == ["Altes"])
        check("Vorher eine Sicherung", c.get("/api/sicherungen").json()["liste"][0]["grund"] == "vor-fehlende")
        check("Was nicht fehlt, wird abgewiesen",
              c.post("/api/fehlende/entscheiden", json={"archiv": [ids["Haken"]]}).status_code == 400)
        z["scanner"].starten(); z["scanner"].warten(120)
        check("Ein Lauf ohne Neues fragt nicht noch einmal", z["scanner"].status["fehlt_neu"] == 0)
    muster.ende()
