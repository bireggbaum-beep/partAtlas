"""Baugruppen: Stückliste mit Mengen über mehrere Ebenen, Fortschritt,
Filament und Einkaufsliste, Kaufteil-Katalog, Vorschläge aus Ordnern."""
import os
import tempfile

import muster
from muster import check
from fastapi.testclient import TestClient
from partatlas.baugruppen import menge_aus_namen
from partatlas.main import erstelle_app

# Sidecar: Baugruppen sprechen den Kern nur über Teilezugriff an (siehe partatlas/teilezugriff.py).
VERBOTEN = ("_kurz(", "PART_GEOMETRY", ".k.", "katalog.k", "get_node(ref(MODELL", "MODEL_ASSET/")


def kern_zugriffe(datei):
    quelle = os.path.join(os.path.dirname(__file__), "..", "partatlas", datei)
    with open(quelle, encoding="utf-8") as f:
        zeilen = [z for z in f if not z.lstrip().startswith("#")]
    return [v for v in VERBOTEN for z in zeilen if v in z.split("#")[0]]


if __name__ == "__main__":
    check("Baugruppen greifen nur über Teilezugriff in den Kern (keine Kachel-, Geometrie- oder Modellknoten-Zugriffe)",
          kern_zugriffe("baugruppen.py") == [] and kern_zugriffe("stueckliste.py") == [])
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

    # Serverfehler als 500 statt Ausnahme: sonst bricht die Suite ab, statt FAIL zu melden.
    with TestClient(erstelle_app(os.path.join(tmp, "bestand"), prozesse=2), raise_server_exceptions=False) as c:
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
        check("Filament je Material und Farbe: PETG schwarz aus der 3MF, der Rest mit dem Standard (PLA)",
              abs(fil.get(("PETG", "#000000"), -1e9) - 15.75) < 0.1 and abs(fil.get(("PLA", None), -1e9) - 36.25) < 0.2)
        mat = {m["material"]: m for m in s["materialien"]}
        check("Je Material zusammengefasst, mit Farben und Rollenanteil; was nur angenommen ist, steht dabei",
              mat["PETG"]["farben"] == [{"farbe": "#000000", "gesamt_g": 15.8, "offen_g": 15.8}]
              and mat["PETG"]["rollen"] == 0.02 and mat["PETG"]["angenommen_g"] == 0
              and abs(mat["PLA"]["angenommen_g"] - 36.2) < 0.2)
        # Standard aus den Einstellungen: wer nur PLA+ druckt, stellt das einmal ein.
        e = c.put("/api/einstellungen", json={"standard_material": "pla+", "standard_farbe": "#8a8a8a", "rolle_g": 750})
        s = c.get(f"/api/baugruppen/{bid}").json()["summen"]
        mat = {m["material"]: m for m in s["materialien"]}
        check("Einstellungen: Standard PLA+ grau, Rolle 750 g — gilt für alle Teile ohne Angabe",
              e.status_code == 200 and "PLA+" in mat and "PLA" not in mat and mat["PLA+"]["farben"][0]["farbe"] == "#8a8a8a"
              and s["rolle_g"] == 750 and mat["PLA+"]["rollen"] == round(mat["PLA+"]["gesamt_g"] / 750, 2))
        check("… das PETG aus dem Slicer bleibt PETG schwarz", "PETG" in mat and mat["PETG"]["farben"][0]["farbe"] == "#000000")
        check("Einstellungen: falsche Farbe abgelehnt", c.put("/api/einstellungen", json={"standard_farbe": "blau"}).status_code == 400)
        r = c.post(f"/api/baugruppen/{bid}/material", json={"material": "tpu", "farbe": "#c0392b"})
        s = c.get(f"/api/baugruppen/{bid}").json()["summen"]
        mat = {m["material"]: m for m in s["materialien"]}
        check("Für alle ohne Angabe festlegen: TPU rot, das PETG bleibt PETG, nichts mehr angenommen",
              r.status_code == 200 and "TPU" in mat and "PETG" in mat and "PLA+" not in mat
              and mat["TPU"]["farben"][0]["farbe"] == "#c0392b" and mat["TPU"]["angenommen_g"] == 0)
        check("Farbe nur als #RRGGBB (landet als CSS in der Oberfläche)",
              c.patch(f"/api/baugruppen/{modul}/positionen", json={"ref": f"MODEL_ASSET/{m['Halter']}",
                      "farbe": "red;background:url(x)"}).status_code == 400)
        check("Druckzeit ehrlich: zwei der drei Druckteile ohne Slicer-Zeit", s["ohne_zeit"] == 2)

        # -- Fortschritt
        f = c.get(f"/api/baugruppen/{bid}").json()["fortschritt"]
        check("Fortschritt getrennt: 0 von 13 Druckteilen, 0 von 22 Kaufteilen",
              (f["druck_bedarf"], f["druck_erledigt"], f["kauf_bedarf"], f["kauf_erledigt"]) == (13, 0, 22, 0))
        c.patch(f"/api/baugruppen/{modul}/positionen", json={"ref": f"MODEL_ASSET/{m['Halter']}", "erledigt": 8})
        c.patch(f"/api/baugruppen/{bid}/positionen", json={"ref": f"PURCHASED_PART/{eigen}", "erledigt": 10})
        f = c.get(f"/api/baugruppen/{bid}").json()["fortschritt"]
        check("Zähler gelten über alle Exemplare (8 Halter); zu viel zählt nur bis zum Bedarf (4 Propeller)",
              f["erledigt"] == 12 and f["druck_erledigt"] == 8 and f["kauf_erledigt"] == 4)
        z = {x["name"]: x for x in c.get(f"/api/baugruppen/{bid}").json()["summen"]["zeiten"]}
        check("Druckzeit je Teil: Platte mit Slicer-Zeit vorn (1 h aus slice_info), Halter ohne Zeit, 8 Stück",
              list(z)[0] == "Top_Plate" and z["Top_Plate"]["gesamt_s"] == 3600 and z["Halter"]["je_s"] is None
              and z["Halter"]["stueck"] == 8)
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

        r = c.get(f"/api/baugruppen/{bid}/export", params={"format": "pdf"})
        import io
        import sys
        # pypdf lädt `cryptography`, falls vorhanden; in manchen Umgebungen
        # stürzt das beim Import ab. Zum Textlesen braucht es keins.
        sys.modules.setdefault("cryptography", None)
        from pypdf import PdfReader
        try:
            text = "\n".join(seite.extract_text() for seite in PdfReader(io.BytesIO(r.content)).pages)
        except Exception:
            text = ""          # kein lesbares PDF: die Prüfungen darunter melden FAIL
        check("Stückliste als PDF: application/pdf, lesbar — auch mit kaputtem eingebettetem Vorschaubild", r.status_code == 200
              and r.headers["content-type"] == "application/pdf" and r.content[:5] == b"%PDF-")
        check("PDF: Strukturstückliste mit Positionsnummern über die Ebenen (Arm-Modul 1.1, 1.2 …)",
              "Strukturstückliste" in text and "Arm-Modul" in text and any(f"{n}.1" in text for n in range(1, 6)))
        check("PDF: Mengenübersicht zählt über alle Ebenen (8× Halter)", "Mengenübersicht" in text and "8×" in text)
        struktur = text.split("Strukturstückliste", 1)[-1].split("Mengenübersicht", 1)[0]
        import re as _re
        check("PDF: Strukturstückliste zeigt Menge je Modul (2) und gesamt (8) für den Halter",
              bool(_re.search(r"\d\.\d+\s+Halter\s+[^\n]*Halter\.stl\s+2\s+8\s", struktur)))
        check("PDF: Einkaufsliste mit 18 Schrauben M3×10 über alle Ebenen",
              "Einkaufsliste" in text and "18" in text and "M3×10" in text)
        # -- PDF einstellbar: Abschnitte und Darstellung kommen aus den Einstellungen
        c.put("/api/einstellungen", json={"pdf": {"mengen": False, "einkauf": False, "pfade": False, "Unsinn": True}})
        check("PDF-Einstellungen: nur bekannte Schalter werden gespeichert, Standard bleibt für den Rest",
              c.get("/api/einstellungen").json()["pdf"] == {"struktur": True, "mengen": False, "einkauf": False, "filament": True,
                                                            "kennzahlen": True, "bilder": True, "kaestchen": True, "pfade": False})
        r2 = c.get(f"/api/baugruppen/{bid}/export", params={"format": "pdf"})
        try:
            text2 = "\n".join(s.extract_text() for s in PdfReader(io.BytesIO(r2.content)).pages)
        except Exception:
            text2 = ""
        check("PDF: abgeschaltete Abschnitte fehlen, die übrigen bleiben und werden neu nummeriert",
              "Strukturstückliste" in text2 and "Mengenübersicht" not in text2 and "Einkaufsliste" not in text2
              and bool(_re.search(r"\n2\s+Filament", text2)) and "Halter.stl" not in text2)
        c.put("/api/einstellungen", json={"pdf": {}})
        md = c.get(f"/api/baugruppen/{bid}/export", params={"format": "md"}).text
        csv_text = c.get(f"/api/baugruppen/{bid}/export").text
        check("Export Markdown mit Einkaufsliste über alle Ebenen", "18 Stück Zylinderkopfschraube M3×10" in md)
        check("Export CSV mit Semikolon (öffnet in deutschem Excel)", csv_text.splitlines()[0].startswith("Art;Menge;"))

        # -- Bezugsquelle am Kaufteil (Paket A)
        link = "https://www.aliexpress.com/item/1005001"
        r = c.patch("/api/kaufteile/din912-m3x10", json={"link": link, "artikelnr": "M3x10-A2", "hinweis": "Mit Schraubensicherung"})
        check("Kaufteil: Link, Artikelnummer und Hinweis speichern", r.status_code == 200
              and next(t for t in c.get("/api/kaufteile", params={"q": "m3x10"}).json() if t["id"] == "din912-m3x10")["link"] == link)
        schr = next(e for e in c.get(f"/api/baugruppen/{bid}").json()["summen"]["einkauf"] if e["id"] == "din912-m3x10")
        check("Einkaufsliste trägt Link, Artikelnummer und Hinweis", (schr["link"], schr["artikelnr"], schr["hinweis"]) == (link, "M3x10-A2", "Mit Schraubensicherung"))
        md = c.get(f"/api/baugruppen/{bid}/export", params={"format": "md"}).text
        zeile = next(z for z in c.get(f"/api/baugruppen/{bid}/export").text.splitlines() if "M3×10" in z)
        check("Markdown und CSV nennen die Bezugsquelle", f"{link} (M3x10-A2)" in md and zeile.endswith(f"{link};M3x10-A2"))
        pdf = PdfReader(io.BytesIO(c.get(f"/api/baugruppen/{bid}/export", params={"format": "pdf"}).content))
        check("PDF-Einkaufsliste nennt die Bezugsquelle", "aliexpress.com/item/1005001" in "".join(x.extract_text() for x in pdf.pages))
        check("Link nur mit http(s): javascript: wird abgelehnt",
              c.patch("/api/kaufteile/din912-m3x10", json={"link": "javascript:alert(1)"}).status_code == 400
              and c.patch("/api/kaufteile/din912-m3x10", json={"link": 'https://x.de/"onclick=1'}).status_code == 400)
        check("Unbekanntes Feld, zu langer Text und unbekanntes Kaufteil werden abgelehnt",
              c.patch("/api/kaufteile/din912-m3x10", json={"preis": 1}).status_code == 400
              and c.patch("/api/kaufteile/din912-m3x10", json={"hinweis": "x" * 201}).status_code == 400
              and c.patch("/api/kaufteile/gibt-es-nicht", json={"link": link}).status_code == 400)
        c.patch("/api/kaufteile/din912-m3x10", json={"link": ""})
        check("Link leeren geht", next(t for t in c.get("/api/kaufteile", params={"q": "m3x10"}).json() if t["id"] == "din912-m3x10")["link"] == "")

        # -- Wo verbaut über alle Ebenen (Paket A)
        wege = c.get("/api/verwendung", params={"ziel": "PURCHASED_PART/din912-m3x10"}).json()
        gesamt = sorted((w["gesamt"], [x["name"] for x in w["weg"]]) for w in wege)
        check("Wo verbaut: M3×10 steckt direkt in der Drohne (2) und über das Arm-Modul darin (4×4 = 16)",
              gesamt == [(2, ["Drohne V2"]), (16, ["Drohne V2", "Arm-Modul"])])
        check("Die Gesamtmengen aller Wege ergeben den Bedarf der Einkaufsliste (18)", sum(w["gesamt"] for w in wege) == 18)
        halter = c.get("/api/verwendung", params={"ziel": f"MODEL_ASSET/{m['Halter']}"}).json()
        check("Wo verbaut: ein Halter steckt 2× im Arm-Modul, das 4× in der Drohne steckt (8)",
              [(w["gesamt"], [(x["name"], x["menge"]) for x in w["weg"]]) for w in halter] == [(8, [("Drohne V2", 4), ("Arm-Modul", 2)])])
        check("Wo verbaut: eine unbekannte Art von Teil wird abgelehnt",
              c.get("/api/verwendung", params={"ziel": "TAG/x"}).status_code == 400)

        # -- Rückgängig und Wiederholen (je Kontext eine Liste: das Projekt oder die Baugruppe, die bearbeitet wird)
        def pos(b_id):
            return {p["ref"]: p for p in c.get(f"/api/baugruppen/{b_id}").json()["positionen"]}
        def zurueck(k):
            return c.post(f"/api/baugruppen/{k}/rueckgaengig")

        def wieder(k):
            return c.post(f"/api/baugruppen/{k}/wiederholen")
        arm = f"MODEL_ASSET/{m['Arm_x4']}"
        menge0 = pos(modul)[arm]["menge"]
        c.patch(f"/api/baugruppen/{modul}/positionen", json={"ref": arm, "menge": menge0 + 5})
        v = c.get(f"/api/baugruppen/{modul}").json()["verlauf"]
        check("Verlauf nennt die letzte Änderung mit dem Namen der Baugruppe", v["zurueck"] == "Menge ändern (Arm-Modul)" and v["vor"] is None)
        r = zurueck(modul)
        check("Rückgängig: die Menge ist wieder die alte", r.json()["text"] == "Menge ändern (Arm-Modul)" and pos(modul)[arm]["menge"] == menge0)
        wieder(modul)
        check("Wiederholen: die Änderung gilt wieder", pos(modul)[arm]["menge"] == menge0 + 5)
        zurueck(modul)
        c.patch(f"/api/baugruppen/{modul}/positionen", json={"ref": arm, "menge": menge0 + 1})
        check("Eine neue Änderung löscht die Wiederholen-Liste", wieder(modul).status_code == 400)
        zurueck(modul)

        halter_ref = f"MODEL_ASSET/{m['Halter']}"
        c.patch(f"/api/baugruppen/{modul}/positionen", json={"ref": halter_ref, "material": "PETG", "farbe": "#112233", "notiz": "mit Stützen"})
        c.put(f"/api/baugruppen/{modul}/reihenfolge", json={"refs": [halter_ref, arm]})
        vorher = pos(modul)
        reihe0 = [p["ref"] for p in c.get(f"/api/baugruppen/{modul}").json()["positionen"]]
        c.delete(f"/api/baugruppen/{modul}/positionen", params={"ref": halter_ref})
        check("Position entfernt", halter_ref not in pos(modul))
        zurueck(modul)
        nachher = pos(modul)
        check("Rückgängig bringt die entfernte Position mit Menge, Material, Farbe, Notiz und Platz in der Reihenfolge zurück",
              halter_ref in nachher and [nachher[halter_ref][k] for k in ("menge", "material", "farbe", "notiz")] == [vorher[halter_ref][k] for k in ("menge", "material", "farbe", "notiz")]
              and [p["ref"] for p in c.get(f"/api/baugruppen/{modul}").json()["positionen"]] == reihe0)
        zurueck(modul); zurueck(modul)        # Reihenfolge und Material/Farbe/Notiz wieder weg

        name0 = c.get(f"/api/baugruppen/{modul}").json()["name"]
        c.patch(f"/api/baugruppen/{modul}", json={"name": "Neuer Name"})
        zurueck(modul)
        check("Rückgängig nimmt eine Umbenennung zurück", c.get(f"/api/baugruppen/{modul}").json()["name"] == name0)
        c.patch(f"/api/baugruppen/{modul}", json={"name": "Zwischen"})             # zwei neue Änderungen leeren die Wiederholen-Liste
        c.patch(f"/api/baugruppen/{modul}", json={"name": name0})

        schr0 = next(t for t in c.get("/api/kaufteile", params={"q": "m3x10"}).json() if t["id"] == "din912-m3x10")["hinweis"]
        c.patch("/api/kaufteile/din912-m3x10", json={"hinweis": "geändert"})
        zurueck('din912-m3x10')
        check("Rückgängig nimmt eine Änderung der Bezugsquelle zurück",
              next(t for t in c.get("/api/kaufteile", params={"q": "m3x10"}).json() if t["id"] == "din912-m3x10")["hinweis"] == schr0)
        c.patch("/api/kaufteile/din912-m3x10", json={"hinweis": "zwischen"})       # zwei neue Änderungen leeren die Wiederholen-Liste
        c.patch("/api/kaufteile/din912-m3x10", json={"hinweis": schr0})

        unter = c.post("/api/baugruppen", json={"name": "Unten", "modelle": [m["Einzelteil"]]}).json()["id"]
        oben = c.post("/api/baugruppen", json={"name": "Oben", "modelle": [m["Halter"]]}).json()["id"]
        c.post(f"/api/baugruppen/{oben}/positionen", json={"ref": f"ASSEMBLY/{unter}", "menge": 2})
        vor_mat = (pos(unter), pos(oben))
        c.post(f"/api/baugruppen/{oben}/material", json={"material": "ABS"})
        gesetzt = [p["material"] for p in pos(unter).values()] + [pos(oben)[halter_ref]["material"]]
        check("Material für alle offenen Teile setzt es über zwei Ebenen und steht als ein Schritt im Verlauf",
              gesetzt == ["ABS", "ABS"] and c.get(f"/api/baugruppen/{oben}").json()["verlauf"]["zurueck"] == "Material für alle offenen Teile setzen (Oben)")
        zurueck(oben)
        check("Ein Rückgängig nimmt das Material auf beiden Ebenen zurück", (pos(unter), pos(oben)) == vor_mat)
        wieder(oben)
        einzel = f"MODEL_ASSET/{m['Einzelteil']}"
        c.patch(f"/api/baugruppen/{unter}/positionen", json={"ref": einzel, "menge": 9})        # danach: die untere Baugruppe wird für sich geändert
        r = zurueck(oben)
        check("Konflikt: wurde eine Baugruppe danach woanders geändert, nimmt Rückgängig den Schritt nicht zurück, sondern sagt warum",
              r.status_code == 400 and "Unten" in r.json()["fehler"] and pos(unter)[einzel]["menge"] == 9 and pos(unter)[einzel]["material"] == "ABS")
        zurueck(unter)
        check("Nach dem Rückgängig dort geht es auch im anderen Kontext", zurueck(oben).status_code == 200 and (pos(unter), pos(oben)) == vor_mat)

        stand = (pos(modul), pos(bid))
        kontexte = [modul, bid, "din912-m3x10"]          # Bearbeitet wurden die beiden Baugruppen und ein Kaufteil, jedes mit eigener Liste
        n = 0

        def reihum(schritt):
            """Jeder Kontext, solange sein oberster Schritt gilt; ein Schritt, der auf einen Schritt anderswo wartet, kommt in der nächsten Runde."""
            zaehler, weiter = 0, True
            while weiter:
                weiter = False
                for k in kontexte:
                    if schritt(k).status_code == 200:
                        zaehler, weiter = zaehler + 1, True
            return zaehler
        n = reihum(zurueck)
        leer = (pos(modul), pos(bid))
        check("Alles zurücknehmen geht über alle Kontexte bis zum Anfang, dann kommt eine verständliche Meldung",
              all(zurueck(k).status_code == 400 for k in kontexte) and n >= 5 and leer != stand)
        reihum(wieder)
        check("Alles wiederholen führt genau zum Stand von vorher zurück", (pos(modul), pos(bid)) == stand)
        c.delete(f"/api/baugruppen/{oben}"); c.delete(f"/api/baugruppen/{unter}")      # Hilfs-Baugruppen dieses Abschnitts

        # -- Projekte: Klammer um einen Bau-Auftrag (KONZEPT §4.5a)
        pid = c.post("/api/projekte", json={"name": "Halloween Deko"}).json()["id"]
        check("Projekt anlegen: Kennung p_…, Status Entwurf, eigene Liste (nicht in der Baugruppenliste)",
              pid.startswith("p_") and c.get(f"/api/projekte/{pid}").json()["status"] == "Entwurf"
              and [x["name"] for x in c.get("/api/projekte").json()] == ["Halloween Deko"]
              and "Halloween Deko" not in [x["name"] for x in c.get("/api/baugruppen").json()])
        modul_s = c.get(f"/api/baugruppen/{modul}").json()["summen"]
        c.post(f"/api/projekte/{pid}/positionen", json={"ref": f"ASSEMBLY/{modul}", "menge": 2})
        c.post(f"/api/projekte/{pid}/positionen", json={"ref": f"MODEL_ASSET/{m['Einzelteil']}", "menge": 3})
        c.post(f"/api/projekte/{pid}/positionen", json={"ref": "PURCHASED_PART/din912-m3x10", "menge": 1})
        dp = c.get(f"/api/projekte/{pid}").json()
        einkauf_p = {e["name"]: e["bedarf"] for e in dp["summen"]["einkauf"]}
        einkauf_m = {e["name"]: e["bedarf"] for e in modul_s["einkauf"]}
        check("Projekt mit lose Teilen, Baugruppe und Kaufteil: Summen über beide Ebenen (2× Baugruppe + 3 lose; 2×4+1 Schrauben)",
              dp["art"] == "projekt" and len(dp["positionen"]) == 3 and dp["summen"]["druckteile"] == 2 * modul_s["druckteile"] + 3
              and einkauf_p["Zylinderkopfschraube M3×10"] == 2 * einkauf_m["Zylinderkopfschraube M3×10"] + 1)
        check("Ein Projekt steckt in nichts und enthält kein Projekt",
              c.post(f"/api/baugruppen/{bid}/positionen", json={"ref": f"PROJECT/{pid}"}).status_code == 400
              and c.post(f"/api/projekte/{pid}/positionen", json={"ref": f"PROJECT/{pid}"}).status_code == 400)
        check("Der Kern bleibt unberührt: das lose Modell zeigt das Projekt nicht als Baugruppe",
              c.get(f"/api/modelle/{m['Einzelteil']}").json()["baugruppen"] == [])
        wege = c.get("/api/verwendung", params={"ziel": f"MODEL_ASSET/{m['Halter']}"}).json()
        ueber_projekt = [w for w in wege if w["weg"][0]["name"] == "Halloween Deko"]
        check("Wo verbaut reicht bis zum Projekt: Halloween Deko › Arm-Modul, 2 × 2 = 4×",
              len(ueber_projekt) == 1 and [x["name"] for x in ueber_projekt[0]["weg"]] == ["Halloween Deko", "Arm-Modul"] and ueber_projekt[0]["gesamt"] == 4)
        pid2 = c.post("/api/projekte", json={"name": "Zweites Projekt"}).json()["id"]
        modul_vor = c.get(f"/api/baugruppen/{modul}").json()["verlauf"]["schritte"]
        c.patch(f"/api/baugruppen/{modul}/positionen", params={"im": pid}, json={"ref": arm, "menge": menge0 + 7})
        check("Eine Änderung an einer Baugruppe im Projekt-Kontext steht in der Liste des Projekts, nicht in der der Baugruppe oder eines anderen Projekts",
              c.get(f"/api/projekte/{pid}").json()["verlauf"]["zurueck"] == "Menge ändern (Arm-Modul)"
              and c.get(f"/api/baugruppen/{modul}").json()["verlauf"]["schritte"] == modul_vor
              and c.get(f"/api/projekte/{pid2}").json()["verlauf"]["schritte"] == 0)
        zurueck(pid)
        check("Rückgängig im Projekt nimmt die Änderung an der Baugruppe zurück", pos(modul)[arm]["menge"] == menge0 and zurueck(pid2).status_code == 400)
        c.delete(f"/api/projekte/{pid2}")
        c.patch(f"/api/projekte/{pid}", json={"status": "In Arbeit"})
        check("Projekt-Status ist frei wählbar; an einer Baugruppe gibt es keinen Status",
              c.get(f"/api/projekte/{pid}").json()["status"] == "In Arbeit"
              and c.patch(f"/api/baugruppen/{modul}", json={"status": "Fertig"}).status_code == 400)
        zurueck(pid)
        check("Rückgängig gilt auch für Projekte (Status zurück)", c.get(f"/api/projekte/{pid}").json()["status"] == "Entwurf")
        c.patch(f"/api/projekte/{pid}/positionen", json={"ref": f"MODEL_ASSET/{m['Einzelteil']}", "menge": 5})
        check("Position im Projekt ändern", {p["name"]: p["menge"] for p in c.get(f"/api/projekte/{pid}").json()["positionen"]}["Einzelteil"] == 5)
        zurueck(pid)
        c.delete(f"/api/projekte/{pid}/positionen", params={"ref": f"MODEL_ASSET/{m['Einzelteil']}"})
        zurueck(pid)
        check("Rückgängig bringt die Menge und eine entfernte Position im Projekt zurück",
              {p["name"]: p["menge"] for p in c.get(f"/api/projekte/{pid}").json()["positionen"]}["Einzelteil"] == 3)
        # -- Druckeinstellungen als Vorgabe an der Position
        einz = f"MODEL_ASSET/{m['Einzelteil']}"
        c.patch(f"/api/projekte/{pid}/positionen", json={"ref": einz, "infill": 40, "waende": "4", "schicht": "0,2"})
        pe = {p["name"]: p for p in c.get(f"/api/projekte/{pid}").json()["positionen"]}["Einzelteil"]
        check("Druckeinstellungen: Füllung, Wandlinien, Schichthöhe (auch mit Komma) werden als Zahlen gespeichert",
              (pe["infill"], pe["waende"], pe["schicht"]) == (40, 4, 0.2))
        check("Druckeinstellungen: Werte ausserhalb, keine Zahl oder an einem Kaufteil werden abgelehnt",
              all(c.patch(f"/api/projekte/{pid}/positionen", json={"ref": ref_, **w}).status_code == 400
                  for ref_, w in ((einz, {"infill": 101}), (einz, {"waende": 0}), (einz, {"schicht": "dick"}), (einz, {"schicht": 2}),
                                  ("PURCHASED_PART/din912-m3x10", {"infill": 20}))))
        check("Ungültiger Wert ändert nichts", {p["name"]: p for p in c.get(f"/api/projekte/{pid}").json()["positionen"]}["Einzelteil"]["infill"] == 40)
        check("Rückgängig nimmt alle drei Einstellungen in einem Schritt zurück und der Verlauf nennt sie",
              c.get(f"/api/projekte/{pid}").json()["verlauf"]["zurueck"] == "Füllung und Wandlinien und Schichthöhe ändern (Halloween Deko)"
              and zurueck(pid).status_code == 200
              and {p["name"]: p for p in c.get(f"/api/projekte/{pid}").json()["positionen"]}["Einzelteil"]["infill"] is None)
        wieder(pid)
        c.patch(f"/api/projekte/{pid}/positionen", json={"ref": einz, "infill": ""})
        check("Leeren nimmt die Vorgabe wieder weg", {p["name"]: p for p in c.get(f"/api/projekte/{pid}").json()["positionen"]}["Einzelteil"]["infill"] is None)
        c.patch(f"/api/projekte/{pid}/positionen", json={"ref": einz, "infill": 40})

        # -- Der ganze Baum in einer Antwort
        baum = c.get(f"/api/projekte/{pid}/baum").json()
        zweige = {e["name"]: e for e in baum["positionen"]}
        halter_im_modul = next(e for e in zweige["Arm-Modul"]["positionen"] if e["name"] == "Halter")
        check("Baum: Projekt, darunter Baugruppe mit ihren Positionen und lose Teile, mit Gesamtmenge ab der Wurzel (2 Module × 2 Halter = 4)",
              baum["art"] == "projekt" and set(zweige) == {"Arm-Modul", "Einzelteil", "Zylinderkopfschraube M3×10"}
              and zweige["Arm-Modul"]["art"] == "baugruppe" and halter_im_modul["menge"] == 2 and halter_im_modul["gesamt"] == 4
              and zweige["Einzelteil"]["gesamt"] == 3 and zweige["Einzelteil"]["infill"] == 40 and "positionen" not in zweige["Einzelteil"])
        check("Baum: auch für eine Baugruppe allein, und ein Baustein kennt seine Ebene darunter",
              [e["name"] for e in c.get(f"/api/baugruppen/{modul}/baum").json()["positionen"]].count("Halter") == 1
              and c.get(f"/api/baugruppen/{modul}/baum").json()["art"] == "baugruppe")

        # -- Flache Stückliste
        flach = c.get(f"/api/projekte/{pid}/stueckliste").json()
        dp = c.get(f"/api/projekte/{pid}").json()
        druck = {z["name"]: z for z in flach["druck"]}
        kauf = {k["name"]: k for k in flach["kauf"]}
        check("Flache Stückliste: jedes Druckteil einmal mit Gesamtmenge über die Ebenen (Halter 4, Einzelteil 3), Materialien mit Mengen",
              druck["Halter"]["menge"] == 4 and druck["Einzelteil"]["menge"] == 3
              and sum(x["menge"] for x in druck["Halter"]["materialien"]) == 4 and all(x["material"] for x in druck["Halter"]["materialien"]))
        check("Flache Stückliste: Kaufteile mit Gesamtmenge und Bezug (M3×10: 2×4 + 1 = 9)",
              kauf["Zylinderkopfschraube M3×10"]["menge"] == 9 and "link" in kauf["Zylinderkopfschraube M3×10"])
        check("Flache Stückliste: die Summen stimmen mit denen der Baugruppenansicht überein (Druckteile, Gewicht, Zeit)",
              flach["summen"]["druckteile"] == dp["summen"]["druckteile"] and flach["summen"]["gewicht_g"] == dp["summen"]["gewicht_g"]
              and flach["summen"]["zeit_s"] == dp["summen"]["zeit_s"])

        check("Export des Projekts: CSV, Markdown und PDF",
              all(c.get(f"/api/projekte/{pid}/export", params={"format": f}).status_code == 200 for f in ("csv", "md", "pdf"))
              and "Einzelteil" in c.get(f"/api/projekte/{pid}/export").text)
        c.delete(f"/api/projekte/{pid}")
        check("Projekt löschen: Modelle und Baugruppen bleiben",
              c.get("/api/projekte").json() == [] and "Arm-Modul" in [x["name"] for x in c.get("/api/baugruppen").json()]
              and len(c.get("/api/modelle").json()) == 4)

        # -- Lange Beschreibung liegt in vault_text/ und kommt beim Lesen ganz zurück
        lang = ("Bauanleitung: " + "Teil an Teil schrauben, dann prüfen. " * 60).strip()
        kurz = "Kurz."
        c.patch(f"/api/baugruppen/{bid}", json={"beschreibung": lang})
        z = c.app.state.zustand["bestand"]
        roh = z.db.get_node_raw(f"ASSEMBLY/{bid}")["beschreibung"]
        check("Lange Beschreibung: im Knoten nur der Verweis, der Text als Datei in vault_text/",
              roh.startswith("@vault_text/") and os.path.exists(z.pfad(*roh[len("@vault_text/"):].split("/"))) and len(roh) < 200)
        check("… Detail, Markdown und PDF bekommen den vollen Text",
              c.get(f"/api/baugruppen/{bid}").json()["beschreibung"] == lang
              and lang in c.get(f"/api/baugruppen/{bid}/export", params={"format": "md"}).text
              and c.get(f"/api/baugruppen/{bid}/export", params={"format": "pdf"}).status_code == 200)
        c.patch(f"/api/baugruppen/{bid}", json={"beschreibung": kurz})
        check("Kurze Beschreibung bleibt im Knoten",
              z.db.get_node_raw(f"ASSEMBLY/{bid}")["beschreibung"] == kurz and c.get(f"/api/baugruppen/{bid}").json()["beschreibung"] == kurz)

        c.delete(f"/api/baugruppen/{bid}")
        check("Baugruppe löschen: Modelle und Unterbaugruppe bleiben",
              len(c.get("/api/modelle").json()) == 4 and [b["name"] for b in c.get("/api/baugruppen").json()] == ["Arm-Modul"])

        sid = c.post("/api/sammlungen", json={"name": "Kiste", "modelle": [m["Einzelteil"], m["Halter"]]}).json()["id"]
        neu = c.post("/api/baugruppen", json={"aus_sammlung": sid}).json()["id"]
        check("Sammlung in Baugruppe umwandeln", [p["name"] for p in c.get(f"/api/baugruppen/{neu}").json()["positionen"]] == ["Einzelteil", "Halter"])

        # -- Entwurf: ein Etikett, das neue Baugruppen aus Ordnern nicht übernehmen
        r = c.post("/api/stapel", json={"aktion": "entwurf", "modelle": [m["Halter"], m["Top_Plate"]], "wert": True})
        check("Entwurf für mehrere auf einmal setzen", r.status_code == 200
              and all(c.get(f"/api/modelle/{x}").json()["entwurf"] for x in (m["Halter"], m["Top_Plate"])))
        neu2 = c.post("/api/baugruppen", json={"aus_ordner": f"{w}/Drohne V2"}).json()["id"]
        check("Baugruppe aus Ordner nimmt keine Entwürfe",
              [p["name"] for p in c.get(f"/api/baugruppen/{neu2}").json()["positionen"]] == ["Arm_x4"])
        d = c.get(f"/api/baugruppen/{neu}").json()
        check("Eine bestehende Stückliste behält den Entwurf, die Position sagt es",
              {p["name"]: p["entwurf"] for p in d["positionen"]} == {"Einzelteil": False, "Halter": True})
        c.patch(f"/api/modelle/{m['Arm_x4']}", json={"entwurf": True})
        r = c.post("/api/baugruppen", json={"aus_ordner": f"{w}/Drohne V2"})
        check("Nur Entwürfe im Ordner: abgelehnt mit Grund", r.status_code == 400 and "Entwürfe" in r.json().get("fehler", ""))
        c.patch(f"/api/modelle/{m['Arm_x4']}", json={"entwurf": False})
        check("Entwurf zurücknehmen", c.get(f"/api/modelle/{m['Arm_x4']}").json()["entwurf"] is False)
    muster.ende()
