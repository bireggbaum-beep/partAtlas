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
        check("Spule angelegt: Rest = voll, Durchmesser 1,75, Farbwert klein geschrieben, Preis mit Komma gelesen, nicht archiviert",
              s["id"] == sid and s["rest_g"] == 1000 and s["durchmesser"] == 1.75 and s["farbe"] == "#1a1a1a" and s["preis"] == 24.9 and not s["archiviert"])
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
        c.patch(f"/api/spulen/{sid}", json={"archiviert": True})
        liste = c.get("/api/spulen").json()["spulen"]
        check("Archivierte Spule bleibt in der Liste, steht aber hinten", liste[-1]["id"] == sid and liste[-1]["archiviert"] is True)
        c.patch(f"/api/spulen/{sid}", json={"archiviert": False})
        check("Wieder aktiviert", not next(x for x in c.get("/api/spulen").json()["spulen"] if x["id"] == sid)["archiviert"])
        m = c.get("/api/spulen").json()["materialien"]
        check("Die Auswahl der Materialien kommt mit (Grundbestand)", "PLA" in m and "PETG" in m)

    with TestClient(erstelle_app(bestand, prozesse=1)) as c2:
        check("Nach einem Neustart sind alle Spulen noch da", len(c2.get("/api/spulen").json()["spulen"]) == 7)
    muster.ende()
