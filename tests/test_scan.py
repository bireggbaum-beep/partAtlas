"""Scan und Katalog: was der Anwender mit seinen Ordnern tut, muss der
Katalog richtig nachvollziehen — ohne Duplikate, ohne Verlust."""
import os
import shutil
import tempfile

import muster
from muster import check
from partatlas.bestand import Bestand
from partatlas.katalog import Katalog, KatalogFehler
from partatlas.scan import Scanner


def neu_oeffnen():
    global b, k, s
    b.schliessen()
    b = Bestand(bestand_pfad)
    k = Katalog(b)
    s = Scanner(b, k, prozesse=2)


def scannen():
    s.lauf()
    return s.status


if __name__ == "__main__":
    tmp = tempfile.mkdtemp()
    sammlung = os.path.join(tmp, "3D-Druck")
    downloads = os.path.join(tmp, "Downloads")
    bestand_pfad = os.path.join(tmp, "bestand")
    os.makedirs(os.path.join(sammlung, "Drohne", "Arme"))
    os.makedirs(os.path.join(sammlung, "Haushalt"))
    os.makedirs(os.path.join(sammlung, ".versteckt"))
    os.makedirs(downloads)
    muster.stl_binaer(os.path.join(sammlung, "Drohne", "Arme", "Arm_Front_v2.stl"))
    muster.dreimf(os.path.join(sammlung, "Drohne", "Top_Plate.3mf"))
    muster.obj(os.path.join(sammlung, "Haushalt", "Haken.obj"), 5, 5, 5)
    muster.step(os.path.join(sammlung, "Haushalt", "Welle.step"))
    muster.stl_binaer(os.path.join(sammlung, ".versteckt", "geheim.stl"), 1, 1, 1)
    with open(os.path.join(sammlung, "Haushalt", "kaputt.3mf"), "wb") as f:
        f.write(b"kein zip")
    with open(os.path.join(sammlung, "notiz.txt"), "w") as f:
        f.write("kein Modell")

    b = Bestand(bestand_pfad)
    k = Katalog(b)
    s = Scanner(b, k, prozesse=2)
    w1 = k.wurzel_hinzufuegen(sammlung)

    try:
        k.wurzel_hinzufuegen(os.path.join(sammlung, "Drohne"))
        check("Ein Unterordner einer Wurzel wird nicht zweite Wurzel", False)
    except KatalogFehler:
        check("Ein Unterordner einer Wurzel wird nicht zweite Wurzel", True)
    try:
        k.wurzel_hinzufuegen(tmp)
        check("Ein Ordner, der den Bestand enthält, wird keine Wurzel", False)
    except KatalogFehler:
        check("Ein Ordner, der den Bestand enthält, wird keine Wurzel", True)

    st = scannen()
    alle = {m["name"]: m for m in k.modelle()}
    check("Erster Scan: fünf Modelldateien, versteckte Ordner und .txt bleiben draussen",
          sorted(alle) == ["Arm_Front_v2", "Haken", "Top_Plate", "Welle", "kaputt"])
    check("Kaputte Datei steht im Katalog, als unlesbar markiert, der Scan lief durch",
          alle["kaputt"]["fehler"] and st["unlesbar"] == 1 and st["phase"] == "fertig")
    check("3MF mit eingebettetem Bild: Vorschau „eingebettet“, Datei im Vault",
          alle["Top_Plate"]["vorschau"] == "eingebettet"
          and os.path.exists(b.vorschau_pfad(alle["Top_Plate"]["hash"], "extrahiert")))
    check("STL ohne Bild: Vorschau auf dem Server gerendert",
          alle["Arm_Front_v2"]["vorschau"] == "gerendert"
          and os.path.getsize(b.vorschau_pfad(alle["Arm_Front_v2"]["hash"], "berechnet")) > 500)
    check("STEP: aufgenommen, Vorschau „keine“", alle["Welle"]["vorschau"] == "keine")
    dat = lambda m: {k: v for k, v in b.db.get_node(f"PART_GEOMETRY/{m['hash']}", readonly=True).items()
                     if k.startswith("vorschau_") and v}
    check("Vorschau gehört zur Datei, die Art steht im Namen: aus der Datei vs. berechnet, STEP ohne",
          dat(alle["Top_Plate"]) == {"vorschau_extrahiert": f"vault/vorschau/{alle['Top_Plate']['hash']}.extrahiert.png"}
          and dat(alle["Arm_Front_v2"]) == {"vorschau_berechnet": f"vault/vorschau/{alle['Arm_Front_v2']['hash']}.berechnet.png"}
          and dat(alle["Welle"]) == {} and not os.path.exists(b.pfad("cache")))
    check("Gewicht und Material aus dem Slicer an der Kachel",
          alle["Top_Plate"]["gewicht_g"] == 15.75 and alle["Top_Plate"]["material"] == "PETG")
    check("Automatische Tags wie im 3MF Katalog: Wörter aus dem Namen, ohne Versionsnummer",
          alle["Arm_Front_v2"]["tags"] == ["arm", "front", "miniatur"])
    check("Automatische Tags: mehrteilig und mehrfarbig aus der 3MF, das Material nicht als Tag",
          {"mehrteilig", "mehrfarbig"} <= set(alle["Top_Plate"]["tags"]) and "petg" not in alle["Top_Plate"]["tags"])
    check("Material aus der 3MF als Knoten: Datei ─[REQUIRES_MATERIAL]→ PETG und PLA",
          sorted(r.split("/")[1] for r in b.db.get_connected(f'PART_GEOMETRY/{alle["Top_Plate"]["hash"]}',
                                                              rel_type="REQUIRES_MATERIAL")) == ["PETG", "PLA"]
          and alle["Top_Plate"]["materialien"] == ["PETG", "PLA"])

    anzahl_knoten = len(b.db.list_nodes("PART_GEOMETRY")) + len(b.db.list_nodes("MODEL_ASSET"))
    st = scannen()
    check("Zweiter Scan ohne Änderung: nichts neu gelesen, kein Knoten dazu",
          st["zu_pruefen"] == 0 and st["neu"] == 0
          and len(b.db.list_nodes("PART_GEOMETRY")) + len(b.db.list_nodes("MODEL_ASSET")) == anzahl_knoten)

    arm = alle["Arm_Front_v2"]
    k.tag_setzen(arm["id"], "#Funktional")
    k.modell_aendern(arm["id"], {"favorit": True})
    shutil.move(os.path.join(sammlung, "Drohne", "Arme", "Arm_Front_v2.stl"),
                os.path.join(sammlung, "Haushalt", "Arm umbenannt.stl"))
    st = scannen()
    nach = k.modell(arm["id"])
    check("Verschoben und umbenannt ausserhalb der App: dasselbe Modell, neuer Ort",
          [o["pfad"] for o in nach["orte"]] == ["Haushalt/Arm umbenannt.stl"] and st["neu"] == 0)
    check("… Tags und Favorit bleiben dran", "funktional" in nach["tags"] and nach["favorit"])
    check("… der Name folgt dem Dateinamen (Name = Dateiname wie im 3MF Katalog)", nach["name"] == "Arm umbenannt")

    w2 = k.wurzel_hinzufuegen(downloads)
    shutil.copy(os.path.join(sammlung, "Drohne", "Top_Plate.3mf"), os.path.join(downloads, "Top_Plate (1).3mf"))
    st = scannen()
    top = k.modell(alle["Top_Plate"]["id"])
    check("Dieselbe Datei in einer zweiten Wurzel: ein Modell mit zwei Orten, als Duplikat",
          len(top["orte"]) == 2 and top["duplikat"] and st["neu"] == 0)
    check("Ansicht Duplikate zeigt es", [m["id"] for m in k.modelle(ansicht="duplikate")] == [top["id"]])

    os.remove(os.path.join(sammlung, "Haushalt", "Haken.obj"))
    st = scannen()
    haken = k.modell(alle["Haken"]["id"])
    check("Datei weg: Modell bleibt, gilt als fehlend", haken["fehlt"] and st["entfernt"] == 1)

    ordner = {w["name"]: w for w in k.ordnerbaum()}
    drohne = [c for c in ordner["3D-Druck"]["kinder"] if c["name"] == "Drohne"]
    check("Ordnerbaum abgeleitet aus den Pfaden, mit Anzahl", drohne and drohne[0]["anzahl"] == 1
          and ordner["Downloads"]["anzahl"] == 1)
    check("Filter nach Ordner, Unterordner eingeschlossen",
          sorted(m["name"] for m in k.modelle(ordner=f"{w1}/Haushalt")) == ["Arm umbenannt", "Welle", "kaputt"]
          and [m["name"] for m in k.modelle(ordner=f"{w1}/Drohne")] == ["Top_Plate"])
    check("Suche über den Feldindex von flatgraph, Teilwort, gross/klein egal",
          [m["name"] for m in k.modelle(suche="plate")] == ["Top_Plate"])
    check("Filter nach Tag über die Nachbarschaft", [m["name"] for m in k.modelle(tag="funktional")] == ["Arm umbenannt"])

    # -- Umbenennen wie im 3MF Katalog: auf der Platte, ohne zu überschreiben
    k.umbenennen(arm["id"], "Arm Front")
    check("Umbenennen benennt die Datei auf der Platte um, Endung bleibt",
          os.path.exists(os.path.join(sammlung, "Haushalt", "Arm Front.stl"))
          and not os.path.exists(os.path.join(sammlung, "Haushalt", "Arm umbenannt.stl")))
    muster.stl_binaer(os.path.join(sammlung, "Haushalt", "Belegt.stl"), 3, 3, 3)
    try:
        k.umbenennen(arm["id"], "Belegt")
        check("Umbenennen auf einen belegten Namen wird abgelehnt, nichts überschrieben", False)
    except KatalogFehler:
        check("Umbenennen auf einen belegten Namen wird abgelehnt, nichts überschrieben",
              os.path.getsize(os.path.join(sammlung, "Haushalt", "Belegt.stl")) == 684
              and os.path.exists(os.path.join(sammlung, "Haushalt", "Arm Front.stl")))

    # -- Löschen mit Vorschau, Papierkorb, Wiederherstellen
    top_id = top["id"]
    vorschau = k.loeschvorschau(top_id)
    check("Löschvorschau nennt die Datei-Knoten, die per Kaskade mitgehen",
          vorschau["knoten"] == [f"PART_GEOMETRY/{top['hash']}"])
    check("Löschvorschau nennt beide Dateien auf der Platte", len(vorschau["dateien"]) == 2)
    k.loeschen(top_id)
    check("Löschen: beide Dateien liegen im Papierkorb von partAtlas, nicht mehr im Ordner",
          not os.path.exists(os.path.join(sammlung, "Drohne", "Top_Plate.3mf"))
          and len(os.listdir(b.pfad("papierkorb"))) == 2)
    check("Löschen: Modell weg aus dem Katalog, sichtbar im Papierkorb",
          top_id not in [m["id"] for m in k.modelle()] and [m["id"] for m in k.modelle(ansicht="papierkorb")] == [top_id])
    # Der Anwender legt eine Kopie der gelöschten Datei zurück in den Ordner.
    kopie = os.path.join(sammlung, "Haushalt", "Top_Plate zurueck.3mf")
    shutil.copy(os.path.join(b.pfad("papierkorb"), sorted(os.listdir(b.pfad("papierkorb")))[0]), kopie)
    st = scannen()
    check("Scan holt ein gelöschtes Modell nicht still zurück, wenn seine Datei wieder auftaucht",
          st["im_papierkorb"] == 1 and st["neu"] == 1 and top_id not in [m["id"] for m in k.modelle()]
          and [m["name"] for m in k.modelle(suche="plate")] == [])
    os.remove(kopie)
    k.wiederherstellen(top_id)
    zurueck = k.modell(top_id)
    check("Wiederherstellen: Dateien zurück an ihrem Ort, Modell mit Tags wieder da",
          os.path.exists(os.path.join(sammlung, "Drohne", "Top_Plate.3mf"))
          and os.path.exists(os.path.join(downloads, "Top_Plate (1).3mf"))
          and len(zurueck["orte"]) == 2 and "mehrteilig" in zurueck["tags"])

    # -- Auftrag während eines Laufs: läuft danach nochmal
    # Der erste Lauf wird nach seiner Arbeit angehalten: so liegt die neue
    # Datei sicher hinter ihm, ohne auf Zeiten zu wetten.
    import threading
    halt, laeufe, echt = threading.Event(), [], s.lauf

    def lauf_mit_halt():
        echt()
        laeufe.append(1)
        if len(laeufe) == 1:
            halt.wait(30)
    s.lauf = lauf_mit_halt
    s.starten()
    while not laeufe:
        threading.Event().wait(0.01)
    muster.stl_binaer(os.path.join(sammlung, "Nachzuegler.stl"), 4, 4, 4)
    check("Zweiter Auftrag während eines Laufs wird angenommen, nicht verworfen", s.starten() is False)
    halt.set()
    s.warten(120)
    s.lauf = echt
    check("… und der Nachlauf findet die Datei, die der erste Lauf schon hinter sich hatte",
          "Nachzuegler" in [m["name"] for m in k.modelle()])

    # -- Nach Neustart ist alles da (flatgraph auf der Platte)
    neu_oeffnen()
    check("Nach Neustart: dieselben Modelle, Tags, Orte",
          sorted(m["name"] for m in k.modelle()) == ["Arm Front", "Belegt", "Haken", "Nachzuegler", "Top_Plate", "Welle", "kaputt"]
          and "funktional" in k.modell(arm["id"])["tags"])

    # -- Überschreiben: die Datei führt, der Container folgt
    def ueberschreiben(pfad, *masse):
        alt = os.stat(pfad).st_mtime
        muster.stl_binaer(pfad, *masse)
        os.utime(pfad, (alt + 10, alt + 10))   # sicher „geändert“, auch bei grober Zeitauflösung

    walze = os.path.join(sammlung, "Haushalt", "Schleifwalze.stl")
    muster.stl_binaer(walze, 30, 30, 60)
    scannen()
    w = next(m for m in k.modelle() if m["name"] == "Schleifwalze")
    k.tag_setzen(w["id"], "werkstatt")
    k.material_vorsehen(w["id"], "PETG")
    alt_hash = w["hash"]
    anzahl = len(k.modelle())
    ueberschreiben(walze, 30, 30, 62)
    scannen()
    neu = k.modell(w["id"])
    check("Überarbeitete Datei am selben Ort: derselbe Container mit Tags und Material, neuer Inhalt, kein zweites Modell",
          neu["hash"] != alt_hash and "werkstatt" in neu["tags"] and neu["material_herkunft"]["vorgesehen"] == ["PETG"]
          and abs(neu["masse"][2] - 62) < 0.01 and len(k.modelle()) == anzahl and not neu["fehlt"])
    check("… die Vorschau der alten Fassung ist weg, die neue gerendert",
          not os.path.exists(b.vorschau_pfad(alt_hash, "berechnet")) and os.path.exists(b.vorschau_pfad(neu["hash"], "berechnet")))
    muster.stl_binaer(os.path.join(sammlung, "Haushalt", "Schleifwalze alt.stl"), 30, 30, 60)
    scannen()
    check("Die alte Fassung taucht wieder auf: eigenes Modell, nicht als „im Papierkorb“ verschluckt",
          "Schleifwalze alt" in [m["name"] for m in k.modelle()] and k.modell(w["id"])["hash"] == neu["hash"])
    kopie_a, kopie_b = os.path.join(sammlung, "Haushalt", "Halter.stl"), os.path.join(sammlung, "Drohne", "Halter.stl")
    muster.stl_binaer(kopie_a, 11, 12, 13)
    shutil.copy(kopie_a, kopie_b)
    scannen()
    halter = next(m for m in k.modelle() if m["name"] == "Halter")
    ueberschreiben(kopie_a, 11, 12, 14)
    scannen()
    namen = [m["name"] for m in k.modelle()]
    check("Gibt es den alten Inhalt noch an einem anderen Ort: abgezweigte Kopie, eigenes Modell; das alte behält die andere",
          namen.count("Halter") == 2 and len(k.modell(halter["id"])["orte"]) == 1
          and k.modell(halter["id"])["orte"][0]["pfad"] == "Drohne/Halter.stl")

    # -- Bestand von vorher: bis 0.10 cache/vorschau/<h>.png, in 0.11 vault/vorschau/<h>.png mit `datei`
    from partatlas.katalog import Katalog
    alt = b.pfad("cache", "vorschau")
    os.makedirs(alt)
    h, h2 = arm["hash"], top["hash"]
    os.replace(b.vorschau_pfad(h, "berechnet"), os.path.join(alt, f"{h}.png"))
    os.replace(b.vorschau_pfad(h2, "extrahiert"), b.pfad("vault", "vorschau", f"{h2}.png"))
    b.db.update_node("PART_GEOMETRY", h, {"vorschau_berechnet": None})
    b.db.update_node("PART_GEOMETRY", h2, {"vorschau_extrahiert": None, "datei": f"vault/vorschau/{h2}.png"})
    Katalog(b)
    n1, n2 = (b.db.get_node(f"PART_GEOMETRY/{x}", readonly=True) for x in (h, h2))
    check("Bestand von vorher: Vorschauen aus cache/ und ohne Art im Namen ziehen um, Art aus dem Status, cache/ weg",
          os.path.exists(b.vorschau_pfad(h, "berechnet")) and os.path.exists(b.vorschau_pfad(h2, "extrahiert"))
          and n1["vorschau_berechnet"] == f"vault/vorschau/{h}.berechnet.png"
          and n2["vorschau_extrahiert"] == f"vault/vorschau/{h2}.extrahiert.png" and not n2.get("datei")
          and not os.path.exists(b.pfad("cache")))

    k.loeschen(top_id)
    n = k.papierkorb_leeren()
    check("Papierkorb leeren: endgültig, Datei und Vorschau weg", n == 1 and os.listdir(b.pfad("papierkorb")) == []
          and not os.path.exists(b.vorschau_pfad(top["hash"], "extrahiert")))
    b.schliessen()

    # -- Ein Arbeiter, der hart stirbt, reisst nicht den ganzen Lauf mit
    from partatlas.scan import Scanner as _S
    pruef = _S(None, None, prozesse=2)
    pruef._pool = pruef._neuer_pool()
    try:
        namen = [f"n{i}" for i in range(7)] + ["gift"] + [f"m{i}" for i in range(6)] + ["kaputt"]
        ergebnis = {k: (e, f) for k, e, f in pruef._verteilen([(n, (n,)) for n in namen], muster.arbeit_test)}
    finally:
        pruef._pool.shutdown(wait=False, cancel_futures=True)
    check("Arbeiter stirbt hart: nur diese Datei wird als Fehler gemeldet, alle anderen kommen durch",
          set(ergebnis) == set(namen) and ergebnis["gift"][0] is None and "Arbeitsprozess beendet" in ergebnis["gift"][1]
          and all(ergebnis[n] == (n * 2, None) for n in namen if n not in ("gift", "kaputt")))
    check("Eine Datei mit Ausnahme im Arbeiter wird ebenfalls einzeln gemeldet, der Lauf geht weiter",
          ergebnis["kaputt"][0] is None and "ValueError" in ergebnis["kaputt"][1])

    # -- Abbrechen: nichts geht verloren, der nächste Lauf macht weiter
    from partatlas import scan as _scan
    _scan.GRUPPE = 5                                   # sonst wäre ein Lauf mit 30 Dateien eine einzige Gruppe
    ab_tmp = tempfile.mkdtemp()
    ab_dir = os.path.join(ab_tmp, "viele")
    os.makedirs(ab_dir)
    for i in range(30):
        muster.stl_binaer(os.path.join(ab_dir, f"Teil_{i:02d}.stl"), 10 + i, 20, 30)
    ab_b = Bestand(os.path.join(ab_tmp, "bestand"))
    ab_k = Katalog(ab_b)
    ab_k.wurzel_hinzufuegen(ab_dir)
    nachrichten, ausgeloest = [], []

    def beobachter(st):
        nachrichten.append(dict(st))
        if st.get("phase") == "analysieren" and st.get("analysiert", 0) >= 5 and not ausgeloest:
            ausgeloest.append(None)                    # vorher eintragen: abbrechen() meldet selbst wieder
            ausgeloest[0] = ab_s.abbrechen()

    ab_s = Scanner(ab_b, ab_k, melden=beobachter, prozesse=2)
    check("Abbrechen ohne laufenden Scan ist wirkungslos und meldet das", ab_s.abbrechen() is False)
    ab_s.lauf()
    st = ab_s.status
    n_halb = len(ab_k.modelle())
    check("Abbrechen mitten im Einlesen: der Lauf endet als abgebrochen, nicht als fertig",
          ausgeloest == [True] and st["abgebrochen"] is True and st["phase"] == "abgebrochen" and st["laeuft"] is False)
    check("Abgebrochen: ein Teil ist angelegt, der Rest nicht, und die Zahl stimmt mit dem Katalog überein",
          0 < n_halb < 30 and st["neu"] == n_halb and st["bearbeitet"] == n_halb)
    check("Abgebrochen: keine Meldung „fertig“ und keine abgebrochene Phase ohne Dauer",
          not any(m.get("phase") == "fertig" for m in nachrichten) and st["dauer_s"] is not None)
    check("Abgebrochen: danach läuft weder das Entfernen verschwundener Orte noch die Vorschau-Phase an",
          not any(m.get("phase") == "vorschau" for m in nachrichten))
    ab_s.lauf()
    st = ab_s.status
    n_ende = len(ab_k.modelle())
    check("Der zweite Lauf vollendet das Einlesen: alle 30, keine Duplikate",
          st["phase"] == "fertig" and st["abgebrochen"] is False and n_ende == 30 and st["neu"] == 30 - n_halb)
    check("Der zweite Lauf holt die ausstehenden Vorschauen nach", ab_k.ausstehende_vorschauen() == [])

    # Abbruch schon beim Suchen: die Liste der gesehenen Orte ist unvollständig, also darf nichts als „weg“ gelten
    frueh = []

    def frueh_abbrechen(st):
        if st.get("phase") == "suchen" and not frueh:
            frueh.append(None)
            frueh[0] = ab_s2.abbrechen()

    ab_s2 = Scanner(ab_b, ab_k, melden=frueh_abbrechen, prozesse=2)
    ab_s2.lauf()
    check("Abbruch beim Suchen: alle 30 Modelle bleiben, keines gilt als fehlend",
          frueh == [True] and ab_s2.status["abgebrochen"] and len(ab_k.modelle()) == 30
          and ab_k.modelle(ansicht="fehlt") == [] and ab_s2.status["entfernt"] == 0)
    ab_b.schliessen()
    _scan.GRUPPE = 100

    # -- FreeCAD-Dokumente: mit Thumbnail ein Bild, ohne keines, und nie eine „ausstehende“ Vorschau, die nie kommt
    fc_tmp = tempfile.mkdtemp()
    fc_dir = os.path.join(fc_tmp, "cad")
    os.makedirs(fc_dir)
    muster.fcstd(os.path.join(fc_dir, "mit_bild.FCStd"))
    muster.fcstd(os.path.join(fc_dir, "ohne_bild.FCStd"), thumbnail=False)
    fc_b = Bestand(os.path.join(fc_tmp, "bestand"))
    fc_k = Katalog(fc_b)
    fc_k.wurzel_hinzufuegen(fc_dir)
    fc_s = Scanner(fc_b, fc_k, prozesse=2)
    fc_s.lauf()
    fc = {m["name"]: m for m in fc_k.modelle()}
    check("FCStd im Scan: mit Thumbnail „eingebettet“, ohne „keine“, nichts bleibt ausstehend",
          sorted(fc) == ["mit_bild", "ohne_bild"] and fc["mit_bild"]["vorschau"] == "eingebettet"
          and fc["ohne_bild"]["vorschau"] == "keine" and fc_k.ausstehende_vorschauen() == []
          and fc_s.status["vorschauen_offen"] == 0)
    fc_b.schliessen()

    muster.ende()
