# partAtlas — Stand und nächste Schritte

Arbeitsstand für den nächsten Chat. Führend bleibt `KONZEPT.md`; hier steht,
was gerade offen ist und was entschieden wurde. Nach jeder erledigten Sache
aktualisieren.

## Als Nächstes (8.10.2026, Anwender)

1. Offene Punkte nach 0.50 abarbeiten. **Erledigt (0.50.1):** Protokoll schreibt „nimmt Anfragen an“ erst, wenn der Port offen ist
   (vorher schon davor, auch bei belegtem Port); `einlesen=0` aus `/api/hochladen` entfernt (kein Aufrufer mehr; test_verwalten 76/76,
   die zwei Prüfungen dazu entfallen); Kommentar 3 × 4 MB. **Zurückgestellt auf v0.60:** Gruppengrösse 200 messen
   (funktioniert heute); Ordner entfernen mit vielen Dateien (seltene Aktion). „EIGENE“-Markierungen entfernt (0.50.2): sie markierten „Eigene Komponente“ als rückbaubar; die Funktion bleibt (Anwender).
2. **Listenkopf analog zu pDMS** (Capacities „Listen-Header analog zu pDMS“), vier Pakete: (1) Sortieren per Klick, zweiter Klick dreht
   die Richtung; (2) Häkchen „alle“ links im Kopf; (3) ⋮ rechts: Spalten ein/aus (Format, Grösse, Gewicht, Status, Material, Tags,
   Dateigrösse, Eingelesen, Ordner, Drucke; gemerkt); (4) Spaltenbreite ziehen (Anwender: „essenziell“). Verschieben von Spalten später.
   **Paket 1 erledigt (0.51.0):** jede Spalte ausser Bild/Häkchen sortierbar (Name, Format, Grösse, Gewicht, Status), ▲/▼, zweiter Klick
   dreht; erster Klick: Name/Format/Status aufsteigend, Zahlen absteigend; Auswahlfeld „Sortieren“ folgt (Format, Status neu darin).
   Sortiert wird jetzt immer in der Oberfläche (natürliche Reihenfolge, bei Gleichstand nach Name); bei Suche/Chips gilt die Relevanz,
   bis man eine Spalte anklickt — ein neuer Suchbegriff setzt das zurück (wie pDMS). test_ui +1 (gezielt geprüft, Gegenprobe fällt).
   **Fehler (Anwender, 0.51.1 behoben):** Format-Chips zeigten die Zahlen des ganzen Katalogs statt der Ansicht. Jetzt zählt der Server in
   der Ansicht (Ordner, Suche, Chips), ohne den Format-Filter selbst (`leiste.formate`). test_suche 28/28 (+2, Gegenprobe fällt).
   Nicht berücksichtigt: ausgeblendete Entwürfe (blendet die Oberfläche aus, der Server zählt sie mit).
   **Paket 2 erledigt (0.51.2):** Häkchen „alle“ im Listenkopf (Spalte der Zeilen-Häkchen): wählt alle Gezeigten bzw. keine; Strich, wenn ein
   Teil gewählt ist; folgt jeder Auswahl (`kopfWahlZeichnen` aus `zeichneStapel`). test_ui +1 (gezielt, Gegenprobe fällt).
   Nebenbei: test_api-Prüfung zum Protokoll nachgezogen (seit 0.50.1 rot, nicht gelaufen).
   **Paket 3 erledigt (0.51.3):** ⋮ rechts im Kopf öffnet die Spaltenwahl (Format, Grösse, Gewicht, Status, Material, Tags, Datei, Eingelesen,
   Ordner, Drucke; „Vorgabe“ setzt zurück), gemerkt im Browser (`partatlas.spalten`). Kopf und Zeilen aus einer Definition (`SPALTEN`), ein
   gemeinsames Raster (`--listen-spalten`); Breiten „mindestens–höchstens“, damit viele Spalten nicht über den Rand laufen (im Bild geprüft).
   Neu sortierbar: Datei, Material, Ordner, Drucke. test_ui +1 (gezielt, Gegenprobe fällt).
   **Paket 4 erledigt (0.51.4):** Spaltenbreite ziehen wie in pDMS — die Linie im Kopf ist die Grenze zweier Nachbarn (links breiter, rechts
   genau so viel schmaler, Tabelle gleich breit; rechts vom Namen gibt nur die rechte ab; rechts von der letzten nimmt sie vom Namen, nur
   über dessen Minimum). Doppelklick setzt die Spalte zurück, „Vorgabe“ im ⋮-Menü alle. Gemerkt (`partatlas.spaltenBreiten`).
   Einpassen rechnet jetzt die Oberfläche (`spaltenRaster`, bei jeder Grössenänderung über ResizeObserver): passt es nicht, schrumpfen alle
   anteilig bis zu ihrem Minimum, und reicht selbst das nicht (Liste 435 px mit sechs Spalten), darunter — nie über den Rand (im Bild
   geprüft, schmal und breit). Beim Ziehen gelten die gezeigten Breiten, damit die Grenze genau der Maus folgt. test_ui +1 (gezielt,
   Gegenprobe fällt). **Listenkopf damit fertig**; Spalten verschieben bleibt für später.
3. **Inspektor: Reiter ganz oben (Capacities, für 0.50 geplant) — erledigt (0.52.0):** Name, Öffnen und Reiterleiste oben, darunter das
   Vorschaubild, nur im Reiter Übersicht (im Papierkorb ohne Reiter immer). Die anderen Reiter beginnen direkt unter der Leiste — Platz für
   mehr aus den 3MF-Dateien. Geprüft: eine in einem anderen Reiter gewählte 3D-Ansicht erscheint beim Wechsel in voller Grösse. test_ui
   67/67 komplett (zweimal: der erste Lauf brach an der neuen Prüfung ab), +1 mit Gegenprobe (gezielt). In Capacities: App-Freeze,
   Klare Ingest-Pipeline, Listen-Header auf Erledigt; Reiter auf In Arbeit → nach Abnahme Erledigt.
   **Kopfzeile des Inspektors aufgeräumt (0.52.1, Anwender: „plump, Krautsalat“):** eine Linie — Name links, rechts dieselben Symbolknöpfe
   wie in der Liste (Slicer, CAD; `programmKnoepfe`, gestrichelt, wenn keins eingerichtet) und dezent ⋯ in gleicher Grösse. Der grosse
   „Öffnen“-Knopf und das „▾“-Auswahlfeld sind weg; ihr Inhalt steht im ⋯-Menü (alle Programme je Art, „Mit dem System öffnen“,
   „Programme einstellen …“), darunter Umbenennen, Verschieben, Bild, Löschen. Papierkorb: Wiederherstellen/Endgültig unverändert.
   test_ui: drei Prüfungen auf die neuen Knöpfe umgestellt, gezielt mit Slicer-/FreeCAD-Ersatz geprüft (4/4).
   **Gruppenbänder sichtbarer (0.52.2, Anwender: „zu unauffällig“):** eigener Hintergrund, Name in der Textschrift 15 px statt grauer
   Monospace 12,5 px, Anzahl als Pille; Höhe unverändert. Reine Gestaltung, kein Test.
4. **Backup & Wiederherstellung (KONZEPT §3.3a) später** — grösser als gedacht, nicht direkt nach dem Umbau des Einlesens. Pakete:
   (1) Reiter mit automatischer Sicherung (nur Datenbank), Liste und Zurückholen, 5 / 30 Tage; (2) Backup als ZIP, einstellbar;
   (3) Erinnerung nach 30 Tagen.

## Stand: 0.52.1 auf `main` (8.10.2026, für den Tester)

Seit 0.51.4: Inspektor mit Reitern ganz oben (Bild nur in der Übersicht), Kopfzeile in einer Linie (Name, Slicer-/CAD-Knopf wie in der Liste,
⋯ mit „Öffnen mit …“). Auf Wunsch des Anwenders ohne vollen test_ui-Lauf auf `main` (zuletzt komplett bei 0.52.0: 67/67); die geänderten
Prüfungen gezielt (Reiter 1/1, Öffnen 4/4).

## Stand davor: 0.51.4 auf `main` (8.10.2026, für den Tester)

Seit 0.50: Listenkopf wie pDMS (Sortieren per Klick mit Richtung, Häkchen „alle“, Spalten über ⋮, Spaltenbreite ziehen), Format-Chips zählen
in der Ansicht, Protokoll meldet Bereitschaft erst bei offenem Port, Rückbau-Markierungen „EIGENE“ entfernt. Geprüft: nach jeder Änderung
die betroffene Suite (suche 28, api 86, verwalten 76, eigene 17, baugruppen 48), test_ui einmal komplett 66/66.

## Stand davor: 0.50.0 auf `main` (8.10.2026, für den Tester)

Pipeline nach KONZEPT §3.4: Einträge und Ordnerbaum sofort beim Einlesen, Auslesen/Vorschaubilder/FreeCAD im Hintergrund (schnelle Formate
zuerst), Oberfläche bekommt nur Geändertes nachgereicht, bleibt in allen Phasen bedienbar; Hochladen und Ziehen ins Fenster entfernt;
Massenaktionen (Löschen, Wiederherstellen, Behalten) gruppiert mit Anzeige unten links. Vom Anwender unter Windows mit ≈ 8600 Dateien
getestet („Einlesen sieht jetzt sehr ok aus, bedienbar, verstehbar“); die letzten Behebungen (Abfragen unter einer Sperre, leerer Ordner
ohne Sicherung, Wiederherstellen nach Ordner entfernen) sind nur hier nachgestellt, unter Windows noch nicht gesehen.
Alle 14 Suiten grün: api 86, aufraeumen 13, baugruppen 48, cad 14, drucke 28, eigene 17, formate 25, sammlungen 18, scan 110, schutz 22,
suche 26, verwalten 78, zuordnen 12; test_ui einmal komplett gelaufen (60/62 — die zwei fallenden beschrieben das alte Nachladen; neu
gefasst und gezielt geprüft, 5/5, Gegenprobe fällt; nicht noch einmal komplett, CLAUDE.md).
**Rückmeldung des Testers (8.10.2026):** „In 0.50 funktioniert der Import.“ Er hat im Explorer einen Unterordner („Mähklingen“, 11 Objekte)
in einen schon aufgenommenen Ordner gelegt und in partAtlas ohne Fehler eingelesen. Damit ist der Hänger aus 0.46 bei ihm nicht mehr
aufgetreten.
Offen danach: Gruppengrösse der Massenaktionen messen (200 ist geschätzt); Ordner entfernen mit vielen Dateien (eine grosse Transaktion);
Sicherung über harte Verweise (Vorschlag); automatische Überwachung (Schritt 5).

## Als Nächstes: Zielbild „sofort da, Auslesen im Hintergrund“ (Anwender, 7.10.2026) — erledigt in 0.50

Test des Anwenders mit ≈ 8600 Dateien unter Windows: die Fassung 0.49 erfüllt sein Zielbild nicht. Gebaut war nur „Vorschaubilder und
FreeCAD getrennt im Hintergrund“; das Einlesen liest weiterhin jede Datei ganz aus, bevor ihr Eintrag erscheint, und die Oberfläche lädt
bei jeder Änderung die ganze Liste (8600 Einträge) neu. Zielbild steht jetzt in KONZEPT §3.4 („Sofort da, Auslesen im Hintergrund“).
Teile (Aufwand 1–5, Reihenfolge noch vom Anwender zu bestätigen):
- a) Einträge und Ordnerstruktur sofort aus dem Ordner (Name, Ort, Format, Grösse), Auslesen füllt nach. Aufwand 3–4.
  **Gebaut (7.10.2026):** Einlesen = suchen + Fingerabdruck + sofort anlegen (Format aus der Endung, Name aus dem Dateinamen,
  `auslesen: ausstehend`), gruppenweise schon während des Hashens. Der Fingerabdruck bleibt im Einlesen: er ist die Kennung der Datei.
  Worker: neue erste Phase „auslesen“ (`Katalog.auszulesen`/`ausgelesen`, Masse, Slicer-Daten, eingebettetes Bild, Tags aus den Werten),
  schnelle Formate zuerst, STEP zuletzt (damit ist Teil c erledigt), Ergebnisse spätestens alle 2 s. Die FCStd-Frage kommt jetzt nach dem
  Auslesen (vorher am Ende des Einlesens). „Unlesbar“, „Bilder aus der Datei“ zählt jetzt der Worker. Beim Umbau gefunden und behoben:
  neu gespeicherte Datei am selben Ort bekam ein zweites Modell (alter Ort muss vor dem Anlegen weg).
  Tests: test_scan 103/103 (+3, Gegenproben fallen; 6 Prüfungen auf den neuen Ablauf umgestellt), test_api 85/85, test_cad 14/14.
  **Gemessen** (3000 Dateien, Browser): Liste wächst während des Einlesens (200 nach 4 s, 2500 nach 14 s), Masse aller nach 15 s,
  danach Vorschaubilder laufend, Klick 0,1 s.
  **Filter-Klick während Einlesen/Auslesen war 1,4–4 s — behoben (7.10.2026):** zwei Ursachen. (1) `_kurz_alle` baute bei jeder
  Änderung alle Kacheln neu; jetzt nur die geänderten (`_kurz_veraltet` merkt sich Modell, Datei und Kanten-Enden aus den Meldungen von
  flatgraph; Tag/Material geändert → alles neu; ein Nachbau zur Zeit). (2) Grösser: jede Kachel las fünfmal einzeln und wartete jedes
  Mal auf die Schreib-Transaktion des Einlesens (1,3 ms statt 0,03 ms je Kachel) — jetzt baut sie unter EINER Sperre (Transaktion ohne
  Schreiben, flatgraph VERTRAG §3.1). Gemessen 3000 Dateien: Klick 0,05–0,28 s in allen Phasen; eine Einzelabfrage wartet noch bis
  0,3 s auf eine laufende Schreib-Transaktion. test_scan 104/104 (+1, beide Gegenproben fallen), test_api 85/85.
  **Test des Anwenders (Windows, 8600 Dateien, 7.10.2026): „nichts besser, Klicks ohne Wirkung“, bis die Vorschaubilder laufen.**
  Protokoll: `GET /api/baugruppen/vorschlaege` 3,3–3,9 s, etwa jede Sekunde neu. Ursache: jede Graph-Änderung ging einzeln an den
  Browser; beim Einlesen tausende je Sekunde → Schlange > 1000 → „neu_laden“ → die Oberfläche lud alles neu, samt Vorschlägen (die je
  Modell einzeln die Datenbank fragten). In meiner Messung (Linux, schneller) lief die Schlange nicht über. Behoben: `Verteiler.graph`
  fasst zusammen (höchstens alle 0,3 s eine Meldung `stapel`, je Verweis einmal); Vorschläge lesen Namen aus den Kacheln; „neu_laden“
  wartet auf eine laufende Liste. test_api 86/86 (+1, Gegenprobe fällt), test_baugruppen 48/48.
  **Alle löschen (8600) hing ebenso** (Protokoll: /api/modelle 51 s, /api/zaehler 35 s): `loeschen_mit` schrieb je Modell eine eigene
  Transaktion samt fsync. Jetzt je 200 eine (`LOESCHEN_GRUPPE`), dazwischen kommen andere Anfragen dran. test_scan 105/105 (+1, Gegenprobe
  fällt), test_api 86/86.
  **Andere Massenaktionen durchgesehen (7.10.2026):** Schleifen über Modelle mit je eigenem Schreibvorgang (Server) oder je eigener
  Anfrage (Oberfläche). Betroffen und behoben: **viele wiederherstellen** (je Modell eine Anfrage → Stapel-Aktion `wiederherstellen`,
  je 200 eine Transaktion) und **Aufräumen › Alle behalten** (→ Stapel-Aktion `behalten`, eine Transaktion). In Ordnung: Ordner entfernen
  (eine Transaktion), Stapel Favorit/Tag/Material/Sammlung/Warteschlange (eine Transaktion), endgültig entfernen (nur einzeln, bewusst),
  Verschieben (Dateiaktionen einzeln, gewollt). test_scan 106/106 (+1, Gegenprobe fällt), test_api 86/86, test_aufraeumen 13/13.
  Offen: die Sicherung vor Massenaktionen bei grossem Bestand (nicht gemessen); Ordner entfernen hält bei 8600 Dateien die Sperre für
  eine grosse Transaktion (unter Windows nicht gemessen).
  **Löschen 8600 danach (Protokoll Anwender):** 19 s, Zähler und Tags warteten 14–15 s. Ursache: die Sperre von flatgraph ist nicht
  fair — der Löschende holte sie nach jeder Gruppe gleich wieder. Behoben: `_gruppenweise` lässt nach jeder Gruppe 20 ms los; `_kurz_alle`
  nimmt die Sperre nur noch, wenn etwas nachzubauen ist (vorher auch bei unverändertem Zwischenspeicher). Nachgestellt (2936 Modelle,
  Linux): Löschen 2,9 s, eine Anfrage alle 0,3 s wartet höchstens 0,15 s (vorher bis 14 s). Kein eigener Test (Zeitverhalten, wäre
  wackelig); test_scan 106/106, test_api 86/86. Die Sicherung vorher: 0,04 s bei 2936 (Linux).
  **Danach noch (Protokoll 8.10.2026):** Tags und Zähler warteten weiter 14–18 s. Ursache: sie lesen in vielen Einzelschritten (Tags je
  Tag, Papierkorb je Modell), und jeder wartete auf eine Lücke zwischen zwei Schreibgruppen. Behoben: `am_stueck` (main.py) — Abfragen
  der Seitenleiste und Listen nehmen die Sperre einmal (zaehler, tags, ordner, sammlungen, warteschlange, wurzeln, wurzeln/entfernt,
  modelle, modelle/{mid}, modelle/aenderungen, baugruppen, baugruppen/vorschlaege). Nicht: Bilder ausliefern (Plattenarbeit). Dabei
  gefunden: Sperr-Reihenfolge beim Kachel-Nachbau musste fest werden (erst flatgraph, dann `_kurz_bau`), sonst Verklemmung. Nachgestellt:
  2936 löschen und wiederherstellen mit 6 pausenlos fragenden Abfragen: 14 s, 336 Abfragen, längste 0,65 s, kein Hänger.
  **Danach (Protokoll 8.10.2026):** nur noch die Massenaktion selbst langsam (8600: 30 s), keine wartenden Abfragen mehr.
  **Anzeige gebaut:** Löschen und Wiederherstellen vieler Modelle melden ihren Fortschritt (`_gruppenweise(melden)`, Live-Meldung
  „aktion“), unten links „Wiederherstellen | 1.400 / 2.936“ mit Balken, geht der Einlese-Anzeige vor; am Ende „2.936 Modelle
  wiederhergestellt.“ Im Browser gesehen (2936). test_scan 107/107 (+1, Gegenprobe fällt).
  **Offen, Anwender fragt:** Gruppengrösse 200 ist geschätzt, nicht gemessen — grössere Gruppen schreiben seltener (schneller), halten
  die Sperre aber länger (Abfragen warten länger). Messen und wählen (Variante b).
  **Ordner entfernen 4,3 s (8600, Windows):** gemessen 2936 unter Linux 0,74 s ohne Sicherung (Sicherung 0,06 s): jede Datei bekommt neue
  Orte, also wird die ganze Sammlung der Dateien einmal neu geschrieben (JSON 0,35 s, fsync von 126 Dateien). Wächst mit der Grösse; unter
  Windows mit 3× so vielen Dateien und teurerem fsync passen 4 s. Während dieser Zeit warten Abfragen. Nicht behoben.
  **Korrektur (Anwender):** der Ordner war leer (alles vorher im Papierkorb) und brauchte trotzdem 4 s — also die **Sicherung** davor:
  sie kopiert die ganze Datenbank samt Papierkorb (hier 493 Dateien) unter der Sperre und zählte vorher die Grössen aller bis zu 20
  alten Sicherungen, zweimal. Linux 0,11 s; Windows nicht gemessen (Virenscanner prüft jede neue Datei). Geändert: leerer Ordner →
  keine Sicherung (nur sein Eintrag ändert sich, und der ist zurückholbar); beim Anlegen keine Grössen mehr; jede Sicherung schreibt
  ihre Dauer ins Protokoll. Nebenbei: test_schutz kannte `Worker._cad` noch als `Scanner._cad` (seit Schritt 3 rot, nicht gelaufen).
  test_scan 108/108 (+1, Gegenprobe fällt), test_schutz 22/22, test_api 86/86.
  **Ordner entfernen → alle löschen → Ordner zurückholen → mitten im Einlesen wiederherstellen (Anwender, 8.10.2026):** alle 8000 auf
  „Datei fehlt“, 2100 blieben es. Zwei Fehler: (a) das Einlesen merkte Dateien als „Modell im Papierkorb“ vor und schrieb am Ende keinen
  Ort, auch wenn das Modell inzwischen wiederhergestellt war — jetzt erneut geprüft, dann Ort gesetzt; (b) gelöscht, während die Datei
  schon fehlte, hatte das Modell im Papierkorb keinen Ort — Wiederherstellen nimmt jetzt `zuletzt_ort`, wenn die Datei dort gleich gross
  liegt. test_scan 110/110 (+2, beide Gegenproben fallen).
  **Vorschlag, nicht gebaut:** Sicherung über harte Verweise statt Kopien (flatgraph ersetzt Dateien immer über os.replace, ändert nie
  an Ort und Stelle — ein harter Verweis ist dann ein gültiger Stand, ohne Daten zu kopieren). Aufwand 2; dagegen: gilt nur, solange
  wirklich nichts an Ort und Stelle schreibt, auch partAtlas selbst (einstellungen.json, vault_text) — vorher prüfen.
  **Nächstes:** erneuter Test des Anwenders; danach einmal alle Suiten samt test_ui, dann 0.50.
