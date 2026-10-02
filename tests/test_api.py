"""Die Schnittstelle, wie die Oberfläche sie benutzt — und die Wache davor."""
import os
import stat
import tempfile
import time

import muster
from muster import check
from fastapi.testclient import TestClient
from partatlas.main import erstelle_app

if __name__ == "__main__":
    tmp = tempfile.mkdtemp()
    sammlung = os.path.join(tmp, "3D-Druck")
    os.makedirs(os.path.join(sammlung, "Technik"))
    muster.dreimf(os.path.join(sammlung, "Technik", "Zahnrad.3mf"))
    muster.stl_binaer(os.path.join(sammlung, "Haken.stl"))

    # Attrappen statt echter Programme: sie schreiben nur auf, womit sie
    # gestartet wurden. Vorne im PATH, damit die Erkennung sie findet.
    attrappen, protokoll = os.path.join(tmp, "bin"), os.path.join(tmp, "gestartet.txt")
    os.makedirs(attrappen)
    for name in ("freecad", "prusa-slicer", "xdg-open", "meincad", "dbus-send"):
        with open(os.path.join(attrappen, name), "w") as f:
            f.write(f'#!/bin/sh\necho "{name} $*" >> "{protokoll}"\n')
        os.chmod(os.path.join(attrappen, name), 0o755)
    # Der Dateidialog des Rechners: gibt aus, was in antwort.txt steht (leer = „Abbrechen“).
    antwort = os.path.join(tmp, "antwort.txt")
    with open(os.path.join(attrappen, "zenity"), "w") as f:
        f.write(f'#!/bin/sh\ncat "{antwort}"\n[ -s "{antwort}" ]\n')
    os.chmod(os.path.join(attrappen, "zenity"), 0o755)
    os.environ["PATH"] = attrappen + os.pathsep + os.environ["PATH"]

    def gestartet(erwartet):
        for _ in range(50):
            if os.path.exists(protokoll) and erwartet in open(protokoll).read():
                return True
            time.sleep(0.1)
        return False

    with TestClient(erstelle_app(os.path.join(tmp, "bestand"), prozesse=2)) as c:
        z = c.app.state.zustand
        r = c.post("/api/wurzeln", json={"pfad": sammlung})
        check("Ordner hinzufügen startet das Einlesen", r.status_code == 200)
        z["scanner"].warten(120)
        ph = z["scanner"].status.get("phasen", {})
        check("Scan hält die Dauer je Phase fest (Hashen, Analysieren …), zusammen höchstens die Gesamtdauer",
              {"hashen", "analysieren"} <= set(ph) and sum(ph.values()) <= z["scanner"].status["dauer_s"] + 0.3)
        check("Wurzel falsch: verständliche Meldung statt Absturz",
              c.post("/api/wurzeln", json={"pfad": "/gibt/es/nicht"}).json().get("fehler", "").startswith("Kein Ordner"))

        liste = c.get("/api/modelle").json()
        check("Liste liefert beide Modelle mit Kachel-Feldern",
              sorted(m["name"] for m in liste) == ["Haken", "Zahnrad"] and all("vorschau" in m for m in liste))
        zahnrad = next(m for m in liste if m["name"] == "Zahnrad")
        check("Suche", [m["name"] for m in c.get("/api/modelle", params={"q": "zahn"}).json()] == ["Zahnrad"])
        check("Filter nach Format", [m["name"] for m in c.get("/api/modelle", params={"format": "stl"}).json()] == ["Haken"])

        r = c.get(f"/api/vorschau/{zahnrad['hash']}.png")
        check("Vorschaubild ausgeliefert, lange cachebar", r.status_code == 200
              and r.headers["content-type"] == "image/png" and "immutable" in r.headers["cache-control"])
        import io
        from PIL import Image
        foto = io.BytesIO()
        Image.effect_noise((900, 900), 40).convert("RGB").save(foto, "PNG")
        mid = zahnrad["id"]
        c.post(f"/api/modelle/{mid}/bilder", content=foto.getvalue())
        gross = c.get(f"/api/modelle/{mid}/bild")
        klein = c.get(f"/api/modelle/{mid}/bild", params={"t": 1})
        bild = Image.open(io.BytesIO(klein.content))
        check("Thumbnail: ?t=1 liefert ein kleines WebP, lange cachebar, das Original bleibt unverändert",
              klein.headers["content-type"] == "image/webp" and bild.format == "WEBP" and max(bild.size) <= 320
              and len(klein.content) * 5 < len(gross.content) and gross.headers["content-type"] == "image/png"
              and "immutable" in klein.headers["cache-control"])
        check("Thumbnail: liegt als Datei in thumbs/ und wird beim zweiten Abruf nicht neu erzeugt",
              len(os.listdir(os.path.join(tmp, "bestand", "thumbs"))) == 1
              and c.get(f"/api/modelle/{mid}/bild", params={"t": 1}).content == klein.content)
        check("Thumbnail: ein nicht lesbares Bild fällt auf das Original zurück, kein Fehler",
              c.get(f"/api/vorschau/{zahnrad['hash']}.png", params={"t": 1}).status_code == 200)
        check("Vorschau: nur echte Hashes, kein Pfad durch die Hintertür",
              c.get("/api/vorschau/..%2F..%2Fetc%2Fpasswd.png").status_code == 404)

        c.post(f"/api/modelle/{zahnrad['id']}/tags", json={"tag": "#Funktional"})
        m = c.get(f"/api/modelle/{zahnrad['id']}").json()
        check("Tag hinzufügen: ohne #, klein geschrieben", "funktional" in m["tags"])
        check("Tag-Liste zählt über die Nachbarschaft",
              {t["name"]: t["anzahl"] for t in c.get("/api/tags").json()}.get("funktional") == 1)
        c.delete(f"/api/modelle/{zahnrad['id']}/tags/funktional")
        check("Tag entfernen", "funktional" not in c.get(f"/api/modelle/{zahnrad['id']}").json()["tags"])

        r = c.patch(f"/api/modelle/{zahnrad['id']}", json={"favorit": True, "gedruckt": True})
        check("Favorit und Gedruckt setzen", r.json()["favorit"] and r.json()["gedruckt"])
        check("Unbekanntes Feld wird abgelehnt", c.patch(f"/api/modelle/{zahnrad['id']}", json={"hash": "x"}).status_code == 400)

        # -- Ordner wählen: durchsuchen statt Pfad tippen
        os.makedirs(os.path.join(tmp, ".versteckt"))
        d = c.get("/api/durchsuchen", params={"pfad": tmp}).json()
        check("Durchsuchen: Unterordner sichtbar, versteckte nicht, Eltern-Ordner bekannt",
              "3D-Druck" in [o["name"] for o in d["ordner"]] and ".versteckt" not in [o["name"] for o in d["ordner"]]
              and d["eltern"] == os.path.dirname(tmp))
        d = c.get("/api/durchsuchen", params={"pfad": sammlung}).json()
        check("… zählt die Modelldateien samt Unterordnern, bevor man wählt", d["modelle"] == 2 and d["vollstaendig"])
        check("… mit dem persönlichen Ordner als Sprungziel",
              d["sprungziele"][0]["pfad"] == os.path.expanduser("~"))
        check("Kein Ordner: verständliche Meldung",
              c.get("/api/durchsuchen", params={"pfad": "/gibt/es/nicht"}).json().get("fehler", "").startswith("Kein Ordner"))

        # -- Wache
        fremd = c.post(f"/api/modelle/{zahnrad['id']}/loeschen", headers={"Origin": "http://boese.example"})
        check("Wache: Löschen von fremder Seite abgelehnt (403)", fremd.status_code == 403)
        fremd = c.post(f"/api/modelle/{zahnrad['id']}/loeschen", headers={"Sec-Fetch-Site": "cross-site"})
        check("Wache: Sec-Fetch-Site cross-site abgelehnt", fremd.status_code == 403)
        check("… und das Modell ist noch da", c.get(f"/api/modelle/{zahnrad['id']}").json()["papierkorb"] is False)

        # -- Öffnen in …
        prog = c.get("/api/programme").json()
        art = {p["name"]: p["art"] for p in prog["programme"]}
        check("Erkennung: FreeCAD als CAD, PrusaSlicer als Slicer", art.get("FreeCAD") == "cad" and art.get("PrusaSlicer") == "slicer")
        fc = next(p["pfad"] for p in prog["programme"] if p["name"] == "FreeCAD")
        check("Standard ohne Einstellung: STEP ins CAD, 3MF und STL in den Slicer",
              prog["standard"]["step"] == fc and "prusa-slicer" in prog["standard"]["3mf"] and "prusa-slicer" in prog["standard"]["stl"])
        haken = next(m for m in liste if m["name"] == "Haken")
        r = c.post(f"/api/modelle/{zahnrad['id']}/oeffnen", json={})
        check("Hauptknopf: Standardprogramm bekommt die Datei des Modells",
              r.json().get("programm") == "PrusaSlicer" and gestartet("prusa-slicer " + os.path.join(sammlung, "Technik", "Zahnrad.3mf")))
        c.post(f"/api/modelle/{haken['id']}/oeffnen", json={"pfad": fc})
        check("Öffnen mit: gewähltes Programm", gestartet("freecad " + os.path.join(sammlung, "Haken.stl")))
        c.post(f"/api/modelle/{haken['id']}/oeffnen", json={"system": True})
        check("Mit dem System öffnen: xdg-open", gestartet("xdg-open " + os.path.join(sammlung, "Haken.stl")))
        c.post(f"/api/modelle/{haken['id']}/im_ordner")
        check("Im Ordner zeigen: Dateimanager über ShowItems mit der Datei markiert (file://-Adresse)",
              gestartet("dbus-send --session") and "ShowItems array:string:file://" + os.path.join(sammlung, "Haken.stl") in open(protokoll).read())
        r = c.post(f"/api/modelle/{zahnrad['id']}/oeffnen", json={"pfad": "/bin/sh"})
        check("Öffnen: nur bekannte Programme, kein beliebiger Pfad", r.status_code == 400)
        e = c.get("/api/einstellungen").json()["programm"]
        check("Einstellungen: Slicer und CAD stehen schon drin, als „automatisch“ gefunden",
              e["slicer"]["name"] == "PrusaSlicer" and e["cad"]["name"] == "FreeCAD" and e["slicer"]["automatisch"] and e["cad"]["automatisch"])
        r = c.put("/api/einstellungen", json={"programm": {"slicer": os.path.join(tmp, "gibtsnicht")}})
        check("Programm wählen: nur was es gibt und ausführbar ist", r.status_code == 400)
        mein = os.path.join(attrappen, "meincad")
        open(antwort, "w").close()
        check("Dateidialog abgebrochen: nichts ändert sich", c.post("/api/programme/waehlen", json={"art": "slicer"}).json() == {"abgebrochen": True})
        with open(antwort, "w") as f:
            f.write(mein + "\n")
        w = c.post("/api/programme/waehlen", json={"art": "slicer"}).json()
        check("Dateidialog des Rechners: der gewählte Pfad kommt zurück, mit Namen vom Dateinamen",
              w["pfad"] == mein and w["name"] == "meincad" and w["art"] == "slicer" and not w["automatisch"])
        check("… gespeichert wird erst mit „Speichern“", c.get("/api/einstellungen").json()["programm"]["slicer"]["name"] == "PrusaSlicer")
        c.put("/api/einstellungen", json={"programm": {"slicer": mein}})
        c.post(f"/api/modelle/{haken['id']}/oeffnen", json={})
        check("Eigener Slicer übernimmt den Hauptknopf für STL", gestartet("meincad " + os.path.join(sammlung, "Haken.stl")))
        check("Es bleiben genau zwei Programme zur Auswahl: der gewählte Slicer und das CAD",
              [p["name"] for p in c.get("/api/programme").json()["programme"]] == ["meincad", "FreeCAD"])
        with open(antwort, "w") as f:
            f.write(sammlung + "\n")
        w = c.post("/api/wurzeln/waehlen").json()
        check("Ordner hinzufügen: der Ordnerdialog des Rechners liefert Pfad und Zahl der Modelldateien",
              w["pfad"] == sammlung and w["modelle"] >= 2)
        open(antwort, "w").close()
        check("Ordnerdialog abgebrochen: nichts wird gewählt", c.post("/api/wurzeln/waehlen").json() == {"abgebrochen": True})
        c.put("/api/einstellungen", json={"programm": {"slicer": ""}})
        check("„Automatisch“: Slicer ist wieder der gefundene",
              c.get("/api/einstellungen").json()["programm"]["slicer"]["name"] == "PrusaSlicer")

        check("Skript und Stile werden bei jedem Aufruf neu geprüft (kein veralteter Stand nach einer Aktualisierung)",
              c.get("/web/app.js").headers.get("cache-control") == "no-cache" and c.get("/web/app.css").headers.get("cache-control") == "no-cache")
        check("… das mitgelieferte three.js dagegen darf ewig im Zwischenspeicher liegen",
              "immutable" in c.get("/web/vendor/three.module.min.js").headers.get("cache-control", ""))

        # -- Erkennung auf einem Linux-Rechner mit AppImage und Flatpak (z. B. Anycubic Slicer Next 1.3.9.4)
        from partatlas import programme as prog_mod
        heim = os.path.join(tmp, "heim")
        os.makedirs(os.path.join(heim, "Downloads")); os.makedirs(os.path.join(heim, ".local/share/flatpak/exports/bin"))
        alt_heim, os.environ["HOME"] = os.environ.get("HOME"), heim
        try:
            app = os.path.join(heim, "Downloads", "AnycubicSlicer-1.3.9.4-x86_64.AppImage")
            open(app, "w").close()
            fp = os.path.join(heim, ".local/share/flatpak/exports/bin", "io.github.unbekannt.AnycubicSlicer")
            open(fp, "w").close(); os.chmod(fp, 0o755)
            pfade = lambda: [e["pfad"] for e in prog_mod.erkennen() if e["name"] == "Anycubic Slicer"]
            check("Erkennung: Flatpak mit unbekannter Kennung wird über das Stichwort gefunden, die AppImage ohne Ausführrecht nicht",
                  pfade() == [fp])
            os.chmod(app, 0o755)
            check("… mit Ausführrecht auch die AppImage in Downloads", app in pfade())
            with open(app, "w") as f:
                f.write("#!/bin/sh\nexit 127\n")
            try:
                prog_mod.oeffnen(app, os.path.join(sammlung, "Haken.stl"))
                gemeldet = ""
            except OSError as e:
                gemeldet = str(e)
            check("AppImage, die sich sofort beendet: sagt es (FUSE) statt still zu scheitern", "FUSE" in gemeldet and "sofort" in gemeldet)
            with open(app, "w") as f:
                f.write("#!/bin/sh\necho 'libfuse.so.2: kann nicht geoeffnet werden' >&2\nexit 3\n")
            log = os.path.join(tmp, "arbeit-test", "programmstart.log")
            try:
                prog_mod.oeffnen(app, os.path.join(sammlung, "Haken.stl"), log)
                gemeldet = ""
            except OSError as e:
                gemeldet = str(e)
            check("Fehlstart: die Ausgabe des Programms steht in der Meldung und im Protokoll",
                  "libfuse.so.2" in gemeldet and "Code 3" in gemeldet and "libfuse.so.2" in open(log).read())
        finally:
            os.environ["HOME"] = alt_heim

        # -- Löschen über die API
        v = c.get(f"/api/modelle/{zahnrad['id']}/loeschen").json()
        check("Löschvorschau über die API", len(v["dateien"]) == 1 and len(v["knoten"]) == 1)
        c.post(f"/api/modelle/{zahnrad['id']}/loeschen", headers={"Sec-Fetch-Site": "same-origin"})
        check("Gelöscht: Datei weg aus dem Ordner", not os.path.exists(os.path.join(sammlung, "Technik", "Zahnrad.3mf")))
        check("Zähler: Papierkorb 1", c.get("/api/zaehler").json()["papierkorb"] == 1)
        c.post(f"/api/modelle/{zahnrad['id']}/wiederherstellen")
        check("Wiederhergestellt: Datei zurück", os.path.exists(os.path.join(sammlung, "Technik", "Zahnrad.3mf")))

        baum = c.get("/api/ordner").json()
        check("Ordnerbaum über die API", baum[0]["name"] == "3D-Druck" and baum[0]["kinder"][0]["name"] == "Technik")
        check("Oberfläche wird ausgeliefert", "partAtlas" in c.get("/").text)
    muster.ende()
