"""Baugruppen: Stückliste mit Mengen über mehrere Ebenen, Fortschritt,
Filament und Einkaufsliste, Kaufteil-Katalog, Vorschläge aus Ordnern."""
import os
import tempfile

import muster
from muster import check
from fastapi.testclient import TestClient
from partatlas.baugruppen import menge_aus_namen
from partatlas.main import erstelle_app

if __name__ == "__main__":
    check("Menge aus dem Namen: Arm_x4 → 4, 2x_Halter → 2, Box → 1, Box_v2 → 1",
          [menge_aus_namen(n) for n in ["Arm_x4", "2x_Halter", "Box", "Box_v2", "Motorhalter x 4"]] == [4, 2, 1, 1, 1])

    tmp = tempfile.mkdtemp()
    samm = os.path.join(tmp, "3D-Druck")
    drohne = os.path.join(samm, "Drohne V2")
    os.makedirs(drohne)
    muster.stl_binaer(os.path.join(drohne, "Arm_x4.stl"), 100, 10, 10)          # 10 cm³
    muster.stl_binaer(os.path.join(drohne, "Halter.stl"), 10, 10, 10)            # 1 cm³
    muster.dreimf(os.path.join(drohne, "Top_Plate.3mf"))                         # 15,75 g aus dem Slicer, PETG schwarz
    muster.stl_binaer(os.path.join(samm, "Einzelteil.stl"), 5, 5, 5)

    with TestClient(erstelle_app(os.path.join(tmp, "bestand"), prozesse=2)) as c:
        w = c.post("/api/wurzeln", json={"pfad": samm}).json()["id"]
        c.app.state.zustand["scanner"].warten(120)
        m = {x["name"]: x["id"] for x in c.get("/api/modelle").json()}

        # -- Kaufteil-Katalog
        schrauben = c.get("/api/kaufteile", params={"q": "m3x10"}).json()
        check("Normteile sind da und durchsuchbar (m3x10 findet DIN 912, 7991, 7380)",
              {t["norm"] for t in schrauben} >= {"DIN 912", "DIN 7991", "ISO 7380"})
        m3 = [t["name"] for t in c.get("/api/kaufteile", params={"q": "zylinderkopf m3"}).json()]
        check("Sortierung mit Zahlen: M3×8 vor M3×10", m3.index("Zylinderkopfschraube M3×8") < m3.index("Zylinderkopfschraube M3×10"))
        eigen = c.post("/api/kaufteile", json={"name": "Propeller 5 Zoll"}).json()["id"]
        check("Eigenes Kaufteil anlegen, Kategorie „Eigene“",
              c.get("/api/kaufteile", params={"kategorie": "Eigene"}).json()[0]["id"] == eigen)

        # -- Vorschlag aus dem Ordner
        v = c.get("/api/baugruppen/vorschlaege").json()
        check("Vorschlag: Ordner „Drohne V2“ mit 3 Modellen, eines mit Menge im Namen",
              v and v[0]["name"] == "Drohne V2" and v[0]["anzahl"] == 3 and v[0]["mengen_im_namen"] == 1)
        bid = c.post("/api/baugruppen", json={"aus_ordner": v[0]["ordner"]}).json()["id"]
        d = c.get(f"/api/baugruppen/{bid}").json()
        check("Aus Ordner angelegt; Arm_x4 bekommt Menge 4",
              d["name"] == "Drohne V2" and {p["name"]: p["menge"] for p in d["positionen"]} == {"Arm_x4": 4, "Halter": 1, "Top_Plate": 1})
        check("… und der Vorschlag verschwindet", c.get("/api/baugruppen/vorschlaege").json() == [])

        # -- Unterbaugruppe: Arm-Modul = 1 Arm + 2 Halter, 4× in der Drohne
        modul = c.post("/api/baugruppen", json={"name": "Arm-Modul", "modelle": [m["Arm_x4"]]}).json()["id"]
        c.patch(f"/api/baugruppen/{modul}/positionen", json={"ref": f"MODEL_ASSET/{m['Arm_x4']}", "menge": 1})
        c.post(f"/api/baugruppen/{modul}/positionen", json={"ref": f"MODEL_ASSET/{m['Halter']}", "menge": 2})
        c.post(f"/api/baugruppen/{modul}/positionen", json={"ref": "PURCHASED_PART/din912-m3x10", "menge": 4})
        c.delete(f"/api/baugruppen/{bid}/positionen", params={"ref": f"MODEL_ASSET/{m['Arm_x4']}"})
        c.delete(f"/api/baugruppen/{bid}/positionen", params={"ref": f"MODEL_ASSET/{m['Halter']}"})
        c.post(f"/api/baugruppen/{bid}/positionen", json={"ref": f"ASSEMBLY/{modul}", "menge": 4})
        c.post(f"/api/baugruppen/{bid}/positionen", json={"ref": f"PURCHASED_PART/{eigen}", "menge": 4})
        c.post(f"/api/baugruppen/{bid}/positionen", json={"ref": "PURCHASED_PART/din912-m3x10", "menge": 2})
        r = c.post(f"/api/baugruppen/{modul}/positionen", json={"ref": f"ASSEMBLY/{bid}"})
        check("Kreis verhindert: das Modul kann die Drohne nicht enthalten", r.status_code == 400)

        s = c.get(f"/api/baugruppen/{bid}").json()["summen"]
        check("Mengen multiplizieren sich: 4 Arme + 8 Halter + 1 Platte = 13 Druckteile", s["druckteile"] == 13)
        einkauf = {e["name"]: e["bedarf"] for e in s["einkauf"]}
        check("Einkaufsliste über alle Ebenen: 4×4 + 2 = 18 Schrauben M3×10, 4 Propeller",
              einkauf == {"Zylinderkopfschraube M3×10": 18, "Propeller 5 Zoll": 4})
        # Ohne Slicer: 1,2 mm Hülle + 15 % Füllung, PLA 1,24 g/cm³.
        # Arm 100×10×10 mm: V 10 cm³, A 42 cm² → Hülle 5,04 → 5,784 cm³ → 7,172 g, ×4 = 28,69 g
        # Halter 10×10×10: V 1, A 6 → Hülle 0,72 → 0,762 cm³ → 0,945 g, ×8 = 7,56 g
        # Platte 15,75 g aus dem Slicer.
        check("Gewicht: Slicer-Wert, sonst Hülle + 15 % Füllung, als geschätzt markiert",
              abs(s["gewicht_g"] - (28.69 + 7.56 + 15.75)) < 0.2 and s["gewicht_geschaetzt"])
        fil = {(f["material"], f["farbe"]): f["gesamt_g"] for f in s["filament"]}
        check("Filament je Material und Farbe: PETG schwarz aus der 3MF, der Rest „Material offen“ statt still PLA",
              abs(fil.get(("PETG", "#000000"), -1e9) - 15.75) < 0.1 and abs(fil.get((None, None), -1e9) - 36.25) < 0.2)
        mat = {m["material"]: m for m in s["materialien"]}
        check("Je Material zusammengefasst, mit Farben und Anteil einer 1-kg-Rolle; „offen“ steht zuletzt",
              mat["PETG"]["farben"] == [{"farbe": "#000000", "gesamt_g": 15.8, "offen_g": 15.8}]
              and mat["PETG"]["rollen"] == 0.02 and s["materialien"][-1]["material"] is None and s["material_offen"] == 1)
        r = c.post(f"/api/baugruppen/{bid}/material", json={"material": "tpu", "farbe": "#c0392b"})
        s = c.get(f"/api/baugruppen/{bid}").json()["summen"]
        mat = {m["material"]: m for m in s["materialien"]}
        check("„Material festlegen“ für alle Offenen: TPU rot, das PETG bleibt PETG",
              r.status_code == 200 and "TPU" in mat and "PETG" in mat and None not in mat
              and mat["TPU"]["farben"][0]["farbe"] == "#c0392b")
        check("Farbe nur als #RRGGBB (landet als CSS in der Oberfläche)",
              c.patch(f"/api/baugruppen/{modul}/positionen", json={"ref": f"MODEL_ASSET/{m['Halter']}",
                      "farbe": "red;background:url(x)"}).status_code == 400)
        check("Druckzeit ehrlich: zwei der drei Druckteile ohne Slicer-Zeit", s["ohne_zeit"] == 2)

        # -- Fortschritt
        f = c.get(f"/api/baugruppen/{bid}").json()["fortschritt"]
        check("Fortschritt am Anfang: 0 von 13 + 22 Kaufteile", f == {"bedarf": 35, "erledigt": 0})
        c.patch(f"/api/baugruppen/{modul}/positionen", json={"ref": f"MODEL_ASSET/{m['Halter']}", "erledigt": 8})
        c.patch(f"/api/baugruppen/{bid}/positionen", json={"ref": f"PURCHASED_PART/{eigen}", "erledigt": 10})
        f = c.get(f"/api/baugruppen/{bid}").json()["fortschritt"]
        check("Zähler gelten über alle Exemplare (8 Halter); zu viel zählt nur bis zum Bedarf (4 Propeller)",
              f["erledigt"] == 12)
        dm = c.get(f"/api/baugruppen/{modul}").json()
        check("Unterbaugruppe weiss, dass sie 4× gebraucht wird: Halter-Bedarf 8, nicht 2",
              dm["exemplare"] == 4 and next(p for p in dm["positionen"] if p["name"] == "Halter")["bedarf"] == 8)
        s = c.get(f"/api/baugruppen/{bid}").json()["summen"]
        # Arm ist inzwischen TPU: 5,784 cm³ × 1,21 × 4 = 27,99 g — die Dichte folgt dem Material.
        check("Offen: Gewicht ohne die fertigen Halter, mit der Dichte des gewählten Materials",
              abs(s["offen_gewicht_g"] - (27.99 + 15.75)) < 0.2)
        check("Negative Menge wird zu 1", c.patch(f"/api/baugruppen/{bid}/positionen",
                                                  json={"ref": f"ASSEMBLY/{modul}", "menge": -3}).status_code == 200
              and next(p for p in c.get(f"/api/baugruppen/{bid}").json()["positionen"] if p["art"] == "baugruppe")["menge"] == 1)
        c.patch(f"/api/baugruppen/{bid}/positionen", json={"ref": f"ASSEMBLY/{modul}", "menge": 4})

        n = c.post(f"/api/baugruppen/{bid}/warteschlange").json()["eingereiht"]
        check("Fehlende Druckteile in die Warteschlange (Arm und Platte, nicht die fertigen Halter)",
              n == 2 and sorted(x["name"] for x in c.get("/api/warteschlange").json()) == ["Arm_x4", "Top_Plate"])

        # -- Wo verwendet, Löschen
        mod = c.get(f"/api/modelle/{m['Halter']}").json()
        check("Im Modell sichtbar: steckt im Arm-Modul (2×)", mod["baugruppen"] == [{"id": modul, "name": "Arm-Modul", "menge": 2}])
        check("Löschvorschau nennt die Baugruppen-Verknüpfung",
              c.get(f"/api/modelle/{m['Halter']}/loeschen").json()["kanten"].get("CONTAINS") == 1)
        liste = {b["name"]: b for b in c.get("/api/baugruppen").json()}
        check("Liste mit Fortschritt; das Modul weiss, dass es verwendet wird",
              liste["Drohne V2"]["bedarf"] == 35 and liste["Arm-Modul"]["verwendet_in"] == 1)

        md = c.get(f"/api/baugruppen/{bid}/export", params={"format": "md"}).text
        csv_text = c.get(f"/api/baugruppen/{bid}/export").text
        check("Export Markdown mit Einkaufsliste über alle Ebenen", "18 Stück Zylinderkopfschraube M3×10" in md)
        check("Export CSV mit Semikolon (öffnet in deutschem Excel)", csv_text.splitlines()[0].startswith("Art;Menge;"))

        c.delete(f"/api/baugruppen/{bid}")
        check("Baugruppe löschen: Modelle und Unterbaugruppe bleiben",
              len(c.get("/api/modelle").json()) == 4 and [b["name"] for b in c.get("/api/baugruppen").json()] == ["Arm-Modul"])

        sid = c.post("/api/sammlungen", json={"name": "Kiste", "modelle": [m["Einzelteil"], m["Halter"]]}).json()["id"]
        neu = c.post("/api/baugruppen", json={"aus_sammlung": sid}).json()["id"]
        check("Sammlung in Baugruppe umwandeln", [p["name"] for p in c.get(f"/api/baugruppen/{neu}").json()["positionen"]] == ["Einzelteil", "Halter"])
    muster.ende()
