"""
Erfundene Drucke für die Demo-Sammlung — damit der Reiter „Drucke“ in einer
Vorführung nicht leer ist. Spricht mit einem laufenden partAtlas über dessen
Schnittstelle, wie die Oberfläche; legt nichts an, wenn schon Drucke da sind.

    python werkzeuge/demo_drucke.py [--port 8765]

Alles ist ausgedacht: Gewichte, Zeiten, Notizen und die Fotos (ein Farbfeld
mit einem Umriss). Fester Samen: zwei Läufe erzeugen dasselbe.
"""
import argparse
import io
import json
import random
import time
import urllib.request

from PIL import Image, ImageDraw

NOTIZEN = [
    "Düse 215 °C, Bett 60 °C, Lüfter 100 %.", "Mit Brim, sonst löst sich die Ecke.", "Zu schnell: Schichten haben sich verzogen.",
    "Perfekt — so wieder drucken.", "Stützen nur am Rand, 0,2 mm Schicht.", "Zweiter Versuch nach dem Düsenwechsel.",
    "Füllung 20 % Gyroid, 3 Wände.", "Langsam gedruckt (60 %), dafür sauber.",
]
MATERIAL = [("PLA", "#d9d9d9"), ("PLA", "#c0392b"), ("PETG", "#2c6fbb"), ("PETG", "#222222"), ("PLA+", "#27ae60"), ("TPU", "#e67e22")]


def anfrage(port, pfad, methode="GET", daten=None, roh=None):
    kopf = {"Content-Type": "application/json"} if daten is not None else {}
    body = json.dumps(daten).encode() if daten is not None else roh
    r = urllib.request.Request(f"http://127.0.0.1:{port}{pfad}", data=body, method=methode, headers=kopf)
    with urllib.request.urlopen(r, timeout=30) as a:
        return json.loads(a.read() or b"null")


def foto(zufall):
    farbe = tuple(zufall.randint(40, 220) for _ in range(3))
    bild = Image.new("RGB", (640, 480), tuple(int(c * 0.35) for c in farbe))
    z = ImageDraw.Draw(bild)
    z.rectangle((0, 380, 640, 480), fill=(60, 60, 64))                       # das Druckbett
    x, y, b, h = zufall.randint(150, 300), zufall.randint(150, 220), zufall.randint(120, 220), zufall.randint(100, 180)
    z.rounded_rectangle((x, y + 90, x + b, y + 90 + h), radius=18, fill=farbe, outline=(255, 255, 255))
    puffer = io.BytesIO()
    bild.save(puffer, "JPEG", quality=85)
    return puffer.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    port = ap.parse_args().port
    for _ in range(120):                       # auf den ersten Scan warten
        try:
            if anfrage(port, "/api/stand")["scan"].get("laeuft") is False and anfrage(port, "/api/modelle"):
                break
        except OSError:
            pass
        time.sleep(1)
    modelle = sorted(anfrage(port, "/api/modelle"), key=lambda m: m["name"])
    if not modelle or any(m.get("drucke_n") for m in modelle):
        print("Demo-Drucke: nichts zu tun.")
        return
    zufall = random.Random(7)
    ids = [m["id"] for m in modelle]
    fertig = 0
    for mid in zufall.sample(ids, k=max(1, len(ids) * 2 // 5)):
        gute = []
        for versuch in range(zufall.choice((1, 1, 2, 3))):
            typ, farbe = zufall.choice(MATERIAL)
            g = round(zufall.uniform(4, 180), 1)
            felder = {"datum": f"2026-{zufall.randint(5, 9):02d}-{zufall.randint(1, 28):02d}", "gewicht_g": g,
                      "dauer_s": int(g * zufall.uniform(40, 70)), "notiz": zufall.choice(NOTIZEN),
                      "ergebnis": zufall.choice(("gut", "gut", "gut", "fehler", "abgebrochen")),
                      "filament": [{"typ": typ, "farbe": farbe, "g": g}]}
            did = anfrage(port, "/api/drucke", "POST", {"modelle": [mid], "felder": felder})["id"]
            if zufall.random() < 0.6:
                anfrage(port, f"/api/drucke/{did}/bilder", "POST", roh=foto(zufall))
            if felder["ergebnis"] == "gut":
                gute.append(did)
            fertig += 1
        if gute and zufall.random() < 0.85:          # der letzte gute Druck ist „so war es gut“
            anfrage(port, f"/api/drucke/{gute[-1]}/referenz", "POST", {"modell": mid})
    # Eine Platte mit drei Modellen, ein Foto für alle.
    drei = zufall.sample(ids, k=min(3, len(ids)))
    did = anfrage(port, "/api/drucke", "POST", {"modelle": drei, "felder": {
        "datum": "2026-09-14", "gewicht_g": 58.4, "dauer_s": 9300, "ergebnis": "gut",
        "notiz": "Alle drei zusammen auf einer Platte, ging beim ersten Mal.",
        "filament": [{"typ": "PETG", "farbe": "#2c6fbb", "g": 58.4}]}})["id"]
    anfrage(port, f"/api/drucke/{did}/bilder", "POST", roh=foto(zufall))
    print(f"Demo-Drucke: {fertig + 1} angelegt.")


if __name__ == "__main__":
    main()
