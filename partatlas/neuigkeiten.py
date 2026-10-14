"""„Neu in dieser Fassung“: was seit dem letzten Start dazugekommen ist, in ein paar Zeilen für den Anwender.

Der Tester fragte bei jeder neuen Fassung nach, was anders ist (Anwender, 14.10.2026). Beim ersten Start nach einem Update zeigt die Seite
ein kleines Fenster; gemerkt wird die gesehene Fassung im Bestand (`einstellungen.json`, Schlüssel `neuigkeiten_gesehen`).

**Zu jeder Fassung gehört ein Eintrag** (neueste zuerst) — ohne Eintrag zeigt die Fassung nichts an, und `test_neuigkeiten` fällt.
Zeilen in der Sprache des Anwenders, was er sieht oder tun kann, nicht was im Code geschah.
"""

NEUES = [
    ("0.95.7", ["Kaufteile: Ein selbst angelegtes Kaufteil (etwa mit Tippfehler) lässt sich in der Auswahl „Kaufteile hinzufügen“ mit „löschen“ entfernen — "
                "sofern es in keiner Baugruppe steckt. Die mitgelieferten Normteile bleiben."]),
    ("0.95.6", ["Beim ersten Start nach einem Update erscheint dieses Fenster mit dem, was neu ist. Ein Klick auf die Fassung oben links zeigt es wieder."]),
    ("0.95.5", ["Anhänge: SVG, XHTML und HTML öffnen im neuen Tab des Browsers, ohne Download. Skripte darin laufen nicht."]),
    ("0.95.4", ["Anhänge, die der Browser nicht zeigt (DXF, CorelDRAW …), starten beim Anklicken im Programm des Rechners — ohne Datei im Downloadordner.",
                "Mehrfaches Öffnen legt keine neuen Kopien mehr an, solange die Datei unverändert ist."]),
    ("0.95.3", ["Bereinigen: Der Wechsel zwischen Duplikate, Papierkorb, Datei fehlt … ist deutlich schneller."]),
    ("0.95.2", ["Ordner hinzufügen (＋): Erscheint der Ordnerdialog des Rechners nicht, bietet ein Hinweis nach drei Sekunden den Ordnerbaum von partAtlas an."]),
    ("0.95.1", ["Windows: Der Ordnerdialog kommt nach vorn, und es ist immer nur einer offen.",
                "Beenden mit Strg+C endet ohne lange Fehlermeldung."]),
]

# Ein Bestand, der schon Modelle hat, aber noch nichts über „gesehen“ weiss, kommt von vor diesem Fenster: er sieht alles ab hier.
START = "0.95.0"


def _nr(version):
    return tuple(int(t) for t in str(version).split(".") if t.isdigit())


def seit(gesehen, aktuell):
    """Die Einträge nach der gesehenen bis zur aktuellen Fassung, neueste zuerst."""
    return [{"version": v, "zeilen": z} for v, z in NEUES if _nr(gesehen) < _nr(v) <= _nr(aktuell)]


def letzte(n=5):
    return [{"version": v, "zeilen": z} for v, z in NEUES[:n]]


def beim_oeffnen(bestand, katalog):
    """Ein ganz neuer Bestand hat nichts verpasst — das gilt beim Öffnen, nicht erst, wenn die Seite fragt (bis dahin kann ein Ordner dazugekommen
    sein). Ein Bestand mit Inhalt, der noch nichts über „gesehen“ weiss, kommt von vor diesem Fenster und sieht alles ab START."""
    from .version import VERSION
    if bestand.einstellungen().get("neuigkeiten_gesehen") is not None:
        return
    if not katalog.wurzeln() and not bestand.db.list_nodes("MODEL_ASSET", include_deleted=True, readonly=True):
        bestand.einstellungen_setzen(neuigkeiten_gesehen=VERSION)