- b) Oberfläche: Liste einmal laden, danach nur geänderte/neue Einträge nachreichen — kein Neuladen der ganzen Liste. Aufwand 3.
  **Gebaut (7.10.2026, 65f053d):** während etwas läuft, sammelt die Oberfläche die Verweise aus den Live-Meldungen und holt jede halbe
  Sekunde nur diese Modelle (`POST /api/modelle/aenderungen`, gefiltert wie die Liste; ersetzt `/api/modelle/kacheln`); fertige Kacheln
  werden ausgetauscht, neue eingefügt, die Kachel oben im Bild bleibt stehen (`raster.anker`). Ordnerbaum/Zähler höchstens alle 5 s.
  Ansichten Neu, Warteschlange, Sammlung, Papierkorb, Baugruppe laden weiter ganz. test_api 85/85 (+1, Gegenprobe fällt).
  **Gemessen** (Browser, 3000 Demo-Dateien, 4 Kerne, `gross_check.py` im Scratchpad — gehört als Werkzeug nach `werkzeuge/`):
  Vorschau-Phase 4 min: Liste vollständig, Bilder erscheinen laufend (alle 3 s ≈ 30–70 mehr), Filter-Klick 0,1–0,2 s, Anfrage < 20 ms.
  **Während des Einlesens (12 s) noch schlecht:** ein Filter-Klick 3,8 s (die ganze Liste wird neu gebaut, der Zwischenspeicher ist
  während des Einlesens immer veraltet), die Liste hinkt hinterher (347 gezeigt bei 900 ausgelesen). Bei 8600 Dateien unter Windows dauert
  das Einlesen viel länger — dort ist das der Hauptärger. Behebt Teil a (Einträge sofort, Auslesen im Hintergrund).
  Beobachtet beim Anwender: Vorschaubilder erschienen nicht nach und nach, sondern nur einmal am Ende, „nach 1000 Stück“ oder beim Wechsel
  auf Raster. Ursache: `kachelVon`/`teilLaden` tauschen nur Kacheln, die in der geladenen Liste stehen; die stand bei 100 (Fehler f4b9ae4).
- c) Reihenfolge der Warteschlange: zuerst STL/OBJ/3MF/FCStd mit Bild, danach STEP und FCStd über FreeCAD. **Erledigt mit a.**
- d) Anzeige unten links: **Schritte entfernt (7.10.2026)** — ein Balken, darüber was gerade passiert („Ordner durchsuchen“,
  „Datenbank aufbauen“, „Daten auslesen“, „Vorschaubilder erzeugen“, „Kleine Bilder erzeugen“, „FreeCAD-Dateien umwandeln“), Zähler,
  Restzeit; die Zeile „Danach: FreeCAD …“ ist weg. Offen: dass die Zahlen bei grossen Sammlungen stimmen (mit a/b prüfen).
Abnahme: mit einer grossen Sammlung (Werkzeug `werkzeuge/demo_sammlung.py` mit ≈ 8000 Dateien), nicht nur mit den Suiten.

## Als Nächstes: Umbau der Pipeline, Schritt 4 (Durchsicht 7.10.2026, Ziel 0.50)

Stand 0.49.0 (Schritte 1–3 erledigt, test_ui gekürzt). Schritt 4 erledigt; 0.50 siehe oben
(Hochladen als Bedienung raus, Ordner ins Fenster ziehen = Ordner hinzufügen), in kleinen Paketen (CLAUDE.md). Danach einmal alle
Suiten samt test_ui, dann 0.50.

Durchgesehen: alle Sonnet-Commits auf `main` (0.39 bis 0.46.3), Schwerpunkt Einlesen, Beenden, `start.sh`. Suiten auf `main` grün
(test_scan 92/92, test_api 79/79, test_cad 14/14, test_ui 97/97) — keine prüft einen der Befunde unten. Planung des Anwenders in Capacities:
Projekt partAtlas, Release „partAtlas 0.50“. **Nichts bauen, bis der Anwender entschieden hat.** Aufwand 1–5.

Hänger (Capacities „App-Freeze …“):
1. **Beenden geht nicht, solange ein Tab offen ist** (nachgestellt: nach SIGTERM 20 s weiter da, beendet erst, als die Live-Verbindung zu war).
   uvicorn wartet auf `/api/live`; das Abbrechen aus 0.46.2 wird gar nicht erreicht, `start.sh` gibt nach 45 s auf. Vorschlag:
   `timeout_graceful_shutdown` und den Strom beim Beenden schliessen. Aufwand 1.
2. **Fehler im Einlesen → Dialog ohne Ausweg** (nachgestellt mit „No space left on device“ in `_anlegen`): Status bleibt `laeuft=False`,
   Phase „analysieren“, `abgebrochen=False`; die Oberfläche liest `abbruch` nirgends, zeigt kein OK, „Abbrechen“ wirkt nicht mehr. Aufwand 1.
3. **FreeCAD in der Ereignisschleife:** `async def eigene_datei_setzen` ruft `datei_setzen` direkt, samt FreeCAD (bis ca. 5 min) — der ganze
   Server steht. Dasselbe Muster (async-Route mit synchroner Arbeit) bei Hochladen, Ordner hinzufügen u. a.; sie warten auf jede Transaktion
   des Einlesens. Vorschlag: `def` statt `async def`, wo nichts awaited wird. Aufwand 1–2.
4. **Einlesen wartet modal hinter dem Hintergrundlauf:** läuft Vorschau/FreeCAD/kleine Bilder (startet nach jedem Neustart von selbst), zeigt
   „Neu einlesen“ nur „Wartet, bis das laufende Einlesen fertig ist …“ — ohne Dauer, ggf. Stunden. Passt auf „nach dem Neustart hing es weiter“.
   Kern von §3.4. Notlösung: Einlesen bricht den Hintergrundlauf ab (Ausstehendes bleibt im Bestand). Aufwand 2; richtig: Umbau §3.4, Aufwand 4.
5. **Folgelauf kann verloren gehen** (aus dem Code, nicht nachgestellt): `_lauf_sicher` entscheidet „kein Folgelauf“ und endet; kommt `starten`
   dazwischen, sieht es den Faden noch lebend, setzt `_nochmal` und kehrt zurück — kein Lauf, der Dialog wartet für immer. Aufwand 1.
6. **Beenden schliesst die Datenbank, während der Scan noch läuft:** `warten(30)`, dann `schliessen()`; `_verteilen` prüft den Abbruch erst
   nach einem fertigen Ergebnis (bis 180 s), die Einzelwiederholung gar nicht; hängende Arbeiter werden beim Abbruch nicht beendet. Aufwand 2.
7. **`start.sh`: `curl` ohne `--max-time`** — hängt der Server, hängt `start.sh` mit (alte und neue Fassung). Aufwand 1.

Zum Protokoll des Testers: 0.46.1 schrieb nach „FreeCAD-Aufruf …“ bei Erfolg **keine** Zeile mehr. Das Protokoll passt also ebenso zu „alles lief
durch, gehangen hat Browser oder Beenden“ (1, 4). Der Schluss oben („danach blieb etwas stehen“) ist daraus nicht zu ziehen. 0.46.3 schreibt genug.

Anbau statt Konzept (Capacities „Klare Ingest-Pipeline“):
8. Der Commit „UNFERTIG … Nicht nach main“ ist auf `main` gelandet; 0.46.0 hat das Selbstschliessen still zurückgenommen. Übrig und mit §3.4
   zu streichen: `einlesen=0` beim Hochladen, `_kette_buchen`.
9. Während des ganzen Hintergrundlaufs alle 5 s die ganze Liste neu (Server baut alle Kacheln neu); jeder Laufbeginn schickt zuerst den alten
   „fertig“-Stand (`_setze(fcstd_frage=0 …)` vor dem Zähler) und lädt ein weiteres Mal. Aufwand 2–3.
10. Ein Status-Dict für Einlesen und Worker; der Worker heisst `nur_cad`. Teil des Umbaus.

Kleineres: „EIGENE“-Markierungen in sechs Dateien (behalten oder raus, entscheidet der Anwender); Kommentar „3 × 1 MB“, Protokoll hat 4 MB.

Repo (Capacities „Repo bereinigen“): `ccr-b2d020e3` ist ganz auf `main`; `ccr-97d3e8b3` (0.47.0) überholt; `ccr-790df345`, `ccr-ad9349b7`,
`claude/intelligent-babbage-…`, `claude/intelligent-hawking-…` (Stand 1.–2.10.) mit vielen Commits, die inhaltlich nicht auf `main` sind —
vor dem Löschen einzeln ansehen. Das Repo selbst ist 2 MB; aufgebläht ist eher diese Datei.

**Entschieden (7.10.2026): robuste Pipeline nach KONZEPT §3.4 bis 0.50**, Schritt für Schritt, je ein Schritt pro Chat; nach jedem
alle Suiten samt `test_ui`. Der Tester wird mit dem Hänger nicht weiter belastet: die Pipeline soll die Stellen nicht mehr haben, an
denen etwas hängen kann (Ursache bei ihm unbewiesen; sein Protokoll 0.46.3 zeigt: Server und Einlesen fertig in 7 s, der Browser nicht).
1. **Erledigt (0.47.0, 7.10.2026):** Befunde 1, 2, 3, 5, 6, 7.
   - Ein Fehler im Einlesen endet in der Phase „fehler“ mit Grund (`abbruch`); das Fenster zeigt ihn mit OK.
   - Ein Wunsch, während ein Lauf endet, geht nicht verloren (`_faden = None` unter der Sperre).
   - Abbrechen wirkt binnen Sekunden, auch wenn ein Arbeiter hängt (Warten in 0,5-s-Schritten, auch bei der Einzelwiederholung);
     beim Abbruch werden die Arbeiter beendet — vorher hielt ein hängender Arbeiter sogar das Ende des Prozesses auf (Gegenprobe: 200 s).
   - Alle 46 Routen mit Körper sind `def` statt `async def`; den Körper lesen `json_koerper`/`roh_koerper` (Depends). Damit laufen
     Datenbank, Platte, FreeCAD und der Dateidialog im Thread-Pool, nicht in der Ereignisschleife.
   - Beenden schliesst zuerst die Live-Verbindungen (`Verteiler.beenden` aus `handle_exit`), dazu `timeout_graceful_shutdown=5`:
     mit offenem Tab vorher erst nach dem Schliessen des Tabs, jetzt in 0,2 s.
   - `start.sh`: jede Abfrage mit `-m`; ein Server, der den Port hält, aber nicht antwortet, wird erkannt und nach Rückfrage beendet
     (notfalls `kill -9`).
   - Tests: test_scan +5, test_api +3, test_ui +1, jede mit Gegenprobe. Die 0.47.0 auf `ccr-97d3e8b3` kam nie auf `main`; diese ist eine andere.
2. **Erledigt (0.48.0, 7.10.2026):** kein Einlesen-Fenster mehr (es zeigt nur noch den Fortschritt beim Hochladen, bis Schritt 4);
   ⟳ dreht sich, neben „Bibliothek“ „liest ein …“, dann Meldung („3 neue Modelle“ mit „Zeigen“, „Nichts Neues – n Dateien geprüft“,
   Hinweise mit Knopf nach Bereinigen) und das Ergebnis bleibt stehen. Im Importieren-Menü und oben rechts entfallen Einlesen bzw. Ergebniszeile.
   - Neu gespeicherte Datei am selben Ort zählt als „geändert“, nicht „neu“ (Status `geaendert`).
   - Ein Lauf beginnt mit EINER Statusmeldung (vorher zuerst nur die neue Nummer mit dem alten Ergebnis — Befund 9, beim Bauen gefunden).
   - „Zuletzt eingelesen“ gilt ab Ende des Einlesens, nicht erst nach FreeCAD.
   - Live-Verbindung schickt beim (Wieder-)Verbinden zuerst den ganzen Stand; ältere Antworten von Liste und Seitenleiste werden verworfen;
     während des Einlesens lädt eine geänderte Kachel nur sich selbst (`/api/modelle/kacheln`).
   - Tests: test_scan +3, test_api +2, test_ui +4 (Fenster-Prüfungen ersetzt), je mit Gegenprobe.
3. Worker getrennt vom Einlesen, Warteschlange je Datei im Bestand; Einlesen eines Teilbaums. Aufwand 3–4.
   **Erledigt (0.49.0, 7.10.2026)** bis auf das Einlesen eines Teilbaums (zurückgestellt, braucht erst der Explorer):
   `scan.py` ist geteilt in `_Bahn` (Thread mit Folgelauf, Pool, Abbrechen, Stand), `Worker` (Vorschaubilder, kleine Bilder, FreeCAD;
   Stand `worker`) und `Scanner` (`einlesen()`; stösst den Worker an, wartet nicht). `lauf()` bleibt ein ganzer Durchgang ohne Thread
   (Werkzeuge, Tests). Die FreeCAD-Zusage startet den Worker sofort, auch während eines Einlesens. Oberfläche: Anzeige unten links zeigt
   das Einlesen, sonst den Worker; Abbrechen gilt für beide. Tests: test_scan 100/100, test_api 84/84; zwei neue Prüfungen mit Gegenprobe.
   `test_ui` ist für diesen Schritt nicht gelaufen — es läuft einmal vor 0.50.
   **Jede Suite hat eine Zeitgrenze** (`muster.zeitgrenze`, 300 s, test_ui 900 s, `MUSTER_ZEITGRENZE`): eine hängende Suite bricht ab und
   zeigt die Zeile, an der sie stand.
   **test_ui gekürzt (7.10.2026):** 98 → 65 Prüfungen, einmalige Gestaltung gestrichen (Formatfarben, Zeit in Worten, Tab-Titel,
   Galerie-Blättern, Seitenleisten ziehen, Kaufteil-Wähler-Details, Baugruppen-Beschreibung, Entwurf in drei Ansichten u. a.).
   Ein Lauf: 60 s. Regeln dazu in CLAUDE.md.
