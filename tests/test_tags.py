"""Tags verwalten: löschen (Papierkorb, kommt nicht automatisch wieder), umbenennen, zusammenführen, automatische entfernen."""
import os
import tempfile

import muster
from muster import check
from fastapi.testclient import TestClient
from partatlas.main import erstelle_app


def warten(z):
    z["scanner"].warten(120)
    z["scanner"].worker.warten(120)


def tags_von(c, mid):
    return set(c.get(f"/api/modelle/{mid}").json()["tags"])


if __name__ == "__main__":
    tmp = tempfile.mkdtemp()
    sammlung = os.path.join(tmp, "3D-Druck")
    os.makedirs(sammlung)
    muster.stl_binaer(os.path.join(sammlung, "Halter_Arm_gross.stl"), 10, 20, 30)
    muster.stl_binaer(os.path.join(sammlung, "Halter_Kabel.stl"), 50, 20, 30)
    muster.stl_binaer(os.path.join(sammlung, "Deckel.stl"), 60, 20, 30)

    with TestClient(erstelle_app(os.path.join(tmp, "bestand"), prozesse=2)) as c:
        z = c.app.state.zustand
        c.post("/api/wurzeln", json={"pfad": sammlung})
        warten(z)
        ids = {m["name"]: m["id"] for m in c.get("/api/modelle").json()}
        arm, kabel, deckel = ids["Halter_Arm_gross"], ids["Halter_Kabel"], ids["Deckel"]
        check("Ausgangslage: Tags aus dem Dateinamen", {"halter", "arm", "gross"} <= tags_von(c, arm))

        c.post(f"/api/modelle/{arm}/tags", json={"tag": "Drohne"})
        v = {t["name"]: t for t in c.get("/api/tags/verwaltung").json()["tags"]}
        check("Verwaltung zählt Modelle und davon automatische",
              v["halter"]["anzahl"] == 2 and v["halter"]["auto"] == 2 and v["drohne"]["anzahl"] == 1 and v["drohne"]["auto"] == 0)

        # -- Ein Tag, an einem Modell entfernt, kommt beim nächsten Auslesen derselben Datei nicht wieder.
        c.delete(f"/api/modelle/{arm}/tags/arm")
        z["katalog"]._auto_tags(arm, "Halter_Arm_gross", {})
        check("Am Modell entfernter Auto-Tag kommt beim Auslesen nicht wieder", "arm" not in tags_von(c, arm))
        c.post(f"/api/modelle/{arm}/tags", json={"tag": "arm"})
        check("Von Hand wieder gesetzt, ist er da (und kein automatischer mehr)", "arm" in tags_von(c, arm))

        # -- Löschen: in den Papierkorb, von allen Modellen weg, nicht mehr vorgeschlagen.
        r = c.post("/api/tags/loeschen", json={"namen": ["halter"]})
        check("Tag löschen nimmt ihn von allen Modellen", r.status_code == 200
              and "halter" not in tags_von(c, arm) and "halter" not in tags_von(c, kabel))
        check("Gelöschter Tag wird nicht mehr automatisch vorgeschlagen",
              "halter" in c.get("/api/tags/verwaltung").json()["gesperrt"])
        z["katalog"]._auto_tags(kabel, "Halter_Kabel", {})
        check("… auch nicht beim nächsten Auslesen", "halter" not in tags_von(c, kabel))
        c.post(f"/api/modelle/{deckel}/tags", json={"tag": "halter"})
        check("Von Hand neu gesetzt: nur an diesem Modell, nicht wieder an allen von früher",
              "halter" in tags_von(c, deckel) and "halter" not in tags_von(c, arm) and "halter" not in tags_von(c, kabel))

        # -- Zusammenführen und Umbenennen
        c.post(f"/api/modelle/{kabel}/tags", json={"tag": "kabelhalter"})
        r = c.post("/api/tags/zusammenfuehren", json={"quellen": ["kabel", "kabelhalter"], "ziel": "Kabel-Führung"}).json()
        v = {t["name"] for t in c.get("/api/tags/verwaltung").json()["tags"]}
        check("Zusammenführen: Ziel an allen Modellen der Quellen, Quellen weg",
              "kabel-führung" in tags_von(c, kabel) and not {"kabel", "kabelhalter"} & v and r["modelle"] == 2)
        c.post("/api/tags/zusammenfuehren", json={"quellen": ["drohne"], "ziel": "copter"})
        check("Umbenennen = Zusammenführen mit neuem Namen", "copter" in tags_von(c, arm) and "drohne" not in tags_von(c, arm))
        check("Leerer Zielname wird abgewiesen",
              c.post("/api/tags/zusammenfuehren", json={"quellen": ["copter"], "ziel": " # "}).status_code == 400)

        # -- Alle automatischen entfernen: die eigenen bleiben, Einlesen schlägt keine mehr vor.
        c.post(f"/api/modelle/{arm}/tags", json={"tag": "gross"})       # war automatisch, jetzt bewusst gesetzt
        n = c.post("/api/tags/auto_entfernen", json={"nur_zaehlen": True}).json()
        check("Vorschau zählt nur automatische Tags", n["kanten"] > 0 and "copter" in tags_von(c, arm))
        r = c.post("/api/tags/auto_entfernen", json={}).json()
        rest = tags_von(c, arm) | tags_von(c, kabel) | tags_von(c, deckel)
        check("Automatische entfernt, eigene bleiben — auch ein automatischer, den man von Hand bestätigt hat", r["kanten"] == n["kanten"]
              and rest == {"copter", "arm", "gross", "kabel-führung", "halter"})
        check("… und künftig keine Tags aus Dateinamen", c.get("/api/einstellungen").json()["auto_tags"] is False)
        check("Vorher eine Sicherung", any(s["grund"] == "vor-auto-tags-entfernen" for s in c.get("/api/sicherungen").json()))

    muster.ende()
