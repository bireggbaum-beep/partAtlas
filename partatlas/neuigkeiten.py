"""„Neu in dieser Fassung“: was seit dem letzten Start dazugekommen ist, in ein paar Zeilen für den Anwender.

Der Tester fragte bei jeder neuen Fassung nach, was anders ist (Anwender, 14.10.2026). Beim ersten Start nach einem Update zeigt die Seite
ein kleines Fenster; gemerkt wird die gesehene Fassung im Bestand (`einstellungen.json`, Schlüssel `neuigkeiten_gesehen`).

**Zu jeder Fassung gehört ein Eintrag** (neueste zuerst) — ohne Eintrag zeigt die Fassung nichts an, und `test_neuigkeiten` fällt.
Zeilen in der Sprache des Anwenders, was er sieht oder tun kann, nicht was im Code geschah.
"""

NEUES = [
    ("1.0.12", ["Papierkorb und Archiv haben eigene Knöpfe in der Leiste links, gleich unter ▦ Bibliothek: 🗄 Archiv und 🗑 Papierkorb — ein Klick öffnet sie. "
                "Am Papierkorb steht, wie viele Modelle darin liegen. Unter 🧹 Bereinigen bleibt nur noch das Aufräumen; der Besen öffnet gleich die erste Liste, "
                "in der etwas zu tun ist.",
                "Ziehen in den Papierkorb: Zieh ein Modell (oder mehrere gewählte) auf 🗑. Ab 25 Modellen fragt PartAtlas einmal nach, darunter geht es gleich. "
                "Die Dateien bleiben auf der Platte, wie beim Entfernen über das Menü.",
                "Ziehen ins Archiv: auf 🗄 ziehen. Zurück holst du Modelle aus Papierkorb oder Archiv, indem du sie auf ▦ Bibliothek ziehst.",
                "Ziehen auf einen Tag in der Seitenleiste: Die Modelle bekommen diesen Tag.",
                "Ziehen auf ♥ Favoriten: Die Modelle werden Favoriten.",
                "Ziehen auf ＋ bei den Sammlungen: Eine neue Sammlung entsteht mit den gezogenen Modellen darin, der Name ist gleich zum Tippen bereit.",
                "Beim Ziehen steht am Zeiger, was beim Loslassen geschieht, etwa „2 Modelle in den Papierkorb“ oder „3 Modelle in die Sammlung „Werkbank““. "
                "Das gilt auch für die schon bekannten Ziele: Ordner, Sammlung, Baugruppe.",
                "Alles Gezogene lässt sich zurücknehmen: „Rückgängig“ in der Meldung oder Strg+Z. Neu auch bei Sammlungen (es geht nur heraus, was eben dazukam) "
                "und bei Baugruppen. Bei Tag und Favorit verlieren ihn nur die Modelle, die ihn vorher nicht hatten.",
                "Die Meldung unten bleibt stehen, solange die Maus darauf liegt, ein Knopf darin gewählt ist oder du in einem anderen Programm bist. "
                "Danach bleibt sie noch mindestens zwei Sekunden. So verschwindet „Rückgängig“ nicht unter dem Zeiger. Esc schliesst sie.",
                "Behoben: Backups mit der alten Schreibweise „partAtlas-Backup-…“ fehlten seit 1.0.11 in der Liste unter Einstellungen › Backup & Wiederherstellung "
                "und wurden nicht mehr aufgeräumt. Sie waren nie weg und stehen jetzt wieder da.",
                "Behoben: Holtest du ein Backup zurück, konnte PartAtlas beim nächsten Start meinen, es laufe schon. Diese Merkdatei kommt nicht mehr ins Backup.",
                "Behoben: Startest du PartAtlas ein zweites Mal, während das erste noch öffnet (bei grossem Bestand dauert das), wartet der zweite Start "
                "jetzt bis zu zwei Minuten und öffnet dann den Browser beim ersten. Vorher gab er sofort auf.",
                "Behoben: War ein Laufwerk beim Einlesen nicht eingesteckt (USB, Netz), vergass PartAtlas, welche G-Codes von dort du schon zugeordnet "
                "oder mit „Nicht zuordnen“ ausgeblendet hattest — sie standen danach wieder unter „G-Code ohne Modell“.",
                "Behoben: Änderst du Einstellungen schnell hintereinander, ging gelegentlich eine Änderung verloren oder es kam ein Fehler.",
                "Behoben: Hast du die Kachelzeile „Geändert“ abgeschaltet, kam sie in einem anderen Browser von selbst wieder.",
                "Behoben: Ordnest du unter „G-Code ohne Modell“ einen G-Code von Hand einem Modell zu, der schon an einem anderen Modell hängt, "
                "bekommt jetzt auch das gewählte Modell den Druck. Vorher geschah stillschweigend nichts.",
                "Behoben: Der Dateiname eines G-Codes ordnet nur noch über ganze Wörter zu — „Halter.gcode“ landet nicht mehr bei „Halterung“.",
                "Behoben: Während PartAtlas grosse G-Codes aus deinen Ordnern einliest, mussten andere Aktionen (Tag setzen, Verschieben …) warten. Jetzt nicht mehr. "
                "Das Einlesen selbst dauert so lange wie vorher.",
                "Bei vielen Modellen reagiert die Liste etwas flüssiger: die Haken mit Strich („teilweise gewählt“) werden nur noch dort geprüft, wo sich etwas ändert."]),
    ("1.0.11", ["Aus „Katalog“ wird „PartAtlas“: Meldungen und Fenster sagen jetzt etwa „Aus PartAtlas entfernen“ oder „Zurück in PartAtlas“. "
                "Der Knopf oben links heisst „Bibliothek“, wie die Überschrift daneben.",
                "Behoben: Schlug „Rückgängig“ nach dem Verschieben fehl, stand trotzdem „Rückgängig gemacht“ da. Jetzt sagt die Meldung, warum es nicht ging."]),
    ("1.0.10", ["Auf jeder Kachel steht jetzt, wann die Datei zuletzt geändert wurde — mit Uhrzeit, wie im Explorer. So erkennst du bei mehreren Ständen "
                "eines Teils (etwa FreeCAD-Dateien) sofort den neuesten. Sortieren nach „Zuletzt geändert“ stellt ihn nach vorn; in der Liste gibt es die "
                "Spalte „Geändert“. Abschalten lässt sich die Zeile unter Einstellungen › Ansicht.",
                "Die Kachel zeigt den Stand vom letzten Einlesen; der Inspektor (Reiter „Datei“) liest das Datum direkt von der Platte."]),
    ("1.0.9", ["Nach dem Einlesen sagt die Meldung unten, wie viele G-Codes aus deinen Ordnern zugeordnet wurden — und ob neue dazukamen, die PartAtlas keinem Modell "
               "zuordnen konnte. Ein Knopf in der Meldung führt dann direkt zu Bereinigen › „G-Code ohne Modell“.",
               "Versehentlich gelöscht? Die Meldung nach dem Löschen hat jetzt „Rückgängig“ und einen Knopf zum Papierkorb. Neu einlesen holt ein gelöschtes Modell "
               "absichtlich nicht zurück — dafür ist der Papierkorb da (Bereinigen › Papierkorb › Wiederherstellen).",
               "Startest du PartAtlas ein zweites Mal, während es schon läuft, öffnet sich der Browser beim laufenden — auch auf einem anderen Port. "
               "Vorher blieb dann eine leere Seite mit „Bestand belegt“ stehen.",
               "Vor jedem Update sichert PartAtlas deinen Katalog eigens („Vor dem Update von 1.0.8 auf 1.0.9“, Einstellungen › Backup & Wiederherstellung). "
               "Die letzten drei dieser Sicherungen bleiben immer — falls du einmal zur Fassung davor zurück musst.",
               "Mehr mit der Tastatur: „?“ zeigt alle Tastenkürzel. Im Suchfeld führen ↓ oder Enter zu den Treffern, ↑ in der ersten Reihe wieder zurück. "
               "Entf entfernt auch ein einzelnes angeklicktes Modell (Enter bestätigt), danach ist gleich das nächste gewählt — und Strg+Z holt es zurück.",
               "Tags im Inspektor: Beim Tippen schlägt PartAtlas deine vorhandenen Tags vor, mit Anzahl. ↑ ↓ wählt, Enter übernimmt — und das Feld bleibt offen "
               "für den nächsten. So entsteht nicht aus Versehen „halterung“ neben „halter“; einen neuen Tag legst du in der letzten Zeile an.",
               "Verschieben rückgängig: Nach dem Verschieben von Modellen in einen anderen Ordner nennt die Meldung das Ziel und hat „Rückgängig“ — Strg+Z geht ebenso. "
               "Ziehst du mehrere gewählte Modelle, zeigt das Ziehbild, wie viele mitgehen.",
               "Alle auswählen mit einem Haken: oben links über den Kacheln (in der Liste wie bisher im Spaltenkopf), je Gruppe und oben in Listen zum Ankreuzen "
               "wie „Archive entpacken“. Ist nur ein Teil gewählt, zeigt der Haken einen Strich."]),
    ("1.0.8", ["G-Code im Ordner: Legst du einen G-Code aus dem Slicer in einen deiner Ordner, liest PartAtlas ihn beim Einlesen mit. Das Modell erkennt es am Inhalt der Datei "
               "und hängt den G-Code daran; die Datei im Ordner bleibt liegen. Er erscheint als Druck „Noch nicht gedruckt“ — das Modell gilt erst als gedruckt, wenn du das sagst. "
               "Ist das Modell nicht eindeutig (etwa zwei mit demselben Namen) oder nicht vorhanden, steht der G-Code unter Bereinigen › „G-Code ohne Modell“ — "
               "dort ordnest du ihn mit einem Klick zu oder blendest ihn aus.",
               "Neben der Fassung oben links erscheint „↑ 1.0.9“, wenn auf main eine neuere Fassung liegt. Ein Klick zeigt, was darin neu ist. "
               "(Das klappt, wenn PartAtlas aus einem Git-Ordner läuft.)",
               "Behoben: Die Tag-Zahlen in der Seitenleiste zählten Modelle im Papierkorb mit (#bar zeigte 1412 statt 1409)."]),
    ("1.0.7", ["Behoben: 1.0.6 liess sich nicht öffnen, wenn Modelle im Papierkorb lagen. Deine Daten waren davon nicht betroffen; es ging nichts verloren."]),
    ("1.0.6", ["Schneller bei vielen Modellen: Ein Klick auf Ordner, Tag oder Format holt nur noch die Liste und nicht jedes Mal die ganze Seitenleiste neu. "
               "Bei 9 000 Modellen war das auf unserem Testrechner zwei- bis dreimal so schnell.",
               "Tags in der Seitenleiste: Über der Liste wählst du „Eigene“ (nur die, die du selbst gesetzt hast) oder „Alle“ (auch die automatischen aus den Dateinamen, etwas blasser).",
               "Hängt an einem Druck ein G-Code, zeigt der Druck das Vorschaubild, das der Slicer in die Datei legt.",
               "Behoben: Bei G-Codes mit mehreren Filament-Plätzen (etwa Anycubic mit vier) standen alle Profile da, jetzt nur das benutzte."]),
    ("1.0.5", ["Auf der Kachel steht „G-Code“, wenn zu einem Modell ein G-Code gehört — an einem Druck angehängt oder schon im geslicten 3MF. Ein Klick öffnet den passenden Reiter, "
               "die Suche kennt dazu „gcode:ja“. Das Zeichen sitzt unten rechts immer am selben Platz, der Status (✓ gedruckt, Datei fehlt) links davon.",
               "Der Schriftzug oben heisst jetzt „PartAtlas“. Im Spulenformular ist das Bild der Spule grösser."]),
    ("1.0.4", ["Im Lager steht jetzt eine Spule vor jeder Karte — die Wicklung hat die Farbe der Spule, auch im leeren Lager und im Formular als Platzhalter."]),
    ("1.0.3", ["Neu: das Lager. Das Spulensymbol in der Leiste links öffnet deine Spulen — mit Rest, Preis und Lagerort, als Karten oder Liste, mit Suche und Filter. Spulen "
               "anlegen (auch mehrere gleiche), bearbeiten, nachkaufen und löschen.",
               "Ein viertes Farbschema zur Probe: „GNOME“ (Einstellungen › Ansicht), mit den Farben von GTK 4.",
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
    ("1.0.0", ["Handbuch in PartAtlas: Knopf „?“ links unten oder F1 öffnet es — neu geschrieben, mit Bildern der Oberfläche und Kapiteln zu "
               "Ordnern und Tastatur.",
               "Ordner wie im Explorer: Rechtsklick auf einen Ordner › Neuer Ordner, Umbenennen, Verschieben nach … — oder einen Ordner auf einen "
               "anderen ziehen. Alles darin geht mit, Tags und Drucke bleiben. Der Baum zeigt jetzt alle Unterordner, auch leere (grau).",
               "Umbenennen direkt am Namen, bei Ordnern und Modellen: F2, Rechtsklick › Umbenennen oder ein zweiter Klick auf den Namen eines schon "
               "gewählten Eintrags. Das kleine Fenster dafür gibt es nicht mehr. Rückgängig mit Strg+Z oder dem Knopf in der Meldung.",
               "Bereinigen neu gegliedert: „Aufräumen“ (Datei fehlt, Gleiche Datei — vorher „Duplikate“ —, Unlesbar, Vorschläge) und „Aufbewahrt“ "
               "(Archiv, Papierkorb). Jede Ansicht sagt oben, was sie zeigt und was ihre Aktionen tun.",
               "Einstellungen › Backup & Wiederherstellung zeigt, wo dein Katalog liegt (Tags, Drucke, Baugruppen, Notizen …) — nimm diesen Ordner "
               "in dein eigenes Backup auf.",
               "Geht etwas schief (Platte voll, Datei in einem anderen Programm offen), sagt PartAtlas es in einem Satz statt „Fehler 500“.",
               "Windows: start.bat zum Doppelklicken richtet PartAtlas ein und startet es (siehe README).",
               "Ausgeblendet: „Farbe der Vorschaubilder“ unter Einstellungen › Ansicht — sie wirkte noch nicht und kommt, wenn sie es tut."]),
    ("0.95.7", ["Kaufteile: Ein selbst angelegtes Kaufteil (etwa mit Tippfehler) lässt sich in der Auswahl „Kaufteile hinzufügen“ mit „löschen“ entfernen — "
                "sofern es in keiner Baugruppe steckt. Die mitgelieferten Normteile bleiben."]),
    ("0.95.6", ["Beim ersten Start nach einem Update erscheint dieses Fenster mit dem, was neu ist. Ein Klick auf die Fassung oben links zeigt es wieder."]),
    ("0.95.5", ["Anhänge: SVG, XHTML und HTML öffnen im neuen Tab des Browsers, ohne Download. Skripte darin laufen nicht."]),
    ("0.95.4", ["Anhänge, die der Browser nicht zeigt (DXF, CorelDRAW …), starten beim Anklicken im Programm des Rechners — ohne Datei im Downloadordner.",
                "Mehrfaches Öffnen legt keine neuen Kopien mehr an, solange die Datei unverändert ist."]),
    ("0.95.3", ["Bereinigen: Der Wechsel zwischen Duplikate, Papierkorb, Datei fehlt … ist deutlich schneller."]),
    ("0.95.2", ["Ordner hinzufügen (＋): Erscheint der Ordnerdialog des Rechners nicht, bietet ein Hinweis nach drei Sekunden den Ordnerbaum von PartAtlas an."]),
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