4. Hochladen als Bedienung raus (sicheres Ablegen bleibt im Code für den späteren Explorer), Ordner ziehen = hinzufügen. Aufwand 2–3.
   **Paket A erledigt (7.10.2026):** Menüpunkt „Dateien hochladen“, Dateifeld, Liste/Zielordner und das Fenster `#einlesen` sind weg
   (JS, HTML, CSS). `/api/hochladen` und `Katalog.hochladen` bleiben. Modelldateien ins Fenster gezogen → Hinweis auf „Ordner hinzufügen“;
   Bilder auf Vorschau/Druck wie bisher. test_ui: Hochladen-Prüfungen (2) raus, „Nimm.stl“ fürs Aufräumen wird direkt angelegt.
   Handbuch nachgezogen. test_ui nicht gelaufen (läuft einmal vor 0.50).
   **Ziehen ins Fenster aus (7.10.2026, Anwender):** Modelle und Ordner von aussen ins Fenster gezogen bewirken nichts mehr (keine Fläche,
   kein Hinweis; der Browser öffnet die Datei auch nicht). Aufnehmen nur über ＋ Importieren › Ordner hinzufügen; KONZEPT §3.4 angepasst.
   Bilder auf Vorschau/Druck ziehen bleibt. Damit ist Schritt 4 fertig.
   **Fehler aus dem Test des Anwenders (Windows, 8600 Dateien, 7.10.2026):** Liste blieb bei 100 Einträgen, Filter und Klicks ohne
   Reaktion. Ursache: das Nachladen aus Live-Meldungen (alle LIVE_SCAN_MS) startete, auch wenn die vorige Liste noch unterwegs war; dauerte
   eine Liste länger als 5 s, wurde jede Antwort verworfen (auch die auf Filter-Klicks), und auf dem Server stapelten sich Listen.
   Behoben: das Nachladen wartet auf die laufende Liste (`ladeModelle.unterwegs`/`.danach`). Nachgestellt im Browser mit künstlich
   langsamer Liste (1,5 s, Meldungen alle 0,2 s, 6 s): vorher 0 Antworten gezeichnet, jetzt 3. Prüfung dazu gehört noch in test_ui.
   **Noch offen aus demselben Test:** Anzeige unten links („Schritt 1 von 2“, dann „1 von 3“) und die Texte dazu stimmen nicht.
   Protokoll schreibt „nimmt Anfragen an“, bevor der Port offen ist (bei belegtem Port falsch).
5. *Offen:* automatische Überwachung in 0.50 oder danach. Aufwand 2.
Abnahmefall und Härtetest: KONZEPT §3.4.

## Zuerst wissen

- **Server und Tests laufen nur mit `flatgraph`.** In Cloud-Sitzungen ist
  `flatgraphdb` nur erreichbar, wenn es beim Start als Repository
  angehängt wurde (öffentlich reicht nicht; ohne Anhängen: HTTP 403).
  Ohne flatgraph lassen sich weder die Suiten noch `tests/test_ui.py`
  ausführen. Erst prüfen: `python3 -c "import flatgraph"`.
- `flatgraph` liegt als Nachbar-Repo: `PYTHONPATH=/home/user/flatgraphdb`.
- Arbeitsweise: `CLAUDE.md` (eine Sache pro Antwort, Tests sparsam).

## Erledigt

Runde 1 (13 Punkte): verlorene Klicks (Ursache: GET schrieb
`zuletzt_angesehen` → Live-Meldung → komplettes Neuzeichnen; jetzt kein
Schreiben mehr und Abgleich statt `innerHTML`), Enter im Dialog = Hauptaktion,
Kaufteile-Wähler (feste Höhe, alle Kategorien, ✓ nimmt zurück), Baugruppe
(Name/Beschreibung an Ort und Stelle, ganze Zeile klickbar, Notizfeld raus,
Raster/Liste/Sortieren dort ausgeblendet), Seitenleisten in der Breite
ziehbar, schmale Scrollleisten, Zähler „Neu hinzugefügt“.

Runde 2: **c)** Inspektor: Vorschau und Name bleiben oben fest, die
technischen Daten heissen „Modelldaten“, stehen unter „Zum Drucken“ und
sind standardmässig offen.

Runde 3 (Galerie im Inspektor): Blättern zeichnet nur noch das Bild neu —
Pfeile, Leiste und Aktionen bleiben stehen (vorher: Flackern, verlorene
Klicks). Rechtsklick auf das Bild: „Als Vorschaubild festlegen“, „Bild
entfernen“, „Eigenes Bild hinzufügen“. Das Original (aus der Datei /
berechnet) kann Vorschaubild der Kachel sein (Feld `vorschau_art`). Ziehen
aus der Leiste legt keine Kopie mehr an. „← Baugruppe“ lag unter dem festen
Kopfstück und ist jetzt darin. `test_ui.py` läuft mit flatgraph: 51/51.

Runde 4 (Phase 1 ohne Druckmanagement): `PHASE = 1` in `app.js`
(`?phase=2` in der Adresse schaltet um; die Tests laufen so). Die Warteschlange
ist überall ausgeblendet (Seitenleiste, Inspektor, Stapel, Menüs, Baugruppe).
Baugruppen und „Gedruckt“ bleiben, beides von Hand pflegbar.

Runde 5 (Drucke, 0.19.0): Inspektor mit Reitern **Übersicht / Drucke / Datei**
(Vorschau, Name, Öffnen und Reiterleiste bleiben oben fest, der Reiter wird
gemerkt). Drucke Stufe a (KONZEPT §4.6): `PRINT_JOB` an einem oder mehreren
Modellen, Zähler und „gedruckt“ abgeleitet (am Modell vorgehalten:
`drucke_n`, `gedruckt`, `ref_werte`), Referenzdruck liefert Gewicht/Zeit/
Filament der Kachel und Übersicht, Fotos je Druck, Formular zum Anlegen und
Bearbeiten, „Zusammen gedruckt …“ im Menü bei mehreren gewählten Modellen,
alte Haken werden zu leeren Drucken. Demo: `werkzeuge/demo_drucke.py`
(`./start.sh --demo` und der Codespace rufen es auf). Start für Tester:
`./start.sh` (Manjaro).
Noch nicht: Baugruppensummen nehmen den Referenzdruck nicht (Dateiwert);
die Löschvorschau nennt Drucke nicht; Plattenwerte werden nicht verteilt.

Schrift (0.19.1): alle Schriftgrössen gestaffelt grösser (kleinste 9 → 11 px,
Fliesstext 13 → 14 px), Kacheln 246 → 262 px, Listenzeilen 36 → 38 px. Wer
weitere Stellen zu klein findet: die Stufen stehen als Variablen
`--fs-*` in `app.css`.

Kachel beruhigt (0.19.2): Checkbox und ♥ nur beim Darüberfahren (♥ bleibt, wenn
gesetzt; Checkboxen bleiben, sobald etwas gewählt ist), NEU als Punkt,
Gedruckt als „✓ 2×“, Mass gerundet, Gewicht rechts neben höchstens zwei
Tags, Ecken 10 px, Rahmen nur bei Hover/Auswahl. Richtung: etwas Apple,
„einfach an der Oberfläche, viel darunter“. Als Nächstes aus dem Gespräch:
Filterleiste (Tags nur wo Platz ist), Seitenleiste (Tipp wegklickbar, leere
Abschnitte nur Titel), Schrift (Mono nur für Zahlen).

Filter ohne Tag-Lärm (0.19.3): Filterleiste = Material und **Format** als Chips
(Format ist aus der Seitenleiste in die Leiste gezogen), Tags nur als gewählte
Chips zum Wegnehmen; Tags stehen weiter in der Seitenleiste, im Inspektor und
in der Suche (`tag:`). Auf der Kachel keine Tags mehr (Zeile 3 = Gewicht).
Einstellung **„Tags aus dem Dateinamen vorschlagen“** (`auto_tags`, Vorgabe an,
wie im 3MF Katalog) im Einstellungsdialog; gilt für neu Eingelesenes, Vorhandenes
bleibt. Nicht gebaut: „Auto-Tags entfernen“ für den Bestand (Aufwand 2).
Verworfen: Filter-Dropdowns mit Kaskade — für wenige Werte nicht nötig.

Seitenleiste ruhig (0.19.4): Abschnittsüberschriften klein, grau, in normaler
Schrift und ohne Bänder/Linien (Abstand trennt), etwas luftigere Einträge, der
Baugruppen-Hinweis ist eine wegklickbare Zeile statt eines Kastens (kommt erst
wieder bei mehr Vorschlägen). Noch offen aus dem Gespräch: Schrift im Rest der
Oberfläche (Mono nur für Zahlen), Einstellungsdialog mit Reitern.

Seitenleiste wie VS Code (0.20.0): oben Suche und drei Icon-Knöpfe für die Ansichten
(Alle, Neu, Favoriten), darunter die Ordner als Explorer (nimmt den freien Platz),
unten einklappbare Felder (Baugruppen, Sammlungen, Aufräumen, Tags) mit feinen
Linien und Kopfband; das Feld mit der aktuellen Wahl trägt einen Akzentbalken.
Unterordner sind 14 px je Ebene eingerückt, mit Führungslinie (der Fehler aus
0.19.4: eine Regel hatte die Einrückung überschrieben). **Tests:** `test_ui.py`
nur bei Änderungen an der Oberfläche und nur einmal vor dem Commit.

Seitenleiste nachgebessert (0.20.1): Felder lassen sich an ihrer Oberkante in der Höhe
ziehen (Höhe gemerkt, Doppelklick = Inhaltshöhe), der Explorer (Ordner) bleibt bei
mindestens 120 px stehen, unten gedeckelte Felder (40 %) scrollen innen — das volle
Tag-Feld verdrängt die Ordner nicht mehr. Suchfeld mit × (und Esc). Unten eine
Statuszeile „57 Modelle · 3 ausgewählt“ statt der Zahl in der Kopfzeile.
Geprüft nur mit einem Playwright-Skript, nicht mit `test_ui.py`.

Seitenleiste als Split View (0.20.2): alle Höhen rechnet `seitenLayout()` in `app.js`,
nicht mehr das CSS. Jedes offene Feld hat dieselbe Mindesthöhe (125 px = 4,5 Zeilen à 22 px, bei sehr
niedrigem Fenster gemeinsam kleiner), eingeklappt nur die Kopfzeile. Das erste offene
Feld (Ordner) ist das biegsame. Griff an der Oberkante jedes Feldes verschiebt die
Grenze: das eine wächst, die auf der anderen Seite schrumpfen der Reihe nach bis zur
Mindesthöhe. Höhen gemerkt (`localStorage` „felder“). Zeilen 24 px, Köpfe 24 px.
Geprüft mit Skript (Summe = Höhe, Mindesthöhe, Ziehen in beide Richtungen),
nicht mit `test_ui.py`.

Bibliothek (0.20.3): das obere Feld der Seitenleiste heisst „Bibliothek“ und lässt sich
nicht mehr zuklappen (wie der Explorer in VS Code: zu klappen sind nur die Ordner
darin). Es ist immer das biegsame Feld. Offen: ein Gegenstück für die rechte
Seitenleiste (Details) — Vorschlag im Gespräch, noch nicht entschieden.

Vorschau im Inspektor ziehbar (0.20.4): Griff unter der Vorschau (erscheint beim Darüberfahren),
Höhe 48 px bis 60 % der Fensterhöhe, die Leiste mit den kleinen Bildern entfällt unter 120 px,
gemerkt (`localStorage` „bildhoehe“), Doppelklick = 220 px. Rechte Seitenleiste als Felder
(Split View wie links): bewusst zurückgestellt.

Drucke und Bilder (0.20.5): Bilder lassen sich auf einen Druck ziehen (Foto dazu) oder auf den
leeren Teil des Reiters „Drucke“ (neuer Druck mit dem Foto); ein Bild irgendwo sonst wird nicht
mehr als Modelldatei eingelesen (Hinweis statt Fehlversuch). Die 2D-Vorschau schrumpft jetzt
mit dem Rahmen (vorher bestimmte die Eigengrösse des Bildes die Zeilenhöhe).

## Entschieden, noch nicht gebaut (Phase 1)

1. **Drucke Stufe b:** G-Code oder Slicer-Projekt auf einen Druck ziehen,
   Einstellungen auslesen (`GCODE_ARTIFACT`, `PRINT_PROFILE`), Vergleich
   zweier Drucke (KONZEPT §4.6). Danach Löschvorschau und Baugruppensummen.
2. **Einstellungsdialog neu:** Reiter links, rechts nur, was zum Thema gehört
   (wie pDMS). Materialien dort anlegen.
3. **Zusammen im Slicer öffnen:** prüfen, ob die Slicer mehrere Dateien in
   **einem** Fenster aufnehmen (ungeprüft, §4.6).

**Bereinigen:** „Aufräumen“ ist aus der Seitenleiste raus. In der Activity Bar
sitzt statt des Papierkorbs ein Besen (🧹) mit Zählabzeichen (Duplikate +
fehlt + unlesbar) und schaltet die ganze Seitenleiste um: Papierkorb ·
Duplikate · Datei fehlt · Unlesbar. Später möglich: Nicht verknüpft, Ohne
Vorschau.

**Karten:** dritte Ansicht neben Raster und Liste — eine Spalte, 118 px hoch,
Bild links, rechts Name, Maße · Gewicht · Grösse, Status, Material und Tags
als Chips, Ordner. Feste Feldauswahl (`zeileK()` in `app.js`).

**Scroll-Leistung (2.10.2026, `messung/scroll_bench.py`, 5000 Modelle, headless):**
Hauptthread je Frame — Raster Skript 2,6 → 1,35 ms (Gesamt 6,2 → 4,6 ms), Karten
1,4 → 1,1 ms; Layout und Stil je ≈ 0,2 ms. Gebaut wurde nur: beim Scrollen
nicht neu zeichnen, solange der Zeilenbereich gleich bleibt. Die Frame-Abstände
(Raster 33 ms, Liste/Karten 17 ms) hängen hier am Malen der Bilder in Software
(ohne Bilder halbiert sich das Raster); `contain` je Kachel brachte nichts.
Auf echter Grafikkarte nicht gemessen.

**Scrollleiste ziehen (2.10.2026, 3000 Modelle, 60 Sprünge, kleine Bilder):**
ohne Aufschub 1844 Bild-Anfragen im Raster (641 in Karten), Hauptthread
51 ms/Frame (25); mit Aufschub 20 (8) Anfragen, 9 ms/Frame (4,8). Die Bilder
werden erst nach 120 ms Ruhe angefordert. Mit 4-MB-Fotos brach der Bench ohne
Aufschub ab (Playwright-Leitung, vermutlich Bench-Artefakt) — mit Aufschub lief er.

**Thumbnails (gebaut):** `?t=1` an den Bild-Adressen liefert eine 320-px-WebP-Fassung
aus `<Bestand>/thumbs/` (abgeleitet, löschbar; erzeugt beim ersten Abruf; Name aus
Pfad + Zeit + Grösse). Kacheln, Zeilen und Karten laden sie, Inspektor und Galerie
das Original; nicht lesbare Bilder fallen auf das Original zurück. Format steht nur
in `THUMB_ENDUNG` (`bestand.py`). Thumbs aus Sicherung/Export lassen: offen.
**Aufschub bleibt:** auch ohne Bilddaten (404) kostet das Anfordern allein beim Ziehen
30 vs. 10,7 ms/Frame im Raster (1844 vs. 20 Anfragen) — Anfragen, nicht Bytes,
sind der Preis.

**Einstellungen:** Dialog wie in pDMS — links Abschnitte (Vorgaben · Einlesen ·
PDF-Export · Programme), rechts der Inhalt, ein gemeinsames Speichern; der zuletzt gewählte
Abschnitt wird gemerkt. `tests/test_ui.py` klickt vor dem Programm-Wähler auf
„Programme“ (ungelaufen). Thumbs im Hintergrund vorbauen: wird ein Issue.
**PDF-Export einstellbar:** Abschnitt „PDF-Export“ im Einstellungsdialog — Strukturstückliste,
Mengenübersicht, Einkaufsliste, Filament, Kennzahlen je ein/aus; dazu Vorschaubilder,
Abhakkästchen, Dateipfade. Gespeichert in `einstellungen.json` unter `pdf`
(`PDF_STANDARD` in `stueckliste.py`); Abschnittsnummern im PDF zählen mit.
Nicht einstellbar (bisher): Papierformat, Schrift, Logo/Titelzeile.

**Programme (Einstellungen):** nur noch zwei Plätze, Slicer und CAD, mit dem gefundenen
Programm vorbelegt; „Ändern …“ öffnet den Dateidialog des Rechners (`dateidialog.py`:
zenity, kdialog oder Tk unter Linux; PowerShell unter Windows; AppleScript am Mac —
**Windows und Mac ungeprüft**), „Automatisch“ nimmt die Wahl zurück. Kein Textfeld,
keine Liste, kein Standard je Format mehr (STEP → CAD, sonst Slicer). Alte Einträge
(`slicer`, `programme`) gelten weiter, bis neu gewählt wird. „Ordner hinzufügen“ nutzt jetzt
ebenfalls den Rechner-Dialog (`POST /api/wurzeln/waehlen`); der eigene Ordnerbaum
(`durchsuchen.py`) bleibt nur als Rückfall, wenn der Rechner keinen Dialog hat (ohne
Pfad-Texteingabe). Mehrere Wurzeln: gleichnamige Ordner tragen den übergeordneten
Ordner als Zusatz („3D-Druck · USB-Stick“); Rechtsklick auf eine Wurzel →
„Aus partAtlas entfernen …“ (Dateien bleiben, Modelle gelten als „Datei fehlt“).

**Hover-Knöpfe (Liste und Karten):** beim Überfahren erscheinen unten rechts (Karten) bzw. am
Zeilenende (Liste) zwei Linien-Symbole — Slicer (Schichten) und CAD (Würfel) — mit Tooltip
„In <Programm> öffnen“; nur, wo die Datei da ist und ein Programm das Format kann
(`hoverAktionen()` in `app.js`). Raster hat sie nicht. Meine Prüfskripte laufen mit
`?phase=2` (Warteschlange sichtbar) — im Normalbetrieb bleibt sie ausgeblendet.

