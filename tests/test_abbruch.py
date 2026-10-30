"""Abschusstest 3 (OFFEN.md, 30.10.2026): harter Abbruch (kill -9) mitten in Schreibvorgängen.
Ein Arbeiter-Prozess ändert den Bestand in einer Schleife (Tag setzen, Modell löschen/zurückholen, Druck mit Abbuchung anlegen, Neu einlesen);
der Prüfer tötet ihn nach zufälliger Zeit mit SIGKILL, öffnet den Bestand neu und prüft: öffnet, jede Liste antwortet, nichts halb geschrieben
(Zähler am Modell = Drucke; Spule = voll minus Abbuchungen; Tag-Zählung = Wahrheit; keine Kante ins Leere). Viele Läufe.
Gehört zu „vor einer Fassung“, nicht in jeden Lauf. ABBRUCH_LAEUFE setzt die Zahl der Läufe (Vorgabe 25)."""
import os
import random
import signal
import subprocess
import sys
import tempfile
import time

import muster
from muster import check
from fastapi.testclient import TestClient
from partatlas.main import erstelle_app
from partatlas.drucke import ZAEHLT

NAMEN = ["Halter_Arm", "Halter_Kabel", "Deckel", "Bar_Hocker", "Miniatur_Figur", "Rohr_S235JR", "Gehaeuse_Netzteil", "Clip", "Welle", "Zahnrad"]
TAGS = ["alpha", "beta", "gamma", "delta"]


def arbeiter(wurzel, sid):
    """Läuft bis zum Abbruch. Meldet „bereit“, sobald der Bestand offen ist."""
    rnd = random.Random()
    with TestClient(erstelle_app(wurzel, prozesse=1)) as c:
        ids = [m["id"] for m in c.get("/api/modelle").json()]
        print("bereit", flush=True)
        while True:
            mid, was = rnd.choice(ids), rnd.randrange(5)
            if was == 0:
                c.post(f"/api/modelle/{mid}/tags", json={"tag": rnd.choice(TAGS)})
            elif was == 1:
                c.delete(f"/api/modelle/{mid}/tags/{rnd.choice(TAGS)}")
            elif was == 2:
                c.post(f"/api/modelle/{mid}/loeschen", json={})
                c.post(f"/api/modelle/{mid}/wiederherstellen", json={})
            elif was == 3:
                c.post("/api/drucke", json={"modelle": [mid], "felder": {"ergebnis": "gut", "abbuchung": {"spule": sid, "g": 1}}})
            else:
                c.post("/api/scan", json={})


def pruefen(wurzel, sid, lauf):
    try:
        c = TestClient(erstelle_app(wurzel, prozesse=1))
        c.__enter__()
    except Exception as e:
        check(f"Lauf {lauf}: Bestand öffnet nach dem Abbruch", False)
        print("   ", repr(e))
        return False
    try:
        z = c.app.state.zustand
        db, dr = z["katalog"].db, z["katalog"].drucke
        schlecht = [p for p in ("/api/modelle", "/api/tags", "/api/tags/verwaltung", "/api/zaehler", "/api/spulen", "/api/drucke", "/api/wurzeln")
                    if c.get(p).status_code >= 500]
        fehler = [f"Listen: {schlecht}"] if schlecht else []
        # Zähler am Modell = Drucke des Modells (das Anlegen und das Nachziehen sind eine Transaktion)
        for mid, m in db.list_nodes("MODEL_ASSET", readonly=True).items():
            echt = sum(1 for i in dr._ids_von(mid) if (db.get_node(f"PRINT_JOB/{i}", readonly=True) or {}).get("ergebnis") in ZAEHLT)
            if (m.get("drucke_n") or 0) != echt:
                fehler.append(f"drucke_n {mid}: {m.get('drucke_n')} statt {echt}")
        # Spule = voll minus alles, was an Drucken als abgebucht steht
        s = db.get_node(f"MATERIAL_SPOOL/{sid}", readonly=True)
        abgebucht = sum((d.get("abbuchung") or {}).get("g", 0) for d in db.list_nodes("PRINT_JOB", readonly=True).values())
        if s is None or abs(s["start_g"] - abgebucht - s["rest_g"]) > 0.01:
            fehler.append(f"Spule: rest {s and s['rest_g']}, abgebucht in Drucken {abgebucht}")
        # Tag-Zählung = Wahrheit
        lebend = {m["id"]: m for m in c.get("/api/modelle").json()}
        wahr = {}
        for mid in lebend:
            for t in c.get(f"/api/modelle/{mid}").json()["tags"]:
                wahr[t] = wahr.get(t, 0) + 1
        falsch = {t["name"]: (t["anzahl"], wahr.get(t["name"], 0)) for t in c.get("/api/tags").json() if t["anzahl"] != wahr.get(t["name"], 0)}
        if falsch:
            fehler.append(f"Tag-Zählung: {falsch}")
        # keine Kante ins Leere (ein Knoten im Papierkorb zählt als vorhanden)
        for art in ("HAS_TAG", "PRINTED_IN"):
            for kid, k in db.list_edges(art).items():
                for ende in ("source", "target"):
                    sammlung_, i = k[ende].split("/", 1)
                    if i not in db.list_nodes(sammlung_, include_deleted=True, readonly=True):
                        fehler.append(f"Kante {kid} ins Leere")
        check(f"Lauf {lauf}: Bestand ist nach dem Abbruch ganz und stimmig", not fehler)
        for f in fehler:
            print("   ", f)
        return not fehler
    finally:
        c.__exit__(None, None, None)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--arbeiter":
        arbeiter(sys.argv[2], sys.argv[3])
        sys.exit(0)
    muster.zeitgrenze(900)
    laeufe = int(os.environ.get("ABBRUCH_LAEUFE") or 25)
    tmp = tempfile.mkdtemp()
    sammlung = os.path.join(tmp, "3D-Druck")
    os.makedirs(sammlung)
    wurzel = os.path.join(tmp, "bestand")
    for i, n in enumerate(NAMEN):
        muster.stl_binaer(os.path.join(sammlung, n + ".stl"), 10 + i, 20, 30)
    with TestClient(erstelle_app(wurzel, prozesse=1)) as c:
        z = c.app.state.zustand
        c.post("/api/wurzeln", json={"pfad": sammlung})
        z["scanner"].warten(120)
        z["scanner"].worker.warten(120)
        sid = c.post("/api/spulen", json={"felder": {"material": "PLA", "farbname": "Rot", "start_g": 20000}}).json()["ids"][0]
    check("Ausgangslage: Bestand mit Spule vorbereitet", bool(sid))

    rnd, ok, gekillt = random.Random(int(os.environ.get("ABBRUCH_SAMEN") or 1)), 0, 0
    for lauf in range(1, laeufe + 1):
        p = subprocess.Popen([sys.executable, os.path.abspath(__file__), "--arbeiter", wurzel, sid], stdout=subprocess.PIPE, text=True,
                             stderr=subprocess.DEVNULL, cwd=os.path.dirname(os.path.abspath(__file__)))
        if p.stdout.readline().strip() != "bereit":
            check(f"Lauf {lauf}: Arbeiter startet", False)
            break
        time.sleep(rnd.uniform(0.05, 1.5))
        p.send_signal(signal.SIGKILL)
        gekillt += p.wait() == -signal.SIGKILL
        if not pruefen(wurzel, sid, lauf):
            break
    check("Alle Arbeiter wurden mit SIGKILL beendet (nicht von selbst)", gekillt == lauf)
    muster.ende()
