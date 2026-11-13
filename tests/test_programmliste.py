"""Mehrere Slicer in der Liste: der bisherige Standard bleibt Standard, Ausblenden/Hinzufügen/Entfernen, der Hauptknopf und das geslichte 3MF
starten nur den Standard-Slicer, und das CAD behält genau einen Platz. Die Programme sind Attrappen, die nur aufschreiben, womit sie gestartet wurden."""
import json
import os
import tempfile
import time

import muster
from muster import check
from fastapi.testclient import TestClient

from test_gcode_ordner import gcode, gcode_3mf

if __name__ == "__main__":
    tmp = tempfile.mkdtemp()
    heim = os.path.join(tmp, "heim")
    os.makedirs(heim)
    os.environ["HOME"] = heim                      # ~/Applications, ~/.local/… des Rechners bleiben aussen vor
    attrappen, protokoll = os.path.join(tmp, "bin"), os.path.join(tmp, "gestartet.txt")
    os.makedirs(attrappen)

    def attrappe(ordner, name):
        os.makedirs(ordner, exist_ok=True)
        pfad = os.path.join(ordner, name)
        with open(pfad, "w") as f:
            f.write(f'#!/bin/sh\necho "{name} $*" >> "{protokoll}"\n')
        os.chmod(pfad, 0o755)
        return pfad

    # Erkennung in der Reihenfolge von BEKANNT: Bambu Studio, OrcaSlicer, PrusaSlicer — „der erste Fund“ ist also Bambu Studio.
    bambu, orca, prusa = (attrappe(attrappen, n) for n in ("bambu-studio", "orca-slicer", "prusa-slicer"))
    freecad, freecadcmd = attrappe(attrappen, "freecad"), attrappe(attrappen, "FreeCADCmd")
    os.environ["PATH"] = attrappen + os.pathsep + "/usr/bin" + os.pathsep + "/bin"
    from partatlas import programme as pr, cad
    from partatlas.main import erstelle_app

    # Weitere Slicer der Liste ziehen den Hauptknopf nicht an sich: kennt der Standard-Slicer ein Format nicht (SuperSlicer kein STEP) und gibt
    # es kein CAD, bleibt es wie vor der Liste bei „nichts“ — es startet nicht ein anderer Slicer, den der Anwender nie dafür gewählt hat.
    ohne_step = {"name": "SuperSlicer", "art": "slicer", "formate": ["3mf", "stl", "obj"], "pfad": "/a", "standard": True}
    mit_step = {"name": "Bambu Studio", "art": "slicer", "formate": ["3mf", "stl", "obj", "step"], "pfad": "/b", "standard": False}
    check("Hauptknopf: ein weiterer Slicer springt nicht für ein Format ein, das der Standard-Slicer nicht kennt",
          pr.standard([ohne_step, mit_step])["step"] is None and pr.standard([ohne_step, mit_step])["stl"] == "/a")

    sammlung = os.path.join(tmp, "3D-Druck")
    os.makedirs(sammlung)
    muster.stl_binaer(os.path.join(sammlung, "Haken.stl"))
    with open(os.path.join(sammlung, "Fertig.gcode.3mf"), "wb") as f:
        f.write(gcode_3mf(["Haken.stl"]))
    with open(os.path.join(sammlung, "Haken.gcode"), "wb") as f:
        f.write(gcode(["Haken.stl"]))

    def zeilen():
        return open(protokoll).read().splitlines() if os.path.exists(protokoll) else []

    def namen(c):
        return [p["name"] for p in c.get("/api/programme").json()["programme"]]

    def slicer(c):
        return [p for p in c.get("/api/programme").json()["programme"] if p["art"] == "slicer"]

    with TestClient(erstelle_app(os.path.join(tmp, "bestand"), prozesse=2)) as c:
        z = c.app.state.zustand
        c.post("/api/wurzeln", json={"pfad": sammlung})
        z["scanner"].warten(120)
        modelle = {m["name"]: m for m in c.get("/api/modelle").json()}
        haken = modelle["Haken"]
        fertig = next(m for m in c.get("/api/modelle").json() if m["name"].startswith("Fertig"))
        check("Vorbereitung: ein STL und ein geslichtes 3MF sind im Katalog", c.get(f"/api/modelle/{fertig['id']}").json().get("geslict"))

        def oeffne(m, **kw):
            if os.path.exists(protokoll):
                os.remove(protokoll)
            r = c.post(f"/api/modelle/{m['id']}/oeffnen", json=kw)
            for _ in range(50):                       # die Attrappe schreibt erst, wenn sie läuft
                if r.status_code != 200 or os.path.exists(protokoll):
                    break
                time.sleep(0.1)
            return r, zeilen()

        # ---- Nichts gewählt: der erste Fund bleibt Standard, wie vor der Liste
        liste = slicer(c)
        check("Ohne Wahl: alle erkannten Slicer stehen da, der erste Fund (Bambu Studio) vorn als Standard",
              [p["name"] for p in liste] == ["Bambu Studio", "OrcaSlicer", "PrusaSlicer"] and [p["standard"] for p in liste] == [True, False, False])
        check("… sie sind als „erkannt“ gekennzeichnet, mit Herkunft „System“", all(p["quelle"] == "erkannt" and p["ort"] == "System" for p in liste))
        check("CAD: weiter genau ein Platz", [p["name"] for p in c.get("/api/programme").json()["programme"] if p["art"] == "cad"] == ["FreeCAD"])
        r, z1 = oeffne(haken)
        check("Hauptknopf für STL startet den Standard-Slicer (Bambu Studio), nicht irgendeinen",
              r.status_code == 200 and len(z1) == 1 and z1[0].startswith("bambu-studio ") and r.json()["programm"] == "Bambu Studio")
        std = c.get("/api/programme").json()["standard"]
        check("Standard je Format: STL im Slicer-Standard, STEP im CAD", std["stl"] == bambu and std["step"] == freecad)
        r, z1 = oeffne(fertig)
        check("Geslichtes 3MF ohne Angabe: startet den Standard-Slicer", r.status_code == 200 and len(z1) == 1 and z1[0].startswith("bambu-studio "))

        did = c.get(f"/api/modelle/{haken['id']}").json()["drucke"][0]["id"]

        def druck_oeffnen():
            if os.path.exists(protokoll):
                os.remove(protokoll)
            r = c.post(f"/api/drucke/{did}/oeffnen")
            for _ in range(50):
                if r.status_code != 200 or os.path.exists(protokoll):
                    break
                time.sleep(0.1)
            return r, zeilen()
        r, z1 = druck_oeffnen()
        check("Druck öffnen (G-Code im Slicer): der Standard-Slicer, nicht der erste der Liste nach Namen", r.status_code == 200 and len(z1) == 1
              and z1[0].startswith("bambu-studio ") and z1[0].endswith(".gcode"))

        # ---- Ausdrücklich gewählt (Prusa): er bleibt Standard, auch wenn er nicht der erste Fund ist
        c.put("/api/einstellungen", json={"programm": {"slicer": prusa}})
        liste = slicer(c)
        check("Gewählter Slicer führt die Liste und trägt die Marke; die übrigen folgen in der Reihenfolge der Erkennung",
              [p["name"] for p in liste] == ["PrusaSlicer", "Bambu Studio", "OrcaSlicer"] and [p["standard"] for p in liste] == [True, False, False])
        r, z1 = oeffne(haken)
        check("Hauptknopf startet den gewählten Standard (Prusa), obwohl Bambu Studio vor ihm erkannt wird", len(z1) == 1 and z1[0].startswith("prusa-slicer "))
        r, z1 = oeffne(fertig)
        check("Geslichtes 3MF: ebenso der gewählte Standard", len(z1) == 1 and z1[0].startswith("prusa-slicer "))
        r, z1 = druck_oeffnen()
        check("Druck öffnen: ebenso der gewählte Standard", len(z1) == 1 and z1[0].startswith("prusa-slicer "))
        r, z1 = oeffne(haken, pfad=orca)
        check("Ausdrücklich ein anderer Slicer aus der Liste: der startet", len(z1) == 1 and z1[0].startswith("orca-slicer "))
        r, _ = oeffne(haken, pfad="/bin/sh")
        check("Ein Pfad, der nicht in der Liste steht, startet nie — auch nicht bei mehreren Slicern", r.status_code == 400)
        r, _ = oeffne(fertig, pfad=freecad)
        check("Geslichtes 3MF in ein CAD: abgelehnt", r.status_code == 400)
        e = c.get("/api/einstellungen").json()
        check("Einstellungen: „programm.slicer“ behält seine Bedeutung (der Standard, hier gewählt)",
              e["programm"]["slicer"]["pfad"] == prusa and not e["programm"]["slicer"]["automatisch"])

        # ---- Zurück auf „automatisch“: wieder der erste Fund
        c.put("/api/einstellungen", json={"programm": {"slicer": ""}})
        check("„Automatisch“: wieder der erste Fund vorn", namen(c)[0] == "Bambu Studio" and slicer(c)[0]["standard"])

        # ---- Alter Eintrag aus früheren Fassungen (Schlüssel „slicer“): bleibt der Standard
        eigener = attrappe(os.path.join(tmp, "irgendwo"), "mein-slicer")
        z["bestand"].einstellungen_setzen(slicer=[{"name": "Alter Slicer", "pfad": eigener}], programm={})
        check("Alter Eintrag („slicer“ aus früheren Fassungen): bleibt Standard und steht vorn",
              slicer(c)[0]["pfad"] == eigener and slicer(c)[0]["standard"] and len(slicer(c)) == 4)
        r, z1 = oeffne(haken)
        check("… und der Hauptknopf startet ihn", len(z1) == 1 and z1[0].startswith("mein-slicer "))
        z["bestand"].einstellungen_setzen(slicer=[], programm={"slicer": prusa})

        # ---- Ausblenden
        r = c.put("/api/einstellungen", json={"programme_aus": {"slicer": [orca]}})
        check("Ausblenden eines erkannten Slicers", r.status_code == 200 and namen(c) == ["PrusaSlicer", "Bambu Studio", "FreeCAD"])
        check("… der Server nennt ihn unter „ausgeblendet“ (zum Wiederanzeigen)", [p["pfad"] for p in c.get("/api/programme").json()["ausgeblendet"]] == [orca])
        r, _ = oeffne(haken, pfad=orca)
        check("Ein ausgeblendeter Slicer startet nicht mehr über die Anfrage", r.status_code == 400)
        check("Der Standard lässt sich nicht ausblenden", c.put("/api/einstellungen", json={"programme_aus": {"slicer": [orca, prusa]}}).status_code == 400
              and namen(c)[0] == "PrusaSlicer")
        check("… die Ablehnung ändert nichts an der gespeicherten Liste", z["bestand"].einstellungen()["programme_aus"] == {"slicer": [orca]})
        r = c.put("/api/einstellungen", json={"programm": {"slicer": bambu}, "programme_aus": {"slicer": [orca, prusa]}})
        check("Im selben Speichern einen anderen Standard wählen und den alten ausblenden: geht",
              r.status_code == 200 and namen(c) == ["Bambu Studio", "FreeCAD"])
        c.put("/api/einstellungen", json={"programm": {"slicer": ""}, "programme_aus": {"slicer": [bambu]}})
        check("Ausgeblendeter erster Fund wird bei „automatisch“ nicht zum Standard: der nächste ist es",
              slicer(c)[0]["name"] == "OrcaSlicer" and slicer(c)[0]["standard"] and "Bambu Studio" not in namen(c))
        c.put("/api/einstellungen", json={"programm": {"slicer": prusa}, "programme_aus": {"slicer": []}})
        check("Wieder anzeigen: alle drei sind zurück, der Standard bleibt vorn",
              namen(c) == ["PrusaSlicer", "Bambu Studio", "OrcaSlicer", "FreeCAD"] and c.get("/api/programme").json()["ausgeblendet"] == [])

        # ---- Hinzufügen und Entfernen eigener Slicer
        r = c.put("/api/einstellungen", json={"programme_eigene": {"slicer": [eigener]}})
        liste = slicer(c)
        check("Eigener Slicer hinzugefügt: steht hinter den erkannten, als „eigen“ mit Herkunft „eigener Ort“",
              r.status_code == 200 and liste[-1]["pfad"] == eigener and liste[-1]["quelle"] == "eigen" and liste[-1]["ort"] == "eigener Ort"
              and not liste[-1]["standard"] and liste[0]["name"] == "PrusaSlicer")
        r, z1 = oeffne(haken, pfad=eigener)
        check("… ihn lässt sich ausdrücklich starten, ohne dass er Standard wurde", len(z1) == 1 and z1[0].startswith("mein-slicer "))
        check("Eigener Pfad nur, wenn er ausführbar ist",
              c.put("/api/einstellungen", json={"programme_eigene": {"slicer": [eigener, os.path.join(tmp, "gibtsnicht")]}}).status_code == 400
              and z["bestand"].einstellungen()["programme_eigene"] == {"slicer": [eigener]})
        check("Eigene Liste: ein Pfad doppelt wird nur einmal gespeichert",
              c.put("/api/einstellungen", json={"programme_eigene": {"slicer": [eigener, eigener]}}).status_code == 200
              and z["bestand"].einstellungen()["programme_eigene"] == {"slicer": [eigener]})
        c.put("/api/einstellungen", json={"programme_eigene": {"slicer": []}})
        check("Entfernen: der eigene Slicer ist aus der Liste", eigener not in [p["pfad"] for p in slicer(c)])
        c.put("/api/einstellungen", json={"programme_eigene": {"slicer": [eigener]}})
        c.put("/api/einstellungen", json={"programm": {"slicer": eigener}})
        check("Eigener Slicer als Standard gewählt: führt die Liste", slicer(c)[0]["pfad"] == eigener and slicer(c)[0]["standard"])
        r = c.put("/api/einstellungen", json={"programme_eigene": {"slicer": []}})
        check("Der Standard lässt sich nicht entfernen, auch wenn er ein eigener ist", r.status_code == 400 and "Standard" in r.json()["fehler"]
              and z["bestand"].einstellungen()["programme_eigene"] == {"slicer": [eigener]})
        c.put("/api/einstellungen", json={"programm": {"slicer": prusa}, "programme_eigene": {"slicer": []}})
        check("Erst einen anderen wählen, im selben Speichern den alten entfernen: geht", eigener not in [p["pfad"] for p in slicer(c)]
              and slicer(c)[0]["pfad"] == prusa)
        # Geisterzeile: ein eingetragener Pfad, den es nicht mehr gibt
        c.put("/api/einstellungen", json={"programme_eigene": {"slicer": [eigener]}})
        os.remove(eigener)
        check("Ein eingetragener Pfad, den es nicht mehr gibt, bleibt keine Geisterzeile", eigener not in [p["pfad"] for p in slicer(c)])
        eigener = attrappe(os.path.join(tmp, "irgendwo"), "mein-slicer")
        c.put("/api/einstellungen", json={"programme_eigene": {"slicer": []}})

        # ---- Unbekanntes wird nicht übernommen
        c.put("/api/einstellungen", json={"programme_eigene": {"cad": [eigener], "sonst": [eigener]}, "programme_aus": {"cad": [freecad]}})
        check("Nur Arten mit Liste werden gespeichert: für das CAD und Unbekanntes bleibt es beim Alten",
              z["bestand"].einstellungen()["programme_eigene"] == {"slicer": []} and z["bestand"].einstellungen()["programme_aus"] == {"slicer": []})
        check("… das CAD hat weiter genau einen Eintrag", [p["name"] for p in c.get("/api/programme").json()["programme"] if p["art"] == "cad"] == ["FreeCAD"])
        check("Schlechte Form wird abgelehnt statt gespeichert", c.put("/api/einstellungen", json={"programme_aus": ["x"]}).status_code == 400)

        # ---- CAD: die Umwandlung bekommt denselben Aufruf wie vorher, egal wie lang die Slicerliste ist
        c.put("/api/einstellungen", json={"programme_eigene": {"slicer": [eigener]}, "programme_aus": {"slicer": [orca]}})
        e = z["bestand"].einstellungen()
        cadprog = pr.programm_fuer(pr.CAD, e)
        check("CAD: `programm_fuer(CAD)` liefert dasselbe FreeCAD, und die Umwandlung ruft denselben FreeCADCmd auf",
              cadprog["pfad"] == freecad and cad.konsole_befehl(cadprog["pfad"]) == [freecadcmd])
        check("CAD: `alle()` liefert weiter genau einen CAD-Eintrag", len([p for p in pr.alle(e) if p["art"] == "cad"]) == 1)
        c.put("/api/einstellungen", json={"programme_eigene": {"slicer": []}, "programme_aus": {"slicer": []}})

        # ---- Gleichnamige Programme: Herkunft unterscheidet sie
        orca_appimage = attrappe(os.path.join(heim, "Applications"), "OrcaSlicer-2.3.0.AppImage")
        orca_flatpak = attrappe(os.path.join(heim, ".local/share/flatpak/exports/bin"), "io.github.softfever.OrcaSlicer")
        gleich = [p for p in slicer(c) if p["name"] == "OrcaSlicer"]
        check("Drei Programme heissen OrcaSlicer: jedes hat eine eigene Herkunft (System, AppImage, Flatpak)",
              sorted(p["ort"] for p in gleich) == ["AppImage", "Flatpak", "System"] and {p["pfad"] for p in gleich} == {orca, orca_appimage, orca_flatpak})
        check("Programme mit eindeutigem Namen haben dennoch eine Herkunft (die Oberfläche zeigt sie nur bei Gleichnamigen)",
              all(p.get("ort") for p in slicer(c)))

    muster.ende()