**Gestaltungsregeln:** Maßsystem (Fibonacci 3-5-8-13-21-34-55-89), gemeinsame Kanten, Aktionen
in eigener Spalte auf der Mittellinie — in `KONZEPT.md` („Gestaltungsregeln“) und als `--s1…--s8` in
`app.css`. Umgesetzt für Karten und Liste; die Liste ist entschlackt (Tags und Ordner raus).
Raster-Kachel jetzt 144 × 233 (1 : φ), Rail 55, Ränder 13. Inspektor jetzt im Maßsystem (377 breit, Seitenleiste 233). Als Nächstes prüfen: Seitenleiste links (Felder, Zeilen), Dialoge, Baugruppen-Ansicht.

**Baugruppen-Ansicht (2.10.2026):** Schriftfeld, Reiter Stückliste · Notizen · Anhänge, Stückliste als
nummerierte Tabelle (Zeilen 55), Hover-Knöpfe Slicer/CAD an den Druckteilen, Zähler und Balken weg (auch in der
Seitenleiste). **Notizen und Anhänge sind nur als Layout da („folgt“), nicht verdrahtet.** Das Backend zählt
`erledigt` weiter mit (wird in der Oberfläche nicht mehr gezeigt, `tests/test_baugruppen.py` prüft es noch).

**Gruppieren (2.10.2026):** neben „Sortieren“ eine Auswahl „Gruppieren“ — Keine · Ordner · Format · Material ·
Status · Angelegt; gilt für Raster, Liste und Karten, gemerkt. Gruppenband 34 hoch mit Pfeil (ein-/ausklappen), Haken
(Gruppe markieren) und Anzahl; innerhalb der Gruppe gilt die Sortierung. **Ordner:** nur die nächste Ebene unter der Wahl in der
Seitenleiste (ohne Wahl: mit **einer** Wurzel deren Unterordner — sonst gäbe es nur eine Gruppe und kein Band —, mit mehreren die Wurzeln); jede Gruppe enthält alle Modelle darunter, auch aus tieferen Unterordnern;
Dateien direkt im gewählten Ordner stehen davor als „Direkt in <Ordner>“. Klick auf den Namen geht in den Ordner
(Seitenleiste klappt den Weg auf), Pfeil klappt die Gruppe zu, Haken markiert sie. **Nur eine Gruppe → kein Band**
(Blattordner). **Pfad über der Liste:** „Alle › 3D-Druck › Technik“, dezent, jeder Teil führt zurück (nur bei gewähltem Ordner). Tags, Sammlungen, Baugruppen bewusst nicht (Mehrfachzugehörigkeit).
Nicht geprüft in `tests/test_ui.py` (keine neue Prüfung); Scroll-Bench unverändert. Kein klebendes Band beim Scrollen.

**Programmerkennung unter Linux (2.10.2026, für den Test mit Anycubic Slicer Next 1.3.9.4 auf Manjaro):**
Flatpak-Exporte werden zusätzlich über ein Stichwort im Namen gefunden (Kennung des Anycubic-Flatpaks ist uns unbekannt);
AppImages nur mit Ausführrecht; mehr Ordner (/opt, ~/Desktop, ~/Schreibtisch, ~/Apps, ~/bin); eine AppImage, die sich
sofort beendet, meldet FUSE (`sudo pacman -S fuse2`); „Datei nicht ausführbar“ sagt, wie man es ändert; fehlender
Dateidialog nennt `sudo pacman -S zenity`. **Nicht an einem echten Manjaro/Anycubic geprüft** — nur simuliert.
Quelle der Linux-Pakete: Releases von develonrails/anycubic-slicer-next (AppImage und Flatpak, kein offizieller Hersteller-Build).

**Hover-Knöpfe ohne Programm:** Ist kein Slicer bzw. CAD eingerichtet, bleibt der Knopf gedämpft (gestrichelt) da und führt
in die Einstellungen › Programme; vorher verschwand er still. **Fassung 0.21.0** (die Fassungsnummer war seit 0.20.6 nicht
mitgezogen worden). `tests/test_ui.py` lief am 2.10.2026 durch (58/58, ein Test an die zwei Programm-Plätze angepasst).

**Einlese-Dauer sichtbar (0.22.0):** nach dem Einlesen bleibt in der Statuszeile oben „Eingelesen: 2 413 Dateien, 2 413 neu
in 48 s“ stehen (auch nach Neuladen), dazu ein Hinweis. Für den Test mit dem ganzen Bestand eines Anwenders. Der Wert ist
die Dauer des gesamten Laufs inklusive der Vorschauen (`dauer_s` aus `scan.py`).

**Programmstart mit Diagnose (0.22.1):** die Ausgabe eines gestarteten Programms geht nach `<Bestand>/arbeit/programmstart.log`
(Standard: `~/.local/share/partatlas/arbeit/`); beendet es sich binnen 1,2 s mit Fehler, steht Code und Anfang der Ausgabe in der
Meldung. Preis: der „wird geöffnet“-Hinweis kommt bei laufenden Programmen etwa 1,2 s später. Auslöser: Test mit Anycubic Slicer
auf Manjaro — FreeCAD startete (3D-Ansicht nur nicht eingepasst: `V`, `F`), der Slicer nicht, Grund unbekannt.

**Lesbarkeit (0.23.0), Rückmeldung eines Testers:** `--ink-3` hatte nur 3,8–4,0 : 1 (dunkel) bzw. 3,0–3,3 : 1 (hell); jetzt
etwa 6 : 1, `--ink-2` etwa 9 : 1 bzw. 8 : 1. Kleine Schrift von 11/11,5 auf 12/12,5 px, Einstellungsdialog 14,5 px.
Regel steht in `KONZEPT.md` (Gestaltungsregeln, 8). Hell und dunkel im Einstellungsdialog geprüft, nicht überall.

**Aktualisierung prüfbar (0.23.1):** die Fassung steht klein neben dem Logo; Skript und Stile (`/web/…`) werden bei jedem Aufruf
per ETag neu geprüft, damit nach einer Aktualisierung nicht die alte Oberfläche aus dem Zwischenspeicher kommt (three.js bleibt
ewig gecacht). Test: `tests/test_api.py`. Beim Tester: Anycubic Slicer wurde **nicht automatisch gefunden**, nach manuellem
Hinzufügen läuft es — Ort seiner Datei noch offen (würde die Erkennung verbessern).

**Einlese-Dauer je Phase (0.24.0):** Statuszeile nach dem Einlesen: „Eingelesen: N Dateien, M neu in X (Hashen … · Analysieren … ·
Vorschauen …)“; Phasen unter 0,5 s werden weggelassen. Erste Messung (150 Demo-Dateien, 2,5 MB, hier): 8,3 s gesamt, davon **Vorschauen
7,9 s**, Hashen 0,2 s, Analysieren 0,2 s — die Vorschaubilder (STL werden gerechnet) sind der Hebel, wenn das Einlesen schneller werden
soll. Tester: ein Ordner mit 330 MB brauchte geschätzt 1,5–2 min (noch nicht aus der Statuszeile abgelesen).

**Roadmap in der Oberfläche (0.25.0):** Knopf ⚑ in der linken Leiste über den Einstellungen → Fenster „Wohin partAtlas geht“ mit drei
Gruppen (Jetzt da · Als Nächstes · Später), je Punkt Überschrift und ein Satz, keine Termine. Inhalt in `web/roadmap.js` (`ROADMAP`);
**beim Fertigstellen eines Punkts dort von „Als Nächstes“ nach „Jetzt da“ schieben**. Quelle bleibt KONZEPT §7 und diese Datei.

**Ordner-Wähler (Rückfall) repariert (0.25.1), Rückmeldung eines Testers („Dialog instabil“):** er erscheint nur, wenn der Rechner
keinen Dateidialog hat (kein zenity/kdialog/Tk) — Ursache beim Tester. Behoben: Liste scrollt in fester Höhe statt über Fußzeile und Knöpfe
zu laufen, Zeilen werden nicht mehr gequetscht; im Wurzelverzeichnis wird nicht gezählt (lief durch die ganze Platte) und „/“ sowie
Systemordner lassen sich nicht als Wurzelordner hinzufügen (Server und Dialog). `start.sh` warnt, wenn zenity/kdialog fehlt; README
nennt `zenity` als Voraussetzung. Kopfzeile bricht nicht mehr um (Einlese-Zeile kürzt sich, Tooltip zeigt alles).

**Einlesen robuster und schneller (0.25.2):** (1) Vorschau-Status wird in Gruppen zu 100 in einer Transaktion geschrieben statt einzeln mit
je einem fsync. (2) Stirbt ein Arbeiter hart (Speichermangel) oder wirft er eine Ausnahme, wird nur diese Datei als Fehler/„unlesbar“
gemeldet und der Lauf geht weiter (`Scanner._verteilen`: erst alles parallel, nach einem Absturz in Wellen, die zerbrochene Welle einzeln).
Vorher brach der ganze Lauf ab und scheiterte beim nächsten Mal an derselben Datei. Geprüft in `tests/test_scan.py` (42/42) mit
Gegenprobe. **Nicht gemessen**, wie viel (1) bringt — keine grossen Bestände mehr gemessen. Daten des Testers (351 Dateien, 149 neu, 29,8 s):
Vorschauen 25 s (84 %), Hashen 2,9 s, Analysieren 1,8 s. **Noch offen:** (3) einmal parsen statt dreimal (Hash, Analyse, Render), sowie
eine Zeitgrenze je Datei (ein hängender Render hält den Lauf auf).

