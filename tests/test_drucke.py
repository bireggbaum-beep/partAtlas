"""Drucke (KONZEPT §4.6): ein Druck an einem oder mehreren Modellen, Zähler und
„gedruckt“ abgeleitet, Referenzdruck, Fotos, der Haken, der Umzug alter Haken."""
import io
import os
import tempfile

import muster
from muster import check
from fastapi.testclient import TestClient
from PIL import Image
from partatlas.main import erstelle_app


def jpeg(farbe):
    p = io.BytesIO()
    Image.new("RGB", (300, 200), farbe).save(p, "JPEG")
    return p.getvalue()


if __name__ == "__main__":
    tmp = tempfile.mkdtemp()
    samm = os.path.join(tmp, "3D")
    os.makedirs(samm)
    for i, n in enumerate(("Halter", "Clip", "Deckel")):
        muster.stl_binaer(os.path.join(samm, f"{n}.stl"), 10 + i * 3, 8, 9)

    with TestClient(erstelle_app(os.path.join(tmp, "bestand"), prozesse=2)) as c:
        c.post("/api/wurzeln", json={"pfad": samm})
        c.app.state.zustand["scanner"].warten(120)
        m = {x["name"]: x["id"] for x in c.get("/api/modelle").json()}
        kachel = lambda n: next(x for x in c.get("/api/modelle").json() if x["id"] == m[n])
        H, C, D = m["Halter"], m["Clip"], m["Deckel"]

        check("Neues Modell: noch nicht gedruckt, Zähler 0, keine Drucke",
              not kachel("Halter")["gedruckt"] and kachel("Halter")["drucke_n"] == 0
              and c.get(f"/api/modelle/{H}").json()["drucke"] == [])

        r = c.post("/api/drucke", json={"modelle": [H], "felder": {"gewicht_g": 12.5, "dauer_s": 5400, "ergebnis": "gut",
                                                                  "filament": [{"typ": "PLA", "farbe": "#ff0000", "g": 12.5}]}})
        d1 = r.json()["id"]
        check("Ein Druck am Modell: gedruckt, Zähler 1, Felder da, Datum heute als Vorgabe",
              r.status_code == 200 and kachel("Halter")["gedruckt"] and kachel("Halter")["drucke_n"] == 1
              and c.get(f"/api/modelle/{H}").json()["drucke"][0]["gewicht_g"] == 12.5
              and len(c.get(f"/api/modelle/{H}").json()["drucke"][0]["datum"]) == 10)

        d2 = c.post("/api/drucke", json={"modelle": [H, C, D], "felder": {"gewicht_g": 45, "dauer_s": 7800}}).json()["id"]
        check("Eine Platte mit drei Modellen: der Zähler jedes der drei steigt, die anderen stehen als „zusammen mit“",
              [kachel(n)["drucke_n"] for n in ("Halter", "Clip", "Deckel")] == [2, 1, 1]
              and {z["name"] for z in next(x for x in c.get(f"/api/modelle/{C}").json()["drucke"])["zusammen_mit"]} == {"Halter", "Deckel"})

        c.post("/api/drucke", json={"modelle": [D], "felder": {"ergebnis": "abgebrochen"}})
        check("Abgebrochen zählt nicht, und allein macht es das Modell nicht „gedruckt“ ",
              kachel("Deckel")["drucke_n"] == 1)
        c.post("/api/drucke", json={"modelle": [m["Deckel"]], "felder": {"ergebnis": "fehler"}})
        check("Mit Fehlern zählt (es hat stattgefunden)", kachel("Deckel")["drucke_n"] == 2)

        # -- Referenz
        c.post(f"/api/drucke/{d1}/referenz", json={"modell": H})
        k = kachel("Halter")
        check("Referenzdruck: die Kachel zeigt sein Gewicht, mit Herkunft; der Referenzdruck steht vorn",
              k["gewicht_g"] == 12.5 and k["gewicht_herkunft"] == "druck"
              and c.get(f"/api/modelle/{H}").json()["drucke"][0]["id"] == d1
              and c.get(f"/api/modelle/{H}").json()["drucke"][0]["referenz"])
        c.post(f"/api/drucke/{d2}/referenz", json={"modell": H})
        check("Höchstens eine Referenz je Modell: die zweite löst die erste ab",
              [x["id"] for x in c.get(f"/api/modelle/{H}").json()["drucke"] if x["referenz"]] == [d2]
              and kachel("Halter")["gewicht_g"] == 45)
        check("Referenz nur an einem Modell des Drucks",
              c.post(f"/api/drucke/{d1}/referenz", json={"modell": C}).status_code >= 400)
        c.post(f"/api/drucke/{d2}/referenz", json={"modell": H, "an": False})
        check("Referenz zurücknehmen: die Kachel fällt auf den Dateiwert zurück",
              kachel("Halter")["gewicht_herkunft"] != "druck")

        # -- Eingaben
        for name, felder in (("Ergebnis", {"ergebnis": "super"}), ("Gewicht", {"gewicht_g": "viel"}),
                             ("Datum", {"datum": "gestern"}), ("Farbe", {"filament": [{"typ": "PLA", "farbe": "rot"}]}),
                             ("unbekanntes Feld", {"foo": 1})):
            check(f"Ungültig abgelehnt: {name}",
                  c.post("/api/drucke", json={"modelle": [H], "felder": felder}).status_code >= 400)
        check("Ohne Modell oder mit unbekanntem Modell abgelehnt",
              c.post("/api/drucke", json={"modelle": []}).status_code >= 400
              and c.post("/api/drucke", json={"modelle": ["m_gibtsnicht"]}).status_code >= 400)
        c.patch(f"/api/drucke/{d1}", json={"notiz": "Fuss 0,1 mm langsamer", "ergebnis": "fehler"})
        e = next(x for x in c.get(f"/api/modelle/{H}").json()["drucke"] if x["id"] == d1)
        check("Ändern: Notiz und Ergebnis, der Zähler folgt (Fehler zählt weiter, gedruckt bleibt durch den anderen Druck)",
              e["notiz"] == "Fuss 0,1 mm langsamer" and e["ergebnis"] == "fehler" and kachel("Halter")["drucke_n"] == 2)

        # -- Fotos
        k1 = c.post(f"/api/drucke/{d1}/bilder", content=jpeg((200, 30, 30))).json()["k"]
        check("Foto am Druck: als PNG abrufbar, in der Liste, derselbe Inhalt nicht doppelt",
              c.get(f"/api/drucke/{d1}/bilder/{k1}").status_code == 200
              and c.post(f"/api/drucke/{d1}/bilder", content=jpeg((200, 30, 30))).json()["k"] == k1
              and len(next(x for x in c.get(f"/api/modelle/{H}").json()["drucke"] if x["id"] == d1)["bilder"]) == 1)
        check("Kein Bild: abgelehnt", c.post(f"/api/drucke/{d1}/bilder", content=b"kein bild").status_code >= 400)
        c.delete(f"/api/drucke/{d1}/bilder/{k1}")
        check("Foto entfernen", c.get(f"/api/drucke/{d1}/bilder/{k1}").status_code == 404)

        # -- Löschen
        c.delete(f"/api/drucke/{d2}")
        check("Druck löschen: alle drei Modelle zählen neu",
              [kachel(n)["drucke_n"] for n in ("Halter", "Clip", "Deckel")] == [1, 0, 1] and not kachel("Clip")["gedruckt"])

        # -- Der Haken „gedruckt“
        c.patch(f"/api/modelle/{C}", json={"gedruckt": True})
        dr = c.get(f"/api/modelle/{C}").json()["drucke"]
        check("Haken setzen legt einen leeren Druck an", kachel("Clip")["gedruckt"] and len(dr) == 1 and dr[0]["leer"])
        c.patch(f"/api/modelle/{C}", json={"gedruckt": True})
        check("Haken nochmal setzen: kein zweiter Druck", len(c.get(f"/api/modelle/{C}").json()["drucke"]) == 1)
        c.patch(f"/api/modelle/{C}", json={"gedruckt": False})
        check("Haken zurücknehmen entfernt den leeren Druck", not kachel("Clip")["gedruckt"] and kachel("Clip")["drucke_n"] == 0)
        r = c.patch(f"/api/modelle/{H}", json={"gedruckt": False})
        check("Haken zurücknehmen bei einem Druck mit Angaben: abgelehnt, nichts verloren",
              r.status_code >= 400 and kachel("Halter")["drucke_n"] == 1)
        r = c.post("/api/stapel", json={"aktion": "gedruckt", "modelle": [C, D], "wert": True}).json()
        check("Stapel: „gedruckt“ legt nur dort einen Druck an, wo noch keiner zählt",
              kachel("Clip")["drucke_n"] == 1 and kachel("Deckel")["drucke_n"] == 2)

        # -- Suche und Umzug alter Haken
        check("Suche gedruckt:ja findet über die Drucke",
              {x["name"] for x in c.get("/api/modelle", params={"suche": "gedruckt:ja"}).json()} >= {"Halter", "Clip"})
        k_ = c.app.state.zustand["katalog"]
        k_.db.update_node("MODEL_ASSET", D, {"gedruckt": True, "drucke_n": None})
        for did in k_.drucke._ids_von(D):
            k_.db.soft_delete("PRINT_JOB", did)
        k_.drucke._alte_haken_umziehen()
        check("Umzug: ein alter Haken wird zu einem leeren Druck ohne Datum, Zähler stimmt",
              kachel("Deckel")["drucke_n"] == 1 and c.get(f"/api/modelle/{D}").json()["drucke"][0]["datum"] is None)

        # -- Papierkorb
        c.post(f"/api/modelle/{H}/loeschen", json={})
        c.post(f"/api/modelle/{H}/wiederherstellen")
        check("Modell in den Papierkorb und zurück: die Drucke sind noch da",
              len(c.get(f"/api/modelle/{H}").json()["drucke"]) == 1)

        # -- Stufe b: G-Code oder Projekt am Druck (KONZEPT §4.6)
        gcode = lambda waende, name="Profil A": (f"; generated by OrcaSlicer 2.1.1\n; model printing time: 2h 0m 0s\n"
                                                 f"; total filament weight [g] : 21.5\nG28\n; CONFIG_BLOCK_START\n; layer_height = 0.2\n"
                                                 f"; wall_loops = {waende}\n; nozzle_temperature = 240\n; print_settings_id = {name}\n"
                                                 f"; CONFIG_BLOCK_END\n").encode()
        k_ = c.app.state.zustand["katalog"]
        v1 = c.post("/api/drucke", json={"modelle": [C], "felder": {"ergebnis": "fehler"}}).json()["id"]
        r = c.post(f"/api/drucke/{v1}/datei", params={"name": "Clip_v1.gcode"}, content=gcode(2)).json()
        gc = lambda n: next(x for x in c.get("/api/modelle").json() if x["name"] == n)["gcode"]
        suche_gcode = lambda w: sorted(x["name"] for x in c.get("/api/modelle", params={"q": f"gcode:{w}"}).json())
        check("Kachel: das Modell mit G-Code am Druck trägt „druck“, die anderen nichts; die Suche gcode:ja findet genau das eine",
              gc("Clip") == "druck" and gc("Halter") is None and gc("Deckel") is None and suche_gcode("ja") == ["Clip"] and "Clip" not in suche_gcode("nein"))
        d1 = next(x for x in c.get(f"/api/modelle/{C}").json()["drucke"] if x["id"] == v1)
        check("G-Code am Druck: Gewicht und Dauer aus dem Kopf füllen leere Felder, Einstellungen als Profil",
              d1["gewicht_g"] == 21.5 and d1["dauer_s"] == 7200 and d1["datei"]["name"] == "Clip_v1.gcode" and r["werte"] == 4
              and d1["datei"]["slicer"].startswith("OrcaSlicer"))
        g = k_.db.get_node(f"GCODE_ARTIFACT/{r['gcode']}")
        check("Die Datei liegt unverändert im Vault, Name = Titel + Hash", g["datei"].startswith("vault/gcode/Clip_v1__")
              and open(k_.b.pfad(*g["datei"].split("/")), "rb").read() == gcode(2))
        quelle = k_.db.get_node(f"PART_GEOMETRY/{c.get(f'/api/modelle/{C}').json()['hash']}").get("quelle_vault")
        check("Die Modelldatei kommt als Quelle mit in den Vault (SLICED_FROM)", quelle and os.path.exists(k_.b.pfad(*quelle.split("/")))
              and k_.db.get_connected(f"GCODE_ARTIFACT/{r['gcode']}", rel_type="SLICED_FROM"))
        v2 = c.post("/api/drucke", json={"modelle": [C], "felder": {"ergebnis": "gut", "gewicht_g": 20}}).json()["id"]
        c.post(f"/api/drucke/{v2}/datei", params={"name": "Clip_v2.gcode"}, content=gcode(3, "Kopie von Profil A"))
        v3 = c.post("/api/drucke", json={"modelle": [C], "felder": {}}).json()["id"]
        r3 = c.post(f"/api/drucke/{v3}/datei", params={"name": "nochmal.gcode"}, content=gcode(3, "Anders benannt")).json()
        check("Gleiche Einstellungen (anderer Profilname): derselbe Profil-Knoten, gezählt über den Graphen",
              r3["gleiche_einstellungen"] == 2 and r3["profil"] != r["profil"])
        d2 = next(x for x in c.get(f"/api/modelle/{C}").json()["drucke"] if x["id"] == v2)
        check("Von Hand eingetragenes Gewicht bleibt", d2["gewicht_g"] == 20)
        vg = c.get("/api/drucke/vergleich", params={"a": v1, "b": v2}).json()
        check("Vergleich: genau die Wände unterscheiden sich, in Worten benannt",
              [(x["schluessel"], x["a"], x["b"], x["name"]) for x in vg["unterschiede"]] == [("wall_loops", "2", "3", "Qualität › Wände")])
        check("Vergleich gleicher Einstellungen: gleich", c.get("/api/drucke/vergleich", params={"a": v2, "b": v3}).json()["gleich"])
        e = c.get(f"/api/drucke/{v1}/einstellungen").json()
        check("Einstellungen des Drucks: das Wichtigste und alle Werte", len(e["alle"]) == 4 and "Qualität" in [x["gruppe"] for x in e["wichtig"]])
        check("Herunterladen liefert die Datei", c.get(f"/api/drucke/{v1}/datei").content == gcode(2))
        check("Nur G-Code oder 3MF", c.post(f"/api/drucke/{v1}/datei", params={"name": "x.stl"}, content=b"solid").status_code == 400)
        gcn = lambda: k_.db.get_node(f"MODEL_ASSET/{D}", readonly=True).get("gcode_n")
        vorher = gcn()
        vd = c.post("/api/drucke", json={"modelle": [D], "felder": {}}).json()["id"]
        c.post(f"/api/drucke/{vd}/datei", params={"name": "Deckel2.gcode"}, content=gcode(2))
        check("Ein weiterer Druck mit G-Code am selben Modell zählt mit; das Zeichen bleibt „druck“ und die Suche findet das Modell",
              gcn() == vorher + 1 and gc("Deckel") == "druck" and "Deckel" in suche_gcode("ja"))
        c.delete(f"/api/drucke/{vd}/datei")
        check("G-Code gelöst: der Zähler geht zurück (das Zeichen hängt an den übrigen Drucken des Modells)", gcn() == vorher and (gc("Deckel") == "druck") == bool(vorher))
        c.delete(f"/api/drucke/{v1}/datei")
        check("Lösen: der Druck hat keine Datei mehr, die Datei bleibt im Vault",
              next(x for x in c.get(f"/api/modelle/{C}").json()["drucke"] if x["id"] == v1)["datei"] is None
              and os.path.exists(k_.b.pfad(*g["datei"].split("/"))))

    muster.ende()
