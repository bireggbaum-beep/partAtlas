"""Archiv: ein Modell ruht — nicht mehr in Liste, Suche und Zählern, aber mit allem, was daran hängt. Kam es hinein, weil seine Datei
fehlte, kehrt es zurück, sobald sie wieder auftaucht; von Hand Archiviertes holt nur der Anwender zurück."""
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
    os.makedirs(samm)
    for i, n in enumerate(("Halter", "Deckel", "Clip")):
        muster.stl_binaer(os.path.join(samm, f"{n}.stl"), 10 + i, 20, 30)

    with TestClient(erstelle_app(os.path.join(tmp, "bestand"), prozesse=2)) as c:
        z = c.app.state.zustand
        c.post("/api/wurzeln", json={"pfad": samm})
        z["scanner"].warten(120)
        ids = {m["name"]: m["id"] for m in c.get("/api/modelle").json()}
        H, D = ids["Halter"], ids["Deckel"]
        c.post(f"/api/modelle/{H}/tags", json={"tag": "drohne"})
        c.post("/api/drucke", json={"modelle": [H], "felder": {"ergebnis": "gut", "gewicht_g": 5}})
        namen = lambda **p: {m["name"] for m in c.get("/api/modelle", params=p).json()}
        kennungen = lambda **p: {m["id"] for m in c.get("/api/modelle", params=p).json()}

        # -- Von Hand ins Archiv
        c.patch(f"/api/modelle/{H}", json={"archiv": True})
        check("Archiviert: nicht mehr in der Liste und nicht in der Suche, aber in der Ansicht Archiv",
              "Halter" not in namen() and "Halter" not in namen(q="halter") and namen(ansicht="archiv") == {"Halter"})
        zl = c.get("/api/zaehler").json()
        check("Zähler: Alle ohne das Archiv, Archiv zählt eins", zl["alle"] == 2 and zl["archiv"] == 1)
        m = c.get(f"/api/modelle/{H}").json()
        check("Alles bleibt: Tags und Drucke hängen noch daran", m["archiv"] and "drohne" in m["tags"] and m["drucke_n"] == 1)
        shutil.move(os.path.join(samm, "Halter.stl"), os.path.join(tmp, "Halter.stl"))
        z["scanner"].starten(); z["scanner"].warten(120)
        shutil.move(os.path.join(tmp, "Halter.stl"), os.path.join(samm, "Halter.stl"))
        z["scanner"].starten(); z["scanner"].warten(120)
        check("Von Hand Archiviertes bleibt im Archiv, auch wenn seine Datei verschwindet und wiederkommt", namen(ansicht="archiv") == {"Halter"})
        c.patch(f"/api/modelle/{H}", json={"archiv": False})
        check("Zurückholen", "Halter" in namen() and namen(ansicht="archiv") == set())

        # -- Datei fehlt → Archiv → Datei wieder da → zurück im Katalog
        shutil.move(os.path.join(samm, "Deckel.stl"), os.path.join(tmp, "Deckel.stl"))
        z["scanner"].starten(); z["scanner"].warten(120)
        c.post("/api/stapel", json={"aktion": "archiv", "modelle": [D], "wert": True})
        check("Fehlende Datei archiviert", namen(ansicht="archiv") == {"Deckel"} and "Deckel" not in namen(ansicht="fehlt"))
        shutil.move(os.path.join(tmp, "Deckel.stl"), os.path.join(samm, "Unterordner_Deckel.stl"))
        z["scanner"].starten(); z["scanner"].warten(120)
        check("Taucht die Datei wieder auf (auch an anderem Ort und Namen), kehrt das Modell von selbst zurück",
              D in kennungen() and kennungen(ansicht="archiv") == set() and c.get(f"/api/modelle/{D}").json()["archiv"] is None)

        c.post("/api/stapel", json={"aktion": "archiv", "modelle": [H, D], "wert": True})
        check("Mehrere auf einmal, vorher eine Sicherung", kennungen(ansicht="archiv") == {H, D}
              and c.get("/api/sicherungen").json()["liste"][0]["grund"] == "vor-archiv")
    muster.ende()
