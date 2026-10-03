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

def png2():
    import io
    from PIL import Image
    p = io.BytesIO()
    Image.new('RGB', (8, 8), (10, 200, 40)).save(p, 'PNG')
    return p.getvalue()


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

        # -- Konstruktionsdatei: Bild daraus, aber nie im 3D-Katalog
        fc, fc0, stl = (os.path.join(tmp, n) for n in ("Gehaeuse.FCStd", "Ohne.FCStd", "Platte.stl"))
        muster.fcstd(fc)
        import zipfile
        with zipfile.ZipFile(fc) as z:                  # das Testbild aus muster ist kein gültiges PNG
            teile = {n: z.read(n) for n in z.namelist()}
        teile["thumbnails/Thumbnail.png"] = png()
        with zipfile.ZipFile(fc, "w") as z:
            for n, d in teile.items():
                z.writestr(n, d)
        muster.fcstd(fc0, thumbnail=False)
        muster.stl_binaer(stl, 30, 20, 5)
        e2 = c.post("/api/eigene", json={"name": "Gehäuse-Konstruktion"}).json()["id"]
        r = c.post(f"/api/eigene/{e2}/datei", params={"name": "Gehaeuse.FCStd"}, content=open(fc, "rb").read()).json()
        check("FCStd mit Vorschaubild: Bild entsteht aus der Datei", r["bild_neu"] and c.get(f"/api/eigene/{e2}/bild").status_code == 200
              and r["datei"] == "Gehaeuse.FCStd")
        check("Die Datei kommt nicht in den 3D-Katalog und lässt sich zurückladen",
              c.get("/api/modelle").json() == [] and c.get(f"/api/eigene/{e2}/datei").content == open(fc, "rb").read())
        e3 = c.post("/api/eigene", json={"name": "Platte"}).json()["id"]
        r = c.post(f"/api/eigene/{e3}/datei", params={"name": "Platte.stl"}, content=open(stl, "rb").read()).json()
        check("STL: Bild wird gerendert, Maße werden übernommen", r["bild_neu"] and r["masse"] == "30 × 20 × 5 mm")
        c.post(f"/api/eigene/{e3}/bild", content=png2())
        eigenes = c.get(f"/api/eigene/{e3}").json()["bild"]
        r = c.post(f"/api/eigene/{e3}/datei", params={"name": "Platte.stl"}, content=open(stl, "rb").read()).json()
        check("Ein eigenes Bild bleibt, wenn danach eine Datei kommt", r["bild"] == eigenes and not r["bild_neu"] or print(r))
        r = c.post(f"/api/eigene/{e2}/datei", params={"name": "Ohne.FCStd"}, content=open(fc0, "rb").read())
        check("FCStd ohne Bild: gespeichert, kein Absturz, kein Bild erfunden", r.status_code == 200 and r.json()["bild_neu"] is False)
        check("Anderes Dateiformat: verständlicher Fehler",
              c.post(f"/api/eigene/{e2}/datei", params={"name": "a.pdf"}, content=b"x").status_code == 400)

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
        check("Nach dem Herausnehmen: löschbar, danach weg", c.delete(f"/api/eigene/{eid}").status_code == 200 and [x["id"] for x in c.get("/api/eigene").json()] == [e2, e3])
    muster.ende()