**Abbrechen-Knopf fürs Einlesen (0.26.0):** in der Kopfzeile neben der Statuszeile „Abbrechen“, solange gelesen wird; danach „Abgebrochen nach X s,
N Dateien“ (N = neu angelegt, verschoben, Vorschauen fertig), keine „Eingelesen“-Zeile. `Scanner.abbrechen()` setzt ein `threading.Event`, das das
Suchen, das Hashen (die Schleife über `pool.map`) und `_verteilen()` je Ergebnis prüft — nie innerhalb einer Transaktion; was analysiert ist, wird noch
als Gruppe geschrieben. Bei Abbruch wird **nichts entfernt** (die Liste der gesehenen Orte ist unvollständig) und kein Folgelauf gestartet. Der nächste
Lauf macht über Ort, Grösse und Zeit dort weiter; ausstehende Vorschauen bleiben „ausstehend“. Endpunkt `POST /api/scan/abbrechen` (`{"abgebrochen": bool}`).
Geprüft in `tests/test_scan.py` (50/50) und `test_api.py` mit Gegenproben (Ereignis nie gesetzt; Prüfung in `_verteilen` weg; Prüfung nach dem
Analysieren weg). **Nicht geprüft:** `test_ui.py` (nach Absprache), der Knopf im Browser; die Prüfungen beim Suchen und vor dem Analysieren sind
doppelt abgesichert, eine einzelne davon zu entfernen lässt keinen Test fallen. Ein Arbeiter, der gerade eine Datei bearbeitet, läuft zu Ende
(Abbruch wartet nicht darauf).
**Zeitgrenze je Datei (0.41.2):** `Scanner._verteilen` wartet nur noch `ZEITGRENZE` (180 s) auf das *nächste* fertige Ergebnis; kommt keins, wird der Pool beendet (`terminate`, sonst liefe der Hänger weiter) und das Wellen-Verfahren findet die Datei, die einzeln mit derselben Grenze als Fehler „Zeitgrenze … überschritten“ gemeldet wird. Ein hängender Render kostet bis zu etwa 3 Grenzen. Gilt für Vorschauen (und alles andere über `_verteilen`), **nicht** fürs Hashen (`pool.map`). Geprüft in `test_scan` (73/73); Gegenprobe ohne `terminate` fällt (Lauf hängt), die ohne Grenze im Einzelversuch fällt ebenfalls (Lauf hängt, Abbruch nach 200 s).
**Thumbs vorbauen (0.41.3):** letzte Phase `thumbs` im Lauf (auch beim reinen FreeCAD-Lauf), `Scanner._thumbs`: alle Bilder in `vault/vorschau` und
`vault/bilder`, Threads, vorhandene werden übersprungen, ein unlesbares Bild stört nicht (bleibt beim Original); Statuszeile „Kleine Bilder vorbereiten“. Bisher erzeugte sie
erst der erste Abruf — das erste Scrollen durch einen frischen Bestand wartete auf tausend Verkleinerungen. Geprüft in `test_scan` (75/75) mit Gegenprobe, `test_api`;
**nicht gemessen**, wie lang die Phase bei grossen Beständen dauert, und nicht in `test_ui.py` (eine Textzeile in `app.js`). Vorgebaut werden auch Bilder, die keine Kachel zeigt
(`extrahiert` neben `berechnet`).
**Schlafmodus (0.41.4), Rückmeldung des Testers (i7 920, vermutlich 8 GB):** er schickte den Rechner nach dem Einlesen der FreeCAD-Library (8 946 Dateien: FCStd 3 268, STEP 2 894) schlafen.
Die Statuszeile nannte „7 h 57 min“, davon „STEP (FreeCAD) 7 h 45 min“ — das war Wanduhr **mit** Schlaf. **Nachgemessen am 5.10.2026** an den Schreibzeiten von `netz/` (je Stunde):
4.10. 23 Uhr 300, 5.10. 0 Uhr 4 920, 1–6 Uhr **0**, 7 Uhr 635 = 5 855 Netze + 22 Fehler (Protokoll) = 5 877 offene Dateien. Die echte Rechenzeit lag bei **gut 1 h 25 min,
rund 1 Datei je Sekunde**, auf dieser Maschine mit einem FreeCAD-Prozess. (Erste Annahme „4,8 s je Datei“ war falsch; ein Zwischenstand „vielleicht hat er nachts gearbeitet“ ebenso.)
Die angezeigten „2 000 nach 45 min, 8 000 am Morgen“ passen dazu: 2 000 ≈ FreeCAD-Stand nach 45 min (300 bis Mitternacht, danach ca. 80 je Minute); 8 000 ≈ 8 294 neu = 2 417 Dateien ohne FreeCAD (Vorschauen in den ersten ca. 10 min) + 5 877 FreeCAD. Beim Schlafen war FreeCAD nicht fertig (635 Netze erst nach dem Aufwachen).
Ausserdem mass `cad.py` die Zeitgrenze mit `time.time()`: springt die Uhr beim Aufwachen, galt die Datei in Arbeit als hängend. Jetzt `time.monotonic()` in `cad.py` und für die Dauern in `scan.py`.
Geprüft in `test_cad` (13/13, springende Uhr mit Gegenprobe) und `test_scan`. **Nicht belegt:** dass der Fehler den Tester tatsächlich traf (im Protokoll steht um 7:30 keine Zeitgrenze-Zeile).
Nicht geprüft: ob `monotonic` auf Windows/Mac den Schlaf mitzählt (Linux: nein); die Statuszeile zeigt dort weiter die Wanduhr-Dauer.
**Lehre für künftige Messungen:** Dauern aus der Statuszeile nie als Rechenzeit lesen, wenn der Rechner schlafen konnte; die Schreibzeiten in `netz/`, `thumbs/` oder `vault/vorschau/`
(`ls -l --time-style=+%d.%H <Ordner> | awk '{print $6}' | sort | uniq -c`) sind die belastbare Quelle. Der Bestand liegt unter `~/.local/share/partatlas/` (`XDG_DATA_HOME` / `PARTATLAS_BESTAND`
verschieben ihn). `ps -C python3` findet den Server auf Manjaro nicht zuverlässig: `ps -eo rss,cmd --sort=-rss | head -8`.
**Offen aus dem Gespräch:** UI stockt beim Einlesen auf dieser Maschine bis zu einer Minute (Arbeiter laufen mit normaler Priorität, `Kerne − 1` Stück) — Vorschlag: niedrige Priorität,
weniger Arbeiter, Thumbs-Threads begrenzen, Dateien nach Grösse aufsteigend an FreeCAD (Aufwand 2). Parallele FreeCAD-Prozesse sind bei ca. 1 Datei/s weniger dringend.
**Einlesen verständlich und die Oberfläche bedienbar (0.42.0), Rückmeldung des Testers:** „man muss verstehen, was läuft und wie viel fertig ist (8 Stunden oder 15 min?), und die Oberfläche muss bedienbar bleiben“.
(1) Anzeige beim Zahnrad: „Schritt 4 von 5“, Zähler, **Restzeit aus dem Tempo der laufenden Phase** (`restzeit()` in `app.js`, erst ab 10 Dateien und 20 s — vorher geraten), und schon in den frühen Phasen
„Danach: FreeCAD für N Dateien — das dauert am längsten“ (`cad_voraus`, `phase_s` im Status). (2) Arbeiter und FreeCAD laufen mit **niedriger Priorität** (`os.nice(10)` bzw. `nice -n 10`, Windows
`BELOW_NORMAL_PRIORITY_CLASS`), **höchstens die Hälfte der Threads** als Arbeiter (vorher Kerne − 1), Thumbs mit höchstens 2 Threads. (3) FreeCAD bekommt die **kleinen Dateien zuerst**.
Geprüft in `test_scan` (78/78), `test_cad` (14/14), `test_api`, `test_ui` (81/81) mit Gegenproben (ohne Initializer, ohne Sortierung, ohne `cad_voraus`, ohne `nice`); die Restzeit-Rechnung mit `node` an Beispielen.
**Nicht geprüft:** die neue Anzeige im Browser (kein Test in `test_ui.py`, keine Bildschirmprobe), Windows/Mac (Priorität, `monotonic`), und **ob die Oberfläche auf dem Rechner des Testers (i7 920) jetzt reagiert** —
das ist die eigentliche Probe; Rückmeldung abwarten. Die Restzeit kann bei sehr ungleichen Dateien schwanken (kleine zuerst: anfangs eher zu optimistisch).
**Formatfarben: die Linie (0.43.0), Wahl des Testers nach Mock (`mock/format_farbe.html`, `mock/format_vorher_nachher.png`):** eine 3 px breite Linie in der Farbe des Formats — oben an der Kachel (Raster), links an Karte und
Listenzeile (`data-f` am Element, `::before` in `app.css`); STL blau, 3MF grün, STEP orange, FCStd violett, OBJ türkis (gleiche Helligkeit und Sättigung, nur der Farbton). Die Format-Chips der Filterleiste tragen denselben
Farbpunkt als Legende. Keine Tönung (Variante B): sie wurde nicht gewählt; der Mock bleibt, falls es wiederkommt. **Nicht** nach Baugruppe: ein Modell kann in mehreren stecken. Ggesehen im Browser in Raster, Karten und Liste
(dunkel), geprüft in `test_ui` (84/84, Gegenprobe mit gleichen Farben und Höhe 0 fällt), nicht geprüft: hell, Windows/Mac. Die Linie überdeckt oben 3 px der Vorschau. Nicht berücksichtigt: Farbenblindheit — das Format
steht weiter in der Endung und im Chip.
**Zwei weitere Ideen zum Format, nur als Mock (`mock/format_vorschau.html`, `.png`):** D = Format als kleine Beschriftung unten links auf dem Vorschaubild (neutral, immer lesbar auch bei abgeschnittenem Namen „battery-AA.FCS…“,
Aufwand 1); E = Objektfarbe in der Vorschau nach Format (Aufwand 2–3, Dagegen: die Objektfarbe sagt heute etwas — Filamentfarbe bei 3MF, blaue Platte; Farbtonverschiebung beim Anzeigen trifft auch Bilder aus der Datei;
nur für die vom Programm gerechneten erwägen). Beide lassen sich mit der gebauten Linie verbinden. Nicht entschieden.
**Reiter „Verwendet“ und Vor/Zurück (0.44.0), Wunsch des Testers (Rückverweise wie bei Capacities, Sprung wie in pDMS):** vierter Reiter im Inspektor zwischen Übersicht und Drucke: Baugruppen (mit Menge), Sammlungen, Tags, Drucke
(wechselt zum Reiter „Drucke“) und Ordner des Modells; **jede Zeile springt dorthin** (`data-springe`, `springeZu()` in `app.js`; Baugruppen öffnen wie überall). Die Angaben kommen aus dem Modell (flatgraph-Nachbarschaft, kein neuer
Endpunkt); die Zahl am Reiter = Baugruppen + Sammlungen. **Vor und Zurück:** zwei Knöpfe ‹ › neben dem Logo und Alt+←/→ bzw. Maustasten, über den Verlauf des Browsers (`history.pushState`): `navigiere()` hält vorher und nachher eine
Momentaufnahme fest (Ordner, Sammlung, Ansicht, Filter, Suche, Baugruppe, gewähltes Modell); `popstate` stellt sie wieder her. Eingehängt sind die Sprünge über Seitenleiste (Ansicht, Ordner, Sammlung, Besen),
Baugruppen (auch Unter-Baugruppen) und „Verwendet“. **Nicht** im Verlauf: Filter-Chips, Tags in der Leiste, Suche tippen, Gruppieren/Sortieren — sie ändern die Ansicht, ohne einen Schritt zu setzen.
Geprüft in `test_ui` (91/91, Gegenprobe ohne Sprung fällt), im Browser angesehen (dunkel). Nicht geprüft: Firefox (Verlauf, Alt+←), hell, Windows/Mac; nach Neuladen steht „Vor“ aus, obwohl der Browser eins hätte.
**Offen:** Tag-Chips in der Leiste und Filter in den Verlauf nehmen; Rückverweise auch für Sammlungen/Baugruppen („welche Modelle?“ ist die Ansicht selbst), `traverse` für mehrstufige Abfragen.
**Fassung im Tab-Titel (0.44.1), Wunsch des Testers:** „partAtlas 0.44.1“ statt „partAtlas“ (aus `/api/stand`, gesetzt in `app.js`), damit man bei mehreren Tabs sieht, welche Fassung läuft. Die Fassung kommt vom Server und wird
beim Start gelesen: nach `git pull` ohne Neustart zeigt der Tab die alte. Geprüft in `test_ui` (92/92) mit Gegenprobe.
**Antwortzeit der Liste (0.44.2), Rückmeldung des Testers („bei 1 000 und mehr Treffern bis 3 Sekunden“):** gemessen am **5.10.2026** auf einem künstlichen Bestand mit 9 040 Modellen (40 echte Modelle 226-fach geklont; Maschine: 4 vCPU Xeon 2,8 GHz, nicht
die des Testers). Vorher: 0,15 ms je Treffer, dazu ein Sockel von ca. 0,25 s je Anfrage (alle Kacheln wurden bei jeder Anfrage neu gebaut, auch für 3 Treffer; `/api/zaehler` baute sie dreimal): alle 9 040: 1,3 s, STL 4 972: 0,9 s,
„halter“ 2 034: 0,31 s, Ordner (280 Treffer): 0,35 s, `/api/zaehler`: 0,78 s. Zwei Ursachen: (1) **FastAPIs `jsonable_encoder` frass 0,7 s von 1,3 s** (`json.dumps` derselben Daten: 0,1 s) — `/api/modelle` wandelt jetzt selbst um;
(2) **Kacheln zwischenspeichern** (`Katalog._kurz_alle`, verworfen bei jeder Änderung am Graphen über `Bestand.generation`; ausgeliefert werden flache Kopien). Nachher: alle 0,32 s, STL 0,13 s, „halter“ 0,06 s, Ordner 0,04 s, `/api/zaehler` 0,11 s.
Der Zwischenspeicher kostet bei 9 040 Modellen ca. 11,5 MB (gemessen), bei 50 000 grob 60 MB (hochgerechnet). Während eines Einlesens ändert sich der Graph ständig, dann bleibt es beim Neuaufbau.
Geprüft in `test_api` (63/63, neue Prüfung „Liste nach Änderung sofort aktuell“ mit Gegenprobe ohne `generation`), alle anderen Suiten und `test_ui` (92/92). **Nicht gemessen:** der Browser (JSON lesen, Liste zeichnen, Sortieren, Gruppieren) und die Maschine des Testers;
**offen**, falls es dort weiter 1–3 s dauert: Liste in Seiten laden statt alle auf einmal, `_kurz` mit weniger Graph-Abfragen (heute 4 je Modell, je mit Sperre).
**Bilder erscheinen langsam (0.44.3), zweite Rückmeldung des Testers („2 bis 3 Sekunden, bis die Bilder da sind“):** das war nicht die Liste (siehe 0.44.2), sondern die Kacheln. Gemessen am 5.10.2026 (Maschine wie oben): eine
Kachel mit fertiger Thumbnail 2 ms, **eine Thumbnail zu erzeugen 17 ms** (Median, max. 54) — auf dem Rechner des Testers das Drei- bis Vierfache, bei 60 sichtbaren Kacheln Sekunden. Die Vorschauen im Bestand (`vault/vorschau/*.png`) sind aber
**schon 320 × 320 und ca. 11 KB**: die „kleine Fassung“ brachte bei ihnen nichts. Jetzt liefert `Bestand.thumb` PNGs bis 320 px und 64 KB direkt aus (kein Umweg, keine Arbeit beim ersten Abruf); grössere (Fotos, grössere eingebettete Bilder) werden weiter zu WebP.
Ausserdem läuft die Thumbs-Phase jetzt **vor FreeCAD** und danach nochmal (vorher erst danach — bei einer grossen Library nach Stunden). Beim Start läuft ohnehin ein Einlesen (`scan_beim_start`), die Phase also auch ohne Klick.
Geprüft in `test_scan` (79/79, Gegenproben: Reihenfolge, kleine Bilder), `test_api` (63/63), `test_ui` (92/92). **Nicht gemessen:** der Browser und die Maschine des Testers — ob es dort jetzt schnell genug ist; falls nicht, bleibt die Zahl der Anfragen (eine je Kachel) und das Entpacken der PNG im Browser.
**Bedienbar beim Einlesen (0.44.4), Rückmeldung des Testers (langsame Festplatte; „wichtig ist die Bedienbarkeit nach dem Start“):** gemessen (5.10.2026): ein Einlesen **ohne Änderungen schreibt nichts** (0 Änderungsmeldungen von flatgraph), der Start
bis zum ersten Bildschirm dauert hier ca. 3 s (Import 1,2 · Bestand öffnen 1,2 · Katalog 0,1 · erste Liste 0,5). Gefunden im Code: (1) die Oberfläche holte bei **jeder** Änderung nach 300 ms Ruhe die **ganze Liste neu** — beim Einlesen von FreeCAD-Dateien
ist das etwa eine Änderung je Sekunde, also dauernd Liste holen und zeichnen, und der Server baute dazu jedes Mal alle Kacheln neu; (2) am Ende jedes Einlesens wurde die Liste **immer** neu geladen, auch ohne Funde. Jetzt: (1) während eines Einlesens höchstens
alle `LIVE_SCAN_MS` (5 s) einmal (`liveAenderung`), ausserhalb weiter 300 ms; (2) am Ende nur, wenn sich etwas geändert hat (`scanHatVeraendert`: neu, verschoben, entfernt, zurückgeholt, aufgeräumt, Vorschauen, FreeCAD, Abbruch, leere Liste).
Geprüft in `test_ui` (94/94, zwei neue Prüfungen, beide mit Gegenprobe). **Nicht gebaut, vorgeschlagen:** Einlesen beim Start erst ca. 10 s nach dem ersten Bildschirm; Platten-Priorität senken (`ionice`, nur Linux, wirkt je nach Scheduler);
Einstellung „Beim Start einlesen“. Kein Überspringen von Ordnern anhand ihrer Änderungszeit — übersieht an Ort und Stelle überschriebene Dateien. Die 30 s bis „ganz geladen“ sind vermutlich das Einlesen beim Start (Suchen allein 12,7 s auf seiner Platte); nicht bestätigt.
**Einlesen beim Start: Einstellung, Vorgabe aus (0.45.0), Wunsch des Testers (eine Library, langsame Platte, „er hört die Platte rattern“):** `Einstellungen › Einlesen › Beim Start einlesen` (`scan_beim_start` in `einstellungen.json`, Vorgabe **aus**;
gilt ab dem nächsten Start; `erstelle_app(scan_beim_start=…)` übergeben geht vor). Eingelesen wird dann mit **⟳ neben „Bibliothek“** — der Knopf ist jetzt **immer sichtbar** (war nur beim Darüberfahren, der Tester fand ihn nicht; ＋ ebenso). Neben „Bibliothek“ steht
**„gerade eben / vor 3 Std. / vor 1 Tag“** (`zuletzt_eingelesen`, nach jedem vollständigen Einlesen in `einstellungen.json` gespeichert, auch über Neustarts; Tooltip mit Datum; schrumpft zuerst und verschwindet bei schmaler Seitenleiste).
Nicht gespeichert wird es bei Abbruch. Folge der Vorgabe aus: Dateien, die ausserhalb verschoben oder gelöscht wurden, erscheinen erst nach dem nächsten Einlesen (Bereinigen › Datei fehlt). Geprüft in `test_api` (69/69: Vorgabe, Neustart ohne/mit Einlesen, Zeitpunkt) und
`test_ui` (96/96: Knopf ohne Hover sichtbar, Zeit in Worten), je mit Gegenprobe; Anzeige im Browser angesehen (normal und schmal). **Nicht geprüft:** Windows/Mac; ob ein Anwender, der die Vorgabe nicht kennt, das Einlesen vermisst — dafür steht die Zeit neben „Bibliothek“.
**Import von 45 Dateien „sehr langsam“ (0.45.1), Rückmeldung aus dem Codespace:** gemessen am 5.10.2026 (43 Demo-Dateien, meine Maschine): ein Arbeiter (2-Kern-Codespace: Kerne − 1 = 1) **10,5 s**, zwei Arbeiter 5,3 s — davon sind alles ausser den
**Vorschauen** unter 0,5 s (Suchen 0, Hashen 0,2, Analysieren 0,1). Das Rendern (`vorschau.rendere`, numpy-Rasterer) kostet **ca. 0,22–0,3 s je STL**; sein Kern ist eine Schleife über die grossen Dreiecke (ca. 800 je Datei), `np.meshgrid` darin
ersetzt (Bilder byte-identisch in 30 von 30, aber nur 5 % schneller). **Fehler von mir (0.44.4) behoben:** die Drosselung der Liste wartete auch bei der ersten Änderung 5 s, ein kleiner Import zeigte seine Modelle also frühestens nach 5 s; jetzt lädt die erste Änderung
nach einer Ruhepause sofort, danach höchstens alle 5 s (`test_ui` 97/97, Gegenprobe fällt). **Offen, nicht gebaut:** (1) für einen **vom Anwender ausgelösten** Import (Hochladen, Entpacken, ⟳) alle Kerne nehmen statt der Hälfte — der Anwender wartet, bei 2 Kernen halbiert sich die Zeit;
(2) den Rasterer selbst beschleunigen (grosse Dreiecke gebündelt statt einzeln, Aufwand 3, Ausgabe müsste Pixel für Pixel gleich bleiben); (3) Hochladen und Weiterleitung im Codespace nicht gemessen — wie viel der Zeit dort der Upload war, ist unbekannt.
**Warteschlange der Vorschaubilder unabhängig vom Einlesen (0.46.0), Wunsch des Testers (wie OCR bei pDMS):** die Warteschlange ist der Zustand „ausstehend“ an den Dateien im Bestand; sie überlebt Abbruch und Neustart. Bisher arbeitete sie nur ein
vollständiges Einlesen ab (erst Ordner durchsuchen), mit „Beim Start einlesen“ aus (0.45.0) blieben offene Bilder nach einem Neustart liegen. Jetzt: (1) **Hintergrundlauf** ohne Suchen und Hashen (`starten(nur_cad=True)`, heisst aus Gewohnheit so; vorher nur FreeCAD):
Vorschaubilder → kleine Bilder → FreeCAD → kleine Bilder; (2) **beim Start** wird er angestossen, wenn etwas aussteht (`Scanner.hat_offenes()`: Bilder mit bekanntem Ort, oder FreeCAD-Umwandlung bei verfügbarem FreeCAD) — auch mit „Beim Start einlesen“ aus; die Ordner werden dabei
nicht durchsucht; (3) **Bilder erscheinen nach und nach:** Ergebnisse alle 2 s (`SPEICHERN_ALLE_S`) festhalten statt erst nach 100 (bei 121 Dateien kam bisher kein einziges Bild, dann 100 auf einmal). Dazu aus dieser Sitzung: Läufe einer Kette (Hochladen, Entpacken) werden zusammengezählt
(`_kette_buchen`; „219 Dateien, 1 neu in unter 1 s“ nach 121 Dateien war der letzte von mehreren Läufen), und beim Hochladen mehrerer Dateien stösst nur die letzte das Einlesen an (`einlesen=0` bei den anderen). Der Einlese-Dialog ist unverändert (bleibt bis „OK“) —
**ein Selbstschliessen war nicht gewünscht** und wurde wieder entfernt. Geprüft: alle Suiten (`test_scan` 85/85, `test_api` 71/71, `test_verwalten` 78/78, `test_ui` 97/97), drei Gegenproben (Start setzt nicht fort · nur 100er-Gruppen · Hintergrundlauf ohne Vorschauen).
**Offen:** der modale Einlese-Dialog verdeckt das Fenster unten links, bis man „OK“ drückt (Entscheidung des Anwenders: Dialog anders gestalten oder nicht); der Hintergrundlauf wird nicht gezeigt, solange er beim Start unbemerkt fortgesetzt wird — nur das Fenster unten links.
**Einlesen ohne Änderungen: fester Aufwand ohne Grund (0.46.1), Rückmeldung des Testers 6.10.2026:** „Beim Aktualisieren von unveränderten Ordnern braucht er immer 3 Sekunden, egal wie viele Dateien“ — dazu „Werkzeuge“ (31 Dateien, 31 MB, alle Formate) frisch eingelesen: **15 s, bis alle Bilder da waren**.
Ursache der 3 s: die Thumbs-Phase (0.44.3) öffnete bei **jedem** Lauf jedes Bild im Vault, nur um zu sehen, dass keine Verkleinerung nötig ist. Gemessen (6.10.2026, 9 000 Vorschau-PNGs à 320 px / 11 KB, warmer Zwischenspeicher): **2,84 s → 0,06 s**;
nur die Grösse zu erfragen kostet 0,03 s. Jetzt überspringt `_thumbs` PNGs bis `KLEIN_BYTES` (64 KB) ohne sie zu öffnen (`Bestand.thumb` liefert sie bei Bedarf weiterhin direkt aus); grosse Bilder und Fotos werden wie bisher vorgebaut. Auf der Platte des Testers dürfte
der Gewinn grösser sein (kalter Zwischenspeicher, 9 000 Datei-Öffnungen), gemessen ist es dort nicht. Die **15 s** für 31 Dateien sind **nicht** aufgeklärt: bekannt sind pro Lauf der Start der Arbeitsprozesse (`spawn`, jeder importiert numpy und Pillow: hier ca. 1,2 s, dort ein Mehrfaches),
das Rendern (hier 0,22–0,3 s je STL, auf dem alten Rechner ein Mehrfaches, durch vier Arbeiter geteilt), das Speichern alle 2 s und die 3 s der Thumbs-Phase (jetzt weg). **Möglicher nächster Schritt (nicht gebaut):** bei kleinen Stapeln (etwa bis 8 Dateien) im Server-Prozess rechnen statt Arbeiter zu starten.
**Speicher des Browsers (5.10.2026):** Firefox mit partAtlas 708 MB, leer 239 MB (Tester, 8 946 Modelle). Ursache nicht gemessen (Verdacht: ganze Modellliste im Browser, entpackte Bilder);
`about:memory` wäre die Messung. Bewusst zurückgestellt.
**Noch offen (klein):** einmal parsen statt dreimal (Hash, Analyse, Render) — erst nach den Zahlen vom 4,1-GB-Lauf des Testers.

