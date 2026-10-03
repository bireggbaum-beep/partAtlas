"""
Messung: Kaufteile, Einkäufe und Händler als eigene Knoten (Entwurf, 03.10.2026) — was kostet das an Leistung?

    python kaufteile_mess.py <klein|mittel|gross> [wurzel]

Gemessen wird mit den echten partAtlas-Klassen (Bestand, Katalog, Baugruppen) und flatgraph aus dem Pin. Eingefügt wird ZUSÄTZLICH zu
den 199 Normteilen; Einkäufe sind Knoten `EINKAUF` mit Kanten zur Ware (`EINKAUF_VON`) und zum Händler (`BEI`). Das ist der Entwurf, nicht
gebaut: die Zahlen gelten für diese Form der Daten.

Die Mengen sind eine Annahme (klein = ein Bastler, gross = ein Kleinbetrieb), keine Messung eines echten Bestands.
"""
import json
import os
import random
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from partatlas.baugruppen import Baugruppen, KAUFTEIL, BAUGRUPPE
from partatlas.bestand import Bestand
from partatlas.katalog import Katalog

SAMEN = 20261003
STUFEN = {
    #          Kaufteile  Einkäufe  Händler  Baugruppen × Positionen
    "null":   (0,         0,        1,       1,  5),       # nur die 199 Normteile: der Vergleich
    "klein":  (300,       1_000,    10,      10, 40),
    "mittel": (1_500,     8_000,    30,      30, 80),
    "gross":  (5_000,     30_000,   60,      60, 150),
}
EINKAUF, HAENDLER = "EINKAUF", "HAENDLER"
EINKAUF_VON, BEI = "EINKAUF_VON", "BEI"


def rss_mb():
    with open("/proc/self/status") as f:
        for z in f:
            if z.startswith("VmRSS"):
                return int(z.split()[1]) / 1024


def median_ms(f, n=15):
    zeiten = []
    for _ in range(n):
        t = time.perf_counter()
        f()
        zeiten.append((time.perf_counter() - t) * 1000)
    return statistics.median(zeiten)


def bauen(wurzel, stufe):
    kt, ek, hd, bg, pos = STUFEN[stufe]
    rnd = random.Random(SAMEN)
    b = Bestand(wurzel)
    k = Katalog(b)
    B = Baugruppen(k)                        # legt die 199 Normteile an
    db = b.db
    t0 = time.perf_counter()
    with db.transaction():
        for i in range(hd):
            db.create_node(HAENDLER, f"h{i:03d}", {"name": f"Händler {i}", "url": f"https://haendler{i}.example"})
        teile = []
        for i in range(kt):
            kid = f"eigen-{i:05d}"
            db.create_node(KAUFTEIL, kid, {
                "name": f"Teil {i} {rnd.choice(['Schraube', 'Magnet', 'Lager', 'Sensor', 'Kabel', 'Netzteil'])} {rnd.randint(2, 99)}",
                "kategorie": rnd.choice(["Schrauben", "Magnete", "Lager", "Elektronik", "Peltier", "Eigene"]), "einheit": "Stück",
                "hersteller": f"Hersteller {rnd.randint(1, 40)}", "artikelnr": f"A-{rnd.randint(10000, 99999)}",
                "notiz": "x" * rnd.randint(0, 200), "standard": False})
            teile.append(kid)
        for i in range(ek):
            eid = f"ek-{i:06d}"
            kid = rnd.choice(teile)
            db.create_node(EINKAUF, eid, {"datum": f"2025-{rnd.randint(1, 12):02d}-{rnd.randint(1, 28):02d}",
                                          "menge": rnd.randint(1, 500), "preis": round(rnd.uniform(0.5, 80), 2), "beleg": "https://x.example/b"})
            db.create_edge(f"{EINKAUF}/{eid}", f"{KAUFTEIL}/{kid}", EINKAUF_VON)
            db.create_edge(f"{EINKAUF}/{eid}", f"{HAENDLER}/h{rnd.randrange(hd):03d}", BEI)
    aufbau = time.perf_counter() - t0
    alle = list(db.list_nodes(KAUFTEIL, readonly=True))
    bids = []
    with db.transaction():
        for i in range(bg):
            bids.append(B.anlegen(f"Baugruppe {i}", [(f"{KAUFTEIL}/{kid}", rnd.randint(1, 8)) for kid in rnd.sample(alle, pos)]))
    b.schliessen()
    return aufbau, bids


