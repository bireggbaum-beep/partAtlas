"""Eigene Komponenten: anlegen, mit Bild, in der Baugruppe als Bedarf (kein Filament, kein Einkauf), wiederverwendbar,
löschen nur, wenn sie in keiner Baugruppe steckt; Export und PDF nennen sie."""
import os
import tempfile

import muster
from muster import check
from fastapi.testclient import TestClient
from partatlas.main import erstelle_app

def png():
    import io
    from PIL import Image
    puffer = io.BytesIO()
    Image.new("RGB", (8, 8), (200, 80, 40)).save(puffer, "PNG")
    return puffer.getvalue()

if __name__ == "__main__":
    tmp = tempfile.mkdtemp()
    with TestClient(erstelle_app(os.path.join(tmp, "bestand"), prozesse=2), raise_server_exceptions=False) as c:
        eid = c.post("/api/eigene", json={"name": "Kugellager 6203 alt", "art": "Lagerteil", "masse": "40x17x12"}).json()["id"]
        check("Anlegen: erscheint in der Liste, auffindbar über die Art", [e["id"] for e in c.get("/api/eigene", params={"q": "lagerteil"}).json()] == [eid])
        check("Leerer Name und zu lange Art: verständlicher Fehler",
              c.post("/api/eigene", json={"name": "  "}).status_code == 400 and c.post("/api/eigene", json={"name": "x", "art": "a" * 41}).status_code == 400)
        check("Bild setzen und abrufen", c.post(f"/api/eigene/{eid}/bild", content=png()).status_code == 200
              and c.get(f"/api/eigene/{eid}/bild").status_code == 200 and c.get(f"/api/eigene/{eid}").json()["bild"])
        check("Die Arten füllen sich von selbst, mit Vorschlägen dahinter", c.get("/api/eigene/arten").json()[:2] == ["Lagerteil", "Eigenbau"])

        bid = c.post("/api/baugruppen", json={"name": "Gerät"}).json()["id"]
        b2 = c.post("/api/baugruppen", json={"name": "Zweites"}).json()["id"]
        ref = f"CUSTOM_COMPONENT/{eid}"
        for b, n in ((bid, 4), (b2, 1)):
            c.post(f"/api/baugruppen/{b}/positionen", json={"ref": ref, "menge": n})
        d = c.get(f"/api/baugruppen/{bid}").json()
        p = d["positionen"][0]
        check("Position: Art eigen, Menge 4, Art/Maße/Bild dabei", p["art"] == "eigen" and p["menge"] == 4 and p["eigen_art"] == "Lagerteil"
              and p["eigen_masse"] == "40x17x12" and p["eigen_bild"])
        s = d["summen"]
        check("Zählt weder zu Filament noch zum Einkauf, steht aber als Eigene Komponente mit Bedarf",
              not s["einkauf"] and not s["materialien"] and [(e["name"], e["bedarf"]) for e in s["eigene"]] == [("Kugellager 6203 alt", 4)])
        csv = c.get(f"/api/baugruppen/{bid}/export?format=csv").text
        md = c.get(f"/api/baugruppen/{bid}/export?format=md").text
        check("Export (CSV, Markdown): Eigene Komponente mit Art und Maßen", "Eigene Komponente" in csv and "40x17x12" in csv and "Eigene Komponenten" in md)
        pdf = c.get(f"/api/baugruppen/{bid}/export?format=pdf")
        check("PDF lässt sich bauen", pdf.status_code == 200 and pdf.content[:4] == b"%PDF")

        check("Löschen, solange sie in Baugruppen steckt: abgelehnt, nennt wo",
              c.delete(f"/api/eigene/{eid}").status_code == 400 and "Zweites" in c.delete(f"/api/eigene/{eid}").json()["fehler"])
        c.patch(f"/api/eigene/{eid}", json={"name": "Kugellager 6203 (60 Jahre)"})
        check("Umbenennen gilt in beiden Baugruppen", c.get(f"/api/baugruppen/{b2}").json()["positionen"][0]["name"] == "Kugellager 6203 (60 Jahre)")
        for b in (bid, b2):
            c.delete(f"/api/baugruppen/{b}/positionen", params={"ref": ref})
        check("Nach dem Herausnehmen: löschbar, danach weg", c.delete(f"/api/eigene/{eid}").status_code == 200 and c.get("/api/eigene").json() == [])
    muster.ende()
