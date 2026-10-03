"""Aufräumen: Vorschläge mit Grund und Grösse, nichts Gedrucktes, Verbautes oder Favorisiertes ohne Not; Ausnahmen („Behalten“);
ein gelöschter Entwurf gilt als aufgeräumt statt als „Datei fehlt“. partAtlas löscht dabei nichts."""
import os
import tempfile
import time

import muster
from muster import check
from fastapi.testclient import TestClient
from partatlas import aufraeumen
from partatlas.main import erstelle_app


def warten(c):
    c.app.state.zustand["scanner"].warten(120)


def gruppe(c, art):
    return {e["name"]: e for g in c.get("/api/aufraeumen").json()["gruppen"] if g["art"] == art for e in g["eintraege"]}


if __name__ == "__main__":
    tmp = tempfile.mkdtemp()
    samm = os.path.join(tmp, "Sammlung")
    os.makedirs(os.path.join(samm, "Kopie"))
    for n, x in (("Entwurf_v1", 11), ("Doppelt", 12), ("Alt", 13), ("Gedruckt", 14), ("Verbaut", 15), ("Liebling", 16), ("Bleibt", 18)):
        muster.stl_binaer(os.path.join(samm, f"{n}.stl"), x, 12, 13)
    muster.stl_binaer(os.path.join(samm, "Kopie", "Doppelt.stl"), 12, 12, 13)          # gleicher Inhalt
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "werkzeuge"))
    import demo_sammlung
    demo_sammlung.stl(os.path.join(samm, "Gross.stl"), demo_sammlung.drehkoerper([(0.01, 0), (20, 0.5), (26, 30), (0.01, 60)], 64))
    zwei_jahre = time.time() - 2 * 365 * 86400
    for n in ("Alt", "Gedruckt", "Verbaut", "Liebling"):
        os.utime(os.path.join(samm, f"{n}.stl"), (zwei_jahre, zwei_jahre))
    vorher = sorted(os.listdir(samm))
    aufraeumen.GROSS_AB = os.path.getsize(os.path.join(samm, "Gross.stl"))                # „gross“ ohne 10-MB-Datei im Test
    with TestClient(erstelle_app(os.path.join(tmp, "bestand"), prozesse=2)) as c:
        c.post("/api/wurzeln", json={"pfad": samm})
        warten(c)
        m = {x["name"]: x["id"] for x in c.get("/api/modelle").json()}
        os.utime(os.path.join(samm, "Gross.stl"))
        c.patch(f"/api/modelle/{m['Entwurf_v1']}", json={"entwurf": True})
        c.post("/api/drucke", json={"modelle": [m["Gedruckt"]], "felder": {}})
        c.post("/api/baugruppen", json={"name": "Gerät", "modelle": [m["Verbaut"]]})
        c.patch(f"/api/modelle/{m['Liebling']}", json={"favorit": True})

        d = c.get("/api/aufraeumen").json()
        arten = {g["art"]: {e["name"] for e in g["eintraege"]} for g in d["gruppen"]}
        check("Vier Gruppen: Entwürfe, Kopien gleichen Inhalts, gross ohne Verwendung, lange nicht angefasst",
              [g["art"] for g in d["gruppen"]] == ["entwuerfe", "kopien", "gross", "ungenutzt"])
        check("Entwurf, Kopie, grosse und alte Datei werden vorgeschlagen, je in ihrer Gruppe",
              arten["entwuerfe"] == {"Entwurf_v1"} and arten["kopien"] == {"Doppelt"} and "Gross" in arten["gross"]
              and arten["ungenutzt"] == {"Alt"} or print("   ", arten))
        check("Gedrucktes, Verbautes und Favoriten nie als Vorschlag (alt genug wären sie)",
              not ({"Gedruckt", "Verbaut", "Liebling"} & set().union(*arten.values())))
        k = gruppe(c, "kopien")["Doppelt"]
        check("Kopien: zählt nur die überzählige Kopie, nennt beide Pfade und den Grund",
              k["bytes"] == os.path.getsize(os.path.join(samm, "Doppelt.stl")) and len(k["pfade"]) == 2 and "2 Kopien" in k["grund"])
        check("Jede Gruppe mit Anzahl und Summe", all(g["n"] == len(g["eintraege"]) and g["bytes"] == sum(e["bytes"] for e in g["eintraege"])
                                                      for g in d["gruppen"]))
        # Ein Entwurf, an dem noch etwas hängt: vorgeschlagen, aber mit Hinweis.
        c.post("/api/baugruppen", json={"name": "Alt-Gerät", "modelle": [m["Entwurf_v1"]]})
        e = gruppe(c, "entwuerfe")["Entwurf_v1"]
        check("Entwurf in einer Baugruppe: bleibt Vorschlag, aber mit „hängt daran“", e["vorsicht"] and "in Baugruppe Alt-Gerät" in e["haengt"])

        c.post(f"/api/modelle/{m['Alt']}/behalten", json={"an": True})
        check("Behalten: nicht mehr vorgeschlagen, steht in den Ausnahmen",
              "Alt" not in gruppe(c, "ungenutzt") and [x["name"] for x in c.get("/api/aufraeumen/behalten").json()] == ["Alt"]
              and c.get("/api/aufraeumen").json()["behalten"] == 1)
        c.post(f"/api/modelle/{m['Alt']}/behalten", json={"an": False})
        check("Ausnahme zurückgenommen: wieder vorgeschlagen", "Alt" in gruppe(c, "ungenutzt"))
        kat = c.app.state.zustand["katalog"]
        eigen = os.path.join(samm, "Kopie", "Doppelt.stl")
        check("Im Ordner zeigen nur für einen eigenen Pfad des Modells, nicht für einen beliebigen",
              aufraeumen.pfad_von(kat, m["Doppelt"], "/etc/passwd") is None and aufraeumen.pfad_von(kat, m["Doppelt"], eigen) == eigen
              and aufraeumen.pfad_von(kat, m["Alt"], eigen) is None)
        check("Die Ansicht hat nichts gelöscht oder verschoben", sorted(os.listdir(samm)) == vorher)

        # -- Der Anwender löscht selbst: der Entwurf ist aufgeräumt, eine andere Datei fehlt
        os.remove(os.path.join(samm, "Entwurf_v1.stl"))
        os.remove(os.path.join(samm, "Alt.stl"))
        c.post("/api/scan")
        warten(c)
        st = c.app.state.zustand["scanner"].status
        z = c.get("/api/zaehler").json()
        papier = {x["name"] for x in c.get("/api/modelle", params={"ansicht": "papierkorb"}).json()}
        check("Gelöschter Entwurf: still im Papierkorb (zurückholbar), die Bilanz nennt ihn; nicht „Datei fehlt“",
              "Entwurf_v1" in papier and st["aufgeraeumt"] == 1 and "Entwurf_v1" not in {x["name"] for x in c.get("/api/modelle", params={"ansicht": "fehlt"}).json()})
        check("Gelöschte Datei ohne Entwurf: wie bisher „Datei fehlt“, nicht weggeräumt",
              "Alt" not in papier and z["fehlt"] == 1)
        c.post(f"/api/modelle/{m['Entwurf_v1']}/wiederherstellen")
        check("Der aufgeräumte Entwurf lässt sich zurückholen (dann ohne Datei)",
              c.get(f"/api/modelle/{m['Entwurf_v1']}").json()["papierkorb"] is False)
    muster.ende()
