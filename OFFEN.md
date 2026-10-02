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
