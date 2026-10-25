"""Filamentlager (lager.py): Spulen anlegen (auch mehrere gleiche), ändern, archivieren; Eingaben werden geprüft; ein neuer Start liest sie wieder."""
import os
import tempfile

import muster
from muster import check
from fastapi.testclient import TestClient
from partatlas.main import erstelle_app

if __name__ == "__main__":
    muster.zeitgrenze(90)
    tmp = tempfile.mkdtemp()
    bestand = os.path.join(tmp, "bestand")
    with TestClient(erstelle_app(bestand, prozesse=1)) as c:
        check("Ein neuer Bestand hat keine Spulen", c.get("/api/spulen").json()["spulen"] == [])
        r = c.post("/api/spulen", json={"felder": {"material": "PETG", "hersteller": "Prusament", "farbname": "Galaxy Black", "farbe": "#1A1A1A",
                                                    "start_g": 1000, "preis": "24,90", "ort": "Regal 2"}})
        sid = r.json()["ids"][0]
        s = c.get("/api/spulen").json()["spulen"][0]
        check("Spule angelegt: Rest = voll, Durchmesser 1,75, Farbwert klein geschrieben, Preis mit Komma gelesen",
              s["id"] == sid and s["rest_g"] == 1000 and s["durchmesser"] == 1.75 and s["farbe"] == "#1a1a1a" and s["preis"] == 24.9)
        ids = c.post("/api/spulen", json={"felder": {"material": "PLA", "farbname": "Weiss"}, "anzahl": 3}).json()["ids"]
        check("Mehrere gleiche Spulen auf einmal, jede mit eigener Kennung", len(set(ids)) == 3 and len(c.get("/api/spulen").json()["spulen"]) == 4)
        c.patch(f"/api/spulen/{ids[0]}", json={"rest_g": 312.46})
        check("Rest ändern: auf 0,1 g gerundet, die anderen bleiben voll",
              {x["id"]: x["rest_g"] for x in c.get("/api/spulen").json()["spulen"]}[ids[0]] == 312.5
              and {x["id"]: x["rest_g"] for x in c.get("/api/spulen").json()["spulen"]}[ids[1]] == 1000)

        schlecht = [({"felder": {}}, "Material"), ({"felder": {"material": ""}}, "Material"), ({"felder": {"material": "PLA", "farbe": "rot"}}, "Farbwert"),
                    ({"felder": {"material": "PLA", "start_g": "abc"}}, "keine Zahl"), ({"felder": {"material": "PLA", "start_g": 500, "rest_g": 600}}, "grösser"),
                    ({"felder": {"material": "PLA", "bogus": 1}}, "gibt es an der Spule nicht"), ({"felder": {"material": "PLA"}, "anzahl": 99}, "zwischen 1 und 20")]
        ok = True
        for koerper, wort in schlecht:
            r = c.post("/api/spulen", json=koerper)
            ok = ok and r.status_code == 400 and wort in r.json().get("fehler", r.text)
        check("Falsche Eingaben werden mit Satz abgelehnt (Material fehlt, Farbwert, keine Zahl, Rest über voll, fremdes Feld, zu viele)", ok)
        r = c.patch(f"/api/spulen/{sid}", json={"rest_g": 2000})
        check("Ändern: Rest über der vollen Spule wird abgelehnt, die Spule bleibt wie sie war",
              r.status_code == 400 and next(x for x in c.get("/api/spulen").json()["spulen"] if x["id"] == sid)["rest_g"] == 1000)
        check("Eine Spule, die es nicht gibt, meldet sich in einem Satz", c.patch("/api/spulen/sp_99999", json={"rest_g": 1}).status_code == 400)

        neu = c.post(f"/api/spulen/{sid}/nachkaufen", json={"anzahl": 2, "felder": {"preis": "22,50", "ort": "Regal 3", "start_g": 750}}).json()["ids"]
        alle = {x["id"]: x for x in c.get("/api/spulen").json()["spulen"]}
        check("Nachkaufen: zwei neue, volle Spulen mit Material, Hersteller, Farbe der Vorlage und angepasstem Preis, Ort und Menge",
              len(neu) == 2 and all(alle[i]["material"] == "PETG" and alle[i]["hersteller"] == "Prusament" and alle[i]["farbe"] == "#1a1a1a"
                                    and alle[i]["rest_g"] == 750 == alle[i]["start_g"] and alle[i]["preis"] == 22.5 and alle[i]["ort"] == "Regal 3" for i in neu)
              and alle[sid]["ort"] == "Regal 2" and alle[sid]["preis"] == 24.9)
        check("Nachkaufen ohne Anpassung übernimmt Menge, Preis und Ort der Vorlage",
              (lambda i: (lambda a: a[i]["ort"] == "Regal 2" and a[i]["start_g"] == 1000 and a[i]["preis"] == 24.9)({x["id"]: x for x in c.get("/api/spulen").json()["spulen"]}))(
                  c.post(f"/api/spulen/{sid}/nachkaufen", json={"anzahl": 1}).json()["ids"][0]))
        check("Nachkaufen einer unbekannten Spule meldet sich in einem Satz", c.post("/api/spulen/sp_99999/nachkaufen", json={"anzahl": 1}).status_code == 400)
        vorher = len(c.get("/api/spulen").json()["spulen"])
        c.delete(f"/api/spulen/{sid}")
        check("Löschen: die Spule ist aus dem Lager weg", len(c.get("/api/spulen").json()["spulen"]) == vorher - 1
              and sid not in [x["id"] for x in c.get("/api/spulen").json()["spulen"]])
        c.post(f"/api/spulen/{sid}/zurueck")
        check("Rückgängig: dieselbe Spule ist mit allen Angaben wieder da",
              next(x for x in c.get("/api/spulen").json()["spulen"] if x["id"] == sid)["hersteller"] == "Prusament")
        check("Eine Spule, die es nie gab, lässt sich nicht zurückholen", c.post("/api/spulen/sp_99999/zurueck").status_code == 400)

        # -- Bild an der Spule
        import io
        from PIL import Image
        def png(farbe, gross=40):
            p = io.BytesIO(); Image.new("RGB", (gross, gross), farbe).save(p, "PNG"); return p.getvalue()
        c.post(f"/api/spulen/{sid}/bild", content=png("red"), headers={"content-type": "application/octet-stream"})
        r = c.get(f"/api/spulen/{sid}/bild")
        check("Bild an der Spule: wird abgelegt und ausgeliefert, die Spule trägt den Verweis",
              r.status_code == 200 and r.headers["content-type"].startswith("image/") and next(x for x in c.get("/api/spulen").json()["spulen"] if x["id"] == sid).get("bild"))
        r = c.post(f"/api/spulen/{sid}/bild", content=b"keinbild", headers={"content-type": "application/octet-stream"})
        check("Kein lesbares Bild: Satz als Antwort, das alte Bild bleibt", r.status_code == 400 and c.get(f"/api/spulen/{sid}/bild").status_code == 200)
        r = c.post(f"/api/spulen/{sid}/bild", content=b"0" * (5 * 1024 * 1024 + 1), headers={"content-type": "application/octet-stream"})
        check("Bild über 5 MB wird abgelehnt", r.status_code == 400 and "5 MB" in r.json()["fehler"])
        n2 = c.post(f"/api/spulen/{sid}/nachkaufen", json={"anzahl": 1}).json()["ids"][0]
        check("Nachkaufen übernimmt das Bild der Vorlage", c.get(f"/api/spulen/{n2}/bild").status_code == 200)
        c.delete(f"/api/spulen/{sid}/bild")
        check("Bild entfernen: die Spule hat keins mehr", c.get(f"/api/spulen/{sid}/bild").status_code == 404 or c.get(f"/api/spulen/{sid}/bild").status_code == 400)

        m = c.get("/api/spulen").json()["materialien"]
        check("Die Auswahl der Materialien kommt mit (Grundbestand)", "PLA" in m and "PETG" in m)

        # -- Reicht das Filament? (3MF mit zwei Platten: PETG schwarz 12,5 g, PLA weiss 3,25 g)
        samm = os.path.join(tmp, "3D")
        os.makedirs(samm)
        muster.dreimf(os.path.join(samm, "Paar.3mf"))
        c.post("/api/wurzeln", json={"pfad": samm})
        c.app.state.zustand["scanner"].warten(120)
        mid = next(x["id"] for x in c.get("/api/modelle").json() if x["name"] == "Paar")
        reicht = lambda: c.get(f"/api/modelle/{mid}").json()["reicht"]
        for x in c.get("/api/spulen").json()["spulen"]:
            c.delete(f"/api/spulen/{x['id']}")
        r = reicht()
        check("Ohne Spulen: unklar (keine passende Spule), beide Filamente genannt", r["status"] == "unklar" and len(r["filamente"]) == 2
              and all(f["grund"] == "Keine passende Spule" for f in r["filamente"]))
        petg = c.post("/api/spulen", json={"felder": {"material": "PETG", "farbe": "#101010", "farbname": "Schwarz", "start_g": 1000, "ort": "Regal 1"}}).json()["ids"][0]
        r = reicht()
        check("Eine PETG-Spule in fast gleichem Schwarz: das PETG reicht und nennt die Spule mit Ort; das PLA bleibt unklar, also Gesamtstatus unklar",
              {f["typ"]: f["status"] for f in r["filamente"]} == {"PETG": "reicht", "PLA": "unklar"} and r["status"] == "unklar"
              and next(f for f in r["filamente"] if f["typ"] == "PETG")["spulen"][0]["ort"] == "Regal 1")
        pla = c.post("/api/spulen", json={"felder": {"material": "PLA", "farbe": "#ffffff", "start_g": 100, "rest_g": 100}}).json()["ids"][0]
        check("Auch eine weisse PLA-Spule: alles reicht", reicht()["status"] == "reicht")
        c.patch(f"/api/spulen/{pla}", json={"rest_g": 2})
        zweite = c.post("/api/spulen", json={"felder": {"material": "PLA", "farbe": "#f5f5f5", "start_g": 100, "rest_g": 2}}).json()["ids"][0]
        r = reicht()
        pl = next(f for f in r["filamente"] if f["typ"] == "PLA")
        check("Zwei Spulen mit je 2 g für 3,25 g: reicht nur mit Spulenwechsel, beide genannt", pl["status"] == "wechsel" and len(pl["spulen"]) == 2 and r["status"] == "wechsel")
        c.patch(f"/api/spulen/{zweite}", json={"rest_g": 1})
        pl = next(f for f in reicht()["filamente"] if f["typ"] == "PLA")
        check("Zusammen nur 3 g: reicht nicht, es fehlen 0,25 g", pl["status"] == "reicht_nicht" and pl["fehlt_g"] == 0.25 and reicht()["status"] == "reicht_nicht")
        c.patch(f"/api/spulen/{pla}", json={"farbe": "#cc0000"})
        c.patch(f"/api/spulen/{zweite}", json={"farbe": "#cc0000"})
        check("Rote Spulen für weisses PLA: andere Farbe, also unklar", next(f for f in reicht()["filamente"] if f["typ"] == "PLA")["status"] == "unklar")
        c.patch(f"/api/spulen/{pla}", json={"farbe": "#ffffff", "material": "PETG"})
        check("Andere Materialart (PETG-Spule für PLA): unklar", next(f for f in reicht()["filamente"] if f["typ"] == "PLA")["status"] == "unklar")

        lager = c.app.state.zustand["katalog"].lager
        for x in c.get("/api/spulen").json()["spulen"]:
            c.delete(f"/api/spulen/{x['id']}")
        eine = c.post("/api/spulen", json={"felder": {"material": "PLA", "farbe": "#00aa00", "start_g": 1000}}).json()["ids"][0]
        frei = {eine: 1000.0}
        a = lager.reicht([{"typ": "PLA", "farbe": "#00aa00", "g": 600}], frei)["status"]
        b2 = lager.reicht([{"typ": "PLA", "farbe": "#00aa00", "g": 600}], frei)
        check("Warteschlange: dieselbe Spule zählt nicht doppelt — das erste Modell reicht, das zweite reicht nicht (es fehlen 200 g)",
              a == "reicht" and b2["status"] == "reicht_nicht" and b2["filamente"][0]["fehlt_g"] == 200)
        

    with TestClient(erstelle_app(bestand, prozesse=1)) as c2:
        check("Nach einem Neustart sind alle Spulen noch da", len(c2.get("/api/spulen").json()["spulen"]) == 1)
    muster.ende()
