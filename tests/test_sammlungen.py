"""Sammlungen, Warteschlange und das Netz für die 3D-Ansicht."""
import os
import tempfile

import numpy as np

import muster
from muster import check
from fastapi.testclient import TestClient
from partatlas.main import erstelle_app

if __name__ == "__main__":
    tmp = tempfile.mkdtemp()
    sammlung = os.path.join(tmp, "3D-Druck")
    os.makedirs(sammlung)
    for i, name in enumerate(["Arm", "Deckel", "Gehäuse", "Haken"]):
        muster.stl_binaer(os.path.join(sammlung, f"{name}.stl"), 10 + i, 20, 30)
    muster.dreimf(os.path.join(sammlung, "Platte.3mf"))
    muster.step(os.path.join(sammlung, "Welle.step"))

    with TestClient(erstelle_app(os.path.join(tmp, "bestand"), prozesse=2)) as c:
        z = c.app.state.zustand
        k = z["katalog"]
        c.post("/api/wurzeln", json={"pfad": sammlung})
        z["scanner"].warten(120)
        ids = {m["name"]: m["id"] for m in c.get("/api/modelle").json()}

        # -- Sammlungen
        sid = c.post("/api/sammlungen", json={"name": "Drohne V2", "modelle": [ids["Gehäuse"], ids["Arm"]]}).json()["id"]
        check("Sammlung anlegen mit Modellen, Reihenfolge wie übergeben",
              [m["name"] for m in c.get("/api/modelle", params={"sammlung": sid}).json()] == ["Gehäuse", "Arm"])
        c.post(f"/api/sammlungen/{sid}/modelle", json={"modelle": [ids["Deckel"], ids["Arm"]]})
        check("Hinzufügen hängt hinten an, doppelt wird ignoriert",
              [m["name"] for m in c.get("/api/modelle", params={"sammlung": sid}).json()] == ["Gehäuse", "Arm", "Deckel"])
        check("Anzahl über die Nachbarschaft", c.get("/api/sammlungen").json()[0]["anzahl"] == 3)
        c.put(f"/api/sammlungen/{sid}/reihenfolge", json={"modelle": [ids["Deckel"], ids["Gehäuse"]]})
        check("Umsortieren; wer fehlt, kommt in alter Reihenfolge ans Ende",
              [m["name"] for m in c.get("/api/modelle", params={"sammlung": sid}).json()] == ["Deckel", "Gehäuse", "Arm"])
        s2 = c.post("/api/sammlungen", json={"name": "Werkstatt", "modelle": [ids["Arm"]]}).json()["id"]
        check("Ein Modell in mehreren Sammlungen, im Inspektor sichtbar",
              [x["name"] for x in c.get(f"/api/modelle/{ids['Arm']}").json()["sammlungen"]] == ["Drohne V2", "Werkstatt"])
        v = c.get(f"/api/modelle/{ids['Arm']}/loeschen").json()
        check("Löschvorschau nennt die Sammlungs-Verknüpfungen", v["kanten"].get("IN_COLLECTION") == 2)

        k.b.schliessen()
        from partatlas.bestand import Bestand
        from partatlas.katalog import Katalog
        z["bestand"] = Bestand(z["bestand"].wurzel)
        z["katalog"] = k = Katalog(z["bestand"])
        check("Reihenfolge überlebt den Neustart",
              [m["name"] for m in c.get("/api/modelle", params={"sammlung": sid}).json()] == ["Deckel", "Gehäuse", "Arm"])

        c.delete(f"/api/sammlungen/{sid}/modelle/{ids['Gehäuse']}")
        check("Aus der Sammlung nehmen", [m["name"] for m in c.get("/api/modelle", params={"sammlung": sid}).json()] == ["Deckel", "Arm"])
        c.patch(f"/api/sammlungen/{sid}", json={"name": "Drohne V3"})
        c.delete(f"/api/sammlungen/{s2}")
        check("Umbenennen und Löschen einer Sammlung; die Modelle bleiben",
              [x["name"] for x in c.get("/api/sammlungen").json()] == ["Drohne V3"]
              and len(c.get("/api/modelle").json()) == 6
              and [x["name"] for x in c.get(f"/api/modelle/{ids['Arm']}").json()["sammlungen"]] == ["Drohne V3"])
        check("Leerer Name wird abgelehnt", c.post("/api/sammlungen", json={"name": "  "}).status_code == 400)

        # -- Warteschlange
        c.post("/api/warteschlange", json={"modelle": [ids["Haken"], ids["Platte"], ids["Arm"]]})
        check("Warteschlange in Reihenfolge des Einreihens",
              [m["name"] for m in c.get("/api/warteschlange").json()] == ["Haken", "Platte", "Arm"])
        c.put("/api/warteschlange", json={"modelle": [ids["Arm"], ids["Haken"]]})
        check("Warteschlange umsortieren", [m["name"] for m in c.get("/api/warteschlange").json()] == ["Arm", "Haken", "Platte"])
        c.patch(f"/api/modelle/{ids['Haken']}", json={"gedruckt": True})
        check("Als gedruckt markiert: raus aus der Warteschlange (wie im 3MF Katalog)",
              [m["name"] for m in c.get("/api/warteschlange").json()] == ["Arm", "Platte"])
        c.delete(f"/api/warteschlange/{ids['Arm']}")
        check("Aus der Warteschlange nehmen; Zähler stimmt",
              [m["name"] for m in c.get("/api/warteschlange").json()] == ["Platte"]
              and c.get("/api/zaehler").json()["warteschlange"] == 1)

        # -- Netz für die 3D-Ansicht
        r = c.get(f"/api/modelle/{ids['Platte']}/netz")
        netz = np.frombuffer(r.content, dtype="<f4").reshape(-1, 3, 3)
        check("Netz als float32, 9 Werte je Dreieck, mit aufgelösten Komponenten",
              r.status_code == 200 and netz.shape == (24, 3, 3) and r.headers["x-dreiecke"] == "24")
        check("… mit den Transformationen aus dem Build (30 mm breit)",
              round(float(netz[..., 0].max() - netz[..., 0].min()), 1) == 30.0)
        check("STEP ohne Geometrie: 422 statt Absturz", c.get(f"/api/modelle/{ids['Welle']}/netz").status_code == 422)
        check("three.js wird lokal ausgeliefert (kein CDN)",
              c.get("/web/vendor/three.module.min.js").status_code == 200 and "importmap" in c.get("/").text)
    muster.ende()
