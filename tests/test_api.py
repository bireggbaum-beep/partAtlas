"""Die Schnittstelle, wie die Oberfläche sie benutzt — und die Wache davor."""
import logging
import os
import stat
import tempfile
import time

import muster
from muster import check
from fastapi.testclient import TestClient
from partatlas.main import erstelle_app

class Sammler(logging.Handler):
    def __init__(self):
        super().__init__(logging.INFO)
        self.zeilen = []

    def emit(self, r):
        self.zeilen.append(r.getMessage())

    def hat(self, *teile):
        return any(all(t in z for t in teile) for z in self.zeilen)


if __name__ == "__main__":
    log_sammler = Sammler()
    logging.getLogger("partatlas").addHandler(log_sammler)
    logging.getLogger("partatlas").setLevel(logging.INFO)
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
        u = c.post("/api/wurzeln/uebersicht", json={"pfad": sammlung}).json()
        z["scanner"].warten(120)           # das Einlesen beim Start
        vorher, wurzeln_vorher = z["scanner"].status["lauf"], c.get("/api/wurzeln").json()
        r = c.post("/api/wurzeln", json={"pfad": sammlung})
        check("Übersicht vor dem Einlesen: Modelldateien je Format, ohne etwas einzutragen",
              u["modelle"] == sum(u["je_format"].values()) > 0 and u["vollstaendig"] and wurzeln_vorher == [])
        check("Ordner hinzufügen startet das Einlesen und nennt den Lauf, dem der Dialog folgt", r.status_code == 200
              and r.json()["lauf"] == vorher + 1)
        z["scanner"].warten(120)
        check("… dieser Lauf ist es, und er sah alle Dateien der Übersicht",
              z["scanner"].status["lauf"] == r.json()["lauf"] and z["scanner"].status["neu"] == u["modelle"])
        ph = z["scanner"].status.get("phasen", {})
        check("Scan hält die Dauer je Phase fest (Hashen, Analysieren …), zusammen höchstens die Gesamtdauer",
              {"hashen", "analysieren"} <= set(ph) and sum(ph.values()) <= z["scanner"].status["dauer_s"] + 0.3)
        check("Abbrechen ohne laufendes Einlesen: Antwort „nein“, kein Fehler",
              c.post("/api/scan/abbrechen").json() == {"abgebrochen": False})
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
        vor = sorted(os.listdir(os.path.join(tmp, "bestand", "thumbs")))   # die kleinen Vorschauen von partAtlas bekommen keine zweite Fassung; nur das grosse Foto
        nochmal = c.get(f"/api/modelle/{mid}/bild", params={"t": 1}).content
        check("Thumbnail: liegt als Datei in thumbs/ und wird beim zweiten Abruf nicht neu erzeugt",
              len(vor) == 1 and sorted(os.listdir(os.path.join(tmp, "bestand", "thumbs"))) == vor and nochmal == klein.content)
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
        check("Die Liste ist nach jeder Änderung sofort aktuell: der Zwischenspeicher der Kacheln wird bei einer Änderung verworfen, auch für die Ansicht „Favoriten“",
              next(x for x in c.get("/api/modelle").json() if x["id"] == zahnrad["id"])["favorit"] is True
              and [x["id"] for x in c.get("/api/modelle", params={"ansicht": "favoriten"}).json()] == [zahnrad["id"]])
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

        # -- Das Wurzelverzeichnis ist kein Ordner für den Katalog
        check("Das Wurzelverzeichnis „/“ lässt sich nicht als Wurzelordner hinzufügen",
              c.post("/api/wurzeln", json={"pfad": "/"}).status_code == 400)
        check("Der Ordnerbaum zählt im Wurzelverzeichnis keine Modelldateien (es liefe durch die ganze Platte)",
              c.get("/api/durchsuchen", params={"pfad": "/"}).json()["modelle"] is None)

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
        # Ein eigenes Programm gilt für alle Formate; trotzdem gehört FCStd ins CAD, nicht in einen Slicer, der es nicht kennt.
        from partatlas import programme as _prog
        wahl = _prog.standard([{"art": "slicer", "formate": _prog.FORMATE, "pfad": "/slicer"},
                               {"art": "cad", "formate": ("fcstd",), "pfad": "/cad"}])
        check("Standard: FCStd geht ins CAD, auch wenn ein eigener Slicer alle Formate beansprucht", wahl["fcstd"] == "/cad")
        check("3MF: FreeCAD steht zur Wahl, Standard bleibt der Slicer",
              "3mf" in next(p["formate"] for p in prog["programme"] if p["name"] == "FreeCAD") and fc not in (prog["standard"]["3mf"],))
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
        check("Gelöscht: die Datei bleibt im Ordner liegen, nur der Katalogeintrag geht", os.path.exists(os.path.join(sammlung, "Technik", "Zahnrad.3mf")))
        check("Zähler: Papierkorb 1", c.get("/api/zaehler").json()["papierkorb"] == 1)
        c.post(f"/api/modelle/{zahnrad['id']}/wiederherstellen")
        check("Wiederhergestellt: Modell wieder im Katalog, Datei unverändert", os.path.exists(os.path.join(sammlung, "Technik", "Zahnrad.3mf")) and c.get(f"/api/modelle/{zahnrad['id']}").json()["papierkorb"] is False)

        baum = c.get("/api/ordner").json()
        check("Ordnerbaum über die API", baum[0]["name"] == "3D-Druck" and baum[0]["kinder"][0]["name"] == "Technik")
        check("Oberfläche wird ausgeliefert", "partAtlas" in c.get("/").text)

    # -- STEP: Netz und Vorschau kommen von FreeCAD (hier die Attrappe), die 3D-Ansicht liest das Netz
    import sys
    step_dir = os.path.join(tmp, "cad")
    os.makedirs(step_dir)
    muster.step(os.path.join(step_dir, "Welle.step"))
    with TestClient(erstelle_app(os.path.join(tmp, "bestand_step"), prozesse=2)) as c:
        z = c.app.state.zustand
        z["scanner"].cad_befehl = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "cad_attrappe.py")]
        c.post("/api/wurzeln", json={"pfad": step_dir})
        z["scanner"].warten(120)
        welle = c.get("/api/modelle").json()[0]
        check("STEP nach dem Einlesen: Vorschau und Maße stehen da, FreeCAD hat das Netz geliefert",
              welle["cad"] == "ok" and welle["vorschau"] == "gerendert" and welle["masse"] is not None)
        r = c.get(f"/api/modelle/{welle['id']}/netz")
        check("3D-Ansicht für STEP liest das Netz aus dem Bestand", r.status_code == 200 and r.headers["x-dreiecke"] == "12")
        check("Das Vorschaubild wird ausgeliefert", c.get(f"/api/vorschau/{welle['hash']}.png").status_code == 200)
    # -- Einlesen beim Start ist eine Einstellung, Vorgabe aus; der Zeitpunkt des letzten Einlesens bleibt über Neustarts
    st_pfad = os.path.join(tmp, "bestand_start")
    with TestClient(erstelle_app(st_pfad, prozesse=2)) as c:
        check("Einlesen beim Start: Vorgabe aus", c.get("/api/einstellungen").json()["scan_beim_start"] is False)
        check("Noch nie eingelesen: kein Zeitpunkt", c.get("/api/stand").json()["zuletzt_eingelesen"] is None)
        c.post("/api/wurzeln", json={"pfad": sammlung})
        c.app.state.zustand["scanner"].warten(120)
        zeit1 = c.get("/api/stand").json()["zuletzt_eingelesen"]
        check("Nach dem Einlesen steht der Zeitpunkt da (mit Zeitzone) und im Lauf-Status", zeit1 is not None and len(zeit1) >= 20
              and c.get("/api/stand").json()["scan"]["zuletzt_eingelesen"] == zeit1)
    with TestClient(erstelle_app(st_pfad, prozesse=2)) as c:
        time.sleep(1.5)
        stand = c.get("/api/stand").json()
        check("Neustart mit Vorgabe: es wird NICHT eingelesen (kein Lauf), der Zeitpunkt vom letzten Mal bleibt",
              stand["scan"]["lauf"] == 0 and stand["zuletzt_eingelesen"] == zeit1)
        c.put("/api/einstellungen", json={"scan_beim_start": True})
        check("Einstellung gespeichert", c.get("/api/einstellungen").json()["scan_beim_start"] is True)
    with TestClient(erstelle_app(st_pfad, prozesse=2)) as c:
        c.app.state.zustand["scanner"].warten(120)
        time.sleep(0.5)
        check("Neustart mit eingeschalteter Einstellung: es wird eingelesen", c.get("/api/stand").json()["scan"]["lauf"] >= 1)
    # -- Neustart mit offenen Vorschaubildern: die Warteschlange wird fortgesetzt, auch ohne „Beim Start einlesen“ und ohne die Ordner zu durchsuchen
    wq_pfad = os.path.join(tmp, "bestand_warteschlange")
    with TestClient(erstelle_app(wq_pfad, prozesse=2)) as c:
        c.post("/api/wurzeln", json={"pfad": sammlung})
        c.app.state.zustand["scanner"].warten(120)
        bq = c.app.state.zustand["bestand"]
        h0 = c.get("/api/modelle").json()[0]["hash"]
        bq.db.update_node("PART_GEOMETRY", h0, {"vorschau": "ausstehend"})       # wie nach einem Abbruch mitten im Rechnen
        os.remove(bq.vorschau_pfad(h0, "berechnet"))
    muster.stl_binaer(os.path.join(sammlung, "Nach_dem_Beenden.stl"), 77, 20, 30)
    with TestClient(erstelle_app(wq_pfad, prozesse=2)) as c:
        c.app.state.zustand["scanner"].warten(120)
        time.sleep(0.5)
        stand = c.get("/api/stand").json()
        check("Neustart mit offenem Vorschaubild: es wird fortgesetzt (Hintergrundlauf), ohne „Beim Start einlesen“",
              stand["scan"]["lauf"] >= 1 and stand["scan"]["nur_cad"] is True and os.path.exists(c.app.state.zustand["bestand"].vorschau_pfad(h0, "berechnet")))
        check("Dabei werden die Ordner nicht durchsucht: die neue Datei kommt nicht dazu",
              "Nach_dem_Beenden" not in {x["name"] for x in c.get("/api/modelle").json()})
    os.remove(os.path.join(sammlung, "Nach_dem_Beenden.stl"))
    # -- Beenden während des Einlesens: der Server wartet nicht 30 s darauf (FreeCAD, das an einer Datei hängt, hielt ihn so scheinbar fest)
    be_pfad = os.path.join(tmp, "bestand_beenden")
    with TestClient(erstelle_app(be_pfad, prozesse=2)) as c:
        sc = c.app.state.zustand["scanner"]

        def haengender_lauf(nur_cad=False):
            sc._stopp.clear()
            sc._setze(laeuft=True, phase="cad")
            while not sc._stopp.wait(0.05):
                pass
            sc._setze(laeuft=False, abgebrochen=True, phase="abgebrochen")
        sc.lauf = haengender_lauf
        sc.starten()
        while not sc.status.get("laeuft"):
            time.sleep(0.02)
        be_t0 = time.monotonic()
    be_dauer = time.monotonic() - be_t0
    check("Beenden während eines Laufs (etwa FreeCAD hängt): der Server ist in unter 10 s weg, nicht erst nach 30 s", be_dauer < 10)
    # -- Eine langsame Anfrage hält die anderen nicht auf (vorher liefen 46 Routen als `async def` mit synchroner Arbeit in der
    # Ereignisschleife: FreeCAD für eine eigene Komponente, der Dateidialog, jede Schreibanfrage, die auf das Einlesen wartete)
    import threading
    with TestClient(erstelle_app(os.path.join(tmp, "bestand_schleife"), prozesse=2)) as c:
        c.app.state.zustand["katalog"].verschieben = lambda mid, ordner: time.sleep(2)
        langsam = threading.Thread(target=lambda: c.post("/api/modelle/m_000001/verschieben", json={"ordner": "x"}))
        langsam.start()
        time.sleep(0.3)
        t0 = time.monotonic()
        c.get("/api/stand")
        sl_dauer = time.monotonic() - t0
        langsam.join()
    check("Eine Anfrage, die 2 s arbeitet, hält andere nicht auf: /api/stand antwortet währenddessen sofort", sl_dauer < 0.5)
    import ast
    from partatlas import main as _main_quelle
    baum = ast.parse(open(_main_quelle.__file__, encoding="utf-8").read())
    BEWUSST_ASYNC = {"leben", "protokoll", "wache", "clientfehler_melden", "live", "katalogfehler", "fehlt", "get_response", "json_koerper", "roh_koerper"}
    async_routen = [f.name for f in ast.walk(baum) if isinstance(f, ast.AsyncFunctionDef) and f.name not in BEWUSST_ASYNC]
    check("Keine Route ist `async def` (ausser denen, die nur lesen und weiterreichen): synchrone Arbeit gehört in den Thread-Pool",
          async_routen == [])

    # -- Beenden mit offenem Tab: die Live-Verbindung endet nie von selbst; vorher liess sich partAtlas dann nur abschiessen
    import signal
    import socket
    import subprocess
    import sys
    import urllib.request
    with socket.socket() as so:
        so.bind(("127.0.0.1", 0))
        port = so.getsockname()[1]
    quelle = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    umgebung = {**os.environ, "PARTATLAS_BESTAND": os.path.join(tmp, "bestand_tab"), "PARTATLAS_PORT": str(port),
                "PYTHONPATH": os.pathsep.join([os.environ.get("PARTATLAS_QUELLE") or quelle, os.environ.get("PYTHONPATH", "")])}
    server = subprocess.Popen([sys.executable, "-m", "partatlas"], env=umgebung, cwd=tmp, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/api/stand", timeout=2).read()
                break
            except OSError:
                time.sleep(0.1)
        tab = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/live", timeout=30)
        tab.readline()
        t0 = time.monotonic()
        server.send_signal(signal.SIGTERM)
        try:
            server.wait(15)
        except subprocess.TimeoutExpired:
            pass
        tab_dauer = time.monotonic() - t0
    finally:
        if server.poll() is None:
            server.kill()
    check("Beenden mit offenem Tab: der Server schliesst die Live-Verbindung und ist in unter 2 s weg", tab_dauer < 2)

    # -- Protokoll für den Tester ohne Terminal
    from partatlas import main as hauptmodul
    check("Protokoll beim Start: Umgebung, Katalog mit Zahlen, Einstellungen, was im Bestand aussteht",
          log_sammler.hat("Umgebung: Python") and log_sammler.hat("Katalog:", "Modelle", "Wurzelordner") and log_sammler.hat("Einstellungen: Beim Start einlesen")
          and log_sammler.hat("Ausstehend im Bestand"))
    check("Protokoll: Beginn und Ende des Servers stehen drin", log_sammler.hat("nimmt Anfragen an") and log_sammler.hat("partAtlas beendet"))
    with TestClient(erstelle_app(os.path.join(tmp, "bestand_protokoll"), prozesse=2)) as c:
        c.post("/api/clientfehler", json={"meldung": "x is not a function", "ort": "app.js:12:3"})
        check("Ein Fehler in der Oberfläche (JavaScript) kommt ins Protokoll, mit Ort",
              log_sammler.hat("Fehler im Browser: x is not a function", "app.js:12:3"))
        check("Jede Anfrage, die etwas ändert, steht im Protokoll — mit Weg, Status und Dauer, ohne Inhalt",
              log_sammler.hat("Anfrage POST /api/clientfehler", "200"))
        check("Der Browser (Name und Fassung) steht einmal im Protokoll", log_sammler.hat("Seite geöffnet von:"))
        hauptmodul.LANGSAM_S = 0.0
        c.get("/api/stand")
        hauptmodul.LANGSAM_S = 3.0
        check("Eine langsame Anfrage steht als Warnung im Protokoll (was hielt den Server auf)", log_sammler.hat("Langsame Anfrage: GET /api/stand"))
        for _ in range(hauptmodul.CLIENTFEHLER_MAX + 5):
            c.post("/api/clientfehler", json={"meldung": "Schleife"})
        check("Fehler aus dem Browser sind begrenzt: eine Fehlerschleife füllt das Protokoll nicht",
              sum("Fehler im Browser: Schleife" in z for z in log_sammler.zeilen) < hauptmodul.CLIENTFEHLER_MAX)
    muster.ende()

