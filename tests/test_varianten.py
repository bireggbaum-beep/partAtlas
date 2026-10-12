"""Varianten: dasselbe Teil in anderen Formaten — automatisch über gleichen Namen im gleichen Ordner, dazu von Hand verknüpft und gelöst."""
import os
import tempfile

import muster
from muster import check
from fastapi.testclient import TestClient
from partatlas.main import erstelle_app


def varianten(c, mid):
    return sorted((v["name"], v["format"], v["hand"]) for v in c.get(f"/api/modelle/{mid}").json()["varianten"])


if __name__ == "__main__":
    tmp = tempfile.mkdtemp()
    samm = os.path.join(tmp, "3D")
    os.makedirs(os.path.join(samm, "Export"))
    muster.stl_binaer(os.path.join(samm, "Halter.stl"), 10, 20, 30)
    muster.step(os.path.join(samm, "Halter.step"))
    muster.fcstd(os.path.join(samm, "HALTER.FCStd"))
    muster.stl_binaer(os.path.join(samm, "Export", "Halter.stl"), 11, 20, 30)     # gleicher Name, anderer Ordner: keine Variante
    muster.stl_binaer(os.path.join(samm, "Deckel.stl"), 12, 20, 30)

    with TestClient(erstelle_app(os.path.join(tmp, "bestand"), prozesse=2)) as c:
        z = c.app.state.zustand
        c.post("/api/wurzeln", json={"pfad": samm})
        z["scanner"].warten(120)
        alle = c.get("/api/modelle").json()
        stl = next(m["id"] for m in alle if m["format"] == "stl" and m["name"] == "Halter" and "Export" not in (m.get("ordner") or [""])[0])
        step = next(m["id"] for m in alle if m["format"] == "step")
        deckel = next(m["id"] for m in alle if m["name"] == "Deckel")
        check("Gleicher Name im gleichen Ordner (Gross-/Kleinschreibung egal): die anderen Formate sind Varianten, der Export-Ordner nicht",
              varianten(c, stl) == [("HALTER", "fcstd", False), ("Halter", "step", False)])
        c.delete(f"/api/modelle/{stl}/varianten/{step}")
        check("Lösen: beide Seiten vergessen die Zuordnung", ("Halter", "step", False) not in varianten(c, stl)
              and ("Halter", "stl", False) not in varianten(c, step))
        c.post("/api/varianten", json={"modelle": [stl, step, deckel]})
        check("Von Hand verknüpft (auch eine gelöste wieder): als „von Hand“ markiert, auf beiden Seiten",
              ("Deckel", "stl", True) in varianten(c, stl) and ("Halter", "step", True) in varianten(c, stl)
              and ("Halter", "stl", True) in varianten(c, deckel))
        c.delete(f"/api/modelle/{deckel}/varianten/{stl}")
        check("Von Hand verknüpfte lösen", ("Deckel", "stl", True) not in varianten(c, stl))
        check("Ein einzelnes Modell lässt sich nicht verknüpfen", c.post("/api/varianten", json={"modelle": [stl]}).status_code == 400)
    muster.ende()
