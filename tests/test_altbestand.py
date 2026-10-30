"""Abschusstest 1 (OFFEN.md, 30.10.2026): ein Bestand mit Papierkorb, Tags, Drucken, Lager und Daten im alten Format
(Kanten ohne `auto`, Modelle ohne `gcode_n`), dazu fehlende und umbenannte Dateien — darauf jeder Start, jede Liste, die Zähler.
Anlass: 1.0.6 öffnete den Bestand des Testers nicht; das zeigte sich nur an einem echten Bestand, nie an frischen Testbeständen.
Gehört zu „vor einer Fassung“, nicht in jeden Lauf."""
import os
import tempfile

import muster
from muster import check
from fastapi.testclient import TestClient
from partatlas.main import erstelle_app

LISTEN = ["/api/modelle", "/api/tags", "/api/tags/verwaltung", "/api/zaehler", "/api/wurzeln", "/api/ordner", "/api/sammlungen",
          "/api/spulen", "/api/drucke", "/api/materialien", "/api/fehlende", "/api/baugruppen", "/api/eigene", "/api/warteschlange",
          "/api/einstellungen", "/api/sicherungen", "/api/aufraeumen", "/api/varianten", "/api/stand", "/api/neuigkeiten"]


def warten(z):
    z["scanner"].warten(120)
    z["scanner"].worker.warten(120)


def alle_listen(c):
    """Jede Liste muss antworten; Rückgabe: die Listen, die es nicht taten (GET ohne 404/405: den Weg gibt es vielleicht nicht)."""
    return [(p, r.status_code) for p in LISTEN for r in [c.get(p)] if r.status_code >= 500]


def oeffnen(wurzel):
    return TestClient(erstelle_app(wurzel, prozesse=2))


