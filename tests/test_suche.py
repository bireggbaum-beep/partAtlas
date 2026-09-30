"""Suche wie in pDMS: Teilwörter, alle Wörter, Phrase, Ausschluss,
Feldfilter, Relevanz nach Feld — und dass der Index Änderungen nachführt."""
import os
import tempfile

import muster
from muster import check
from fastapi.testclient import TestClient
from partatlas.main import erstelle_app

if __name__ == "__main__":
    tmp = tempfile.mkdtemp()
    sammlung = os.path.join(tmp, "3D-Druck")
    for o in ("Halter", "Technik"):
        os.makedirs(os.path.join(sammlung, o))
    for i, pfad in enumerate(["Halter/Kamerahalter.stl", "Armatur.stl", "Arm_Front.stl", "Technik/Deckel.stl"]):
        muster.stl_binaer(os.path.join(sammlung, pfad), 10 + i, 20, 30)
    muster.dreimf(os.path.join(sammlung, "Platte.3mf"))

    with TestClient(erstelle_app(os.path.join(tmp, "bestand"), prozesse=2)) as c:
        z = c.app.state.zustand
        c.post("/api/wurzeln", json={"pfad": sammlung})
        z["scanner"].warten(120)
        ids = {m["name"]: m["id"] for m in c.get("/api/modelle").json()}
        c.post(f"/api/modelle/{ids['Deckel']}/tags", json={"tag": "arm"})
        c.post(f"/api/modelle/{ids['Deckel']}/tags", json={"tag": "prototyp"})

        def namen(q):
            return [m["name"] for m in c.get("/api/modelle", params={"q": q}).json()]

        check("Teilwort: „halter“ findet Kamerahalter", namen("halter") == ["Kamerahalter"])
        check("Alle Wörter müssen vorkommen, Unterstrich trennt wie ein Leerzeichen", namen("arm front") == ["Arm_Front"])
        check("Relevanz: ganzes Wort im Namen vor Tag vor Wortteil im Namen",
              namen("arm") == ["Arm_Front", "Deckel", "Armatur"])
        check("-wort schliesst aus", namen("arm -front") == ["Deckel", "Armatur"])
        check("\"Wortfolge\" nur in dieser Reihenfolge",
              namen('"arm front"') == ["Arm_Front"] and namen('"front arm"') == [])
        check("Feldfilter ordner: und tag:", namen("ordner:technik") == ["Deckel"] and namen("tag:prototyp") == ["Deckel"])
        check("tag: meint den ganzen Tag, keinen Wortteil", namen("tag:proto") == [])
        check("format: vergleicht genau", namen("format:3mf") == ["Platte"] and namen("format:st") == [])
        check("material: aus den Slicer-Daten", namen("material:petg") == ["Platte"])
        check("Filter verneint: arm -tag:prototyp", namen("arm -tag:prototyp") == ["Arm_Front", "Armatur"])
        check("Unbekanntes feld:wert bleibt ein Suchbegriff statt still nichts zu finden",
              namen("halter:kamera") == ["Kamerahalter"])

        # -- Nachführen über den Rückruf von flatgraph
        c.patch(f"/api/modelle/{ids['Armatur']}", json={"name": "Ventil", "gedruckt": True})
        check("Umbenannt: unter dem neuen Namen gefunden, unter dem alten nicht",
              namen("ventil") == ["Ventil"] and namen("name:armatur") == [])
        check("gedruckt:ja folgt der Änderung", namen("gedruckt:ja") == ["Ventil"])
        bid = c.post("/api/baugruppen", json={"name": "Drohne", "modelle": [ids["Kamerahalter"]]}).json()["id"]
        check("Baugruppe: Teile unter ihrem Namen gefunden", namen("drohne") == ["Kamerahalter"])
        c.patch(f"/api/baugruppen/{bid}", json={"name": "Rover"})
        check("Baugruppe umbenannt: der Index zieht nach", namen("rover") == ["Kamerahalter"] and namen("drohne") == [])
        c.post(f"/api/modelle/{ids['Deckel']}/loeschen")
        check("Gelöscht: nicht mehr gefunden", "Deckel" not in namen("arm"))
    muster.ende()
