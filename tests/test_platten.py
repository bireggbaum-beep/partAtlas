"""Druckplatten am Projekt: Teile mit Mengen auf Platten verteilen, „verteilt“ gegen den Bedarf über Baugruppen hinweg, Überschuss,
Verschieben, Rückgängig im Projekt, Löschen."""
import os
import tempfile

import muster
muster.zeitgrenze(300)
from muster import check
from fastapi.testclient import TestClient
from partatlas.main import erstelle_app

if __name__ == "__main__":
    tmp = tempfile.mkdtemp()
    samm = os.path.join(tmp, "Halloween")
    os.makedirs(samm)
    for name, x in (("Geist", 40), ("Oberarm", 90), ("Unterarm", 80), ("Kuerbis", 60)):
        muster.stl_binaer(os.path.join(samm, f"{name}.stl"), x, 20, 20)

    with TestClient(erstelle_app(os.path.join(tmp, "bestand"), prozesse=2), raise_server_exceptions=False) as c:
        c.post("/api/wurzeln", json={"pfad": samm})
        c.app.state.zustand["scanner"].warten(120)
        m = {x["name"]: x["id"] for x in c.get("/api/modelle").json()}
        ref = lambda n: f"MODEL_ASSET/{m[n]}"

        arm = c.post("/api/baugruppen", json={"name": "Skelett_Arm", "modelle": [m["Oberarm"], m["Unterarm"]]}).json()["id"]
        pid = c.post("/api/projekte", json={"name": "Halloween Deko"}).json()["id"]
        c.post(f"/api/projekte/{pid}/positionen", json={"ref": f"ASSEMBLY/{arm}", "menge": 2})
        c.post(f"/api/projekte/{pid}/positionen", json={"ref": ref("Geist"), "menge": 5})
        c.post(f"/api/projekte/{pid}/positionen", json={"ref": ref("Kuerbis"), "menge": 1})

        def liste():
            return c.get(f"/api/projekte/{pid}/platten").json()

        def auf(plid):
            return {p["name"]: p["menge"] for p in next(x for x in liste()["platten"] if x["id"] == plid)["posten"]}

        def zurueck():
            return c.post(f"/api/projekte/{pid}/rueckgaengig")

        v = liste()["verteilung"]
        bedarf = {k: v["bedarf"][m[k]] for k in ("Geist", "Oberarm", "Unterarm", "Kuerbis")}
        check("Ohne Platten: Bedarf über die Baugruppe hinweg (2 Arme = 2 Oberarme, 2 Unterarme), nichts verteilt",
              bedarf == {"Geist": 5, "Oberarm": 2, "Unterarm": 2, "Kuerbis": 1} and v["ges"] == 10 and v["ver"] == 0 and sum(v["offen"].values()) == 10)

        # -- Anlegen
        p1 = c.post(f"/api/projekte/{pid}/platten", json={}).json()["id"]
        p2 = c.post(f"/api/projekte/{pid}/platten", json={"name": "PETG-Platte", "material": "petg"}).json()["id"]
        namen = [(x["name"], x["material"]) for x in liste()["platten"]]
        check("Platten anlegen: ohne Namen „Platte 1“, mit Material", namen == [("Platte 1", None), ("PETG-Platte", "PETG")])
        check("Platten gibt es nur am Projekt, nicht an einer Baugruppe",
              c.post(f"/api/projekte/{arm}/platten", json={}).status_code == 400 and c.post("/api/projekte/p_9999/platten", json={}).status_code == 400)

        # -- Verteilen: Teilmengen, Rest, Verschieben
        c.put(f"/api/platten/{p1}/posten", json={"ref": ref("Geist"), "menge": 3})
        v = liste()["verteilung"]
        check("Teilmenge: 3 von 5 Geistern auf Platte 1, 2 fehlen", v["verteilt"][m["Geist"]] == 3 and v["offen"][m["Geist"]] == 2 and v["ver"] == 3)
        c.post(f"/api/platten/{p2}/rest", json={"ref": ref("Geist")})
        check("Rest auflegen: die fehlenden 2 kommen auf Platte 2, dann ist alles verteilt",
              auf(p2) == {"Geist": 2} and m["Geist"] not in liste()["verteilung"]["offen"])
        check("Davon ist nichts mehr übrig: noch einmal Rest auflegen wird abgelehnt",
              c.post(f"/api/platten/{p2}/rest", json={"ref": ref("Geist")}).status_code == 400)
        c.post(f"/api/projekte/{pid}/verteilen", json={"ref": ref("Geist"), "von": p2, "nach": p1})
        check("Verschieben von Platte 2 auf Platte 1: die Zeile wandert und die Mengen addieren sich (3 + 2)", auf(p1) == {"Geist": 5} and auf(p2) == {})
        c.post(f"/api/projekte/{pid}/verteilen", json={"ref": ref("Geist"), "von": p1, "nach": ""})
        check("Zurück nach „nicht verteilt“: alle 5 Geister fehlen wieder", liste()["verteilung"]["offen"][m["Geist"]] == 5 and auf(p1) == {})
        c.post(f"/api/projekte/{pid}/verteilen", json={"ref": ref("Geist"), "von": "", "nach": p2})
        check("Von „nicht verteilt“ auf eine Platte: es kommt, was fehlt", auf(p2) == {"Geist": 5})

        # -- Überschuss, Null, Grenzen
        c.put(f"/api/platten/{p2}/posten", json={"ref": ref("Geist"), "menge": 7})
        v = liste()["verteilung"]
        check("Überschuss (Reserve) ist erlaubt, wird gemeldet und zählt nicht als mehr verteilt",
              v["zu_viel"] == {m["Geist"]: 2} and v["ver"] == 5 and m["Geist"] not in v["offen"])
        c.put(f"/api/platten/{p2}/posten", json={"ref": ref("Geist"), "menge": 0})
        check("Menge 0 nimmt das Teil von der Platte", auf(p2) == {} and liste()["verteilung"]["ver"] == 0)
        check("Auf eine Platte kommen nur Modelle (keine Baugruppe, kein Kaufteil, kein unbekanntes Modell)",
              all(c.put(f"/api/platten/{p1}/posten", json={"ref": r_, "menge": 1}).status_code == 400
                  for r_ in (f"ASSEMBLY/{arm}", "PURCHASED_PART/din912-m3x10", "MODEL_ASSET/gibt-es-nicht", "")))
        check("Menge muss eine Zahl sein", c.put(f"/api/platten/{p1}/posten", json={"ref": ref("Geist"), "menge": "viele"}).status_code == 400)

        # -- Summen je Platte
        c.put(f"/api/platten/{p1}/posten", json={"ref": ref("Oberarm"), "menge": 2})
        c.put(f"/api/platten/{p1}/posten", json={"ref": ref("Geist"), "menge": 4})
        pl1 = next(x for x in liste()["platten"] if x["id"] == p1)
        check("Platte rechnet Stück und Gewicht über ihre Teile (Schätzung ohne Slicer-Daten, gekennzeichnet)",
              pl1["stueck"] == 6 and pl1["gewicht_g"] > 0 and pl1["gewicht_geschaetzt"] is True)

        # -- Platten eines anderen Projekts
        pid2 = c.post("/api/projekte", json={"name": "Anderes"}).json()["id"]
        fremd = c.post(f"/api/projekte/{pid2}/platten", json={}).json()["id"]
        check("Eine Platte eines anderen Projekts lässt sich nicht verwenden",
              c.post(f"/api/projekte/{pid}/verteilen", json={"ref": ref("Geist"), "von": "", "nach": fremd}).status_code == 400)

        # -- Rückgängig im Projekt
        vorher = auf(p1)
        c.post(f"/api/projekte/{pid}/verteilen", json={"ref": ref("Oberarm"), "von": p1, "nach": p2})
        text = c.get(f"/api/projekte/{pid}").json()["verlauf"]["zurueck"]
        check("Verschieben steht als ein Schritt im Verlauf des Projekts", text == "Teile verschieben (Platte 1 → PETG-Platte)")
        zurueck()
        check("Rückgängig bringt beide Platten zurück", auf(p1) == vorher and auf(p2) == {})
        c.patch(f"/api/platten/{p2}", json={"name": "Umbenannt", "material": ""})
        check("Platte umbenennen, Material leeren", [(x["name"], x["material"]) for x in liste()["platten"] if x["id"] == p2] == [("Umbenannt", None)])
        zurueck()
        check("Rückgängig nimmt Name und Material der Platte zurück", [(x["name"], x["material"]) for x in liste()["platten"] if x["id"] == p2] == [("PETG-Platte", "PETG")])

        # -- Kern bleibt unberührt, Modell weg, Platte weg, Projekt weg
        check("Der Kern bleibt unberührt: die Platte macht ein Modell nicht zum Teil einer Baugruppe",
              c.get(f"/api/modelle/{m['Geist']}").json()["baugruppen"] == [])
        c.put(f"/api/platten/{p2}/posten", json={"ref": ref("Kuerbis"), "menge": 1})
        ges0 = liste()["verteilung"]["ges"]
        c.post(f"/api/modelle/{m['Kuerbis']}/loeschen", json={})
        v = liste()
        check("Wird ein Modell aus dem Katalog genommen, verschwindet es aus Bedarf und Platte",
              v["verteilung"]["ges"] == ges0 - 1 and all(p_["name"] != "Kuerbis" for x in v["platten"] for p_ in x["posten"]))
        c.delete(f"/api/platten/{p1}")
        v = liste()
        check("Platte löschen: die Teile gelten wieder als nicht verteilt, die Modelle bleiben", [x["id"] for x in v["platten"]] == [p2]
              and v["verteilung"]["offen"][m["Oberarm"]] == 2 and len(c.get("/api/modelle").json()) >= 3)
        c.delete(f"/api/projekte/{pid}")
        check("Projekt löschen nimmt seine Platten mit", c.patch(f"/api/platten/{p2}", json={"name": "x"}).status_code == 400
              and c.get(f"/api/projekte/{pid}/platten").status_code == 400)
        check("Die Platte des anderen Projekts bleibt", c.patch(f"/api/platten/{fremd}", json={"name": "bleibt"}).status_code == 200)
    muster.ende()