if __name__ == "__main__":
    tmp = tempfile.mkdtemp()
    sammlung = os.path.join(tmp, "3D-Druck")
    os.makedirs(sammlung)
    wurzel = os.path.join(tmp, "bestand")
    namen = ["Halter_Arm_gross", "Halter_Kabel", "Deckel", "Bar_Hocker", "Miniatur_Figur", "Rohr_S235JR", "Gehaeuse_Netzteil", "Clip"]
    for i, n in enumerate(namen):
        muster.stl_binaer(os.path.join(sammlung, n + ".stl"), 10 + i, 20, 30)

    with oeffnen(wurzel) as c:
        z = c.app.state.zustand
        c.post("/api/wurzeln", json={"pfad": sammlung})
        warten(z)
        ids = {m["name"]: m["id"] for m in c.get("/api/modelle").json()}
        check("Ausgangslage: alle Modelle eingelesen", len(ids) == len(namen))
        for n, t in [("Bar_Hocker", "bar"), ("Miniatur_Figur", "miniatur"), ("Rohr_S235JR", "s235jr"), ("Halter_Kabel", "werkbank")]:
            c.post(f"/api/modelle/{ids[n]}/tags", json={"tag": t})
        for n in ("Halter_Arm_gross", "Deckel", "Bar_Hocker"):
            c.post("/api/drucke", json={"modelle": [ids[n]], "felder": {"ergebnis": "gut", "gewicht_g": 10}})
        c.post("/api/spulen", json={"material": "PLA", "hersteller": "X", "farbname": "Rot", "farbwert": "#cc0000", "gewicht_start": 1000, "gewicht_rest": 800})
        # Papierkorb: zwei Modelle mit Tags und Drucken, eines davon mit Tag "bar"
        for n in ("Bar_Hocker", "Clip"):
            c.post(f"/api/modelle/{ids[n]}/loeschen", json={})
        sichtbar_vorher = {m["id"] for m in c.get("/api/modelle").json()}
        check("Ausgangslage: gelöschte Modelle sind nicht in der Liste", ids["Bar_Hocker"] not in sichtbar_vorher and ids["Clip"] not in sichtbar_vorher)

        # -- Alter Stand herstellen: Kanten ohne `auto`, Modelle ohne `gcode_n`
        db = z["katalog"].db
        with db.transaction():
            for kid, k in db.list_edges("HAS_TAG").items():
                meta = {a: v for a, v in k.items() if a not in ("source", "target", "auto", "type", "rel_type", "id")}
                lebt = db.get_node(k["source"], readonly=True) is not None
                if lebt:
                    db.delete_edge(kid)
                    db.create_edge(k["source"], k["target"], "HAS_TAG", meta=meta or None)
            for mid, m in db.list_nodes("MODEL_ASSET", readonly=True).items():
                if "gcode_n" in m:
                    db.update_node("MODEL_ASSET", mid, {"gcode_n": None})   # update mischt ein; None gilt wie „fehlt“ (m.get(...) is None)

    # Dateien: eine fehlt, eine umbenannt
    os.remove(os.path.join(sammlung, "Deckel.stl"))
    os.rename(os.path.join(sammlung, "Clip.stl"), os.path.join(sammlung, "Clip_neu.stl"))

    stand = None
    for lauf in (1, 2, 3):
        try:
            c = oeffnen(wurzel)
            c.__enter__()
        except Exception as e:
            check(f"Lauf {lauf}: Bestand öffnet", False)
            print("   ", repr(e))
            break
        try:
            check(f"Lauf {lauf}: Bestand öffnet", True)
            z = c.app.state.zustand
            if lauf == 1:
                warten(z)
            fehl = alle_listen(c)
            check(f"Lauf {lauf}: jede Liste antwortet ohne Serverfehler", not fehl)
            if fehl:
                print("   ", fehl)
            tags = {t["name"]: t for t in c.get("/api/tags").json()}
            lebend = {m["id"] for m in c.get("/api/modelle").json()}
            # Zähler gegen die Wahrheit: kein Tag zählt Modelle im Papierkorb mit
            wahr = {}
            for mid in lebend:
                for t in c.get(f"/api/modelle/{mid}").json()["tags"]:
                    wahr[t] = wahr.get(t, 0) + 1
            falsch = {n: (t["anzahl"], wahr.get(n, 0)) for n, t in tags.items() if t["anzahl"] != wahr.get(n, 0)}
            check(f"Lauf {lauf}: Seitenleiste zählt Tags nur an lebenden Modellen", not falsch)
            if falsch:
                print("   Tag: (gezählt, wahr)", falsch)
            check(f"Lauf {lauf}: Tag von Hand gesetzt zählt als eigen", tags.get("werkbank", {}).get("eigen") == 1)
            check(f"Lauf {lauf}: Tag nur am gelöschten Modell hat keine eigenen",
                  all(t["eigen"] <= t["anzahl"] for t in tags.values()))
            # Papierkorb bleibt, Wiederherstellen geht
            if lauf == 1:
                stand = sorted(lebend)
            check(f"Lauf {lauf}: die Liste der lebenden Modelle ändert sich zwischen Starts nicht", stand == sorted(lebend))
            zl = c.get("/api/zaehler").json()
            check(f"Lauf {lauf}: /api/zaehler ist lesbar", isinstance(zl, dict))
        finally:
            c.__exit__(None, None, None)

    # Wiederherstellen aus dem Papierkorb nach dem Umzug
    with oeffnen(wurzel) as c:
        r = c.post(f"/api/modelle/{ids['Bar_Hocker']}/wiederherstellen", json={})
        check("Wiederherstellen aus dem Papierkorb nach den Umzügen geht", r.status_code < 400)
        tags = {t["name"]: t for t in c.get("/api/tags").json()}
        check("… und der Tag des Modells zählt wieder mit", tags.get("bar", {}).get("anzahl") == 1)
        check("… die Liste antwortet weiter", not alle_listen(c))
    muster.ende()