**FCStd (0.27.0):** FreeCAD-Dokumente werden katalogisiert (Zip mit `Document.xml`; Titel = `Label`, Urheber = `CreatedBy` des Dokuments, nicht
der Objekte). Vorschau nur aus `thumbnails/Thumbnail.png`, wenn FreeCAD es beim Speichern mitlegt (Einstellung in FreeCAD); ohne Thumbnail steht
„FCStd · nur CAD“ wie bei STEP. **Keine Masse, kein Volumen, keine 3D-Ansicht:** die Formen liegen als BREP-Dateien im Zip und brauchen Open CASCADE.
„Öffnen“ geht ins CAD (FreeCAD), nie in einen Slicer (`programme.CAD_FORMATE`). Geprüft in `test_formate`, `test_scan`, `test_api` mit Gegenproben.
**Nicht geprüft:** an einer echten FCStd-Datei (nur ein nachgebautes Zip mit der Struktur aus dem FreeCAD-Format), und `test_ui.py`.
**Offen, falls das Thumbnail zu klein ist:** FreeCAD legt es in kleiner Auflösung ab; ein berechnetes Bild bräuchte FreeCAD selbst (`freecadcmd`) oder
Open CASCADE — Aufwand 3–4, erst nach Rückmeldung des Testers.

**STEP über FreeCAD (0.28.0):** nach dem Einlesen (Phase 6 in `scan.py`) startet partAtlas FreeCAD **ohne Fenster** (`cad.konsole_befehl`:
FreeCADCmd neben dem erkannten Programm, Flatpak mit `--command=FreeCADCmd`, sonst die Datei mit `-c`) **einmal je Stapel von 25** und lässt `cad_skript.py`
darin jede STEP in ein Netz umwandeln (`Part.read`, `MeshPart.meshFromShape`, 0,1 mm). Das Netz liegt abgeleitet in `<bestand>/netz/<hash>.stl` (nicht
gesichert, mit der Datei weg); daraus kommen Maße, Volumen, Gewicht, das berechnete Vorschaubild und die 3D-Ansicht (`/api/modelle/{id}/netz` liest bei STEP
dieses Netz). Eine Datei, die scheitert oder länger als 180 s braucht, wird als Fehler vermerkt (`cad: "fehler"`) und **nicht bei jedem Lauf wiederholt**;
FreeCAD wird für den Rest neu gestartet. Ohne FreeCAD bleibt `cad` ausstehend und kommt beim nächsten Lauf dran. Abbrechen beendet FreeCAD sofort. Auch ältere
Einträge ohne das Feld werden nachgeholt. Geprüft in `test_cad` (11/11), `test_scan` (56/56), `test_api` (59/59) mit Gegenproben und einer Attrappe, die das echte
`cad_skript.py` mit Ersatz für Part/MeshPart ausführt.
**Nicht geprüft — das echte FreeCAD:** der Aufruf (`-c` für AppImage, Flatpak-Name, ob FreeCADCmd nach dem Skript endet; die Zeile wartet sonst 5 s und beendet es),
`Part.read`/`MeshPart.meshFromShape`, ob die ASCII-STL von `mesh.write` für grosse Teile zu langsam einzulesen ist. Der Tester sieht es beim ersten Einlesen:
Kacheln bekommen nach einer Weile ein Bild; sonst steht der Grund im Protokoll (`partatlas.cad`, `arbeit/cad/…/ausgabe.log` nur während des Laufs).
**Offen:** Wiederholen gescheiterter STEP-Dateien aus der Oberfläche; FCStd ohne Thumbnail über denselben Weg (Dokument laden, sichtbare Körper vernetzen);
Auto-Export einer Baugruppe in Einzelteile (brainstorm, braucht erst eine echte Baugruppe vom Tester).

**Inspektor ausblenden (0.29.0):** wie in pDMS — Knopf ⇥/⇤ in der Kopfzeile und, solange er weg ist, ein Griff ‹ am rechten Rand; ein Klick blendet ihn
aus oder ein, die Wahl bleibt gemerkt (`localStorage` „partatlas.inspektor“). Die letzte Spalte wird 0 breit, die Liste bekommt die Breite
(`inspektorSichtbar()` in `app.js`, `.app.insp-versteckt` in `app.css`). Geprüft mit einem Playwright-Skript (aus, Neuladen bleibt aus, Griff holt ihn zurück),
nicht mit `test_ui.py`. **Offen:** bei ausgeblendetem Inspektor zeigt ein Klick auf ein Modell nichts an (wie in pDMS gewollt); die Baugruppen-Übersicht
rechts ist dann ebenfalls weg.

**Ordner löschen (0.29.1):** Rechtsklick auf einen Unterordner der Seitenleiste: „Im Dateimanager zeigen“ (auch für Wurzeln) und „Ordner löschen …“.
Gebaut ist **Weg 1**: die Modelle, die ganz im Ordner liegen, gehen über `loeschen_mit` in den Papierkorb (derselbe Dialog mit Tags, Sammlungen,
Baugruppen), danach `rmdir` von unten nach oben. Was keine Modelldatei ist, bleibt, und mit ihm der Ordner; ein Dialog nennt Pfad und Rest und führt in
den Dateimanager. Ein Modell mit einer Kopie ausserhalb bleibt (sonst ginge die andere Kopie mit). Eine Wurzel wird nie gelöscht. API:
`GET /api/ordner/inhalt`, `POST /api/ordner/loeschen`, `POST /api/ordner/im_ordner`. Geprüft in `test_verwalten` (57/57) mit Gegenproben und einem
Playwright-Skript (Menü, Dialog, Ergebnis), nicht mit `test_ui.py`.
**Offen:** Weg 2 (ganzer Ordner samt fremden Dateien in den Papierkorb und zurück, Aufwand 4). Der Ordnerbaum leitet sich aus den Modelldateien ab: ein Ordner,
in dem nur noch fremde Dateien liegen, verschwindet aus der Seitenleiste — erreichbar bleibt er über den Pfad im Dialog.

**FCStd über FreeCAD (0.29.2):** derselbe Weg wie STEP (`cad.py`, Phase 6), aber **nur nach Zusage**: ein FreeCAD-Dokument kann beim Laden Programmcode
ausführen (nicht geprüft, ob FreeCAD das tatsächlich tut — deshalb vorsichtig). Einstellung `fcstd_freecad` (`None` = fragen, `"ja"`, `"nein"`; Einstellungen › Einlesen).
Ohne Antwort lädt der Scan kein FCStd und meldet `fcstd_frage` (Anzahl); die Oberfläche fragt einmal je Sitzung mit Hinweis: **Nie** / **Nicht jetzt** / **Ja, einlesen**
(`fcstdFrage()` in `app.js`). `cad_skript.py` öffnet das Dokument, nimmt die **sichtbaren Körper, die nicht Teil eines anderen Körpers sind** (`koerper()`), fasst sie zu
einer Form zusammen und vernetzt sie; Zeitgrenze und Stapel wie bei STEP. Das berechnete Bild steht vor dem Thumbnail aus der Datei (`Katalog.vorschauen`, für CAD-Formate
umgekehrt). Geprüft in `test_cad` (12/12), `test_scan` (59/59) mit Gegenproben; **nicht** an echtem FreeCAD: `FreeCAD.openDocument`, `Visibility`/`InList`,
`Part.makeCompound`. **Offen:** Teile in verschachtelten `App::Part` bekommen nur ihre lokale Platzierung (Baugruppen können versetzt erscheinen); `App::Link` wird nicht
aufgelöst; grosse Baugruppen laufen in die Zeitgrenze.

**Papierkorb leeren (0.29.3):** der Server konnte es (`POST /api/papierkorb/leeren`), die Oberfläche bot es nirgends an — gemeldet vom Anwender („man kann ihn nicht leeren“),
ein reiner Fehler. Jetzt eine Leiste über der Liste in der Papierkorb-Ansicht („N Modelle im Papierkorb · Papierkorb leeren …“) mit Rückfrage; nur sichtbar, wenn
etwas drin liegt. Geprüft mit einem Playwright-Skript (Leiste, Dialog, danach leer, Datei weg), nicht mit `test_ui.py`; das Backend deckt `test_scan` ab.
**Offen:** einzelne Modelle endgültig löschen (nur „Alles leeren“); die Leiste ohne Test in `test_ui.py`.

**Protokoll und CAD-Status sichtbar (0.29.4):** gemeldet: FCStd ohne Bild bekamen keine Vorschau, und man sah nicht, woran es lag (Screenshot: STEP-Zeilen haben Maße, die
FCStd nicht; der Lauf nannte keine FreeCAD-Phase — vermutlich nicht beantwortet oder gescheitert, **Ursache nicht geklärt**). Jetzt: (1) `partatlas.log` im Bestand (rotierend
3 × 1 MB, zusätzlich zur Konsole), Knopf „Protokoll im Dateimanager zeigen“ in Einstellungen › Einlesen; (2) im Inspektor, Reiter „Datei“, eine Karte „FreeCAD“ mit dem Zustand
(ok / gescheitert mit Meldung / wartet auf Zusage / FreeCAD nicht gefunden) und „Alle gescheiterten erneut versuchen“ (`POST /api/cad/erneut`). Nicht an echtem FreeCAD geprüft;
Gegenprobe der Tests: `cad_erneut` und `cad_fehler` in `test_scan` (60/60).
**Offen:** Ursache der fehlenden FCStd-Vorschau beim Tester — Meldung aus dem Inspektor oder `partatlas.log` abwarten.

**„Den Ordner gibt es schon“ (0.29.6):** gemeldet. Der Ordnerbaum zeigt nur Ordner mit Modellen; ein gelöschtes Modell lässt sein leeres Verzeichnis auf der Platte zurück, und ein
„Neuer Unterordner“ mit demselben Namen scheiterte, obwohl man davon nichts sah. Jetzt wird ein vorhandener Ordner benutzt; nur eine gleichnamige *Datei* lehnt es ab (mit diesem Grund).
Dazu: **Dateien, deren Inhalt als Modell im Papierkorb liegt, nimmt der Scan bewusst nicht neu auf** (`scan.py`, `im_papierkorb`) — das war stumm; die Kopfzeile nennt jetzt „N schon im
Papierkorb (dort wiederherstellen)“. Geprüft in `test_verwalten` (59/59). **Offen / Entscheidung:** soll eine zurückgelegte Datei das Modell stattdessen selbst aus dem Papierkorb holen?
Ausserdem zeigt der Baum leere Ordner nicht — von aussen ist ein Rest unsichtbar.

**Zurückgelegte Datei und „nur FreeCAD“ (0.29.7):** (1) Eine Datei, deren Inhalt als Modell im Papierkorb liegt, kommt jetzt **ins Modell zurück** statt stumm übergangen zu werden
(`Katalog.aus_papierkorb_zurueck`): Modell samt Tags, Drucken und Baugruppen, neuer Ort, die Kopie im Papierkorb entfällt (dieselbe Datei). Hatte das Modell mehrere Orte, kommen die übrigen
wie bei „Wiederherstellen“ zurück. Die Kopfzeile nennt „N aus dem Papierkorb zurückgeholt“. Das ersetzt die Regel von 0.29.6 („nicht still zurückbekommen“). (2) Nach der Zusage für
FCStd läuft **nur die FreeCAD-Umwandlung** (`Scanner.starten(nur_cad=True)`, `POST /api/cad/starten`, auch bei „erneut versuchen“), nicht mehr ein ganzer Lauf mit Suchen und Hashen.
Geprüft in `test_scan` (62/62) mit Gegenproben. **Offen:** die Frage nach FCStd kommt erst, wenn der Lauf fertig ist.

**partAtlas löscht keine Dateien mehr (0.30.0):** Vorgabe des Anwenders: „die Dateien sollten niemals gelöscht werden, sondern nur in der Datenbank“. „Löschen“ eines Modells oder Ordners
nimmt nur den Katalogeintrag in den Papierkorb (flatgraph-Papierkorb, `Katalog.loeschen`); **die Datei bleibt im Ordner**, ihr Ort wird samt Grösse und Zeit in `papierkorb` gemerkt, damit der Scan sie
überspringt, ohne sie bei jedem Lauf neu zu lesen (`ignorierte_orte`). „Wiederherstellen“ nimmt das Modell am gemerkten Ort wieder auf (fehlt die Datei inzwischen: „Datei fehlt“). „Papierkorb
leeren“ vergisst die Einträge, löscht aber keine Datei; eine noch vorhandene Datei kommt beim nächsten Einlesen als neues Modell wieder. „Ordner löschen“ heisst jetzt „aus dem Katalog entfernen“ und
rührt Verzeichnisse nicht an. Die Option „Archiv-Original in den Papierkorb“ entfällt. Frühere Fassungen hatten die Dateien in den Papierkorb von partAtlas *verschoben*: solche Einträge
(`ablage` gesetzt) werden weiter zurückgelegt, und legt der Anwender die Datei wieder in den Ordner, kommt das Modell zurück (`aus_papierkorb_zurueck`); „Papierkorb leeren“ löscht dort nur diese verschobenen
Kopien. Weiter schreibt partAtlas in den Ordnern: Verschieben und Umbenennen auf Wunsch (nie überschreibend) und die entpackten Archive. Geprüft in `test_scan` (64/64), `test_verwalten` (58/58),
`test_api` (59/59) mit Gegenproben; der Test fand dabei einen echten Fehler (`papierkorb_leeren` ohne `ablage`). **Offen:** leere Ordner sieht man im Baum nicht; ein Papierkorb-Eintrag, dessen Datei der
Anwender selbst gelöscht hat, bleibt bis zum Leeren; „Papierkorb leeren“ lässt Dateien stehen, die danach wieder auftauchen — ein „Ignorieren“ (Eintrag behalten) wäre ein eigener Schritt.

**Nichts darf versehentlich verloren gehen (0.30.1):** gemeldet: Wurzelordner entfernt, dann „bei Bereinigen ist nichts mehr, ich kann nichts wiederherstellen“. Befund: (1) Der Katalog war *nicht* leer —
die Modelle standen als „Datei fehlt“ da —, aber ohne eingetragenen Ordner zeigte die Oberfläche den **Willkommensschirm** und versteckte Bereinigen und alle Felder der Seitenleiste (`body.erststart`).
(2) Es gab keinen Weg zurück für einen entfernten Ordner. (3) **„Papierkorb leeren“ rief den Müllsammler von flatgraph auf, der *alles* Gelöschte abräumt** — auch entfernte Ordner, gelöschte
Baugruppen, Drucke, Sammlungen, Tags; bei früheren Fassungen zudem die in den Papierkorb von partAtlas verschobenen Dateien. Jetzt: **„Papierkorb leeren“ ist ganz entfernt** (Knopf, Endpunkt, `Katalog.papierkorb_leeren`); nichts ruft
`run_garbage_collection` auf, der Papierkorb wächst nur. Ein entfernter Wurzelordner bleibt als Eintrag (`wurzel_entfernen` merkt Zeit und Zahl) und steht unter Bereinigen › Papierkorb mit „Wieder hinzufügen“ (`entfernte_wurzeln`,
`wurzel_wiederherstellen`, `GET /api/wurzeln/entfernt`, `POST /api/wurzeln/{id}/wiederherstellen`; der nächste Scan verbindet die Modelle über den Inhalt, Tags und Drucke sind noch da). Der Willkommensschirm erscheint nur noch in einem
wirklich leeren Katalog; sonst eine Leiste „Es ist kein Ordner mehr eingetragen …“. Ein Modell wiederherstellen, dessen Ordner entfernt ist, sagt, was zu tun ist, statt es halb zurückzuholen. Geprüft in `test_verwalten` (63/63),
`test_scan` (65/65) und mit einem Playwright-Skript an genau diesem Zustand (null Ordner, Modelle da). **Ausdrücklich nicht gebaut:** ein „endgültig löschen“; käme es je, dann nur je Modell, mit Tippbestätigung und ohne Müllsammler (gebaut so in 0.32.0).
**Offen:** Baugruppen, Drucke, Sammlungen und Tags löscht die Oberfläche weiter per `soft_delete` (also wiederherstellbar im Graph), aber ohne Ansicht dafür; Browser-Dateien und laufender Server können nach `git pull` ohne Neustart auseinanderlaufen — die Seite bricht dann
nicht mehr ab (der neue Endpunkt ist abgefangen), ein Hinweis „bitte neu starten“ fehlt noch.

**Datensicherheit als Architektur (0.31.0):** nach dem Vorfall mit „Papierkorb leeren“ systematisch geprüft (Inventur aller Aufrufe, die löschen, verschieben oder ersetzen) und in
KONZEPT §3.3 als Zusagen mit erzwingendem Mechanismus festgehalten. Neu: `Bestand.entfernen` (einziger Löschweg, verweigert ausserhalb des Bestands), Wächter in `tests/test_schutz.py`
(`schutz_inventur.py` findet jeden Aufruf per AST, `ERLAUBT` begründet jeden), `sicherung.py` (Sicherung beim Start und vor Massenaktionen, Rotation, Zurückholen per Kommandozeile),
Scan lässt Orte eines nicht erreichbaren oder leeren Wurzelordners stehen, Archiv-Hochladen über `arbeit/`. Gefunden beim Bauen: gleichsekündige Sicherungen sortierten falsch
(Namensschema mit zweistelligem Zähler behoben). `test_schutz` 16/16 mit vier Gegenproben (unbegründeter Löschaufruf, Verweigerung entfernt, Scan-Schutz entfernt, Sicherung vor
Massenaktion entfernt); alle Suiten grün. **Offen:** Zurückholen einer Sicherung in der Oberfläche (Aufwand 2–3: Scanner anhalten, Bestand schliessen, tauschen, neu öffnen);
Ansicht zum Zurückholen gelöschter Sammlungen, Baugruppen, Drucke, Tags; die Sperre beim Kopieren ist nicht unter Last geprüft (Kopierzeit grosser Bestände nicht gemessen).

