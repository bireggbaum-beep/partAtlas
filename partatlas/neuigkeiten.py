"""„Neu in dieser Fassung“: was seit dem letzten Start dazugekommen ist, in ein paar Zeilen für den Anwender.

Der Tester fragte bei jeder neuen Fassung nach, was anders ist (Anwender, 14.10.2026). Beim ersten Start nach einem Update zeigt die Seite
ein kleines Fenster; gemerkt wird die gesehene Fassung im Bestand (`einstellungen.json`, Schlüssel `neuigkeiten_gesehen`).

**Zu jeder Fassung gehört ein Eintrag** (neueste zuerst) — ohne Eintrag zeigt die Fassung nichts an, und `test_neuigkeiten` fällt.
Zeilen in der Sprache des Anwenders, was er sieht oder tun kann, nicht was im Code geschah.
"""

NEUES = [
    ("1.0.3", ["Neu: das Lager. Das Spulensymbol in der Leiste links öffnet deine Spulen — mit Rest, Preis und Lagerort, als Karten oder Liste, mit Suche und Filter. Spulen "
               "anlegen (auch mehrere gleiche), bearbeiten, nachkaufen und löschen.",
               "„Reicht das Filament?“ im Inspektor eines geslicten 3MF: je Filament, ob eine Spule reicht, mit der Spule und dem Lagerort — oder was fehlt. "
               "Beim Anlegen eines Drucks lässt sich der Verbrauch von einer Spule abziehen; die Materialkosten stehen im Inspektor und am Druck."]),
    ("1.0.2", ["Neue Farben und ein Zeichen: Das Atlas-Zeichen steht vor dem Namen, „Katalog“ ist aus dem Titel. Das Schema „Filament“ (Blaugrün) ist "
               "die Vorgabe; unter Einstellungen › Ansicht lassen sich zur Probe „Messing“ und „Blaupause“ wählen, hell und dunkel wie gewohnt.",
               "3D-Ansicht: Sie zeichnet nur noch, wenn sich etwas bewegt — eine ruhende Ansicht kostet den Rechner nichts mehr. Fällt einem "
               "langsamen Rechner das Bewegen schwer (grosse Modelle, Grafik über den Prozessor), sinkt beim Drehen die Auflösung und wird wieder "
               "scharf, sobald du loslässt. Grosse Modelle werden nicht mehr geglättet.",
               "G-Code aus Cura und darauf aufbauenden Slicern: Die Druckzeit wird jetzt auch dort gelesen."]),
    ("1.0.1", ["FreeCAD-Dateien (FCStd) werden nicht mehr im Slicer angeboten — dort lassen sie sich nicht öffnen. Das galt vorher für einen Slicer, "
               "den du selbst unter Einstellungen › Programme gewählt hast; sie gehen nur noch ins CAD."]),
    ("1.0.0", ["Handbuch in partAtlas: Knopf „?“ links unten oder F1 öffnet es — neu geschrieben, mit Bildern der Oberfläche und Kapiteln zu "
               "Ordnern und Tastatur.",
               "Ordner wie im Explorer: Rechtsklick auf einen Ordner › Neuer Ordner, Umbenennen, Verschieben nach … — oder einen Ordner auf einen "
               "anderen ziehen. Alles darin geht mit, Tags und Drucke bleiben. Der Baum zeigt jetzt alle Unterordner, auch leere (grau).",
               "Umbenennen direkt am Namen, bei Ordnern und Modellen: F2, Rechtsklick › Umbenennen oder ein zweiter Klick auf den Namen eines schon "
               "gewählten Eintrags. Das kleine Fenster dafür gibt es nicht mehr. Rückgängig mit Strg+Z oder dem Knopf in der Meldung.",
               "Bereinigen neu gegliedert: „Aufräumen“ (Datei fehlt, Gleiche Datei — vorher „Duplikate“ —, Unlesbar, Vorschläge) und „Aufbewahrt“ "
               "(Archiv, Papierkorb). Jede Ansicht sagt oben, was sie zeigt und was ihre Aktionen tun.",
               "Einstellungen › Backup & Wiederherstellung zeigt, wo dein Katalog liegt (Tags, Drucke, Baugruppen, Notizen …) — nimm diesen Ordner "
               "in dein eigenes Backup auf.",
               "Geht etwas schief (Platte voll, Datei in einem anderen Programm offen), sagt partAtlas es in einem Satz statt „Fehler 500“.",
               "Windows: start.bat zum Doppelklicken richtet partAtlas ein und startet es (siehe README).",
               "Ausgeblendet: „Farbe der Vorschaubilder“ unter Einstellungen › Ansicht — sie wirkte noch nicht und kommt, wenn sie es tut."]),
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
