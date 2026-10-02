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
Seitenleiste (ohne Wahl: die Wurzeln); jede Gruppe enthält alle Modelle darunter, auch aus tieferen Unterordnern;
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

- **„Direkt drucken“ als Hover-Knopf:** hängt an der Druckanbindung und ist eine
  eigene Sache. Slicer und CAD gibt es schon (siehe unten, „Hover-Knöpfe“).
