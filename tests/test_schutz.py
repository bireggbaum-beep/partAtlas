"""Datensicherheit (KONZEPT §3.3): partAtlas löscht keine Datei des Anwenders, entfernt keine Katalogdaten endgültig, sichert vor
Massenaktionen und hält einen nicht erreichbaren Ordner nicht für leer.

Der Wächter oben vergleicht jeden Aufruf, der löscht, verschiebt oder ersetzt, mit einer Liste samt Begründung. Wer einen neuen
schreibt, lässt diese Suite fallen und muss hier begründen, warum er nichts gefährdet. Darunter prüft die Suite das Verhalten."""
import io
import os
import shutil
import tempfile
import time
import zipfile

import muster
from muster import check
from schutz_inventur import inventur

# (Datei, Funktion, Aufruf) → warum das nichts des Anwenders gefährdet
ERLAUBT = {
    ("bestand.py", "Bestand.entfernen", "os.unlink"): "der einzige Löschweg; verweigert alles ausserhalb des Bestands",
    ("bestand.py", "Bestand.thumb", "os.remove"): "eigene Arbeitsdatei neben dem Thumb (thumbs/ im Bestand)",
    ("bestand.py", "Bestand.thumb", "os.replace"): "Thumb im Bestand fertig ablegen",
    ("bestand.py", "Bestand.einstellungen_setzen", "schreibe_atomar"): "einstellungen.json im Bestand",
    ("cad.py", "_stapel", "shutil.rmtree"): "Arbeitsordner eines FreeCAD-Stapels unter arbeit/cad im Bestand",
    ("dateien.py", "_kopiere_ohne_ueberschreiben", "os.replace"): "eigene Arbeitsdatei → Ziel, nur wenn das Ziel frei ist",
    ("dateien.py", "_kopiere_ohne_ueberschreiben", "os.unlink"): "eigene Arbeitsdatei (.…arbeit), eben angelegt",
    ("dateien.py", "neu_anlegen", "os.replace"): "eigene Arbeitsdatei → neues Ziel, nur wenn es frei ist",
    ("dateien.py", "neu_anlegen", "os.unlink"): "eigene Arbeitsdatei (.…arbeit), eben angelegt",
    ("dateien.py", "schreibe_atomar", "os.replace"): "ersetzt ein Ziel — nur von den unten erlaubten Aufrufern, alle im Bestand",
    ("dateien.py", "schreibe_atomar", "os.unlink"): "eigene Arbeitsdatei (.…arbeit), eben angelegt",
    ("dateien.py", "verschiebe", "os.unlink"): "Quelle eines Verschiebens, erst nach sicherer Kopie (über Dateisystemgrenzen)",
    ("eigene.py", "Eigene.datei_setzen", "dateien.schreibe_atomar"): "Kopie der Konstruktionsdatei einer Eigenen Komponente in vault/komponenten, "
        "nur wenn es sie dort noch nicht gibt",
    ("katalog.py", "Katalog._archivieren", "dateien.verschiebe"): "eigenes Bild oder Datei aus dem alten Papierkorb → vault_archive/, nie weg",
    ("katalog.py", "Katalog.endgueltig_entfernen", "self.db.purge"): "ein Modell aus dem Papierkorb mit genau seiner Kaskade (flatgraph "
        "purge), auf Wunsch je Modell mit Tippbestätigung, vorher eine Sicherung; nie der ganze Papierkorb",
    ("katalog.py", "Katalog._vault_nachziehen", "os.replace"): "Vorschau aus alter Ablage im Bestand in die neue, nur wenn das Ziel fehlt",
    ("katalog.py", "Katalog._vault_nachziehen", "os.rmdir"): "leerer Ordner cache/ der alten Ablage im Bestand",
    ("katalog.py", "Katalog._zurueck", "dateien.verschiebe"): "macht ein gescheitertes Verschieben rückgängig",
    ("katalog.py", "Katalog.umbenennen", "dateien.verschiebe"): "auf Wunsch des Anwenders, nie überschreibend",
    ("katalog.py", "Katalog.verschieben", "dateien.verschiebe"): "auf Wunsch des Anwenders, nie überschreibend",
    ("katalog.py", "Katalog.wiederherstellen", "dateien.verschiebe"): "Datei aus dem alten Papierkorb von partAtlas zurück an ihren Ort",
    ("katalog.py", "Katalog.bild_ablegen", "dateien.schreibe_atomar"): "eigenes Bild in vault/bilder, nur wenn es noch nicht da ist",
    ("scan.py", "Worker._cad", "os.replace"): "Netz aus FreeCAD arbeit/cad → netz/ im Bestand",
    ("scan.py", "_analyse", "dateien.schreibe_atomar"): "Vorschau aus der Datei in vault/vorschau",
    ("scan.py", "_rendern", "dateien.schreibe_atomar"): "berechnete Vorschau in vault/vorschau",
    ("scan.py", "_cad_bild", "dateien.schreibe_atomar"): "berechnete Vorschau in vault/vorschau",
    ("sicherung.py", "_aufraeumen", "shutil.rmtree"): "alte Sicherung unter sicherungen/ (die neuesten 20 und je Tag eine bleiben)",
    ("sicherung.py", "sichern", "os.replace"): "fertige Sicherung an ihren Namen",
    ("sicherung.py", "zurueckholen", "os.replace"): "jetzige Datenbank beiseite nach arbeit/, nicht gelöscht",
}