**Endgültig entfernen je Modell (0.32.0):** flatgraph 4.1.0 (Pin `39698fa`) hat `purge(sammlung, kennung)`: entfernt einen Knoten aus dem Papierkorb mit genau seiner
Kaskade (`_geloescht_durch`), lehnt lebende ab, lässt alle anderen Papierkorb-Einträge samt Texten stehen; `run_garbage_collection` bleibt für die Wartung (VERTRAG §2.9).
In partAtlas: Papierkorb › Inspektor „Endgültig entfernen …“ bzw. Rechtsklick (nur bei einem Modell, nie für eine Auswahl). Dialog nennt, ob die Datei noch im Ordner liegt
(dann kommt sie beim nächsten Einlesen als neues Modell wieder) und wohin eigene Bilder gehen; Knopf erst nach Eintippen von „entfernen“, das auch der Server prüft.
`Katalog.endgueltig_entfernen`: Sicherung (`vor-endgueltig-entfernen`), `purge` des Modells (nimmt den Datei-Knoten mit), eigene Bilder und Dateien aus dem alten
Papierkorb von partAtlas nach `vault_archive/`, Vorschauen und Netz der Datei weg. Wächter: `purge` steht begründet in `ERLAUBT`, `run_garbage_collection` bleibt
verboten. Nebenbei behoben: eine Sicherung bekam nach dem Aufräumen eine frei gewordene, niedrige Nummer derselben Sekunde, sortierte als älteste und wurde sofort wieder
weggeräumt (nur bei über 20 Sicherungen je Sekunde, also im Test); jetzt immer hinter der höchsten. Gegenproben: Sicherung weg, Müllsammler statt `purge`, Bild nicht
archiviert, Vorschau bleibt, Server ohne Tippprüfung, Nummer in der Lücke — jede lässt `test_schutz` bzw. `test_verwalten` fallen. **Offen:** Drucke, die nur an einem
endgültig entfernten Modell hingen, bleiben als Knoten ohne Modell im Graph (unsichtbar, nichts geht verloren; Aufwand 2, sie mit in den Papierkorb zu legen).

**Auswahlleiste unten (0.33.0):** die Leiste der Mehrfachauswahl stand oben im Fluss und rückte beim ersten Häkchen die Liste nach unten —
der nächste Klick traf daneben. Jetzt schwebt sie unten über der Liste (wie pDMS, Capacities), die Liste bekommt unten Luft, Meldungen
rücken darüber. `test_ui` 61/61; die neue Prüfung (Liste bleibt stehen, Leiste unten) fällt mit der alten Leiste.

**Entschieden 02.10.2026: Dateien bleiben an Ort und Stelle.** Verglichen: 3MF Katalog (an Ort und Stelle, verwaiste Einträge nur zum
Löschen vorausgewählt), Manyfold (an Ort und Stelle, kann umräumen; fehlende Datei = Problem „either delete it, or find where it went!“,
ignorierbar), Lightroom (wählbar; letzter Ort, „Suchen“, Nachbarn mitfinden, Smart Previews), Calibre/Apple Fotos/Zotero (eigene Ablage).
Eine Ablage wie in pDMS wäre bei grossen 3D-Dateien doppelter Platz oder nähme dem Anwender seine Ordner. Daraus folgt für eine Datei,
die der Anwender selbst gelöscht hat (Eintrag mit Drucken, Bildern usw. soll bleiben):

1. **Ansehen ohne Datei:** im Backlog (unten, „Idee, noch nicht gebaut“), nicht Priorität.
2. **Gebaut in 0.34.0** — **„Datei fehlt“ mit drei Wegen:** *Suchen …* (Ordner zeigen, Nachbarn mitfinden), *Ohne Datei behalten* (kein Problem mehr, ruhiges
   Zeichen, verschwindet von selbst, wenn die Datei zurückkommt), *Aus dem Katalog entfernen*. „Datei fehlt“ bleibt als Warnung der Standard.
3. **Wiedererkennen:** automatisch nur bei gleichem Inhalt (gibt es schon). Name, Ort, Form höchstens als bestätigter Vorschlag mit beiden
   Vorschauen — eine automatische Zuordnung wäre fehleranfällig.

**„Datei fehlt“ mit drei Wegen (0.34.0):** Inspektor: *Suchen …* (Ordner zeigen; `Katalog.fehlende_suchen` erkennt fehlende Dateien
am Inhalt, auch die anderer Modelle, hasht nur gleich grosse, wenn alle Grössen bekannt sind; liegt der Ordner im Katalog, verbindet der
Scan, sonst bietet der Dialog „Ordner hinzufügen“ an), *Ohne Datei behalten* (Feld `ohne_datei` am Datei-Knoten: zählt nicht im
Zähler/Abzeichen, nicht in Bereinigen › Datei fehlt, Kachel zeigt ruhig „ohne Datei“; verschwindet von selbst, wenn die Datei
zurückkommt), *Aus dem Katalog entfernen …* (der bisherige Löschdialog). Neu `zuletzt_ort`: der letzte Ort bleibt, wenn der letzte
verschwindet („Lag zuletzt in …“). `test_verwalten` 73/73, `test_ui` 63/63; Gegenproben (Zähler zählt Behaltene, Markierung bleibt
bei Rückkehr, kein letzter Ort, Behalten ohne Prüfung, Suche ohne Inhaltsvergleich) fallen. **Offen:** bei fehlender Datei zeigt der
Inspektor oben weiter die Öffnen-Knöpfe (Slicer/CAD) — Öffnen scheitert dann (schon vorher so, Aufwand 1). Modelle, die vor 0.34
fehlten, haben keinen `zuletzt_ort`: kein „Lag zuletzt in“, und „Suchen“ hasht dann jede Modelldatei im Ordner.

**FCStd-Frage kam zu spät (0.34.2, gemeldet 03.10.2026):** Ordner mit STEP und FCStd: erst lief FreeCAD für die STEP-Dateien, dann
kam die Frage — die FCStd-Kacheln zeigten da schon Bilder. Geprüft: an FreeCAD ging nur STEP; das FCStd-Bild ist das Vorschaubild aus
der Datei selbst (ohne FreeCAD gelesen). Fehler war der Zeitpunkt: die Oberfläche fragte erst am Ende des Laufs. Jetzt setzt der Scan
`fcstd_frage`, sobald die FCStd-Dateien bekannt sind (vor Vorschauen und FreeCAD), die Oberfläche fragt sofort, und der Dialog sagt,
woher das Bild schon stammt. Antwort vor der FreeCAD-Phase: FCStd im selben Lauf; danach: Folgelauf „nur FreeCAD“ (0.34.1).
`test_scan` 68/68, die neue Prüfung fällt gegen 0.34.1. Zuerst falsch gelesen und nur einen Nebenfehler behoben:

**FCStd-Zusage während eines Laufs (0.34.1):** „Ja, einlesen“ startet nur die FreeCAD-Umwandlung (seit 0.29.7) —
ausser es lief gerade ein Einlesen (etwa das beim Start, und der Ordner kam kurz danach): dann merkte sich der Scanner nur „nochmal“,
und aus „nur FreeCAD“ wurde ein ganzer Lauf. Ausserdem kam die Frage schon am Ende eines Laufs, dem gleich ein zweiter folgte. Jetzt
merkt sich der Scanner die Art des Folgelaufs (`_nochmal`: "cad" oder ganz; ganz schliesst die Umwandlung ein), und die Frage wartet,
solange ein Lauf folgt (`weiter`). `test_scan` 67/67; die zwei neuen Prüfungen fallen gegen 0.34.0. Nicht nachgestellt mit echtem
FreeCAD; isoliert (ohne laufenden Scan) war das Verhalten schon richtig.

**Einlesen sichtbar wie in pDMS (0.35.0):** vorher eine Übersicht (Ordner hinzufügen: Modelldateien je Format, Einlesen/Abbrechen;
Hochladen: je Endung im Zieldialog), dann ein Fenster `#einlesen` mit Balken — „Dateien prüfen: x von y“, dann „Eingelesen: x von y“ —,
das am Ende mit der Bilanz stehen bleibt bis OK (neu, je Format, Kopien gleichen Inhalts, Bilder aus der Datei, an neuem Ort erkannt,
nicht mehr im Ordner, unlesbar, nicht erreichbar, FCStd wartet; Dauer des eigentlichen Einlesens). Was danach läuft (Vorschaubilder,
FreeCAD, Einlesen beim Start), zeigt `#hintergrund` beim Zahnrad mit kleinem Balken; die Kopfzeile zeigt nur noch das Ergebnis des
letzten Laufs. Der Dialog folgt genau seinem Lauf (`lauf`, von den startenden Endpunkten zurückgegeben, vor `starten` gelesen). Die
FCStd-Frage wartet, bis das Fenster zu ist. Neu im Scanner: `lauf`, `geprueft`, `je_format`, `aus_datei`, `kopien`, `einlesen_s`,
`vorschauen_gesamt`, `cad_gesamt`; behoben: `vorschauen_offen` blieb nach den Vorschauen stehen (wurde nur alle 100 nachgeführt).
`test_scan` 70/70, `test_api` 61/61, `test_ui` 66/66; Gegenproben (Prüfzähler, Formate, Kopien, Dauer, falscher Lauf, Fenster schliesst
von selbst) fallen. **Offen:** Betriebsprotokoll in den Einstellungen lesbar (heute öffnet „Protokoll“ nur die Datei); Fortschritt mit
echter grosser Sammlung nicht angesehen (hier dauerte das Einlesen unter 1 s).

**Hochladen mit Liste wie SecureSafe (0.36.0):** Ordner ins Fenster ziehen ging vorher gar nicht (der Browser liefert den Ordner als
leere Datei, „weder Modell noch Archiv“), und Hochgeladenes landete flach im Zielordner. Jetzt: `abgelegtes()` durchläuft hineingezogene
Ordner (webkitGetAsEntry, versteckte Ordner aussen vor), `dateiListe()` zeigt Modelle und Archive mit Häkchen, Pfad und Grösse
(„Ausgewählt: 5 von 6 · 17,4 MB“, andere Dateien nur gezählt), danach der Zielordner; `/api/hochladen?unterordner=` legt die Struktur
nach (nur Neues, nichts überschrieben, `..`/versteckt/ausserhalb abgelehnt). Das Hochladen zählt im Einlesen-Fenster („Hochgeladen:
12 von 120“, abbrechbar), dann folgt dort das Einlesen. `test_verwalten` 76/76, `test_ui` 69/69 (Ordner-Durchlauf mit nachgebauten
Einträgen; einen echten Ordner-Drop kann Playwright nicht auslösen). Gegenproben: Häkchen wirkungslos, Unterordner flach, kein Schutz
vor versteckten Unterordnern — fallen. **Entschieden 03.10.2026: kein Ausschliessen beim Hinzufügen eines Ordners an Ort und Stelle.** Später soll partAtlas Dateien wieder
selbst verschieben und löschen können (ohne Dateimanager), dann aber sicher (KONZEPT §3.3) — nicht wie vor 0.30. Bis dahin bleibt der
Stand fürs Anwendertesten so, wie er ist: partAtlas löscht und verschiebt nichts von sich aus.

**Entwurf (0.37.0, Anlass: Tester mit vielen Konstruktionsständen im Ordner „Peltierkühler“):** Versionsverwaltung war ihm zu viel;
entschieden: ein einziger Zustand *Entwurf* (Feld `entwurf` am Modell), kein „Final“. Setzen im Inspektor (Schalter), per Auswahlleiste
(schaltet zurück, wenn alle schon Entwurf sind) und Rechtsklick. Kachel: ruhiges Etikett oben links; Listen: Kennzeichen am Namen.
„Entwürfe ausblenden“ als Chip rechts in der Leiste, gemerkt (`partatlas.ohneEntwuerfe`), mit Zahl („3 Entwürfe ausgeblendet ×“).
Baugruppe aus Ordner und Ordner-Vorschläge ohne Entwürfe; eine bestehende Position mit Entwurf sagt „ist das der richtige Stand?“,
getauscht wird nichts. `test_baugruppen` 48/48, `test_ui` 70/70; Gegenproben fallen.

**Aufräumen-Ansicht gebaut (0.38.0):** Bereinigen › 🧹 Aufräumen, eigene Fläche (`aufraeumen.js`, Server `aufraeumen.py`). Gruppen
mit Anzahl und Summe: Entwürfe · Kopien gleichen Inhalts (zählt nur die überzähligen) · grosse Dateien ohne Verwendung (ab 10 MB) ·
lange nicht angefasst (über 365 Tage unverändert). Je Zeile Grund, Grösse, alle Pfade (📂 nur für eigene Pfade des Modells), was daran
hängt (gedruckt, Baugruppe, Favorit; Zeile dann getönt). Auswahl mit Summe → „Pfade speichern (CSV)“ oder „Behalten“ (Ausnahme,
`aufraeumen_behalten` am Modell, unter „Ausnahmen“ zurücknehmbar); „Kein Entwurf“ je Zeile. Der Scan legt einen Entwurf, dessen
Datei gelöscht wurde, in den Papierkorb (`aufgeraeumt`, Bilanz nennt es). `test_aufraeumen` 13/13 (neu), `test_ui` 74/74;
Gegenproben (Verwendetes vorgeschlagen, Kopien voll gezählt, Behalten wirkungslos, kein Aufräumen beim Scan, beliebiger Pfad,
Leer-Hinweis über der Fläche) fallen. **Offen:** Zähler am Eintrag „Aufräumen“ (Summe in GB) — kostet je Seitenaufbau einen Durchgang;
„lange nicht angefasst“ misst die Dateizeit, nicht wann man das Modell zuletzt angesehen hat (wird nicht mehr geschrieben).

**Wunsch dazu (03.10.2026): Aufräumen-Ansicht** — „ein echtes Bereinigen mit echten Vorschlägen und
Übersichten, die kontrollierte, detaillierte Entscheidungen ermöglichen“, Vorbild: feingranulare Firewall mit voller Kontrolle. Der
Tester: „Das Zumüllen ist echt das Problem“. Gruppen mit Platzangabe (Entwürfe, Duplikate, grösste Dateien, nie gedruckt + in keiner
Baugruppe + lange nicht angesehen), je Zeile der Grund und was daran hängt; Gedrucktes und Verbautes nie als Vorschlag. Löschen vorerst
selbst über „Im Ordner zeigen“; ein gelöschter Entwurf/Vorschlag gilt dann als aufgeräumt (still in den Papierkorb, Bilanz nennt es)
statt als „Datei fehlt“. Später, wenn partAtlas sicher löschen darf: „In den Papierkorb des Systems“ direkt aus der Ansicht.

**Zuordnen-Fenster und Leiste (0.39.0, Rückmeldung 03.10.2026: „gebastelt, keine hochprofessionelle Software“):** Tag war ein Textfeld, Material ein
Dialog mit Chips, Baugruppe ein Dialog mit Auswahlliste, Sammlung eine Auswahlliste in der Leiste. Jetzt ein Bauteil (`zuordnen.js`,
Server `zuordnen.py`, `/api/stapel/optionen` und `/api/stapel/zuordnen`): Fenster am Knopf, über der Leiste wachsend; Suchfeld, Liste mit
Stand („✓ alle“, „2 von 5“), ↑↓/Enter/Esc, Klick fügt allen hinzu, Fenster bleibt offen; „… anlegen“ steht hinter den Treffern und wird nur
vorausgewählt, wenn es keinen Treffer gibt (sonst legte „kue“ + Enter einen Müll-Tag an). Nur Hinzufügen. Baugruppe: Modelle, die schon
drinstehen, werden übersprungen (sonst erhöhte jeder weitere Klick die Menge). Auch das Rechtsklick-Menü bei Mehrfachauswahl öffnet es
(an der Klickstelle). Leiste neu geordnet: Kopf (Anzahl, „Alle n auswählen“, ✕), darunter Gruppen Zuordnen · Markieren · Dateien; die
Papierkorb-Leiste ebenso. Entwurf-Etikett fehlte in der Ansicht „Karten“ (Raster und Liste hatten es) — behoben, für alle drei geprüft.
`test_zuordnen` 12/12 (neu), `test_ui` 81/81. Beim Bau: meine Klassen `.waehler`/`.w-zeile` kollidierten mit dem Teile-Wähler der
Baugruppen (dessen Grid-Regeln überschrieben meine) — jetzt `#zuordnen`/`.zw-…`. **Offen:** der Inspektor (ein Modell) hat noch seine eigenen
Wege (Tag-Eingabe, „+ Material …“, „+ Sammlung …“, „+ Baugruppe …“ als Auswahllisten) — dasselbe Fenster würde auch dort passen
(Aufwand 1–2); Entfernen aus dem Fenster (Dreiwert-Häkchen wie bei Gmail-Labels) würde je Art eine Entfernen-Schnittstelle brauchen.

**Eigene Komponente — erste Fassung (0.40.0, 03.10.2026, ausdrücklich zum Ausprobieren):** Dritte Art Bauteil neben Druck- und Kaufteil:
ein freies Objekt (Name, Bild, Notiz, optional Maße, freie „Art“ wie Lagerteil/Eigenbau/Fundstück) für Teile, die weder gedruckt noch
gekauft sind (60 Jahre altes Kugellager ohne Angaben). Knoten `CUSTOM_COMPONENT`, in der Baugruppe eine Position wie ein Kaufteil,
wiederverwendbar. **Bewusst nicht:** Bestandsverwaltung, Lagerort, Einkäufe — die Menge ist der Bedarf. Zählt nicht zu Filament oder
Einkaufsliste; erscheint in Stückliste (Struktur-PDF mit Bild), CSV und Markdown („Eigene Komponenten“). Bedienung: „＋ Eigene Komponente“
in der Baugruppe (Suche über vorhandene, darunter Neuanlage mit Name/Art/Maße/Notiz/Bild per Datei oder Strg+V, legt gleich in die
Baugruppe); Klick auf die Zeile = bearbeiten; löschen nur, wenn in keiner Baugruppe. `test_eigene` 11/11 (neu), `test_baugruppen` 48/48,
`test_schutz` 22/22. **Mit Datei (0.41.0):** Auf den Dialog ziehen oder „＋ Datei hinzufügen“ (FCStd, STEP, 3MF, STL, OBJ): das Bild entsteht aus der Datei
(eingebettetes Bild, sonst gerendert; STEP/FCStd ohne Bild über FreeCAD, FCStd nur nach der Zusage), Maße werden übernommen, wenn leer;
ein selbst gewähltes Bild bleibt. Die Datei kommt **nicht** in den 3D-Katalog: eine Kopie in `vault/komponenten/` (kein Wurzelordner, den der
Scanner sähe), im Dialog zum Zurückladen verlinkt. Anlass: ein FCStd, das nur Konstruktion ist und als Druckteil getarnt in einer Baugruppe
stand. Offen: „Öffnen in FreeCAD“ statt nur Herunterladen; Einlesen läuft noch im Anfrage-Aufruf (ohne Fortschrittsanzeige); weitere Formate
(PDF, DXF); keine Kopie, sondern Verweis auf den Ort, falls Dateien gross werden. `test_eigene` 17/17.
**3MF in FreeCAD öffnen (0.41.1, Wunsch des Testers):** FreeCAD steht jetzt auch für 3MF im Menü „Öffnen mit“ (es liest 3MF als Netz, ohne
Slicer-Daten wie Platten und Farben); der Hauptknopf bleibt beim Slicer. Der alte Hinweis „nicht verlässlich“ war nicht an einer
Installation geprüft; falls es bei einer FreeCAD-Fassung ohne Mesh-Werkbank scheitert, öffnet FreeCAD leer. `test_api` 62/62.

