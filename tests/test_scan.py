"""Scan und Katalog: was der Anwender mit seinen Ordnern tut, muss der
Katalog richtig nachvollziehen — ohne Duplikate, ohne Verlust."""
import os
import time
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
    thumb_dir = b.pfad("thumbs")
    klein_pfad = b.vorschau_pfad(alle["Arm_Front_v2"]["hash"], "berechnet")
    check("Die Vorschauen von partAtlas sind schon klein (320 px, wenige KB): sie werden ohne Umweg ausgeliefert, es entsteht keine zweite Fassung",
          b.thumb(klein_pfad) == klein_pfad and (not os.path.isdir(thumb_dir) or not os.listdir(thumb_dir))
          and st.get("thumbs_gesamt") == 0 and st.get("thumbs_fertig") == 0)
    from PIL import Image as _Img
    gross_pfad = b.pfad("vault", "bilder", "gross_test.png")
    os.makedirs(os.path.dirname(gross_pfad), exist_ok=True)
    _Img.effect_noise((900, 900), 40).convert("RGB").save(gross_pfad, "PNG")
    thumb_gross = b.thumb(gross_pfad)
    check("Ein grosses Bild wird weiterhin verkleinert (WebP in thumbs/) und beim zweiten Abruf nicht neu erzeugt",
          thumb_gross.endswith(".webp") and os.path.dirname(thumb_gross) == thumb_dir and b.thumb(gross_pfad) == thumb_gross
          and len(os.listdir(thumb_dir)) == 1)
    os.remove(gross_pfad)
    # Die Thumbs-Phase fasst kleine PNGs nicht an (kostete bei 9 000 Bildern 3 s je Lauf), baut aber grosse vor
    for _n in os.listdir(thumb_dir):             # Reste des Tests davor
        os.remove(os.path.join(thumb_dir, _n))
    os.makedirs(b.pfad("vault", "bilder"), exist_ok=True)
    gross2 = b.pfad("vault", "bilder", "gross_vorbauen.png")
    _Img.effect_noise((900, 900), 40).convert("RGB").save(gross2, "PNG")
    tp = Scanner(b, k, prozesse=2)
    tp._pool = tp._neuer_pool()
    try:
        tp._thumbs()
    finally:
        tp._pool.shutdown(wait=False, cancel_futures=True)
    check("Die Thumbs-Phase baut nur vor, was sich verkleinern lässt: ein grosses Bild ja, die kleinen Vorschauen nicht (gesamt 1, fertig 1)",
          tp.status.get("thumbs_gesamt") == 1 and tp.status.get("thumbs_fertig") == 1 and len(os.listdir(thumb_dir)) == 1)
    os.remove(gross2)
    for _n in os.listdir(thumb_dir):
        os.remove(os.path.join(thumb_dir, _n))
    check("Bilanz für den Einlesen-Dialog: Laufnummer, geprüft x von y, je Format, Bilder aus der Datei, Dauer des Einlesens",
          st["lauf"] == 1 and st["geprueft"] == st["zu_pruefen"] == 5 and st["analysiert"] == st["zu_analysieren"] == 5
          and st["je_format"] == {"stl": 1, "3mf": 2, "obj": 1, "step": 1} and st["aus_datei"] == 1
          and st["einlesen_s"] is not None and st["vorschauen_gesamt"] == 2 and st["vorschauen_offen"] == 0 and st["kopien"] == 0)
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
    check("Löschen: die Dateien bleiben, wo sie sind — partAtlas löscht und verschiebt nichts; der Papierkorb von partAtlas bleibt leer",
          os.path.exists(os.path.join(sammlung, "Drohne", "Top_Plate.3mf"))
          and os.path.exists(os.path.join(downloads, "Top_Plate (1).3mf")) and os.listdir(b.pfad("papierkorb")) == [])
    check("Löschen: Modell weg aus dem Katalog, sichtbar im Papierkorb",
          top_id not in [m["id"] for m in k.modelle()] and [m["id"] for m in k.modelle(ansicht="papierkorb")] == [top_id])
    st = scannen()
    check("Scan nach dem Löschen: die im Ordner gebliebenen Dateien kommen weder neu noch zurück (und werden nicht neu gelesen)",
          st["im_papierkorb"] == 2 and st["zurueckgeholt"] == 0 and [m["name"] for m in k.modelle(suche="plate")] == []
          and top_id not in [m["id"] for m in k.modelle()])
    k.wiederherstellen(top_id)
    zurueck = k.modell(top_id)
    check("Wiederherstellen: Dateien zurück an ihrem Ort, Modell mit Tags wieder da",
          os.path.exists(os.path.join(sammlung, "Drohne", "Top_Plate.3mf"))
          and os.path.exists(os.path.join(downloads, "Top_Plate (1).3mf"))
          and len(zurueck["orte"]) == 2 and "mehrteilig" in zurueck["tags"])

    # Modell entfernen, Datei bleibt: der Scan lässt sie in Ruhe; „Wiederherstellen“ nimmt das Modell wieder auf
    extra_pfad = os.path.join(sammlung, "Haushalt", "Extra.stl")
    muster.stl_binaer(extra_pfad, 31, 12, 13)
    scannen()
    extra = {m["name"]: m for m in k.modelle()}["Extra"]
    extra_tags = k.modell(extra["id"])["tags"]
    k.loeschen(extra["id"])
    st = scannen()
    check("Entferntes Modell: die Datei liegt noch im Ordner und wird nicht noch einmal aufgenommen",
          st["im_papierkorb"] == 1 and st["neu"] == 0 and extra["id"] not in [m["id"] for m in k.modelle()]
          and os.path.exists(extra_pfad) and [m["id"] for m in k.modelle(ansicht="papierkorb")] == [extra["id"]])
    k.wiederherstellen(extra["id"])
    check("Wiederherstellen nimmt das Modell mit Tags wieder auf, an dem Ort, wo die Datei geblieben ist",
          k.modell(extra["id"])["tags"] == extra_tags and [o["absolut"] for o in k.modell(extra["id"])["orte"]] == [extra_pfad])
    # Ein Modell, das eine frühere Fassung in den Papierkorb von partAtlas verschoben hat (Datei weg aus dem Ordner): kommt die Datei
    # zurück, kommt das Modell zurück.
    h = k.datei_von(extra["id"])
    alt = os.path.join(b.pfad("papierkorb"), f"{h[:12]}__Extra.stl")
    shutil.move(extra_pfad, alt)
    with b.db.transaction():
        b.db.update_node("PART_GEOMETRY", h, {"orte": [], "papierkorb": [{"wurzel": w1, "pfad": "Haushalt/Extra.stl",
                                                                          "ablage": os.path.relpath(alt, b.wurzel)}], "geloescht": "alt"})
        b.db.soft_delete("MODEL_ASSET", extra["id"])
    shutil.copy(alt, extra_pfad)
    st = scannen()
    check("Altes Löschen (Datei im Papierkorb von partAtlas): legt der Anwender sie zurück, kommt das Modell zurück, die Kopie entfällt",
          st["zurueckgeholt"] == 1 and st["neu"] == 0 and extra["id"] in [m["id"] for m in k.modelle()]
          and k.modell(extra["id"])["tags"] == extra_tags and os.listdir(b.pfad("papierkorb")) == [])
    k.loeschen(extra["id"])
    os.remove(extra_pfad)                      # aufräumen (der Test, nicht partAtlas): die späteren Prüfungen kennen dieses Modell nicht

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
    check("Modell entfernt: Vorschau und Eintrag bleiben, es lässt sich jederzeit wiederherstellen; nichts wird endgültig gelöscht",
          os.path.exists(b.vorschau_pfad(top["hash"], "extrahiert")) and top_id in [m["id"] for m in k.modelle(ansicht="papierkorb")])
    check("Es gibt keinen Weg, den Papierkorb endgültig zu leeren: der Müllsammler räumte auch entfernte Ordner, Baugruppen und Drucke ab",
          not hasattr(k, "papierkorb_leeren"))
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

    # -- Eine Datei, die hängt, hält den Lauf nicht auf
    pid_datei = os.path.join(tempfile.mkdtemp(), "pids")
    os.environ["MUSTER_PID_DATEI"] = pid_datei         # die Arbeiter erben es beim Start
    hz = _S(None, None, prozesse=2, zeitgrenze=3)
    hz._pool = hz._neuer_pool()
    try:
        namen = [f"n{i}" for i in range(5)] + ["haengt"] + [f"m{i}" for i in range(3)]
        t0 = time.time()
        ergebnis = {k: (e, f) for k, e, f in hz._verteilen([(n, (n,)) for n in namen], muster.arbeit_test)}
        dauer = time.time() - t0
        time.sleep(1)
        pids = [int(x) for x in open(pid_datei).read().split()]
    finally:
        hz._pool.shutdown(wait=False, cancel_futures=True)
    check("Hängende Datei: nur sie wird als Fehler mit Zeitgrenze gemeldet, alle anderen kommen durch",
          set(ergebnis) == set(namen) and ergebnis["haengt"][0] is None and "Zeitgrenze" in ergebnis["haengt"][1]
          and all(ergebnis[n] == (n * 2, None) for n in namen if n != "haengt"))
    check("Hängende Datei: der Lauf endet nach wenigen Zeitgrenzen, nicht erst nach dem Hänger (600 s)", dauer < 60)
    def _lebt(pid):
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    check("Hängende Datei: der hängende Arbeitsprozess wird beendet, er läuft nicht weiter",
          pids and not any(_lebt(p) for p in pids))

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

    # -- STEP über FreeCAD: Netz, Maße und Vorschau im Hintergrund; ein Fehler betrifft nur seine Datei
    import sys
    from partatlas import cad as _cad
    from partatlas import scan as _scan2
    attrappe = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "cad_attrappe.py")]
    st_tmp = tempfile.mkdtemp()
    st_dir = os.path.join(st_tmp, "cad")
    os.makedirs(st_dir)
    muster.step(os.path.join(st_dir, "Halter.step"))
    muster.step(os.path.join(st_dir, "kaputt.step"))
    with open(os.path.join(st_dir, "kaputt.step"), "a") as f:
        f.write("/* anderer Inhalt: gleiche Dateien wären nur ein Modell mit zwei Orten */\n")
    st_log = os.path.join(st_tmp, "starts.log")
    os.environ["CAD_ATTRAPPE_LOG"] = st_log
    st_b = Bestand(os.path.join(st_tmp, "bestand"))
    st_k = Katalog(st_b)
    st_k.wurzel_hinzufuegen(st_dir)
    _vorher = _scan2.programme.programm_fuer
    _scan2.programme.programm_fuer = lambda *a, **kw: None       # kein echtes FreeCAD des Rechners starten

    st_s = Scanner(st_b, st_k, prozesse=2)
    st_s.lauf()
    d1 = {m["name"]: m for m in st_k.modelle()}
    check("STEP ohne FreeCAD: aufgenommen, bleibt ausstehend, der Lauf sagt es, nichts bricht",
          st_s.status["phase"] == "fertig" and st_s.status["cad_ohne_freecad"] == 2 and len(st_k.ausstehende_cad()) == 2
          and d1["Halter"]["cad"] == "ausstehend" and not os.path.exists(st_b.netz_pfad(d1["Halter"]["hash"])))

    check("Lauf meldet früh, was FreeCAD bekommt (Schritt-Anzeige: „Danach: FreeCAD für 2 Dateien“), und wie lange die Phase schon läuft (Restzeit-Schätzung)",
          st_s.status.get("cad_voraus") == 2 and isinstance(st_s.status.get("phase_s"), float))

    st_s = Scanner(st_b, st_k, prozesse=2, cad_befehl=attrappe)
    st_s.lauf()
    phasen = list(st_s.status["phasen"])          # Reihenfolge der Phasen in diesem Lauf (FreeCAD hat zu tun)
    d2 = {m["name"]: m for m in st_k.modelle()}
    check("STEP mit FreeCAD, beim nächsten Lauf: Maße und berechnete Vorschau stehen da, das Netz liegt im Bestand",
          d2["Halter"]["cad"] == "ok" and d2["Halter"]["vorschau"] == "gerendert" and d2["Halter"]["masse"] is not None
          and os.path.exists(st_b.netz_pfad(d2["Halter"]["hash"])) and os.path.exists(st_b.vorschau_pfad(d2["Halter"]["hash"], "berechnet")))
    check("STEP: die Datei, an der FreeCAD scheitert, ist als Fehler vermerkt und hält die andere nicht auf",
          d2["kaputt"]["cad"] == "fehler" and d2["kaputt"]["vorschau"] == "keine" and st_k.ausstehende_cad() == [])
    st_s.lauf()
    check("Die kleinen Bilder kommen vor FreeCAD (das dauert bei einer grossen Library Stunden), danach nochmal für das Neue",
          "thumbs" in phasen and "cad" in phasen and phasen.index("thumbs") < phasen.index("cad"))
    check("STEP: ein weiterer Lauf startet FreeCAD nicht noch einmal, auch nicht für die gescheiterte Datei",
          open(st_log).read().count("start") == 1)
    check("STEP: der Grund des Scheiterns steht am Modell, und „erneut versuchen“ setzt nur die gescheiterten zurück",
          "kaputt" in (st_k.modell(d2["kaputt"]["id"])["cad_fehler"] or "") and st_k.cad_erneut() == 1
          and {m["name"]: m for m in st_k.modelle()}["kaputt"]["cad"] == "ausstehend"
          and {m["name"]: m for m in st_k.modelle()}["Halter"]["cad"] == "ok")
    st_k.loeschen(d2["Halter"]["id"])
    check("STEP: beim Entfernen des Modells bleibt sein Netz liegen (es kann zurückkommen)",
          os.path.exists(st_b.netz_pfad(d2["Halter"]["hash"])))
    _scan2.programme.programm_fuer = _vorher
    st_b.schliessen()

    # -- Mehrere Läufe hintereinander (jede hochgeladene Datei stösst einen an) zählen als ein Einlesen
    ke_tmp = tempfile.mkdtemp()
    ke_dir = os.path.join(ke_tmp, "hoch")
    os.makedirs(ke_dir)
    for i in range(3):
        muster.stl_binaer(os.path.join(ke_dir, f"Erste_{i}.stl"), 10 + i, 20, 30)
    ke_b = Bestand(os.path.join(ke_tmp, "bestand"))
    ke_k = Katalog(ke_b)
    ke_k.wurzel_hinzufuegen(ke_dir)
    ke_zahl = []

    def ke_melden(st):
        # Am Ende des ersten Laufs kommen vier weitere Dateien und ein Folgelauf wird vorgemerkt — wie beim Hochladen mehrerer Dateien.
        if st.get("phase") == "fertig" and not ke_zahl:
            ke_zahl.append(1)
            for i in range(4):
                muster.stl_binaer(os.path.join(ke_dir, f"Zweite_{i}.stl"), 30 + i, 20, 30)
            ke_s._nochmal = True

    ke_s = Scanner(ke_b, ke_k, melden=ke_melden, prozesse=2)
    ke_s._lauf_sicher()
    check("Zwei Läufe hintereinander: die Zeile zeigt alle neuen Dateien (3 + 4), nicht nur die des letzten Laufs",
          ke_s.status["lauf"] == 2 and ke_s.status["neu"] == 7 and ke_s.status["gefunden"] == 7)
    check("Zwei Läufe hintereinander: die Dauer zählt beide, die Formate auch",
          ke_s.status["dauer_s"] >= ke_s.status["einlesen_s"] and sum(ke_s.status["je_format"].values()) == 7)
    ke_b.schliessen()

    # -- Hintergrundlauf: die Warteschlange der Vorschaubilder hängt nicht am Einlesen der Ordner
    hg_tmp = tempfile.mkdtemp()
    hg_dir = os.path.join(hg_tmp, "teile")
    os.makedirs(hg_dir)
    for i in range(6):
        muster.stl_binaer(os.path.join(hg_dir, f"Teil_{i}.stl"), 10 + i, 20, 30)
    hg_b = Bestand(os.path.join(hg_tmp, "bestand"))
    hg_k = Katalog(hg_b)
    hg_k.wurzel_hinzufuegen(hg_dir)
    hg_s = Scanner(hg_b, hg_k, prozesse=2)
    hg_s.lauf()
    check("Nach dem Einlesen ist nichts offen", not hg_s.hat_offenes())
    hg_modelle = hg_k.modelle()
    for m_ in hg_modelle[:4]:                    # vier Bilder gehen „verloren“: Zustand wie nach einem Abbruch oder Neustart mitten im Rechnen
        hg_b.db.update_node("PART_GEOMETRY", m_["hash"], {"vorschau": "ausstehend"})
        os.remove(hg_b.vorschau_pfad(m_["hash"], "berechnet"))
    muster.stl_binaer(os.path.join(hg_dir, "Neu_nach_dem_Einlesen.stl"), 50, 20, 30)
    check("Ausstehende Vorschaubilder stehen in der Warteschlange (überstehen einen Neustart: sie stehen im Bestand)", hg_s.hat_offenes())
    hg_s2 = Scanner(hg_b, hg_k, prozesse=2)       # wie nach einem Neustart: ein frischer Scanner
    hg_s2.lauf(nur_cad=True)
    check("Der Hintergrundlauf rechnet die offenen Bilder, ohne die Ordner zu durchsuchen: die neue Datei im Ordner kommt nicht dazu",
          all(os.path.exists(hg_b.vorschau_pfad(m_["hash"], "berechnet")) for m_ in hg_modelle[:4]) and not hg_s2.hat_offenes()
          and "Neu_nach_dem_Einlesen" not in {m_["name"] for m_ in hg_k.modelle()} and "suchen" not in hg_s2.status["phasen"])
    # Bilder nach und nach: Ergebnisse nicht erst nach GRUPPE Stück festhalten, sondern alle SPEICHERN_ALLE_S Sekunden
    for m_ in hg_modelle[:4]:
        hg_b.db.update_node("PART_GEOMETRY", m_["hash"], {"vorschau": "ausstehend"})
    gespeichert = []
    hg_s3 = Scanner(hg_b, hg_k, prozesse=1)
    _orig_sp = hg_s3._vorschauen_speichern
    hg_s3._vorschauen_speichern = lambda st: (gespeichert.append(len(st)), _orig_sp(st))[1]
    _g, _t = _scan.GRUPPE, _scan.SPEICHERN_ALLE_S
    _scan.GRUPPE, _scan.SPEICHERN_ALLE_S = 1000, 0.0
    try:
        hg_s3.lauf(nur_cad=True)
    finally:
        _scan.GRUPPE, _scan.SPEICHERN_ALLE_S = _g, _t
    check("Vorschaubilder werden nach und nach festgehalten, nicht in einem Schub am Ende (4 Bilder, grosse Gruppe, 0 s Abstand: mehrere Speicherungen)",
          len(gespeichert) >= 2 and sum(gespeichert) == 4)
    hg_b.schliessen()

    # -- FreeCAD bekommt die kleinen Dateien zuerst (frühe Bilder, ehrliche Restzeit, die grossen mit dem Hänger-Risiko am Ende)
    gr_tmp = tempfile.mkdtemp()
    gr_dir = os.path.join(gr_tmp, "cad")
    os.makedirs(gr_dir)
    for n, pad in (("a_gross.step", 5000), ("b_klein.step", 10), ("c_mittel.step", 1000)):
        muster.step(os.path.join(gr_dir, n))
        with open(os.path.join(gr_dir, n), "a") as f:
            f.write("/*" + n + "*/" + "x" * pad + "\n")
    gr_b = Bestand(os.path.join(gr_tmp, "bestand"))
    gr_k = Katalog(gr_b)
    gr_k.wurzel_hinzufuegen(gr_dir)
    _scan2.programme.programm_fuer = lambda *a, **kw: None
    reihenfolge = []
    _umw = _scan2.cad.umwandeln
    _scan2.cad.umwandeln = lambda befehl, aufgaben, stopp, ordner: (reihenfolge.extend(os.path.basename(q) for _, q, _ in aufgaben), iter(()))[1]
    try:
        Scanner(gr_b, gr_k, prozesse=2, cad_befehl=attrappe).lauf()
    finally:
        _scan2.cad.umwandeln = _umw
        _scan2.programme.programm_fuer = _vorher
    check("FreeCAD-Aufträge nach Grösse aufsteigend, nicht in Datenbankreihenfolge", reihenfolge == ["b_klein.step", "c_mittel.step", "a_gross.step"])
    gr_b.schliessen()

    # -- Arbeiter laufen mit niedriger Priorität (die Oberfläche bleibt bedienbar, solange eingelesen wird)
    pr = _S(None, None, prozesse=1)
    pr._pool = pr._neuer_pool()
    try:
        nice_werte = [e for _, e, _ in pr._verteilen([("a", ("a",))], muster.arbeit_nice)]
    finally:
        pr._pool.shutdown(wait=False, cancel_futures=True)
    check("Arbeitsprozess startet mit niedriger Priorität (nice > 0)", nice_werte and nice_werte[0] > os.nice(0))

    # -- FCStd über FreeCAD nur nach Zusage des Anwenders (ein Dokument kann Programmcode mitbringen)
    fz_tmp = tempfile.mkdtemp()
    fz_dir = os.path.join(fz_tmp, "cad")
    os.makedirs(fz_dir)
    muster.fcstd(os.path.join(fz_dir, "Gehaeuse.FCStd"))
    fz_b = Bestand(os.path.join(fz_tmp, "bestand"))
    fz_k = Katalog(fz_b)
    fz_k.wurzel_hinzufuegen(fz_dir)
    fz = lambda: {m["name"]: m for m in fz_k.modelle()}["Gehaeuse"]
    fz_s = Scanner(fz_b, fz_k, prozesse=2, cad_befehl=attrappe)
    fz_s.lauf()
    check("FCStd ohne Antwort des Anwenders: FreeCAD lädt es nicht, die Oberfläche soll fragen",
          fz_s.status["fcstd_frage"] == 1 and fz()["cad"] == "ausstehend" and not os.path.exists(fz_b.netz_pfad(fz()["hash"])))
    fz_b.einstellungen_setzen(fcstd_freecad="nein")
    fz_s.lauf()
    check("FCStd mit „Nein“: wird nicht geladen und es wird nicht erneut gefragt",
          fz_s.status["fcstd_frage"] == 0 and fz()["cad"] == "ausstehend")
    fz_b.einstellungen_setzen(fcstd_freecad="ja")
    muster.stl_binaer(os.path.join(fz_dir, "Neu.stl"), 16, 12, 13)
    fz_s.lauf(nur_cad=True)
    check("Nach der Zusage läuft nur die FreeCAD-Umwandlung: eine neue Datei im Ordner wird dabei nicht eingelesen",
          fz_s.status["nur_cad"] is True and fz_s.status["phase"] == "fertig" and "Neu" not in {m["name"] for m in fz_k.modelle()})
    fz_s.lauf()
    d = fz_k.db.get_node(f"PART_GEOMETRY/{fz()['hash']}", readonly=True)
    check("FCStd mit „Ja“: Netz, Maße und berechnetes Vorschaubild; das schärfere Bild steht vor dem Thumbnail aus der Datei",
          fz()["cad"] == "ok" and fz()["masse"] is not None and os.path.exists(fz_b.netz_pfad(fz()["hash"]))
          and [a for a, _ in fz_k.vorschauen(d)] == ["berechnet", "extrahiert"])
    fz_b.schliessen()

    # -- STEP und FCStd im selben Ordner (gemeldet 03.10.): die Frage kommt, bevor FreeCAD überhaupt startet — nicht erst nach der
    #    STEP-Umwandlung. Wer gleich antwortet, bekommt die FCStd im selben Lauf.
    sf_tmp = tempfile.mkdtemp()
    sf_dir = os.path.join(sf_tmp, "cad")
    os.makedirs(sf_dir)
    muster.step(os.path.join(sf_dir, "Halter.step"))
    muster.fcstd(os.path.join(sf_dir, "Gehaeuse.FCStd"))
    sf_b = Bestand(os.path.join(sf_tmp, "bestand"))
    sf_k = Katalog(sf_b)
    sf_k.wurzel_hinzufuegen(sf_dir)
    sf_ablauf = []

    def sf_melden(st):
        if st.get("fcstd_frage") and "frage" not in sf_ablauf:
            sf_ablauf.append("frage")
            sf_b.einstellungen_setzen(fcstd_freecad="ja")       # der Anwender antwortet sofort
        if st.get("phase") == "cad" and "cad" not in sf_ablauf:
            sf_ablauf.append("cad")
    sf_s = Scanner(sf_b, sf_k, melden=sf_melden, prozesse=2, cad_befehl=attrappe)
    sf_s.lauf()
    sf = {m["name"]: m for m in sf_k.modelle()}
    check("STEP und FCStd: die Frage kommt vor dem ersten FreeCAD-Start; mit sofortigem „Ja“ ist die FCStd im selben Lauf umgewandelt",
          sf_ablauf == ["frage", "cad"] and sf["Gehaeuse"]["cad"] == "ok" and sf["Halter"]["cad"] == "ok")
    sf_b.schliessen()

    # -- Bilanz: inhaltsgleiche neue Dateien zählen als Kopien (die Übersicht nannte sie als Dateien, die Bilanz als ein Modell)
    kp_tmp = tempfile.mkdtemp()
    os.makedirs(os.path.join(kp_tmp, "s", "b"))
    for rel in ("A.stl", "b/A_Kopie.stl", "b/A_nochmal.stl"):
        muster.stl_binaer(os.path.join(kp_tmp, "s", rel), 10, 11, 12)
    muster.stl_binaer(os.path.join(kp_tmp, "s", "B.stl"), 13, 11, 12)
    kp_b = Bestand(os.path.join(kp_tmp, "bestand"))
    kp_k = Katalog(kp_b)
    kp_k.wurzel_hinzufuegen(os.path.join(kp_tmp, "s"))
    kp_s = Scanner(kp_b, kp_k, prozesse=2)
    kp_s.lauf()
    check("Bilanz: vier Dateien, zwei Modelle, zwei Kopien", kp_s.status["gefunden"] == 4 and kp_s.status["neu"] == 2
          and kp_s.status["kopien"] == 2)
    kp_b.schliessen()

    # -- Folgelauf: „nur FreeCAD“ während eines Laufs bleibt „nur FreeCAD“ (nach der FCStd-Zusage las er sonst alles neu ein)
    import threading as _th
    fl_tmp = tempfile.mkdtemp()
    os.makedirs(os.path.join(fl_tmp, "s"))
    muster.stl_binaer(os.path.join(fl_tmp, "s", "A.stl"), 10, 11, 12)
    fl_b = Bestand(os.path.join(fl_tmp, "bestand"))
    fl_k = Katalog(fl_b)
    fl_k.wurzel_hinzufuegen(os.path.join(fl_tmp, "s"))
    frei, meldungen = _th.Event(), []

    def fl_melden(st):
        meldungen.append(dict(st))
        if st.get("phase") == "suchen":
            frei.wait(10)                     # der erste Lauf wartet, bis die Aufträge gestellt sind

    def laeufe():
        # je Lauf: ganz („suchen“) oder nur FreeCAD; gezählt an der Fertig-Meldung
        return ["cad" if x.get("nur_cad") else "ganz" for v, x in zip([{"phase": "fertig"}] + meldungen, meldungen)
                if x.get("phase") == "fertig" and v.get("phase") != "fertig"]

    fl_s = Scanner(fl_b, fl_k, melden=fl_melden, prozesse=2)
    fl_s.starten()
    gestartet = fl_s.starten(nur_cad=True)
    frei.set()
    fl_s.warten(60)
    check("„Nur FreeCAD“ während eines Laufs: danach folgt nur die Umwandlung, kein zweites ganzes Einlesen",
          gestartet is False and laeufe() == ["ganz", "cad"])
    meldungen.clear()
    frei.clear()
    fl_s.starten()
    fl_s.starten(nur_cad=True)
    fl_s.starten()
    fl_s.starten(nur_cad=True)
    frei.set()
    fl_s.warten(60)
    check("Ganz und „nur FreeCAD“ gewünscht: ein ganzer Folgelauf, der die Umwandlung einschliesst — nicht zwei",
          laeufe() == ["ganz", "ganz"])
    fl_b.schliessen()

    muster.ende()