if __name__ == "__main__":
    # -- Wächter
    funde = inventur()
    neu = sorted(funde - set(ERLAUBT))
    weg = sorted(set(ERLAUBT) - funde)
    if neu:
        print("Nicht begründet:", *neu, sep="\n  ")
    check("Jeder Aufruf, der löscht, verschiebt oder ersetzt, steht mit Begründung in ERLAUBT", not neu)
    check("ERLAUBT nennt nichts, was es nicht mehr gibt (die Liste bleibt genau)", not weg)
    check("Nichts ruft den Müllsammler von flatgraph auf (er räumte alles Gelöschte auf einmal ab)",
          not any("run_garbage_collection" in f[2] for f in funde))

    from partatlas import sicherung
    from partatlas.bestand import Bestand
    from partatlas.katalog import Katalog, KatalogFehler
    from partatlas.scan import Scanner
    import flatgraph

    tmp = tempfile.mkdtemp()
    sammlung = os.path.join(tmp, "Sammlung")
    os.makedirs(os.path.join(sammlung, "Teile"))
    for i, n in enumerate(("A", "B", "C")):
        muster.stl_binaer(os.path.join(sammlung, "Teile", f"{n}.stl"), 10 + i, 12, 13)
    b = Bestand(os.path.join(tmp, "bestand"))
    k = Katalog(b)
    w = k.wurzel_hinzufuegen(sammlung)
    s = Scanner(b, k, prozesse=2)
    s.lauf()

    # -- Löschen nur im Bestand
    fremd = os.path.join(tmp, "fremd.txt")
    open(fremd, "w").write("gehört dem Anwender")
    try:
        b.entfernen(fremd)
        verweigert = False
    except PermissionError:
        verweigert = True
    os.symlink(fremd, b.pfad("arbeit", "verweis"))
    try:
        b.entfernen(b.pfad("arbeit", "verweis"))
        ueber_link = False
    except PermissionError:
        ueber_link = True
    check("Löschen ausserhalb des Bestands wird verweigert, auch über einen Verweis hinein", verweigert and ueber_link and os.path.exists(fremd))

    # -- Hochladen eines Archivs legt nichts in den Ordner, was danach wieder weg müsste
    puffer = io.BytesIO()
    with zipfile.ZipFile(puffer, "w") as z:
        z.writestr("Satz/D.stl", open(os.path.join(sammlung, "Teile", "A.stl"), "rb").read()[:84] + b"\0" * 50)
    vorher = set(os.listdir(sammlung))
    neu = k.hochladen(w, "Satz.zip", puffer.getvalue())
    check("Archiv hochladen: entpackt in einen neuen Unterordner, das Archiv selbst nie im Ordner des Anwenders",
          set(os.listdir(sammlung)) - vorher == {"Satz"} and all(p.startswith(os.path.join(sammlung, "Satz")) for p in neu)
          and os.listdir(b.pfad("arbeit", "hochladen")) == [])

    # -- Sicherungen
    erste = sicherung.sichern(b, "test", immer=True)
    check("Sicherung angelegt, mit Datenbank und Einstellungen", erste and os.path.isdir(os.path.join(b.wurzel, "sicherungen", erste, "datenbank")))
    check("Beim Start keine Sicherung, wenn sich seit der letzten nichts geändert hat", sicherung.sichern(b, "start") is None)
    b.einstellungen_setzen(probe_sicherung=1)
    check("Beim Start eine Sicherung, sobald sich seit der letzten etwas geändert hat", sicherung.sichern(b, "start") is not None)
    vor_zahl = len(sicherung.liste(b.wurzel))
    k.wurzel_entfernen(w)
    check("Vor einer Massenaktion (Ordner entfernen) entsteht immer eine Sicherung",
          len(sicherung.liste(b.wurzel)) == vor_zahl + 1 and sicherung.liste(b.wurzel)[0]["grund"] == "vor-ordner-entfernen")
    k.wurzel_wiederherstellen(w)
    s.lauf()
    modelle_vorher = sorted(m["name"] for m in k.modelle())
    stand = sicherung.sichern(b, "vor-test", immer=True)
    k.loeschen_mit([m["id"] for m in k.modelle()])
    check("Nach dem Entfernen aller Modelle ist der Katalog leer (Ausgangslage für das Zurückholen)", k.modelle() == [])
    try:
        sicherung.zurueckholen(b.wurzel, stand)
        trotz_lauf = True
    except flatgraph.BestandBelegt:
        trotz_lauf = False
    check("Zurückholen verweigert, solange partAtlas den Bestand offen hat", not trotz_lauf)
    b.schliessen()
    beiseite = sicherung.zurueckholen(b.wurzel, stand)
    b = Bestand(os.path.join(tmp, "bestand"))
    k = Katalog(b)
    check("Zurückgeholt: der gesicherte Stand ist wieder da", sorted(m["name"] for m in k.modelle()) == modelle_vorher)
    check("Auch das Zurückholen ist umkehrbar: der vorige Stand liegt beiseite und als Sicherung",
          os.path.isdir(beiseite) and any(x["grund"] == "vor-zurueckholen" for x in sicherung.liste(b.wurzel)))
    for _ in range(25):
        sicherung.sichern(b, "viele", immer=True)
    alle = sicherung.liste(b.wurzel)
    check("Aufräumen: die neuesten 20 bleiben, dazu die erste des Tages, nichts ausserhalb von sicherungen/",
          len(alle) == 21 and alle[-1]["name"] == erste and os.path.isdir(os.path.join(b.wurzel, "datenbank")))

    # -- Ein nicht erreichbarer Ordner ist nicht leer
    s = Scanner(b, k, prozesse=2)
    s.lauf()
    zahl = len([m for m in k.modelle() if not m["fehlt"]])
    os.rename(sammlung, sammlung + "_ab")
    s.lauf()
    check("Wurzelordner weg (Stick gezogen): kein Modell wird „Datei fehlt“, der Lauf sagt es",
          len([m for m in k.modelle() if not m["fehlt"]]) == zahl and s.status["nicht_erreichbar"] == ["Sammlung"])
    os.makedirs(sammlung)                          # leerer Einhängepunkt
    s.lauf()
    check("Wurzelordner leer (Einhängepunkt ohne Laufwerk): ebenso", len([m for m in k.modelle() if not m["fehlt"]]) == zahl)
    os.rmdir(sammlung)
    os.rename(sammlung + "_ab", sammlung)
    os.remove(os.path.join(sammlung, "Teile", "C.stl"))
    s.lauf()
    check("Wieder da, eine Datei wirklich gelöscht: nur diese gilt als fehlend",
          s.status["nicht_erreichbar"] == [] and len([m for m in k.modelle() if m["fehlt"]]) == 1)

    # -- Endgültig entfernen: ein Modell aus dem Papierkorb, sonst nichts
    from PIL import Image
    from partatlas.bestand import DATEI, MODELL
    from partatlas.katalog import ref
    ids = {m["name"]: m["id"] for m in k.modelle()}
    ma, mb, mc = ids["A"], ids["B"], ids["C"]
    puffer = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(puffer, "PNG")
    k.bild_hinzufuegen(ma, puffer.getvalue())
    bild = k.db.get_node(ref(MODELL, ma))["bilder"][0]["datei"]
    ha = k.datei_von(ma)
    sid = k.sammlung_anlegen("Weg", [mb])
    k.sammlung_loeschen(sid)
    k.loeschen(ma)
    k.loeschen(mc)

    def im_papierkorb():
        return {f"{col}/{nid}" for col, alle in k.db._cache["nodes"].items() for nid, d in alle.items() if "_deletion_flag" in d}
    vorher = im_papierkorb()
    try:
        k.endgueltig_entfernen(mb)
        lebend_abgelehnt = False
    except KatalogFehler:
        lebend_abgelehnt = True
    check("Endgültig entfernen nimmt nur ein Modell aus dem Papierkorb, ein lebendes wird abgelehnt",
          lebend_abgelehnt and k.db.get_node(ref(MODELL, mb)) is not None and im_papierkorb() == vorher)
    check("Vorschau: die Datei liegt noch im Ordner (sie kommt beim nächsten Einlesen wieder)",
          k.endgueltig_vorschau(ma)["im_ordner"] == [os.path.join(sammlung, "Teile", "A.stl")])
    namen = {x["name"] for x in sicherung.liste(b.wurzel)}
    k.endgueltig_entfernen(ma)
    check("Endgültig entfernt sind genau das Modell und seine Datei im Katalog; das andere Modell und die Sammlung bleiben im Papierkorb",
          im_papierkorb() == vorher - {ref(MODELL, ma), ref(DATEI, ha)} and k.db.get_node_raw(ref(MODELL, ma)) is None
          and k.db.get_node_raw(ref(DATEI, ha)) is None)
    check("Vorher entsteht eine Sicherung",
          sicherung.liste(b.wurzel)[0]["name"] not in namen and sicherung.liste(b.wurzel)[0]["grund"] == "vor-endgueltig-entfernen")
    check("Die Datei im Ordner bleibt, das eigene Bild kommt ins Archiv, nur die Vorschau (abgeleitet) geht",
          os.path.exists(os.path.join(sammlung, "Teile", "A.stl")) and not os.path.exists(b.pfad(*bild.split("/")))
          and any(n.startswith(os.path.basename(bild)[:-4]) for n in os.listdir(b.pfad("vault_archive")))
          and not any(os.path.exists(b.vorschau_pfad(ha, art)) for art in ("extrahiert", "berechnet")))
    s.lauf()
    check("Beim nächsten Einlesen kommt die Datei als neues Modell wieder (wie der Dialog sagt)",
          "A" in {m["name"] for m in k.modelle()} and ids["A"] not in {m["id"] for m in k.modelle()})
    b.schliessen()
    muster.ende()
