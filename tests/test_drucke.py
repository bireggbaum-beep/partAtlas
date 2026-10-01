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

    muster.ende()
