"""Anhänge an Modellen und Baugruppen (Kopie im Bestand, nie weg) und Notizen (Modell, Baugruppe), durchsuchbar."""
import os
import tempfile

import muster
from muster import check
from fastapi.testclient import TestClient
from partatlas.main import erstelle_app

PDF = b"%PDF-1.4\n1 0 obj << >> endobj\ntrailer << >>\n%%EOF\n"
SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'

if __name__ == "__main__":
    tmp = tempfile.mkdtemp()
    samm = os.path.join(tmp, "3D")
    os.makedirs(samm)
    muster.stl_binaer(os.path.join(samm, "Halter.stl"), 10, 20, 30)
    muster.stl_binaer(os.path.join(samm, "Deckel.stl"), 12, 20, 30)

    with TestClient(erstelle_app(os.path.join(tmp, "bestand"), prozesse=2)) as c:
        z = c.app.state.zustand
        b = z["bestand"]
        c.post("/api/wurzeln", json={"pfad": samm})
        z["scanner"].warten(120)
        ids = {m["name"]: m["id"] for m in c.get("/api/modelle").json()}
        H = ids["Halter"]

        # -- Anhang am Modell
        k = c.post(f"/api/anhaenge/modell/{H}", params={"name": "Montage Anleitung.pdf"}, content=PDF).json()["k"]
        a = c.get(f"/api/modelle/{H}").json()["anhaenge"]
        check("Anhang am Modell: Name, Grösse, Kopie unverändert im Vault (Titel + Hash)",
              len(a) == 1 and a[0]["name"] == "Montage Anleitung.pdf" and a[0]["groesse"] == len(PDF) and a[0]["anzeigen"]
              and a[0]["datei"].startswith("vault/anhaenge/Montage_Anleitung__") and open(b.pfad(*a[0]["datei"].split("/")), "rb").read() == PDF)
        r = c.get(f"/api/anhaenge/modell/{H}/{k}")
        check("PDF zum Ansehen im Browser, in einer Sandbox", r.content == PDF and r.headers["content-type"] == "application/pdf"
              and r.headers["content-disposition"].startswith("inline") and r.headers["content-security-policy"] == "sandbox")
        ks = c.post(f"/api/anhaenge/modell/{H}", params={"name": "Zeichnung.svg"}, content=SVG).json()["k"]
        r = c.get(f"/api/anhaenge/modell/{H}/{ks}")
        check("SVG (kann Skript enthalten) zum Ansehen im Browser, aber in der Sandbox", r.headers["content-disposition"].startswith("inline")
              and r.headers["content-type"] == "image/svg+xml" and r.headers["content-security-policy"] == "sandbox"
              and c.get(f"/api/modelle/{H}").json()["anhaenge"][-1]["anzeigen"])
        kd = c.post(f"/api/anhaenge/modell/{H}", params={"name": "Plan2.dxf"}, content=b"0\nSECTION\n").json()["k"]
        r = c.get(f"/api/anhaenge/modell/{H}/{kd}")
        check("Was der Browser nicht zeigt (DXF), kommt nur als Download", r.headers["content-disposition"].startswith("attachment")
              and r.headers["content-type"] == "application/octet-stream")
        check("Derselbe Inhalt noch einmal: kein zweiter Eintrag",
              c.post(f"/api/anhaenge/modell/{H}", params={"name": "nochmal.pdf"}, content=PDF).json()["k"] == k
              and len(c.get(f"/api/modelle/{H}").json()["anhaenge"]) == 3)
        check("Name aus dem Browser: nur der Dateiname, kein Pfad", c.post(f"/api/anhaenge/modell/{H}", params={"name": "../../x/Plan.dxf"},
              content=b"0\nSECTION").status_code == 200 and "Plan.dxf" in [x["name"] for x in c.get(f"/api/modelle/{H}").json()["anhaenge"]])
        c.patch(f"/api/anhaenge/modell/{H}/{k}", json={"name": "Anleitung v2.pdf"})
        check("Umbenennen", "Anleitung v2.pdf" in [x["name"] for x in c.get(f"/api/modelle/{H}").json()["anhaenge"]])
        check("Leere Datei abgelehnt", c.post(f"/api/anhaenge/modell/{H}", params={"name": "leer.txt"}, content=b"").status_code == 400)

        # -- Entfernen: nie weg, ins Archiv
        pfad = b.pfad(*a[0]["datei"].split("/"))
        c.delete(f"/api/anhaenge/modell/{H}/{k}")
        check("Entfernen: weg aus der Liste, die Datei liegt im Archiv", k not in [x["k"] for x in c.get(f"/api/modelle/{H}").json()["anhaenge"]]
              and not os.path.exists(pfad) and any(n.startswith("Montage_Anleitung__") for n in os.listdir(b.pfad("vault_archive"))))

        # -- Öffnen: eine Kopie, der Vault bleibt unberührt
        kopie = z["katalog"].anhaenge.kopie_zum_oeffnen("modell", H, ks)
        check("Öffnen nimmt eine Kopie in arbeit/geoeffnet/", kopie.startswith(b.pfad("arbeit", "geoeffnet")) and open(kopie, "rb").read() == SVG)

        kopie2 = z["katalog"].anhaenge.kopie_zum_oeffnen("modell", H, ks)
        check("Nochmal öffnen: dieselbe unveränderte Kopie, keine zweite (sonst lägen nach zehn Klicks zehn Dateien da)", kopie2 == kopie)
        with open(kopie, "wb") as f:
            f.write(b"vom Programm geaendert")
        kopie3 = z["katalog"].anhaenge.kopie_zum_oeffnen("modell", H, ks)
        check("Hat das Programm die Kopie geändert, bleibt sie unberührt und es kommt eine neue daneben",
              kopie3 != kopie and open(kopie, "rb").read() == b"vom Programm geaendert" and open(kopie3, "rb").read() == SVG)

        # -- Baugruppe: Anhänge und Notizen
        bid = c.post("/api/baugruppen", json={"name": "Drohne", "modelle": [H]}).json()["id"]
        c.post(f"/api/anhaenge/baugruppe/{bid}", params={"name": "Explosionszeichnung.pdf"}, content=PDF + b"x")
        notiz = "# Montage\n\n- Arme zuerst\n- **M3** Schrauben\n" + "lang " * 400
        c.patch(f"/api/baugruppen/{bid}", json={"notizen": notiz})
        d = c.get(f"/api/baugruppen/{bid}").json()
        check("Baugruppe: Notizen (auch lang) und Anhänge", d["notizen"] == notiz and [x["name"] for x in d["anhaenge"]] == ["Explosionszeichnung.pdf"])
        check("Unbekannte Art abgelehnt", c.post("/api/anhaenge/sammlung/s_0001", params={"name": "a.pdf"}, content=PDF).status_code == 400)

        # -- Notiz am Modell, durchsuchbar wie die Namen der Anhänge
        c.patch(f"/api/modelle/{H}", json={"notiz": "braucht 0.6er Düse wegen Ponyhof"})
        treffer = lambda q: {m["name"] for m in c.get("/api/modelle", params={"q": q}).json()}
        check("Notiz am Modell gespeichert und durchsuchbar", c.get(f"/api/modelle/{H}").json()["notiz"].startswith("braucht")
              and treffer("ponyhof") == {"Halter"})
        check("Namen der Anhänge sind durchsuchbar", treffer("plan") == {"Halter"})
    muster.ende()