**Wenn es nichts taugt, wieder weg:** `partatlas/eigene.py`, `web/eigene.js`, `tests/test_eigene.py` löschen und die
mit „EIGENE“ markierten Stellen in `baugruppen.py`, `stueckliste.py`, `main.py`, `web/baugruppen.js`, `web/index.html`, `web/app.css`
entfernen; bestehende Daten (Knoten `CUSTOM_COMPONENT`) stören die Übrigen nicht. **Feinschliff, falls es bleibt:** eigener Bereich „Teile“
statt nur im Baugruppen-Dialog, Bilder mehrfach/Galerie, Umbenennen der Art für alle, Vorschlag „aus einem Foto“, Löschvorschau,
CSV-Import, Kennzeichnung in der Karten-/Teileliste, Menge mit Einheit.

**Kaufteile als eigene Knoten — Leistung gemessen (03.10.2026, KONZEPT §8):** Rückfrage „was kostet das technisch?“. Kaufteile sind schon
Knoten (`PURCHASED_PART`); der Entwurf (Verwaltung, Einkäufe, Händler) fügt Knoten und Kanten hinzu. Bei *klein* (300 Kaufteile, 1 000
Einkäufe) +13 ms Öffnen und +3 MB; bei *gross* (5 000 / 30 000) +580 ms und +92 MB, jede Abfrage unter 21 ms, Schreiben unabhängig von der
Menge. Daraus: kein Leistungsgrund gegen den Entwurf; die Kaufteile-Liste braucht ab einigen tausend Zeilen virtuelles Scrollen, und die
Sicherung wächst mit (384 ms, 18 MB bei *gross*). Skript und Ergebnis liegen in `messung/`. Gebaut ist davon noch nichts.

## Absicht: partAtlas als Explorer-Ersatz (04.10.2026, noch nicht gebaut)

Der Tester will die Bibliothek tatsächlich anstelle des Dateimanagers benutzen: Dateien und Ordner aus partAtlas heraus umbenennen,
verschieben, anlegen und löschen, ohne daneben den Explorer zu öffnen. **Für das Testen bleibt der Stand unverändert** (nichts wird
gelöscht oder überschrieben, Verschieben und Umbenennen nur auf Klick und nie überschreibend, KONZEPT §3.3; `test_schutz`).

Vorgehen, wenn es soweit ist:
- **Erst Vorbilder ansehen, nicht neu erfinden.** Software, die die Plattenstruktur eingelesener Ordner selbst verwaltet, gibt es
  (zu prüfen, nicht aus dem Gedächtnis zu übernehmen: Foto-Verwaltungen wie digiKam und Lightroom, Manyfold, Calibre). Zu klären je Vorbild:
  Unterscheidung „aus dem Katalog entfernen“ und „von der Platte löschen“, wohin gelöscht wird (Papierkorb des Systems?), was bei
  Verschieben mit dem Katalog passiert, was bei Änderungen ausserhalb der App, was bei Namenskonflikten und eingehängten Laufwerken.
- **Mindestzusagen** (Vorschlag, Aufwand insgesamt ca. 3–4): Löschen nur in den Papierkorb des Systems, nie endgültig; immer mit
  Vorschau (was hängt daran: Drucke, Baugruppen, Kopien) und Sicherung davor; einzeln oder gezielt gewählt, bei Mehrfachauswahl mit
  Tippbestätigung, nie „alles“ oder ein ganzer Ordner in einem Schritt; der Katalog zieht mit (Papierkorb von partAtlas, Wiederherstellen);
  jede neue Löschstelle mit Begründung im Wächter (`ERLAUBT`).
- **Eigener Schritt, nicht mit anderem Neuen zusammen.** Mit Tests auf Verweise, fremde Pfade, nicht erreichbare Laufwerke und Ordner,
  die ausserhalb der App verändert wurden.
- **Dagegen:** Sobald partAtlas Dateien wirklich anfasst, ist ein Fehler bei Pfaden kein Anzeigefehler mehr. Das braucht den Vorlauf oben.

## Auswahl wie im Explorer (5.10.2026, entschieden, noch nicht gebaut)

Wunsch des Testers; gehört zur Linie „partAtlas wie ein Dateimanager bedienen“ (siehe Explorer-Ersatz oben) und zur Überarbeitung des Tabellenkopfs (Punkt e unten). **Vorlage ist pDMS**
(`bireggbaum-beep/homedms`), nicht neu erfinden: dort ansehen, wie es sich verhält, bevor etwas gebaut wird (in dieser Sitzung nicht eingesehen).
- **Alles auswählen:** Kästchen im Kopf der Liste, dreistufig (leer · teilweise · alle), wählt **alles in der Ansicht** (nach Suche und Filter, nicht die ganze Bibliothek); Strg+A für Raster und Karten.
  Die Statuszeile zeigt die Zahl schon („57 Modelle · 3 ausgewählt“). Massenaktionen mit grosser Auswahl: Rückfrage nennt die Zahl („8 946 Modelle“); „Aus dem Katalog entfernen“ bleibt über den Papierkorb umkehrbar.
- **Auswahl mit der Maus:** heute geht nur Kästchen sowie Strg/Umschalt+Klick (`waehleAus()` in `app.js`). Fehlt: **Aufziehen eines Rahmens** (Gummiband) im Raster und in der Liste, Umschalt+Klick als Bereich
  über die Anzeigereihenfolge, Strg+Klick als Einzelwahl, Pfeiltasten mit Umschalt. Aufwand geschätzt 3 (Rahmen über gezeichnete Kacheln — die Liste ist virtualisiert, ausserhalb des Sichtbereichs gibt es keine Elemente;
  die Rechnung läuft auf den Positionen, nicht im DOM).
- **Reihenfolge:** zusammen mit e) (Spalten ein-/ausblenden, ziehen, „Baugruppe“) bauen, dann passt der Kopf.

## Navigation in grossen Beständen (5.10.2026, nur Beobachtung, nichts zu bauen)

Stand beim Tester mit 9 000 Modellen (FreeCAD-Library): Suche und Filter sind schnell, „100× besser als vorher“, er braucht nichts Weiteres. **Erwartung:** das Bedürfnis wächst nach Wochen — Suche
trägt, wenn man den Namen kennt, nicht beim Stöbern oder bei „weiss nicht, wie es heisst“; Ordner helfen bei grossen Beständen auch nicht. Kandidaten, wenn es soweit ist (Einordnung, nicht geprüft):
gemerkte Suchen als Sammlung (Aufwand 2–3), gleiches Teil in mehreren Formaten zu **einer** Kachel zusammenfassen (aus 9 000 gut 3 000; Aufwand 3–4, berührt „ein Modell = eine Datei“, vorher entscheiden),
Tags, die etwas trennen (Auto-Tags für den Bestand entfernen, Suche im Tag-Feld, nach Häufigkeit; Aufwand 2), Einstiege „zuletzt angesehen/hinzugefügt“ (teilweise da), Filter mit Trefferzahl nach dem Einschränken.
**Zeichen, dass es soweit ist:** dieselbe Suche wird mehrfach getippt; etwas wird nicht gefunden, das sicher drin ist. Nicht die Grösse des Bestands.

## Eingangsliste statt „Einlesen anstossen“ (5.10.2026 — **überholt** durch KONZEPT §3.4: Hochladen entfällt; gebaut nur als 0.47.0 auf dem Branch, nicht übernehmen)

**Anlass:** Hochladen von 45 bis 121 Dateien im Codespace war „sehr langsam“, und die Zeile oben rechts zeigte „219 Dateien, 1 neu in unter 1 s“. Der Fix in 0.45/0.46 (nur die letzte hochgeladene Datei stösst das Einlesen an,
Läufe einer Kette werden zusammengezählt) ist ein **Notbehelf, keine Lösung** — so festgehalten vom Anwender. Schwächen: (1) jeder Upload-Stapel kostet einen vollständigen Durchlauf durch **alle** Ordner (auf der langsamen Platte des Testers ca. 12 s,
nur um Dateien zu finden, die man gerade selbst hineingelegt hat); (2) es hängt am Browser — bricht der Upload ab oder wird der Tab geschlossen, bleibt die Datei ungeprüft im Ordner, bis jemand ⟳ klickt; (3) es passt nicht zum Hintergrunddienst nach Art der OCR bei pDMS.

**Lösung (Aufwand 3, eigener Schritt mit Test und Gegenprobe):** der Upload schreibt die Datei und trägt ihren Pfad in eine **Eingangsliste** ein — mehr nicht, keine Wartezeit, kein Anstossen. Ein Dienst im Hintergrund nimmt, was gerade in der Liste steht (mehrere Einträge zu einem Paket
zusammengefasst), liest **nur diese Dateien** ein (Hash, Metadaten, in die Datenbank, ohne Ordner zu durchsuchen) und übergibt an die Warteschlange der Vorschaubilder, die schon ihren eigenen Hintergrundlauf hat (0.46.0, `hat_offenes`). Die Eingangsliste steht im Bestand (`arbeit/`,
atomar geschrieben) und überlebt einen Neustart; die Platte bleibt die Wahrheit — was in der Liste fehlt, findet das nächste vollständige Einlesen trotzdem. Das vollständige Durchsuchen bleibt für ⟳ (Dateien, die von aussen hineinkamen) und „Beim Start einlesen“.

**Zu beachten:** (a) ein Teillauf darf **nichts als „fehlt“ oder „entfernt“ markieren** — die Erkennung verschobener und gelöschter Dateien braucht den Überblick über alle Ordner und gehört nur zum vollständigen Lauf; (b) doppelte Dateien erkennt der Hash schon (`_anlegen`), das gilt im Teillauf genauso;
(c) die Oberfläche folgt heute einem **Lauf** (Dialog, Nummer, `einlesen.lauf`); mit der Eingangsliste braucht sie eine ruhigere Anzeige, am besten das Fenster unten links, und der modale Dialog beim Hochladen muss neu gedacht werden (Entscheidung des Anwenders, siehe unten);
(d) Tests: Upload bricht mitten im Stapel ab → die schon hochgeladenen werden trotzdem eingelesen; Neustart mit gefüllter Liste setzt fort; Teillauf markiert keine fehlenden Dateien; Gegenprobe je Eigenschaft. **Hängt zusammen mit:** der Frage, ob der Einlese-Dialog modal bleibt (er verdeckt das Fenster unten links bis „OK“).

## Offen, in dieser Reihenfolge

1. **Warteschlange (a, b)** — entschieden, noch nicht gebaut:
   - Die Warteschlange besteht aus **Einträgen**: eine Baugruppe oder ein
     Einzelmodell, mit Anzahl Sätze. Eigener Knotentyp statt Feld
     `queue_position` am Modell; KONZEPT §6.1 anpassen; bestehende
     Positionen übernehmen.
   - **Seitenleiste als Baum:** Baugruppe (🧩) oberste Ebene, ihre offenen
     Teile mit Menge darunter, aufklappbar. Einzelmodelle auf gleicher
     Ebene mit eigenem Symbol (🧊). Dieselbe Baugruppe zweimal = ein Eintrag
     „×2 Sätze“.
   - Ziehen verschiebt die oberste Ebene (Baugruppe samt Teilen).
   - Abschnitt einklappbar, begrenzte Höhe mit eigenem Scrollen.
   - Block verschwindet, wenn alle Teile gedruckt sind; „Fehlende in die
     Warteschlange“ legt einen Baugruppen-Eintrag an.
   - Sortieren-Knopf in der Warteschlange ausblenden (wie in der
     Baugruppenansicht).
2. **d) Rechte Seitenleiste:** Informationsdichte. Richtung: Reiter.
   Erst zusammen entwerfen, dann bauen. Vorbild ist 3MF Katalog o. ä.,
   **nicht pDMS** (zu geringe Dichte).
3. **e) Listenansicht:** Spalten ein-/ausblenden, in der Breite ziehen,
   Spalte „Baugruppe“. Sie ist heute zu starr.

Hinweis: Bestehende Notizen an Baugruppen-Positionen sind nur noch als Text
sichtbar, nicht bearbeitbar — bewusst, Testbestand.

## Idee, noch nicht gebaut

- **Ausführliches Protokoll für den Tester ohne Terminal (0.46.3, 6.10.2026, gebaut):** Anlass: „10 min gewartet, partAtlas war tot“ — ohne Hinweis, wo es stand. `partatlas.log` im Bestand (4 MB × 3,
  im Einstellungs-Reiter „Einlesen“ per Knopf im Dateimanager zu zeigen) enthält jetzt: Umgebung (Python, System, Kerne), Katalog mit Zahlen, Einstellungen, was im Bestand aussteht und was beim
  Start geschieht; jeden Lauf mit Beginn, **jedem Phasenwechsel samt Zahlen** und Bilanz; Vorschaubilder mit Anzahl, Fortschritt je 100 und Dauer; **FreeCAD je Datei** („beginnt mit Datei 3 von 25: Name“),
  Zeitgrenze und Prozessnummer; ausgefallene Arbeiter; kleine Bilder mit Dauer; **alle 30 s einen Herzschlag** solange der Dienst arbeitet (Stand und Antwortzeit der Serverschleife) —
  **antwortet die Schleife nicht binnen 5 s, steht der Stapel aller Threads dabei** (woran es festhängt); jede ändernde Anfrage (Weg, Status, Dauer, ohne Inhalt), jede Anfrage über 3 s, jeder neue Browser
  (Name und Fassung, wichtig: Firefox oder Chromium), Fehler der Oberfläche (JavaScript, höchstens 50 je Serverlauf), unbehandelte Fehler in Threads, und Fehler von uvicorn (bisher gingen die
  nicht in die Datei). Geprüft: `test_scan` 92, `test_api` 79, sieben Gegenproben fallen; im echten Server angesehen. **Nicht geprüft:** Firefox; wie gross die Datei bei einem 9 000-Modelle-Lauf wird.
  Wenn der Prozess ganz einfriert (GIL, Speicher), schreibt auch der Herzschlag nichts mehr — das Ausbleiben der Zeilen ist dann selbst der Hinweis.

- **Beenden bricht ein laufendes Einlesen ab (0.46.2, 6.10.2026, gebaut):** Rückmeldung des Testers („hängt im Neu-Einlesen-Menü, nach Abschiessen und Neustart hängt es wieder“) nachgestellt
  (Unterordner mit FCStd und STL, Namen mit °, im Chromium): das Einlesen selbst lief auf 0.46.0 sauber durch (1,4 s), **das Hängen selbst nicht reproduziert**. Gefunden: arbeitet FreeCAD
  an einer Datei oder hängt es, wartete das Beenden bis zu 30 s auf den Lauf (Strg+C schien nichts zu tun), ein hartes Beenden liess FreeCAD als Prozess zurück, und der Neustart setzte die
  Umwandlung derselben Datei fort. Jetzt ruft das Beenden `abbrechen()` (Test in `test_api`, Gegenprobe fällt). Zweite wahrscheinliche Ursache für „auch nach dem Neustart“: `start.sh`
  öffnete bei noch laufendem alten Prozess nur wieder den Browser — jetzt nennt es die laufende Fassung und startet nach Rückfrage neu (`--neu` ohne Rückfrage). **Offen:** Fassung,
  `partatlas.log` und `pgrep -af "partatlas|freecad"` des Testers; ob sein FreeCAD (Paket, Flatpak, AppImage) an der echten FCStd hängt.

- **3D-Ansicht ohne Datei (Backlog, 02.10.2026 zurückgestellt — erst die Kerndinge härten):** beim Einlesen ein vereinfachtes
  Anzeige-Netz im Bestand ablegen; muss vorab geschehen, solange die Datei da ist (für den Bestand ein einmaliger Lauf im Hintergrund,
  0,1–0,4 s je Modell). Gemessen an Stanford-Testmodellen, je Modell: 30 000 Dreiecke 0,23–0,27 MB (~1,4 GB bei 5 700 Modellen —
  zu viel), **5 000 Dreiecke 37–40 kB (~0,23 GB)**, Form klar, feine Struktur weg; 4 Ansichten als WebP 56–91 kB, Drehung mit 8 Bildern
  125–178 kB — Bilder sind also nicht sparsamer. Empfehlung bei Bedarf: 5 000 Dreiecke, Quadrik-Vereinfachung (`fast-simplification`,
  MIT). Nebenbefund: das heutige Ausdünnen per Zufall über 200 000 Dreiecken sieht löchrig; die Vereinfachung behöbe das auch.

- **„Direkt drucken“ als Hover-Knopf:** hängt an der Druckanbindung und ist eine
  eigene Sache. Slicer und CAD gibt es schon (siehe unten, „Hover-Knöpfe“).
