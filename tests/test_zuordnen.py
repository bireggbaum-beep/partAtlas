"""Zuordnen: Tag, Material, Sammlung, Baugruppe für viele Modelle auf einmal — eine Schnittstelle, nur Hinzufügen, nichts doppelt.
Besonders: ein Modell, das schon in der Baugruppe steht, bekommt dort keine höhere Menge, nur weil man nochmal klickt."""
import os
import tempfile

import muster
from muster import check
from fastapi.testclient import TestClient
from partatlas.main import erstelle_app


def optionen(c, art, modelle):
    r = c.post("/api/stapel/optionen", json={"art": art, "modelle": modelle}).json()
    return {o["name"]: o for o in r["optionen"]}


def zuordnen(c, art, modelle, **kw):
    return c.post("/api/stapel/zuordnen", json={"art": art, "modelle": modelle, **kw})


if __name__ == "__main__":
    tmp = tempfile.mkdtemp()
    samm = os.path.join(tmp, "Sammlung")
    os.makedirs(samm)
    for i, n in enumerate(("A", "B", "C", "D")):
        muster.stl_binaer(os.path.join(samm, f"{n}.stl"), 10 + i, 12, 13)
    with TestClient(erstelle_app(os.path.join(tmp, "bestand"), prozesse=2), raise_server_exceptions=False) as c:
        c.post("/api/wurzeln", json={"pfad": samm})
        c.app.state.zustand["scanner"].warten(120)
        m = {x["name"]: x["id"] for x in c.get("/api/modelle").json()}
        alle = [m["A"], m["B"], m["C"]]

        # -- Tag
        c.post(f"/api/modelle/{m['A']}/tags", json={"tag": "lager"})
        o = optionen(c, "tag", alle)
        check("Optionen: vorhandene Tags, bei wie vielen der Gewählten sie schon stehen", o["lager"]["bei"] == 1 and o["lager"]["gesamt"] == 1)
        r = zuordnen(c, "tag", alle, ziel="lager").json()
        check("Tag zu drei Modellen: zwei neu, einer hatte ihn schon", r["hinzugefuegt"] == 2 and r["schon"] == 1)
        r = zuordnen(c, "tag", alle, ziel="lager").json()
        check("Nochmal: nichts mehr hinzuzufügen, nichts doppelt", r["hinzugefuegt"] == 0 and r["schon"] == 3
              and c.get(f"/api/modelle/{m['B']}").json()["tags"].count("lager") == 1)
        r = zuordnen(c, "tag", alle, neu="Neuer Tag").json()
        check("Neuer Tag aus dem Suchfeld: angelegt (normalisiert) und vergeben",
              r["hinzugefuegt"] == 3 and all(r["name"] in c.get(f"/api/modelle/{x}").json()["tags"] for x in alle))

        # -- Material
        zuordnen(c, "material", [m["A"]], ziel="PETG")
        o = optionen(c, "material", alle)
        check("Material: Optionen mit Stand", o["PETG"]["bei"] == 1 and "PLA" in o)
        r = zuordnen(c, "material", alle, ziel="PETG").json()
        check("Material zu drei Modellen: zwei neu, eines schon", r["hinzugefuegt"] == 2 and r["schon"] == 1)

        # -- Sammlung
        r = zuordnen(c, "sammlung", alle, neu="Lager-Kiste").json()
        sid = r["ziel"]
        check("Neue Sammlung aus dem Suchfeld mit den Gewählten", r["neu"] and r["hinzugefuegt"] == 3
              and [s["anzahl"] for s in c.get("/api/sammlungen").json() if s["id"] == sid] == [3])
        r = zuordnen(c, "sammlung", [m["A"], m["D"]], ziel=sid).json()
        check("Zur bestehenden Sammlung: einer neu, einer schon drin", r["hinzugefuegt"] == 1 and r["schon"] == 1
              and [s["anzahl"] for s in c.get("/api/sammlungen").json() if s["id"] == sid] == [4])

        # -- Baugruppe: kein stilles Erhöhen der Menge
        r = zuordnen(c, "baugruppe", [m["A"], m["B"]], neu="Regal").json()
        bid = r["ziel"]
        check("Neue Baugruppe aus dem Suchfeld", r["neu"] and r["hinzugefuegt"] == 2)
        r = zuordnen(c, "baugruppe", [m["A"], m["B"], m["C"]], ziel=bid).json()
        pos = {p["name"]: p["menge"] for p in c.get(f"/api/baugruppen/{bid}").json()["positionen"]}
        check("Zur bestehenden Baugruppe: nur das fehlende kommt dazu, die Mengen der anderen bleiben bei 1",
              r["hinzugefuegt"] == 1 and r["schon"] == 2 and pos == {"A": 1, "B": 1, "C": 1})
        o = optionen(c, "baugruppe", [m["A"], m["D"]])
        check("Optionen der Baugruppen: bei wie vielen schon enthalten", o["Regal"]["bei"] == 1)

        # -- Fehler
        check("Unbekannte Art, keine Modelle, leerer Name: verständlicher Fehler statt Absturz",
              zuordnen(c, "foto", alle, ziel="x").status_code == 400 and zuordnen(c, "tag", [], ziel="x").status_code == 400
              and zuordnen(c, "tag", alle, ziel="  ").status_code == 400 and zuordnen(c, "sammlung", alle, ziel="s_9999").status_code == 400)
    muster.ende()
