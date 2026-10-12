"""Vorschaubilder: das Bild aus der Datei geht vor (auch bei FreeCAD-Dokumenten), berechnet wird es nur, wenn keins da ist, auf Wunsch
für ein Modell oder wenn „immer“ eingestellt ist. FreeCAD ist die Attrappe aus cad_attrappe.py."""
import os
import sys
import tempfile

import muster
from muster import check
from fastapi.testclient import TestClient
from partatlas.main import erstelle_app

ATTRAPPE = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "cad_attrappe.py")]


def warten(z):
    z["scanner"].warten(120)
    z["scanner"].worker.warten(120)


def modell(c, name):
    return next(m for m in c.get("/api/modelle").json() if m["name"] == name)


def arten(c, mid):
    """Bilder in der Reihenfolge der Galerie, mit dem, das die Kachel zeigt."""
    return [(a["art"], a["ist_vorschaubild"]) for a in c.get(f"/api/modelle/{mid}").json()["ansichten"]]


if __name__ == "__main__":
    tmp = tempfile.mkdtemp()
    samm = os.path.join(tmp, "3D")
    os.makedirs(samm)
    muster.fcstd(os.path.join(samm, "Gehaeuse.FCStd"))           # mit Thumbnail
    muster.dreimf(os.path.join(samm, "Platte.3mf"))                # mit eingebettetem Bild
    muster.stl_binaer(os.path.join(samm, "Arm.stl"))

    with TestClient(erstelle_app(os.path.join(tmp, "bestand"), prozesse=2)) as c:
        z = c.app.state.zustand
        z["scanner"].cad_befehl = ATTRAPPE
        c.put("/api/einstellungen", json={"fcstd_freecad": "ja"})
        c.post("/api/wurzeln", json={"pfad": samm})
        warten(z)
        g, p = modell(c, "Gehaeuse"), modell(c, "Platte")
        check("FCStd mit Thumbnail: FreeCAD liefert Maße, aber kein zweites Bild; das aus der Datei ist das Vorschaubild",
              g["cad"] == "ok" and g["masse"] is not None and arten(c, g["id"]) == [("extrahiert", True)])
        check("3MF mit Bild: nichts berechnet", arten(c, p["id"]) == [("extrahiert", True)])

        # -- Von Hand für ein Modell: berechnet und danach das Vorschaubild der Kachel
        r = c.post(f"/api/modelle/{g['id']}/vorschau/berechnen").json()
        warten(z)
        check("Vorschaubild berechnen (FCStd, Netz liegt schon da): gerechnet aus dem Netz und als Vorschaubild gesetzt",
              r["weg"] == "rechnen" and arten(c, g["id"]) == [("extrahiert", False), ("berechnet", True)])
        r = c.post(f"/api/modelle/{p['id']}/vorschau/berechnen").json()
        warten(z)
        check("… ebenso für eine 3MF; das Bild aus der Datei bleibt in der Galerie",
              arten(c, p["id"]) == [("extrahiert", False), ("berechnet", True)])

        # -- Einstellung „immer“: auch Dateien mit Bild bekommen beim Einlesen ein berechnetes, und es steht vorn
        check("Ungültiger Wert wird abgewiesen", c.put("/api/einstellungen", json={"vorschau_berechnen": "manchmal"}).status_code == 400)
        c.put("/api/einstellungen", json={"vorschau_berechnen": "immer"})
        muster.dreimf(os.path.join(samm, "Deckel.3mf"))
        muster.fcstd(os.path.join(samm, "Halter.FCStd"))
        c.post("/api/scan")
        warten(z)
        check("„Immer“: neue 3MF mit Bild bekommt ein berechnetes, das vorn steht",
              arten(c, modell(c, "Deckel")["id"]) == [("berechnet", True), ("extrahiert", False)])
        check("„Immer“: FreeCAD rechnet auch für ein FCStd mit Thumbnail ein Bild",
              arten(c, modell(c, "Halter")["id"]) == [("berechnet", True), ("extrahiert", False)])

        # -- FCStd ohne Zusage: der Wunsch wird mit Grund abgelehnt, nichts wird gestartet
        c.put("/api/einstellungen", json={"fcstd_freecad": "nein"})
        muster.fcstd(os.path.join(samm, "Neu.FCStd"))
        c.post("/api/scan")
        warten(z)
        r = c.post(f"/api/modelle/{modell(c, 'Neu')['id']}/vorschau/berechnen")
        check("FCStd ohne Zusage für FreeCAD: abgelehnt mit Hinweis auf die Einstellung", r.status_code == 400 and "Einstellungen" in r.json()["fehler"])

    muster.ende()
