"""Ordner umbenennen und verschieben wie im Dateimanager (Anwender, 16.10.2026): auf der Platte ein Schritt, nie ersetzend, Windows-Regeln
für Namen, alles im Ordner geht mit, der Katalog zieht die Orte nach — Tags und alles andere bleiben."""
import os
import tempfile

import muster
from muster import check
from fastapi.testclient import TestClient
from partatlas.main import erstelle_app


def namen(c, ordner=None):
    return sorted(m["name"] for m in c.get("/api/modelle", params={"ordner": ordner} if ordner else {}).json())


if __name__ == "__main__":
    muster.zeitgrenze(180)
    tmp = tempfile.mkdtemp()
    samm = os.path.join(tmp, "3D")
    os.makedirs(os.path.join(samm, "Projekt", "Sub"))
    os.makedirs(os.path.join(samm, "Andere"))
    muster.stl_binaer(os.path.join(samm, "Projekt", "Teil.stl"), 10, 20, 30)
    muster.stl_binaer(os.path.join(samm, "Projekt", "Sub", "Deckel.stl"), 11, 20, 30)
    muster.stl_binaer(os.path.join(samm, "Andere", "Fremd.stl"), 12, 20, 30)
    with open(os.path.join(samm, "Projekt", "Anleitung.pdf"), "wb") as f:
        f.write(b"%PDF-1.4")

    with TestClient(erstelle_app(os.path.join(tmp, "bestand"), prozesse=2)) as c:
        z = c.app.state.zustand
        wid = c.post("/api/wurzeln", json={"pfad": samm}).json()["id"]
        z["scanner"].warten(120)
        ids = {m["name"]: m["id"] for m in c.get("/api/modelle").json()}
        c.post("/api/stapel", json={"aktion": "tag", "modelle": [ids["Teil"]], "wert": "wichtig"})
        sid = c.post("/api/sammlungen", json={"name": "Projektsuche", "regel": {"ordner": f"{wid}/Projekt"}}).json().get("id")

        def bewegen(**d):
            return c.post("/api/ordner/bewegen", json=d)

        # -- Umbenennen
        r = bewegen(id=f"{wid}/Projekt", name="Projekt Neu")
        m = c.get(f"/api/modelle/{ids['Teil']}").json()
        check("Umbenennen: Ordner auf der Platte umbenannt, mit allem darin (auch der PDF)", r.status_code == 200
              and r.json() == {"id": f"{wid}/Projekt Neu", "vorher": f"{wid}/Projekt"}
              and os.path.isfile(os.path.join(samm, "Projekt Neu", "Anleitung.pdf")) and not os.path.exists(os.path.join(samm, "Projekt")))
        check("Modelle behalten Kennung und Tags, Orte nachgezogen, nichts fehlt", "wichtig" in m["tags"] and not m["fehlt"]
              and m["orte"][0]["pfad"] == "Projekt Neu/Teil.stl" and namen(c, f"{wid}/Projekt Neu") == ["Deckel", "Teil"])
        regel = next((x for x in c.get("/api/sammlungen").json() if x["id"] == sid), {}).get("regel") or {}
        check("Gemerkte Suche auf den Ordner zeigt auf den neuen Namen", regel.get("ordner") == f"{wid}/Projekt Neu")

        # -- Was der Explorer ablehnt, lehnt partAtlas ab — und es ändert sich nichts
        abgelehnt = {n: bewegen(id=f"{wid}/Projekt Neu", name=n) for n in ("a:b", "CON", "lpt1.txt", "Ende.", "", ".versteckt", "a/b")}
        check(f"Windows-Regeln: verbotene Zeichen, reservierte Namen, Punkt am Ende, leer, versteckt — alle abgelehnt "
              f"({[n for n, x in abgelehnt.items() if x.status_code != 400]})",
              all(x.status_code == 400 for x in abgelehnt.values()) and os.path.isdir(os.path.join(samm, "Projekt Neu")))
        check("Die Meldung sagt, welche Zeichen nicht gehen", "\\ / : * ? \" < > |" in abgelehnt["a:b"].json()["fehler"])
        r = bewegen(id=f"{wid}/Projekt Neu", name="Andere")
        check("Name schon vergeben: abgelehnt, beide Ordner unverändert", r.status_code == 400 and "schon einen Ordner" in r.json()["fehler"]
              and os.path.isfile(os.path.join(samm, "Andere", "Fremd.stl")) and os.path.isdir(os.path.join(samm, "Projekt Neu", "Sub")))
        r = bewegen(id=f"{wid}/Projekt Neu", name="projekt neu")
        check("Nur die Schreibung ändern geht", r.status_code == 200 and os.path.isdir(os.path.join(samm, "projekt neu")))
        bewegen(id=f"{wid}/projekt neu", name="Projekt")

        # -- Verschieben
        r = bewegen(id=f"{wid}/Projekt", eltern=f"{wid}/Andere")
        m = c.get(f"/api/modelle/{ids['Deckel']}").json()
        check("Verschieben: ganzer Ordner samt Unterordner, Orte nachgezogen", r.status_code == 200 and r.json()["id"] == f"{wid}/Andere/Projekt"
              and os.path.isfile(os.path.join(samm, "Andere", "Projekt", "Sub", "Deckel.stl")) and m["orte"][0]["pfad"] == "Andere/Projekt/Sub/Deckel.stl"
              and not m["fehlt"])
        check("In den eigenen Unterordner: abgelehnt", bewegen(id=f"{wid}/Andere", eltern=f"{wid}/Andere/Projekt/Sub").status_code == 400
              and os.path.isdir(os.path.join(samm, "Andere", "Projekt", "Sub")))
        check("Den Bibliotheksordner selbst: abgelehnt", bewegen(id=wid, name="Neu").status_code == 400 and os.path.isdir(samm))
        r = bewegen(id=f"{wid}/Andere/Projekt", eltern=wid)
        check("Rückgängig = zurückschieben: alles wie vorher", r.status_code == 200 and os.path.isfile(os.path.join(samm, "Projekt", "Teil.stl"))
              and namen(c, f"{wid}/Projekt") == ["Deckel", "Teil"])

        # -- Ein leerer Ordner gleichen Namens am Ziel wird nicht ersetzt (unter Linux täte das System es still)
        os.makedirs(os.path.join(samm, "Andere", "Projekt"))
        r = bewegen(id=f"{wid}/Projekt", eltern=f"{wid}/Andere")
        check("Leerer Ordner gleichen Namens am Ziel: abgelehnt, nicht ersetzt", r.status_code == 400
              and os.path.isdir(os.path.join(samm, "Andere", "Projekt")) and os.path.isfile(os.path.join(samm, "Projekt", "Teil.stl")))
        os.rmdir(os.path.join(samm, "Andere", "Projekt"))

        # -- Scheitert das Nachziehen im Katalog, geht der Ordner auf der Platte zurück
        k = z["katalog"]
        echt = k.db.update_node

        def kaputt(*a, **kw):
            raise OSError("Platte voll (gestellt)")
        k.db.update_node = kaputt
        try:
            r = bewegen(id=f"{wid}/Projekt", name="Kaputt")
        except OSError:
            r = None
        finally:
            k.db.update_node = echt
        check("Katalog scheitert: Ordner wieder unter altem Namen, Orte unverändert",
              os.path.isfile(os.path.join(samm, "Projekt", "Teil.stl")) and not os.path.exists(os.path.join(samm, "Kaputt"))
              and c.get(f"/api/modelle/{ids['Teil']}").json()["orte"][0]["pfad"] == "Projekt/Teil.stl")

        # -- Danach einlesen: der Katalog passt zur Platte, nichts neu, nichts fehlt
        bewegen(id=f"{wid}/Projekt", name="Endstand")
        vorher = sorted(ids.values())
        z["scanner"].starten()
        z["scanner"].warten(120)
        alle = c.get("/api/modelle").json()
        check("Einlesen danach: dieselben Modelle, keines fehlt, keines neu", sorted(m["id"] for m in alle) == vorher
              and not any(m["fehlt"] for m in alle) and c.get("/api/zaehler").json().get("fehlt", 0) == 0)

        # -- Während eines Einlesens: abgelehnt
        z["scanner"].status["laeuft"] = True
        r = bewegen(id=f"{wid}/Endstand", name="Später")
        z["scanner"].status["laeuft"] = False
        check("Während des Einlesens abgelehnt, mit einem Satz", r.status_code == 400 and "Einlesen" in r.json()["fehler"]
              and os.path.isdir(os.path.join(samm, "Endstand")))
    muster.ende()
