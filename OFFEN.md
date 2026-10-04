# partAtlas — Stand und nächste Schritte

Arbeitsstand für den nächsten Chat. Führend bleibt `KONZEPT.md`; hier steht,
was gerade offen ist und was entschieden wurde. Nach jeder erledigten Sache
aktualisieren.

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
in `THUMB_ENDUNG` (`bestand.py`). Offen: Thumbs nach dem Einlesen im Hintergrund
vorbauen (heute erst beim ersten Abruf), Thumbs aus Sicherung/Export lassen.
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
**Noch offen (klein):** Zeitgrenze je Datei, einmal parsen statt dreimal (Hash, Analyse, Render) — erst nach den Zahlen vom 4,1-GB-Lauf des Testers.

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

- **3D-Ansicht ohne Datei (Backlog, 02.10.2026 zurückgestellt — erst die Kerndinge härten):** beim Einlesen ein vereinfachtes
  Anzeige-Netz im Bestand ablegen; muss vorab geschehen, solange die Datei da ist (für den Bestand ein einmaliger Lauf im Hintergrund,
  0,1–0,4 s je Modell). Gemessen an Stanford-Testmodellen, je Modell: 30 000 Dreiecke 0,23–0,27 MB (~1,4 GB bei 5 700 Modellen —
  zu viel), **5 000 Dreiecke 37–40 kB (~0,23 GB)**, Form klar, feine Struktur weg; 4 Ansichten als WebP 56–91 kB, Drehung mit 8 Bildern
  125–178 kB — Bilder sind also nicht sparsamer. Empfehlung bei Bedarf: 5 000 Dreiecke, Quadrik-Vereinfachung (`fast-simplification`,
  MIT). Nebenbefund: das heutige Ausdünnen per Zufall über 200 000 Dreiecken sieht löchrig; die Vereinfachung behöbe das auch.

- **„Direkt drucken“ als Hover-Knopf:** hängt an der Druckanbindung und ist eine
  eigene Sache. Slicer und CAD gibt es schon (siehe unten, „Hover-Knöpfe“).
