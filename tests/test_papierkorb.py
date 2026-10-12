"""Papierkorb für alles ausser Modellen: Sammlungen, Baugruppen, Drucke, Tags, eigene Kaufteile — zeigen und zurückholen."""
import io
import os
import tempfile

import muster
from muster import check
from fastapi.testclient import TestClient
from PIL import Image
from partatlas.main import erstelle_app


def jpeg():
    p = io.BytesIO()
    Image.new("RGB", (300, 200), (200, 30, 30)).save(p, "JPEG")
    return p.getvalue()


def im_korb(c, art):
    return {x["id"]: x for x in c.get("/api/papierkorb/weitere").json()[art]}


if __name__ == "__main__":
    tmp = tempfile.mkdtemp()
    samm = os.path.join(tmp, "3D")
    os.makedirs(samm)
    for i, n in enumerate(("Halter", "Clip", "Deckel")):
        muster.stl_binaer(os.path.join(samm, f"{n}.stl"), 10 + i * 3, 8, 9)

    with TestClient(erstelle_app(os.path.join(tmp, "bestand"), prozesse=2)) as c:
        z = c.app.state.zustand
        c.post("/api/wurzeln", json={"pfad": samm})
        z["scanner"].warten(120)
        m = {x["name"]: x["id"] for x in c.get("/api/modelle").json()}
        H, C = m["Halter"], m["Clip"]

        # -- Sammlung
        sid = c.post("/api/sammlungen", json={"name": "Drohne", "modelle": [H, C]}).json()["id"]
        c.delete(f"/api/sammlungen/{sid}")
        check("Gelöschte Sammlung steht im Papierkorb, mit Anzahl", im_korb(c, "sammlung").get(sid, {}).get("info") == "2 Modelle")
        r = c.post("/api/papierkorb/wiederherstellen", json={"art": "sammlung", "id": sid})
        check("Sammlung zurückholen: wieder da, mit ihren Modellen", r.status_code == 200
              and [x["name"] for x in c.get("/api/modelle", params={"sammlung": sid}).json()] == ["Halter", "Clip"]
              and sid not in im_korb(c, "sammlung"))
        check("Was nicht im Papierkorb liegt, lässt sich nicht zurückholen",
              c.post("/api/papierkorb/wiederherstellen", json={"art": "sammlung", "id": sid}).status_code == 400
              and c.post("/api/papierkorb/wiederherstellen", json={"art": "modell", "id": H}).status_code == 400)

        # -- Baugruppe
        bid = c.post("/api/baugruppen", json={"name": "Arm-Modul", "modelle": [H, C]}).json()["id"]
        c.delete(f"/api/baugruppen/{bid}")
        c.post("/api/papierkorb/wiederherstellen", json={"art": "baugruppe", "id": bid})
        check("Baugruppe zurückholen: mit ihren Positionen", len(c.get(f"/api/baugruppen/{bid}").json()["positionen"]) == 2)

        # -- Druck mit Foto
        did = c.post("/api/drucke", json={"modelle": [H], "felder": {"gewicht_g": 12, "ergebnis": "gut"}}).json()["id"]
        k = c.post(f"/api/drucke/{did}/bilder", content=jpeg()).json()["k"]
        c.delete(f"/api/drucke/{did}")
        check("Gelöschter Druck zählt nicht mehr, steht im Papierkorb mit Modellname",
              c.get(f"/api/modelle/{H}").json()["drucke_n"] == 0 and im_korb(c, "druck").get(did, {}).get("name") == "Halter")
        c.post("/api/papierkorb/wiederherstellen", json={"art": "druck", "id": did})
        check("Druck zurückholen: zählt wieder, das Foto ist noch da",
              c.get(f"/api/modelle/{H}").json()["drucke_n"] == 1 and c.get(f"/api/drucke/{did}/bilder/{k}").status_code == 200)
        c.patch(f"/api/modelle/{C}", json={"gedruckt": True})
        c.patch(f"/api/modelle/{C}", json={"gedruckt": False})
        check("Leerer Druck vom Haken „gedruckt“ erscheint nicht im Papierkorb",
              all(x["name"] != "Clip" for x in im_korb(c, "druck").values()))

        # -- Tag
        c.post(f"/api/modelle/{H}/tags", json={"tag": "drohne"})
        c.post(f"/api/modelle/{C}/tags", json={"tag": "drohne"})
        c.post("/api/tags/loeschen", json={"namen": ["drohne"]})
        check("Gelöschter Tag im Papierkorb, mit Zahl der Modelle", im_korb(c, "tag").get("drohne", {}).get("info") == "an 2 Modellen")
        c.post("/api/papierkorb/wiederherstellen", json={"art": "tag", "id": "drohne"})
        check("Tag zurückholen: wieder an beiden Modellen, wird wieder vorgeschlagen",
              "drohne" in c.get(f"/api/modelle/{C}").json()["tags"]
              and "drohne" not in c.get("/api/tags/verwaltung").json()["gesperrt"])
        c.post("/api/tags/zusammenfuehren", json={"quellen": ["drohne"], "ziel": "copter"})
        check("Zusammengeführter Tag erscheint nicht im Papierkorb (er lebt im neuen weiter)", "drohne" not in im_korb(c, "tag"))

        # -- Eigenes Kaufteil
        eid = c.post("/api/eigene", json={"name": "Lager 6203"}).json()["id"]
        c.delete(f"/api/eigene/{eid}")
        c.post("/api/papierkorb/wiederherstellen", json={"art": "kaufteil", "id": eid})
        check("Eigenes Kaufteil zurückholen", eid in [e["id"] for e in c.get("/api/eigene").json()])


    muster.ende()