def abfragen(wurzel, stufe):
    kt, ek, hd, bg, pos = STUFEN[stufe]
    # Öffnen: Median aus fünf Läufen (öffnen, schliessen); der erste Lauf wärmt die Dateien an, zählt aber mit.
    zeiten = []
    for _ in range(5):
        t0 = time.perf_counter()
        b = Bestand(wurzel)
        k = Katalog(b)
        B = Baugruppen(k)
        zeiten.append((time.perf_counter() - t0) * 1000)
        if len(zeiten) == 1:
            ram = rss_mb()                    # gleich nach dem ersten Öffnen: spätere Runden würden Speicherreste mitzählen
        if len(zeiten) < 5:
            b.schliessen()
    oeffnen = statistics.median(zeiten)
    db = b.db
    bid = B.liste()[0]["id"]
    alle = list(db.list_nodes(KAUFTEIL, readonly=True))
    teil = next((t for t in alle if t.startswith("eigen-")), alle[0])
    ergebnis = {"öffnen_warm_ms": round(oeffnen, 1), "öffnen_min_max_ms": f"{min(zeiten):.0f}–{max(zeiten):.0f}", "ram_mb": round(ram, 1)}

    ergebnis["Kaufteile-Liste, alle, sortiert"] = median_ms(lambda: B.kaufteile())
    ergebnis["Kaufteile suchen (2 Wörter)"] = median_ms(lambda: B.kaufteile("schraube 4"))
    ergebnis["Kaufteile einer Kategorie"] = median_ms(lambda: B.kaufteile(kategorie="Magnete"))
    ergebnis["Baugruppe öffnen (Detail, alle Positionen)"] = median_ms(lambda: B.detail(bid), 7)
    ergebnis["Baugruppe: Summen über alle Ebenen"] = median_ms(lambda: B.summen(bid), 7)

    def kosten():
        # Entwurf der Einkaufsliste: je Position der letzte Einkauf (Preis je Stück), Summe der Baugruppe.
        s = 0.0
        for _, r, kante in B._positionen(bid):
            if not r.startswith(KAUFTEIL):
                continue
            letzter = None
            for e in db.get_connected(r, direction="in", rel_type=EINKAUF_VON):
                d = db.get_node(e, readonly=True)
                if letzter is None or d["datum"] > letzter["datum"]:
                    letzter = d
            if letzter:
                s += kante.get("menge", 1) * letzter["preis"] / max(1, letzter["menge"])
        return s
    ergebnis["Baugruppe: Kosten aus dem letzten Einkauf"] = median_ms(kosten, 7)

    def kaufteil_verlauf():
        for e in db.get_connected(f"{KAUFTEIL}/{teil}", direction="in", rel_type=EINKAUF_VON):
            db.get_node(e, readonly=True)
    ergebnis["Ein Kaufteil: sein Einkaufsverlauf"] = median_ms(kaufteil_verlauf)

    def ausgaben():
        je_monat = {}
        for d in db.list_nodes(EINKAUF, readonly=True).values():
            je_monat[d["datum"][:7]] = je_monat.get(d["datum"][:7], 0) + d["preis"]
        return je_monat
    ergebnis["Ausgaben je Monat über ALLE Einkäufe"] = median_ms(ausgaben, 7)

    def je_haendler():
        z = {}
        for h in db.list_nodes(HAENDLER, readonly=True):
            z[h] = len(db.get_connected(f"{HAENDLER}/{h}", direction="in", rel_type=BEI))
        return z
    ergebnis["Einkäufe je Händler"] = median_ms(je_haendler, 7)

    # Schreiben: je Vorgang eine eigene Transaktion, wie die Oberfläche es täte.
    n = [0]

    def neues_kaufteil():
        n[0] += 1
        db.create_node(KAUFTEIL, f"neu-{n[0]:05d}", {"name": "Neu", "kategorie": "Eigene", "einheit": "Stück", "standard": False})
    ergebnis["Neues Kaufteil anlegen"] = median_ms(neues_kaufteil, 30)

    def neuer_einkauf():
        n[0] += 1
        with db.transaction():
            eid = f"neuek-{n[0]:06d}"
            db.create_node(EINKAUF, eid, {"datum": "2026-10-03", "menge": 10, "preis": 12.5})
            db.create_edge(f"{EINKAUF}/{eid}", f"{KAUFTEIL}/{teil}", EINKAUF_VON)
            db.create_edge(f"{EINKAUF}/{eid}", f"{HAENDLER}/h000", BEI)
    ergebnis["Neuer Einkauf (Knoten + 2 Kanten)"] = median_ms(neuer_einkauf, 30)
    ergebnis["Kaufteil ändern (Preisfeld)"] = median_ms(lambda: db.update_node(KAUFTEIL, teil, {"notiz": f"x{time.time()}"}), 30)

    # Die Sicherung beim Start und vor Massenaktionen kopiert den ganzen Bestand, unter der Sperre von flatgraph.
    from partatlas import sicherung
    t = time.perf_counter()
    sicherung.sichern(b, "messung", immer=True)
    ergebnis["Sicherung kopieren (ms)"] = round((time.perf_counter() - t) * 1000)
    b.schliessen()
    ergebnis["Platte_MB"] = round(sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(os.path.join(wurzel, "datenbank")) for f in fs) / 1e6, 1)
    ergebnis["Dateien"] = sum(len(fs) for _, _, fs in os.walk(os.path.join(wurzel, "datenbank")))
    return ergebnis


if __name__ == "__main__":
    stufe = sys.argv[1]
    if stufe not in STUFEN:
        raise SystemExit(__doc__)
    wurzel = sys.argv[2] if len(sys.argv) > 2 else tempfile.mkdtemp(prefix=f"kaufteile_{stufe}_")
    if len(sys.argv) <= 3:
        aufbau, bids = bauen(wurzel, stufe)
        kt, ek, hd, bg, pos = STUFEN[stufe]
        print(json.dumps({"stufe": stufe, "knoten_neu": kt + ek + hd + bg, "kanten_neu": 2 * ek + bg * pos, "aufbau_s": round(aufbau, 1)}))
        # Die Abfragen in einem frischen Prozess: so wie nach einem Start.
        out = subprocess.run([sys.executable, __file__, stufe, wurzel, "abfragen"], capture_output=True, text=True)
        print(out.stdout.strip() or out.stderr[-600:])
        shutil.rmtree(wurzel, ignore_errors=True)
    else:
        print(json.dumps(abfragen(wurzel, stufe), ensure_ascii=False, indent=1))
