# partAtlas — Stand und nächste Schritte

Arbeitsstand für den nächsten Chat. Führend bleibt `KONZEPT.md`; hier steht,
was gerade offen ist und was entschieden wurde. Nach jeder erledigten Sache
aktualisieren.

## Stand: 1.0.4 auf `main` (25.10.2026, für den Tester)

Neu: die **Spule im Lager** (Bild vor jeder Karte, Wicklung in der Farbe der Spule; auch im Formular und im leeren Lager). Handbuchbilder des Lagers neu. Rückweg: Zweig `fassung-1.0.3`.
**Nicht auf `main`:** die Desktop-Arbeit (Zweig `ccr-212cc51e-yf8m3p`).

## Stand: 1.0.3 auf `main` (25.10.2026, für den Tester)

Neu: das **Lager** (Spulen: Karten und Liste, Suche, Filter, Formular, Nachkaufen, Löschen mit Rückgängig, Bild), **„Reicht das Filament?“** im Inspektor und als Punkt in der
Warteschlange (die im Programm weiter ausgeblendet ist), **Abbuchen** beim Anlegen eines Drucks, **Materialkosten**; Farbschema **GNOME** zur Wahl; Handbuch-Kapitel „Lager“.
Rückweg: Zweig `fassung-1.0.2`. **Nicht auf `main`:** die Desktop-Arbeit (Zweig `ccr-212cc51e-yf8m3p`).

## Stand: 1.0.2 auf `main` (25.10.2026, für den Tester)

Neu: Farbschema **Filament** (Blaugrün, Vorgabe) mit **Messing** und **Blaupause** zur Probe (Einstellungen › Ansicht, gemerkt im Browser; später bleibt eines),
Atlas-Zeichen vor dem Namen und im Tab, „Katalog“ aus dem Titel; 3D-Ansicht zeichnet nur bei Bewegung und senkt bei Last die Auflösung (test_viewer_ui 7/7);
Cura-G-Code: Druckzeit wird gelesen (test_slicer 14/14); Handbuchbilder neu. Rückweg: Zweig `fassung-1.0.1`.
**Nicht auf `main`:** die Desktop-Arbeit (`desktop/`, `partatlas/starter.py`, Actions, Tauri-Fenster, Einzeldatei, Starter-Betrieb) liegt nur auf dem Branch
`ccr-212cc51e-yf8m3p` — Anwender 25.10.2026: „keinerlei App-Aktivitäten“ in diesem Update. Die Aufgabenliste unten nennt, was erledigt ist (das alte Bild beim
Berechnen war kein Fehler von partAtlas, sondern ein Verlust im gepackten Fenster-Programm).

## Schema D „GNOME“ (25.10.2026, nur auf dem Branch, kommt mit dem nächsten Update)

Vierte Wahl unter Einstellungen › Ansicht: Palette von libadwaita (GTK 4) — fast Weiss `#fafafb` / Graphit `#242424`, Akzent GNOME-Blau
(`#1b6bcf` hell, `#78aeed` dunkel). **Nur Farben**, Lesbarkeit gerechnet (Schrift und Akzent mindestens 4,5 : 1). Der Anwender meinte „ganz modernes UI-Design
à la GTK 4“; die Formen (grössere Rundung, mehr Luft, Schalter statt Häkchen, flache Kopfleiste) gehören dazu, sind aber **nicht gebaut** und dienen später dazu,
sich weiter vom 3MF Katalog zu lösen. Ein Bild dazu nur, wenn der Anwender es will (Aufwand 2–3 für Rundung und Abstände, `--radius` ist ein einziger Wert,
ob alle Teile ihn nutzen, ist ungeprüft).

## G-Code-Zeichen und Schriftzug (25.10.2026, Wunsch des Testers; auf dem Branch, nicht auf `main`)

Kachel (und Spalte „G-Code“ in der Liste, per Spaltenmenü wählbar): ein kleines Zeichen „G-Code“, wenn zum Modell **irgendwo** ein G-Code gehört — an einem Druck angehängt
(Feld `gcode_n` am Modell, wie `drucke_n` in `Drucke.nachziehen` geführt, Umzug alter Bestände in `_gcode_nachziehen`) oder weil das 3MF schon geslict ist (Platten). Ohne
Zahlen und Farben (Anwender: „sonst verwirrend“). Feste Plätze unten rechts auf der Kachel: G-Code ganz rechts, der Status (✓ n×, Datei fehlt …) links davon, der Platz bleibt auch ohne G-Code frei — nichts rutscht. Ein Klick wählt das Modell und öffnet Reiter Drucke bzw. Slicer. Suche `gcode:ja` / `gcode:nein`. Der Schriftzug oben heisst
„PartAtlas“ (Tester und Anwender: besser lesbar als „PARTATLAS“). test_drucke 42/42, test_gcode_ui 7/7, Gegenproben fallen. **Offen (Entscheidung Anwender):** die Überschneidung
der Reiter „Slicer“ (Einstellungen in der Datei) und „Drucke“ (Einstellungen je Druck): Vorschlag Slicer → „In der Datei“, Drucke = was passiert ist, dazu ein Knopf
„Aus der Datei als Druck anlegen“ (Aufwand 1–2). Handbuchbilder zeigen noch „PARTATLAS“ — beim nächsten Push alle neu erzeugen (`python werkzeuge/handbuch_bilder.py`).

## Spulenbild im Lager (25.10.2026, auf dem Branch, nicht auf `main`)

Das KI-Bild des Anwenders (312 × 327 px, weisser Hintergrund) ist freigestellt (`web/spule.png`, 125 KB, Schatten als weicher Schwarzton) und hat eine Maske für die Wicklung
(`web/spule-wicklung.png`, 17 KB). `lager.js` `lgSpule(farbe, breite)` legt den Farbwert per CSS über die Maske und multipliziert ihn mit dem Bild (`mix-blend-mode: multiply`); sehr
dunkle Farben werden aufgehellt, ohne Farbe ein helles Grau. Eingebaut an Karte (50 px, statt des Kürzels), Bildfeld im Formular (64 px) und leerem Lager (150 px). Entscheidung
des Anwenders: **Grösse so lassen**, bei Bedarf des Testers später grösser (60–64 px auf der Karte). Bekannt: schwarze Spule hebt sich auf dunklem Grund nur schwach ab; ein
farbiger Pixelrand unten an der Wicklung. Die Skripte zum Freistellen liegen nicht im Repo (Scratchpad: `spule_png.py`); bei einer Änderung am Bild neu erzeugen.
Auf `main` mit der nächsten Fassung (1.0.4), samt Eintrag unter „Neu in dieser Fassung“.

## Aufgabenliste (25.10.2026) — Aufwand 1–5, Budget: Stücke mit 1–2 zuerst

**Nächstes sichtbares Update für den Tester (Fassung 1.0.2 → `main`)** — Stand: gebaut / offen
- gebaut auf dem Branch: 3D-Ansicht zeichnet nur bei Bewegung, senkt bei Last die Auflösung (1.0.2); Titel ohne „Katalog“
- **erledigt (1.0.2):** Farbschema C Filament als Vorgabe, A und B wählbar; Atlas-Zeichen in Kopf und Tab (später gegen das Zeichen mit den drei Scheiben tauschen); Handbuchbilder neu
- **erledigt (1.0.2):** Druckzeit aus Cura-G-Code (Orca, Prusa, Bambu gingen schon); „Vorschaubild berechnen“ behält das alte Bild — war schon so, kein Fehler

**Filament und Drucker nach dem 3MF Katalog** (Abschnitt unten): **Etappe 1 gebaut (Branch, 25.10.):** die **Seite „Lager“** (Rail-Knopf, wie Aufräumen eine eigene Ansicht): Kennzahlen, Suche, Filter Niedrig/Leer/Abgelegt, Dashboard und sortierbare Liste, Doppelklick bearbeitet, Formular als Seitenfenster (Farbwert Palette + Hex + Farbwähler, Anzahl −/+, Balken), **Nachkaufen**, Ablegen statt Löschen mit Rückgängig, neue Einträge kurz grün umrandet. `lager.py`, `lager.js`; test_lager 14/14, test_lager_ui 16/16, Gegenproben fallen. **Dazu gebaut (25.10.):** Spulen werden **gelöscht** (mit Rückgängig, nicht abgelegt — Anwender), **Bild an der Spule** (PNG/JPG/WebP ≤ 5 MB, mit „Speichern“ übernommen, Nachkaufen teilt es), **„Reicht das Filament?“** im Inspektor (3MF mit Platten; gleiches Material, ähnliche Farbe; reicht / mit Spulenwechsel / reicht nicht mit fehlender Menge / unklar; Spule und Ort genannt) und als **Punkt in der Warteschlange** (von oben nach unten mit gemeinsamem Bedarf, eine Spule zählt nicht doppelt). test_lager 28/28, test_lager_ui 25/25, Gegenproben fallen. **Beobachtet:** die Warteschlange ist im Programm ausgeblendet (`data-ab-phase=2`, nur mit `?phase=2`) — so vorgefunden; ob sie sichtbar werden soll, entscheidet der Anwender. **Auch gebaut:** Abbuchen beim Anlegen eines Drucks (Spule wird nach Material, Farbe und Verbrauch vorgeschlagen, abgezogen nur nach Wahl, nie unter 0; der Druck merkt sich Spule, Menge, Kosten; keine automatische Rückbuchung beim Löschen) und Materialkosten (Gewicht × Preis je g der zugeteilten Spule, am Modell im Block „Reicht das Filament?“, am Druck als Chip). test_lager 35/35, test_lager_ui 28/28. **Entschieden (Anwender 25.10.):** keine Drucker/Fächer — der Tester hat einen Anycubic mit selbstgebautem Abroller (4 Spulen) und wechselt von Hand; der einfache Weg „eine Spule am Halter“ gilt auch für die A1 Mini. Fächer nur, wenn er sie vermisst. **Parität (ohne Resin, Druckervielfalt, Anbindung) damit erreicht.** Offen bis `main`: Handbuch-Kapitel, „Neu in dieser Fassung“, Warteschlange sichtbar machen? (Entscheidung Anwender). Anwender 25.10.: **kein Resin**, **keine Drucker-Vielfalt** (Vorlagen, Anbindung). Noch nicht auf `main`; kommt mit Handbuch und Neuigkeiten. Weiter:  Spule am Druck, Rest abziehen (2) → „Reicht das Filament?“ (1) → Kosten (1–2); Drucker klein (2) → „Passt auf den Drucker?“ (1)

**Programm zum Anklicken (Tester auf Manjaro, Firefox, AppImage-Manager)** — Einzeldatei mit Starter ist gebaut (Action `einzeldatei.yml`), offen:
Lebenszyklus (Beenden-Knopf mit Rückfrage bei laufender Arbeit, kein unsichtbarer Server; Systemmenü-Symbol als eigener Schritt, Aufwand 3–4; Fortsetzen nach Beenden prüfen) ·
AppImage mit Starter, Menüeintrag, Symbol (2) · Aktualisierung über GitHub Releases (2) · Handbuch/README zum Start (1) · Windows-.exe und Installer (nicht prüfbar, bis ein Windows-Tester da ist) ·
Tauri-Fenster liegt zurückgestellt auf dem Branch.

**Entwickeln (Versionen, Varianten)** — Konzept offen, braucht den Tester (STORIES.md durchgehen, drei Fragen zum Ablauf der Walzen): „gilt“ und „ersetzt durch“ als kleinster Anfang (2); „Wo wird es verwendet?“ (2–3); Versionsverlauf je Modell (3–4)

**Sichern** — Backup als ZIP und sicheres Wiederherstellen (4–5, ausgeblendet gebaut); Grösse des Bestands: Ordnergrössen vom Tester abwarten (`sicherungen`, `vault`, `datenbank`, `thumbs`, `netz`), dann entscheiden (weniger behalten oder harte Verweise, 2–3)

**Formate** — STEP/FCStd ohne FreeCAD: Entscheidung Geometriekern, Spike mit 3–4 echten Dateien (3–4) · 7z/rar entpacken (fremde Pakete)

**Wartet auf den Tester** — Windows: start.bat, Ordner mit offener Datei umbenennen, nur Gross-/Kleinschreibung · echte Dateien aus Bambu Studio und Anycubic Slicer Next · Dauer des Einlesens bei 5 793 Dateien (Protokollzeile) · Firefox/Einzeldatei ausprobieren

**Später (Ideen, nur bei echtem Bedarf)** — G-Code-Vorschau, Messen/Schnitt, mehr Formate (IGES, AMF, PLY, glTF), Name/Markensuche, G-Code-Ordner mit Zuordnung (3)

## Parität Material Manager (3MF Katalog, gelesen 25.10.2026 in `docs/benutzerhandbuch/BENUTZERHANDBUCH.md` und den Bildern 08, 09, 10, 22, 25, 26, 27, 12, 24)

Anwender: **in der ersten Iteration funktionale Parität**. Meine erste Spulenliste (Fenster, lager.js) ist nur ein Teil davon und wird zur Seite umgebaut.
Der Material Manager ist eine **eigene Seite** (zweites Symbol links), nicht ein Fenster: oben Schalter Filament | Resin; vier Kennzahlen (Spulen gesamt,
Restbestand gesamt, belegte Lagerplätze, niedrig/leer); Suchfeld (Material, Hersteller, Lagerort), Filter „Niedrig“ und „Leer“, Umschalter Dashboard | Liste,
Knopf „＋ Spule anlegen“. **Dashboard:** Karte je Spule mit Material-Kürzel, Farbpunkt, Hersteller · Farbname, Lagerort-Marke, Status (VORRÄTIG grün /
NIEDRIG orange / LEER rot), Rest in g mit Balken und Prozent, Durchmesser, Preis, „＋ Nachkaufen“, Stift, ✕. **Liste:** sortierbare Spalten Material,
Hersteller, Farbe, Lagerort, ⌀, Bestand (Balken), Preis, Status. Doppelklick auf Karte/Zeile = Bearbeiten. **Formular** als Seitenfenster rechts: Bild (ziehen
oder klicken, PNG/JPG/WebP ≤ 5 MB), Material, Hersteller, Farbname (Autovorschläge), Farbwert (Palette mit 16 Feldern + Hex-Feld), Anzahl Spulen mit −/+,
Lagerort, Durchmesser, Preis, Ursprungsgewicht, Restgewicht mit Balken und Prozent; Gewichte auf 0,1 g. **Nachkaufen:** kleines Fenster, Anzahl 1–20, Menge/Preis/
Ort anpassbar, übernimmt Art, Material, Hersteller, Farbe, Farbwert, Bild, Durchmesser; neue Einträge kurz grün umrandet. **Resin:** eigene Ansicht (Flaschen, ml,
„− Verbrauch“, nie unter 0, kein Durchmesser), zählt nicht bei „Reicht das Filament?“ und den Kosten. **Drucker** (rechte Spalte, Printer Manager): Drucker
Filament oder Resin (danach fest), Name, Hersteller, Modell, Düse, Bauraum X×Y×Z; **Einheiten** aus Vorlagen (Bambu AMS / AMS lite / AMS HT, Creality CFS, Prusa MMU3,
Anycubic ACE Pro, Spulenhalter) oder eigene mit Fachzahl; jeder Filament-Drucker hat einen Spulenhalter; Spule **auf ein Fach ziehen** oder Fach anklicken und wählen,
„Herausnehmen“ bringt sie an den **Stammplatz** zurück; Resin-Drucker haben eine Harzwanne. **Reicht das Filament?** (Detailseite, für gesliceste 3MF, über alle Platten):
je Filament **reicht / reicht mit Spulenwechsel / reicht nicht (mit fehlender Menge) / unklar**, nennt die Spule mit Rest und wo sie steckt; die **Warteschlange**
zeigt dasselbe als Symbol und rechnet von oben nach unten mit dem gemeinsamen Bedarf; nichts wird dabei abgebucht. **Abbuchen:** nur nach Bestätigung im Dialog „Neue
Drucke“ (Verbrauch in g, vorgeschlagene Spule = die im Drucker eingelegte, vorgeschlagenes Modell über den Dateinamen); mit Modell entsteht ein Druckprotokoll-Eintrag.
Materialkosten je Modell aus Gewicht × Preis. **Moonraker** (Druckerverlauf lesen) entfällt für die Drucker des Testers (A1 Mini, Kobra 2).
Stücke (Aufwand): Seite mit Kennzahlen, Filtern, Dashboard/Liste, Formular, Nachkaufen (4–5) · Bild an der Spule (1) · Drucker mit Einheiten und Fächern, einlegen/herausnehmen (4) ·
Reicht das Filament? mit Warteschlange (3) · Abbuchen mit Bestätigung und Druckeintrag (2–3) · Materialkosten (1) · Resin (2).

## Filament, Drucker, G-Code nach dem 3MF Katalog (Anwender 25.10.2026) — nur Entwurf, nichts gebaut

Drucker des Testers: Bambu A1 Mini, Anycubic Kobra 2 → **Moonraker entfällt** (Kobra 2 ohne Klipper, A1 Mini ist Bambu). Budget: nur Stücke mit Aufwand 1–2.
Vorlage (gelesen in `Bexxs75/3mf-katalog-manager`, README): **Spule** = Material, Hersteller, Farbname, Farbwert (Palette oder Hex), Lagerort, Durchmesser,
Startgewicht und Rest (0,1 g), Preis, optional Bild; mehrere gleiche Spulen auf einmal, „Nachkaufen“ (1–20 volle Spulen); Karten mit Bestandsbalken
und sortierbare Liste mit Statusfiltern, Doppelklick öffnet das Formular; Autovervollständigung für Material/Hersteller/Ort. **Drucker** mit AMS/CFS/MMU/ACE,
jeder Drucker hat einen Spulenhalter; Spule per Ziehen in ein Fach. **„Reicht das Filament?“** am 3MF: Bedarf gegen Spulen mit passendem Material und
ähnlicher Farbe, drei Ausgänge (reicht / reicht nach Spulenwechsel / reicht nicht, mit fehlender Menge), nennt die passende Spule und ob sie geladen ist.
Druckprotokoll getrennt vom Status, mehrere Versuche je Modell. Resin: eigener Schalter, nicht in der Prüfung.
Stücke (Aufwand): 7 Druckdauer aus dem G-Code (1) · 1 Spulenliste (2) · 2 Spule am Druck wählen, Rest abziehen (2) · 3 „Reicht das Filament?“ am Modell (1) ·
4 Filamentkosten (1–2) · 5 Drucker klein: Name, Düse, Bauraum (2) · 6 „Passt auf den Drucker?“ Masse gegen Bauraum (1). Erste Runde: 7 und 1–3; zweite: 5, 6.
Bewusst nicht: Resin, AMS-Fächer, G-Code-Ordner mit Zuordnung (3), Druckeranbindung.

## Zeichen, Farben, Titel (Anwender 25.10.2026)

„Katalog“ aus dem Titel genommen (Kopfzeile zeigt nur PARTATLAS und die Fassung). Zeichen und Farbschema: Vorschlagsseite
(Artefakt, drei Richtungen A Messing / B Blaupause / C Filament neben der heutigen, dazu drei Zeichen: Raster, Würfel, Atlas) — **Entscheidung des Anwenders offen**.
Die heutigen Farben sind aus dem 3MF Katalog übernommen (Kopf von `app.css`).

## Desktop, Wende (23.10.2026): Einzeldatei mit Starter statt Tauri-Fenster (Tester auf Manjaro, Firefox)

Rückmeldungen des Testers zum Tauri-Spike: das AppImage (mit mitgelieferter Webansicht) zeigte ein schwarzes Fenster und **hängte beim zweiten
Start den ganzen Rechner auf** (sehr alte Grafikkarte, Mesa). Das Archiv mit der System-Webansicht (webkitgtk-4.1) und Software-OpenGL
(`LIBGL_ALWAYS_SOFTWARE=1`, `WEBKIT_DISABLE_DMABUF_RENDERER=1`) lief, mit 3D-Ansicht, 9 083 Modellen. Offen blieben: Handbuch (jetzt im eigenen
Fenster), **Anhänge (Bilder/PDF) in Baugruppen** (WebKitGTK ohne PDF-Betrachter), **gepackter Server rechnet keine neuen Vorschaubilder**
(PyInstaller ohne `multiprocessing.freeze_support()`: jeder Hilfsprozess startete einen zweiten Server, „Adresse belegt“; nachgestellt), und
„Vorschaubild berechnen“ lässt das alte Bild verschwinden, bis das neue da ist (in der Git-Fassung nicht aufgefallen, weil dort das Berechnen
gelingt; **bleibt zu beheben: altes Bild behalten bis das neue da ist**).
Der Tester meinte eigentlich: **eine Datei anklicken, der Standardbrowser öffnet partAtlas** (wie eine PWA). Das ist gebaut:
`partatlas/starter.py` (PARTATLAS_STARTER=1: Browser öffnen, laufendes partAtlas nur öffnen, beenden wenn 45 s keine Seite mehr verbunden
ist oder nach 120 s kein Browser kam; läuft das Einlesen, bleibt der Server), `desktop/launch.py` (Starter als Standard, `freeze_support`),
`desktop/bauen-einzeldatei.sh` (PyInstaller onefile, 40 MB), Action `einzeldatei.yml` (Artefakt `partAtlas-Linux`). test_starter 8/8, Gegenproben fallen.
Das Tauri-Fenster bleibt auf dem Branch (`desktop-fenster.yml`, nur von Hand; Tauri setzt PARTATLAS_STARTER=0), eventuell für Windows.
**Nicht gebaut, entschieden nein:** AppImage (kein Vorteil gegenüber der Einzeldatei, braucht FUSE). **Offen:** Menüeintrag mit Symbol
(Skript `installieren.sh` oder die Datei legt ihn selbst an), Selbstaktualisierung (Starter prüft GitHub Releases), Windows-`.exe`, Handbuch
und README zum Start der Einzeldatei.

## Desktop-Programm, Schritt 1: Spike (23.10.2026, Ordner `desktop/`)

Anwender: **Fokus Manjaro** (der Tester hat nur das), Windows erst danach — nicht testbar, solange nur Manjaro da ist.
Gebaut: Tauri 2-Hülle (`desktop/src-tauri/src/main.rs`) startet den Server (PyInstaller-onedir, `desktop/launch.py`) als Kindprozess auf einem freien
Port, wartet bis er antwortet, zeigt ihn im Fenster; beim Beenden wird der Server beendet, unter Linux auch bei hartem Ende (PDEATHSIG).
`desktop/bauen.sh` baut alles (PyInstaller, dann `tauri build`) zu einem **AppImage (114,6 MiB)**, Fassung aus `partatlas/version.py`.
Gemessen hier (Ubuntu 24.04, Xvfb): Fenster zeigt partAtlas 1.0.1, Server läuft, Bestand wird angelegt. **Nicht geprüft: Manjaro.** Bekannte Risiken
(aus Erfahrungsberichten, nicht gemessen): das AppImage bringt webkit2gtk mit, auf Arch/Manjaro kann das zu weissem Fenster oder Absturz führen
(EGL); Ersatz wäre ein `PKGBUILD` mit der Webansicht des Systems.
**Bekannte Lücken im Spike:** F1/„?“ (Handbuch öffnet in neuem Tab: `window.open`), Links nach aussen, Ziehen von Dateien aus dem Dateimanager
(`dragDropEnabled: false`, ungetestet), einzelne Instanz, Fenstergrösse merken, Updater, Windows. Zum Tester kommt es über GitHub Actions
(AppImage als Artefakt) — noch nicht gebaut.

## Stand: 1.0.1 auf `main` (23.10.2026, für den Tester)

Rückmeldung des Testers umgesetzt: FCStd wird in keinem Slicer mehr angeboten (Einzelheiten unten, Abschnitt 1.0.1). Dazu Dokumente ohne
Programmänderung: KONZEPT §0 (Massstab), `STORIES.md` (Nutzungsprofile und Geschichten, Entwurf). Rückweg auf 1.0.0: Zweig `fassung-1.0.0`.
Vor dem Push: alle 33 Suiten ausser test_ui grün, **test_ui komplett 70/70**.
**Offen:** wie bei 1.0.0 (Windows-Rückmeldung, echte Slicer-Dateien) und die Ordnergrössen des Testers (Bestand 264 MB, vermutet: Sicherungen).
**Als Nächstes:** Desktop-Programm mit Tauri (Spike, AppImage; Tester arbeitet unter Manjaro — webkit2gtk-Problem prüfen, `PKGBUILD` als Ersatz).

## 1.0.1 (17.10.2026, Rückmeldung des Testers: „bei FCStd wird der Slicer zum Öffnen angeboten, das geht gar nicht“)

Ursache: ein Programm, das man unter Einstellungen › Programme selbst wählt (`programme.eintrag_fuer`, `eigene`), bekam **alle fünf Formate**,
auch einen Slicer FCStd — erkannte Slicer (BEKANNT) nannten es nie. Der Hauptknopf nimmt für FCStd zwar das CAD, aber „Öffnen mit …“,
Rechtsklick und der Slicer-Knopf boten den Slicer an. Jetzt `formate_fuer`: bekanntes Programm → seine Liste, unbekannter Slicer → alle
ausser FCStd, CAD → alle; auch ältere gespeicherte Einträge mit allen Formaten werden so gelesen. Der gedämpfte Knopf „noch kein Slicer
eingerichtet“ erscheint für FCStd nicht mehr (`/api/programme` liefert `moeglich` je Art). test_api 90/90 (+4), neue Suite
test_programme_ui 3/3; Gegenproben fallen (drei im Server, eine in der Oberfläche). STEP bleibt im Slicer wählbar (Bambu, Orca, Prusa,
Anycubic lesen es), Standard bleibt das CAD.

## Stand: 1.0.0 auf `main` (16.10.2026, für den Tester)

Der Katalog ist fertig. Seit 0.95.7: Bereinigen neu gegliedert, jede Ansicht erklärt sich (0.96); Hinweis „Dein Katalog in deinem
Backup“, ZIP-Backup gebaut aber bis zum Wiederherstellen ausgeblendet (0.97); Ordner anlegen/umbenennen/verschieben wie im Explorer,
alle Unterordner im Baum (0.98.0–0.98.2); Umbenennen überall am Namen mit langsamem zweitem Klick, Rückgängig/Strg+Z (0.98.3);
Fehlermeldungen in einem Satz, feste Paketfassungen, start.bat, README für Fremde (0.98.4); Handbuch in der App mit Bildern, F1
(0.98.5/0.98.6); „Farbe der Vorschaubilder“ ausgeblendet (1.0.0). „Neu in dieser Fassung“: ein Eintrag 1.0.0 statt der Zwischenfassungen
(die nie auf `main` waren). Rückweg: Zweig `fassung-0.95.7` (README).
Vor dem Push: alle 32 Suiten ausser test_ui grün, **test_ui komplett 70/70**. test_ordner_ui fiel im Gesamtlauf einmal bei „Strg+Z:
Modell wieder unter altem Namen“ (Datei nach 10 s nicht zurück), danach siebenmal nachgestellt ohne Fehler, auch unter Volllast aller
Kerne — Wartezeit auf 20 s, die Prüfung nennt beim nächsten Fehlschlag den Zustand (Rückgängig gemerkt, Fokus, Meldung, Ordner).
**Offen nach 1.0:** Rückmeldung des Anwenders unter Windows (start.bat, Ordner mit offener Datei, nur andere Schreibung); echte Dateien
aus Bambu Studio und Anycubic Slicer Next; dann Versionsverlauf je Modell (OFFEN, „Nach 1.0 zuerst“).

## Bereinigen professionell (Auftrag 12.10.2026, nach Iteration 2)

Anwender: Bereinigen muss professionell werden — der Anwender bereinigt dort seine Datenbank bewusst. Entschieden: **Archiv** = das Modell
ruht, alles bleibt; neue und verschobene Dateien **ohne Fenster** wie bisher; **ein Fenster erst ganz am Ende des Einlesens**, nur für
fehlende Dateien, je Zeile Archiv (Vorgabe) / Behalten / Löschen und „Für alle übernehmen“ (ganzer Ordner gelöscht); „nicht unterscheidbar“
= gleicher Name, anderer Inhalt. Gliederung: Aufräumen (Datei fehlt · Gleiche Datei · Nicht unterscheidbar) · Archiv · Papierkorb.
Pakete: (1) Archiv, (2) Fenster am Ende des Einlesens, (3) Bereinigen neu gegliedert. Iteration 3 vom Anwender nicht gewünscht; der
Entwurf `backup.py` liegt im Scratchpad dieser Sitzung (nicht im Repo).
- **Paket 1 Archiv (0.66.0):** Feld `archiv` (Zeit) und `archiv_grund` („fehlt“/„hand“) am Modell. Archiviertes nur in der Ansicht
  „archiv“ (Bereinigen › 🗄 Archiv, mit Zähler), nicht in Liste, Suche, Zählern, Sammlungen. Ins Archiv: Rechtsklick, Leiste der
  Mehrfachauswahl (vorher Sicherung), im Inspektor bei „Datei fehlt“ als erster Weg (Archiv · Behalten · Suchen · Löschen). Zurück:
  Band im Inspektor, Rechtsklick, Leiste. Grund „fehlt“: taucht die Datei wieder auf (auch an anderem Ort), kehrt das Modell von selbst
  zurück (`_orte_setzen`). Neue Suite `test_archiv.py` 8/8, drei Gegenproben fallen.
- **Paket 2 Fenster am Ende des Einlesens (0.67.0):** der Scanner merkt sich genau die Modelle, deren Datei bei diesem Lauf ihren letzten
  Ort verlor (`Scanner.fehlt_neu`, Zahl im Status; nicht über die Zeit — zwei Läufe in derselben Sekunde —, nicht alle fehlenden).
  Am Ende meldet die Oberfläche wie bisher und öffnet dann EIN Fenster (`web/fehlende.js`): „51 Dateien fehlen“, nach Ordner gruppiert,
  je Modell was daran hängt (Drucke, Baugruppen, Sammlungen, Anhänge, eigene Bilder, Tags), Wahl je Zeile / je Ordner / für alle:
  Archiv (Vorgabe) · Behalten · Löschen; Fusszeile zählt die Wahl; „Später entscheiden“ ändert nichts. Dasselbe Fenster für alle offenen
  über Bereinigen › Datei fehlt › „Entscheiden …“. Server: `Katalog.fehlende(nur)`, `fehlende_entscheiden` (Sicherung vorher, prüft,
  dass jedes Modell wirklich fehlt), `/api/fehlende[?neu=1]`, `/api/fehlende/entscheiden`. Entwürfe gehen weiter still in den Papierkorb.
  Im Browser durchgespielt (Ordner „Drohne“, 51 Dateien, weggenommen → Fenster → alle ins Archiv; Ordner zurück → alle 51 von selbst
  zurück im Katalog). Neue Suite `test_fehlende.py` 9/9, drei Gegenproben fallen.
- **Paket 3 Bereinigen neu gegliedert (0.96.0, 16.10.2026):** Seitenleiste in zwei Gruppen — **Aufräumen** (Datei fehlt · Gleiche Datei,
  vorher „Duplikate“ · Unlesbar · Vorschläge, vorher „Aufräumen“) und **Aufbewahrt** (Archiv · Papierkorb). Regel: jede Ansicht unter
  Bereinigen sagt oben in der Leiste über der Liste, was sie zeigt und was ihre Aktionen tun, ob etwas verloren geht (`BEREINIGEN_TEXT` in
  `app.js`; Papierkorb und Datei fehlt mit eigenen Zeilen, Vorschläge mit eigener Fläche); leere Ansichten mit eigenem Satz. Inspektor ›
  Datei: jeder Ort mit 📂 zum Ordner (der Weg, eine überzählige Kopie zu löschen; nur Pfade des Modells, `aufraeumen.pfad_von`).
  **„Nicht unterscheidbar“ (gleicher Name, anderer Inhalt) bewusst nicht gebaut** (Anwender: weglassen, bis es jemanden stört).
  Neue Suite `test_bereinigen_ui.py` 2/2 (geht über alle Einträge der Seitenleiste — eine neue Ansicht ohne Erklärung fällt), zwei
  Gegenproben fallen; test_ansicht_ui 3/3 (einmal 2/3 im ersten Lauf, danach zweimal 3/3 — flatterhaft, nicht verfolgt). Handbuch nachgezogen.

## Qualitätsdurchgang vor 1.0 (16.10.2026)

Liste (mit dem Anwender): (1) alle Suiten ausser test_ui, (2) flatterhafte Prüfungen, (3) eigene Änderungen kritisch lesen,
(4) Oberfläche auf Konsistenz, (5) Fehlerwege, (6) README für Fremde aus frischem Klon, (7) Abhängigkeiten festlegen (Anwender
entscheidet), (8) Liste „nicht geprüft“ für 1.0 in KONZEPT. test_ui komplett erst unmittelbar vor `main`.
- (1) alle 30 Suiten grün (Stand 0.98.3).
- (2) test_ui „Ruhepause“: wartete fest 60 ms auf einen 0-ms-Zeitgeber; jetzt bis 300 ms nachfragen (< 400 ms, unterscheidet weiter).
  Gezielt (`ui_ruhepause.py` im Scratchpad, liest das JS wörtlich aus test_ui): 3/3, unter Volllast aller Kerne 5/5; Gegenprobe
  (Laden erst nach LIVE_SCAN_MS) fällt. test_ansicht_ui schon in 0.98.2 festgemacht.
- (3) gefunden: `ordner_bewegen` las die betroffenen Dateien vor der Sperre — ein gleichzeitiger Schreibvorgang an denselben Orten
  wäre überschrieben worden. Jetzt unter der Sperre gelesen (kein eigener Test: Wettlauf nicht verlässlich nachstellbar).
- (5) unerwartete Fehler zeigten „Fehler 500“. Jetzt `unerwartet` in main.py: Platte voll / keine Berechtigung oder gesperrt / Datei weg
  in einem Satz, sonst Art und Text, immer mit Hinweis aufs Protokoll (0.98.4). Neue Suite test_fehler 4/4, Gegenprobe fällt;
  test_api 86/86 (`unerwartet` in BEWUSST_ASYNC).
- (6) README für Fremde: Linux aus frischem Klon nach Anleitung geprüft (start.sh --demo, 57 Modelle); Windows-Abschnitt neu,
  Beschreibung ohne „Demo-Pilot“, „Wo deine Daten liegen“. **`start.bat`** (Doppelklick): Python ≥ 3.10 und git prüfen, kein zweites
  partAtlas (andere Fassung → Hinweis, beendet nichts selbst), `.venv` anlegen, Pakete nur bei geänderter requirements.txt (SHA256 über
  certutil), Browser öffnen, sobald der Server antwortet; CRLF über .gitattributes. **Unter Windows nicht ausgeführt — Anwender prüft.**
- (7) Feste Paketfassungen (Anwender: ja): requirements.txt (fastapi, starlette, pydantic, uvicorn, numpy, pillow, reportlab) und
  requirements-test.txt auf die geprüften Fassungen. Frische Umgebung nur daraus: `pip check` ohne Konflikt, alle 31 Suiten ausser
  test_ui grün.
- (8) KONZEPT §10 „Stand 1.0“: was nur nachgebaut oder nicht unter Windows geprüft ist.
- **Rückmeldung Windows offen:** start.bat (erster Start, zweiter Start bei laufendem partAtlas, nach `git pull`), Ordner umbenennen
  mit offener Datei, nur andere Schreibung bei Ordner und Modell.

## Weg zu 1.0 (Anwender, 16.10.2026)

Freiheit für Entscheidungen; vor einer Iteration höchstens 3 Fragen, währenddessen 1. Massstab Qualität. Reihenfolge:
1. ~~Bereinigen Paket 3~~ (0.96.0).
2. **Backup & Wiederherstellung** — **Paket 1 Backup erstellen (0.97.0, 16.10.2026):** `backup.py`, Zeilen je Inhalt (`ZEILEN`: Datenbank
   immer; Modelldateien, eigene Bilder/Druckfotos/Kaufteile, Anhänge, G-Code und Quellen, Aufgehobenes = `vault_archive` + alter
   `papierkorb/` — Vorgabe an; Vorschaubilder aus), `AUSGENOMMEN` mit Grund (arbeit, sicherungen, netz, thumbs, cache, Protokoll).
   Unbekanntes im Bestand kommt als „sonstiges“ trotzdem mit, `unbekannt()` meldet es (test_backup). Modelldateien = nur die Orte im
   Katalog, unter `dateien/<Wurzel-Kennung>/<Pfad>`; andere Dateien in den Ordnern nicht. ZIP mit `partatlas-backup.json`
   (Fassung, Zeilen mit Anzahl/Grösse, ausgelassene, Wurzelordner, nicht lesbare Dateien); Datenbank unter der Sperre, Dateien danach;
   Arbeitsdatei + fsync + os.replace, nie überschreiben; Platz vorher geprüft; Abbrechen; die letzten 2 bleiben (nur unser Name);
   Zielordner nicht im Bestand und nicht in einem Ordner mit Modellen. Reiter: Stand („Letztes Backup heute · n Modelle · Grösse“),
   Zielordner (Dialog des Rechners, sonst Pfad eintippen), Zeilen mit Grösse, Summe, Behalten, Fortschritt im Reiter und unten links.
   Zeilen und Zielordner gelten sofort (nicht erst mit „Speichern“ — „Backup erstellen“ braucht sie). test_backup 19/19 (vier
   Gegenproben fallen), test_backup_ui 3/3 (Gegenprobe fällt), test_schutz 28/28 (drei Einträge in ERLAUBT), test_api 86/86.
   Nicht gemessen: grosser Bestand (Zeit, Grösse; Windows).
   **Entscheid 16.10.2026 (Anwender): Backup und Wiederherstellen nach 1.0, als ein Ganzes** — der Anwender hat einen eigenen
   Backup-Ablauf; ein „Backup erstellen“ ohne Gegenstück wäre in 1.0 eine halbe Funktion. **0.97.1:** der ZIP-Teil ist im Reiter
   ausgeblendet (kein `#ein-backup`; Code in `app.js` und `backup.py`, Routen und test_backup bleiben); stattdessen „Dein Katalog in
   deinem Backup“: Pfad des Bestands, „Ordner zeigen“ (`/api/bestand/zeigen`), Hinweis, ihn ins eigene Backup aufzunehmen.
   test_backup_ui entfernt (prüfte die ausgeblendete Oberfläche; Stand in Commit 943f46f — beim Einblenden zurückholen).
   **Entwurf Wiederherstellen (nach 1.0, mit dem Anwender besprochen):** nie über den jetzigen Bestand, immer ein neuer Bestand
   daneben; Wechsel umkehrbar (Band „Zurück zum vorherigen“), den alten löscht partAtlas nie; Modelldateien nur in einen neuen, leeren
   Ordner (ausdrücklich gefragt, voller Pfad), je Ordner aus dem Backup: auspacken / liegen schon dort (Prüfung per Fingerabdruck) /
   nur Katalog; vorher ZIP ganz prüfen (Prüfsummen, Fassung, Platz); Arbeitsordner, erst am Ende umbenennen. Braucht: Bestand im
   Betrieb wechseln und sich merken, welcher gilt. Zusammenführen zweier Kataloge: frühestens danach (Kennungen kollidieren, Regeln je
   Art nötig; Aufwand 5). **Offen (alt):** Paket 2 Wiederherstellen aus dem ZIP (ersetzt den Katalog,
   vorher Sicherung; Wurzelordner auf dem neuen Rechner neu zuordnen; Vorschaubilder neu erzeugen, wenn sie nicht dabei waren),
   Paket 3 Erinnerung nach 30 Tagen und Hinweis in Bereinigen. Ursprünglicher Plan: als ein Reiter in den Einstellungen (KONZEPT §3.3a): der vorhandene Reiter „Automatische Sicherung“
   wird Teil davon; Backup als ZIP mit Zeilen je Inhalt (auch `vault/gcode`, `vault/quellen`, `vault/anhaenge`), Inhaltsverzeichnis,
   Wiederherstellen, letzte 2 behalten, Erinnerung nach 30 Tagen. In Bereinigen nur ein Hinweis mit Link dorthin.
3. **Ordner umbenennen und verschieben** — Vorgabe des Anwenders (16.10.2026): so nah wie möglich am gewohnten Verhalten von
   Windows-Explorer und Linux-Dateimanagern, nichts Unerwartetes. Entschieden (16.10.): alle Unterordner im Baum zeigen (ohne Modelle
   grau, versteckte nicht); auf eine andere Platte: ablehnen mit Hinweis; gleichnamiger Ordner am Ziel: ablehnen (Zusammenführen nach
   1.0); Löschen bleibt „aus dem Katalog entfernen“; Bibliotheksordner selbst nicht umbenennen/verschieben; ein Ordner zur Zeit.
   **Paket 1 Umbenennen (0.98.0):** Server `Katalog.ordner_bewegen(id, eltern, name)` für Umbenennen und Verschieben (Verschieben dort
   schon fertig, Oberfläche folgt in Paket 2): Windows-Regeln überall (`dateien.ordnername_pruefen`, auch für „Ordner anlegen“), auf der
   Platte ein Schritt nie ersetzend (`dateien.ordner_umbenennen`: unter Linux Ziel per mkdir reserviert, sonst ersetzte rename einen
   leeren Ordner still; nur andere Schreibung über Zwischennamen), in derselben Transaktion Orte, `zuletzt_ort` und gemerkte Suchen
   nachgezogen; scheitert das, geht der Ordner zurück; vorher Sicherung (wenn Modelle darin); nicht während des Einlesens, die
   Hintergrundarbeit hält kurz an. Route `POST /api/ordner/bewegen`. Oberfläche: Rechtsklick › Umbenennen (F2), Feld im Baum,
   Enter/Klick daneben übernimmt, Esc bricht ab, Ablehnung → Meldung und Feld bleibt offen; „Rückgängig“ in der Meldung und Strg+Z;
   F2 ohne Ordner im Fokus benennt das gezeigte Modell um. test_ordner 15/15 (Gegenproben fallen), test_ordner_ui 5/5 (drei
   Gegenproben fallen), test_schutz 28/28 (zwei Einträge in ERLAUBT), test_verwalten 76/76, test_api 86/86.
   Nicht geprüft: andere Platte (hier nur ein Dateisystem), Windows (offene Datei → PermissionError → Meldung; andere Schreibung).
   **Paket 2 Verschieben (0.98.1):** Ordner im Baum ziehbar (nicht die Bibliotheksordner); Ablage nur auf einen anderen Ordner, nicht in
   sich selbst, nicht in eigene Unterordner, nicht dorthin, wo er schon liegt; nach 0,8 s Verweilen klappt ein zugeklappter Ordner auf
   (wie im Explorer). Rechtsklick › „Verschieben nach …“ (Auswahl ohne den Ordner und seine Unterordner, mit „Neuer Unterordner darin“).
   Meldung „„X“ verschoben nach „Y““ mit Rückgängig, Strg+Z. test_ordner_ui 9/9 (+4, zwei Gegenproben fallen).
   **Paket 3 Neuer Ordner, alle Ordner im Baum (0.98.2):** `Katalog.ordner_platte_lesen` liest alle Unterordner (ohne .versteckte,
   $System und den Bestand, wie das Einlesen) — nach jedem Einlesen und nach eigenen Ordner-Aktionen, nicht je Abfrage (unter Windows
   kostet jedes Verzeichnis); `ordnerbaum` fügt sie mit Anzahl 0 ein, die Oberfläche zeigt sie grau ohne Zahl. Rechtsklick › „Neuer
   Ordner“ (`Katalog.ordner_neu`: „Neuer Ordner“, „Neuer Ordner (2)“ …, per mkdir nie einen vorhandenen) mit offenem Namensfeld; kein
   Rückgängig dafür (partAtlas löscht nichts, auch keinen eben angelegten Ordner). „Ordner anlegen“ prüft jetzt dieselben Windows-Regeln.
   test_ordner 18/18 (+3), test_ordner_ui 11/11 (+2), je eine Gegenprobe fällt (Baum ohne Platte, ohne Nummer, ohne Grau, ohne Lesen
   nach dem Einlesen). test_scan 110, api 86, verwalten 76, schutz 28, suche 28, bereinigen_ui 2 grün.
   **test_ansicht_ui flatterte** (2/3, auch vor dieser Änderung): `/api/neuigkeiten` (seit 0.95.6 beim Start) kam mal nach dem
   Ansichtswechsel und zählte mit — in der Prüfung jetzt ausgenommen, dreimal 3/3. **Ordner damit fertig für 1.0.**
   **Umbenennen überall an Ort und Stelle (0.98.3, Anwender: „das kleine Fenster ist nicht konsistent“):** Modelle über ein Feld genau
   auf dem Namen (Kachel, Liste, Karten, Inspektor; `umbenennen(id, el)` in app.js — das Feld liegt fixed über der Seite und folgt dem
   Namen beim Rollen, weil das virtuelle Raster Kacheln neu zeichnet), Name ohne Endung markiert. Langsamer zweiter Klick wie im Explorer
   (Ordner und Modelle: Klick auf den Namen eines schon gewählten Eintrags → nach 0,5 s das Feld; Doppelklick, Ziehen, Taste brechen ab).
   Rückgängig/Strg+Z jetzt allgemein (`rueckgaengig`), auch für Modelle. Server: Dateinamen nach denselben Windows-Regeln
   (`ordnername_pruefen(name, "Dateiname")`), nur andere Schreibung einer Datei per os.rename (samefile). test_ordner_ui 18/18 (+7, vier
   Gegenproben fallen), test_schutz 28/28 (+1 ERLAUBT), test_verwalten 76/76, test_api 86/86, test_ordner 18/18.
   Nicht umgestellt (keine Dateien, daher kein Explorer-Vorbild): Umbenennen von Sammlungen, gemerkten Suchen, Tags, Baugruppen — dort
   weiter ein kleines Fenster. (vor Iteration 1 zugesagt; heute gibt es nur „Ordner anlegen“ und „aus dem Katalog entfernen“).
   Auf der Platte samt allen Modellorten, Sicherung vorher, nie überschreiben. Aufwand 3.
4. **Qualitätsdurchgang:** alle Suiten, test_ui komplett, flatterhafte Prüfungen festmachen (test_ui „Ruhepause 60 ms“, test_ansicht_ui),
   README für Fremde (Installation). Echte Dateien aus Bambu Studio und Anycubic Slicer Next vom Anwender, sonst steht im Vertrag
   „mit echten Dateien nicht geprüft“.
5. **Handbuch — Paket H1 Gerüst (0.98.5):** `partatlas/web/handbuch/index.html` (vorher `handbuch.html` im Repo), `/handbuch` leitet
   dorthin; Knopf „?“ in der Leiste links und F1 (in Bereinigen und Baugruppen beim passenden Kapitel); Fassung im Handbuch aus
   `/api/stand`. Bilder: `werkzeuge/handbuch_bilder.py` (Demo-Sammlung, Drucke, Tags, Sammlung, gemerkte Suche, Baugruppe; je Motiv
   hell und dunkel als WebP, roter Rahmen um die gemeinte Stelle); im Handbuch `<figure class="bild">` mit `.hell`/`.dunkel`, folgt dem
   Hell/Dunkel des Handbuchs. test_handbuch 4/4 (Bilder da und gepaart, Kapitel-Verweise, „?“, F1), vier Gegenproben fallen.
   **Paket H2 Inhalt (0.98.6):** Handbuch neu geschrieben, an Oberfläche und Code geprüft (Kapitel neu: Ordner, Tastatur; überarbeitet:
   alle übrigen — Einlesen mit Fenster für fehlende Dateien, Auswahl wie im Explorer, gemerkte Suchen, Tags verwalten, Reiter des
   Inspektors mit Varianten/Slicer, Notizen und Anhänge, Drucke mit G-Code und Vergleich, Baugruppen mit Notizen/Export, Einstellungen
   je Reiter, Bestand unter Windows/Linux, Sicherungen 5/30, Stand 1.0). 13 Motive aus `handbuch_bilder.py` (26 WebP, ≈ 1 MB); jedes
   Bild mit Breite/Höhe (sonst verrutschte der Sprung zu einem Kapitel um 4 300 px, test_handbuch prüft es jetzt, Gegenprobe fällt);
   das Skript trägt die Grössen selbst nach. Roadmap (⚑) auf denselben Stand. **Pflege:** neue Funktion → Kapitel im Handbuch, ggf.
   Motiv in `handbuch_bilder.py`; vor jeder Fassung `python werkzeuge/handbuch_bilder.py`.
   Ursprünglicher Plan: **Handbuch (HTML; PDF später)** — zuletzt, wenn die Oberfläche steht. `handbuch.html` ist seit 0.53 nicht nachgezogen (fehlen u. a.
   Tags verwalten, Varianten, gemerkte Suchen, Archiv bis 0.96, Backup) und **in der App nicht erreichbar**. Geplant: Kapitel für Kapitel
   an der laufenden App prüfen; Eintrag „Handbuch“ in der App (Server liefert es aus, neuer Tab, ohne Internet), mit Prüfung;
   **Screenshots per Skript** (`werkzeuge/`, Demo-Sammlung, Chromium/Playwright, hell und dunkel, roter Rahmen um die gemeinte Stelle,
   eigene Dateien neben dem HTML) — vor jeder Fassung neu erzeugbar. `partAtlas.pdf` ist kein Handbuch, sondern die alte URS v1.5.0.
6. Fassung 1.0: Eintrag „Neu in dieser Fassung“, Rückweg-Zweig auf die letzte 0.x, `main` für den Tester.

## Stand: 0.95.7 auf `main` (12.10.2026, für den Tester)

**0.95.7 (Tester, 14.10.2026):** Selbst angelegte Kaufteile lassen sich löschen (Auswahl „Kaufteile hinzufügen“, Knopf „löschen“): nur wenn in keiner
Baugruppe verwendet (Meldung „Steckt noch in: …“), nie die Normteile, ohne Papierkorb-Eintrag in der Oberfläche (weich gelöscht, in den Sicherungen).
Umbenennen eines Kaufteils gibt es weiterhin nicht.

**0.95.6:** „Neu in dieser Fassung“ — kleines Fenster beim ersten Start nach einem Update (Wunsch Tester/Anwender, 14.10.2026); gemerkt im Bestand
(`einstellungen.json`, `neuigkeiten_gesehen`), nicht im Browser. Ein ganz neuer Bestand sieht nichts, einer von vor dem Fenster alles ab 0.95.1;
Klick auf die Fassung oben links zeigt die letzten fünf Einträge. **Pflege: zu jeder neuen Fassung ein Eintrag in `partatlas/neuigkeiten.py`**
(`test_neuigkeiten` fällt sonst).

**0.95.5:** SVG, XHTML und HTML als Anhang öffnen im neuen Tab (Anwender, 14.10.2026), nicht mehr als Download. Sicher durch
`Content-Security-Policy: sandbox` — in echtem Chromium geprüft: ein Skript in der Datei läuft nicht (`test_anhang_ui`, fällt ohne den Kopf).
Offen bleibt, dass bei XHTML/HTML Bilder und Stile fehlen, die neben der Datei lagen (nur die eine Datei liegt im Bestand); ⤓ und ↗ bleiben.

**0.95.4 (Tester, 13.10.2026):** Der Name eines Anhangs, den der Browser nicht selbst zeigt (SVG, DXF, XHTML …), lud ihn in den Downloadordner — zehn
Klicks, zehn Dateien. Jetzt startet er ihn im Programm des Rechners (Windows: bei unbekannter Endung fragt das System „Öffnen mit“); ⤓ bleibt für den
ausdrücklichen Download. Die Kopie in `arbeit/geoeffnet/` wird bei unverändertem Inhalt wiederverwendet (`test_anhang_ui`, `test_anhaenge`).
Bekannt flatterhaft: test_ui „Die erste Änderung nach einer Ruhepause lädt sofort“ wartet nur 60 ms und fiel einmal unter Last (allein 4/4).

**0.95.3:** Klicks in Bereinigen waren langsam (Anwender, ~8 600 Modelle, Windows). Jeder Wechsel der Ansicht holte Zähler, Ordnerbaum, Tags,
Sammlungen, Warteschlange **und** die Baugruppen-Vorschläge (rechnen über alle Modelle) neu. Jetzt holt er nur die Liste; die Seitenleiste wird aus
den letzten Daten gezeichnet (`ansichtLaden`, `test_ansicht_ui`). Gemessen mit 8 000 Modellen unter Linux: ~250–650 ms → ~15–40 ms je Wechsel;
unter Windows nicht gemessen. Der Server rechnet bei 8 000 Modellen schnell (alle Ansichten ≤ 25 ms, Zähler ≤ 290 ms) — die Last lag im Neuladen.

**0.95.2:** Der Ordnerdialog geht unter Windows trotzdem hinter dem Browser auf (`dateidialog.py` ist seit 0.55 unverändert; „nach vorn“ aus 0.95.1
reichte dort nicht). Darum: nach 3 s ohne Antwort ein Hinweis mit „Stattdessen hier wählen“ — schliesst den Dialog des Rechners und öffnet den
eigenen Ordnerbaum (`test_dialog_ui`). Auf Linux gemessen; die Windows-Foreground-Sperre selbst ist nicht behoben, nur umgangen.

**0.95.1 (Windows, Protokoll des Anwenders):** „+“ tat nichts, Strg+C kam nicht zum Prompt zurück. Ursache: Der Ordnerdialog (PowerShell) ging
hinter dem Browser auf; jeder weitere Klick hängte einen weiteren unsichtbaren Dialog an, und Python wartete beim Beenden auf diese Threads.
Jetzt: Dialog mit unsichtbarem Eigentümer ganz oben (kommt nach vorn), nur ein Dialog zugleich (sonst Meldung), offener Dialog wird beim
Beenden geschlossen, Strg+C ohne „Unbehandelter Fehler“. Auf Linux nachgestellt und getestet (`test_dateidialog`); die Wirkung von
„nach vorn“ unter Windows ist **nicht** nachgemessen — der Anwender bestätigt.

Alles aus Iteration 1 und 2 und Bereinigen Pakete 1–2 (0.56–0.67). Rückweg: Zweig `fassung-0.55.0` (README, „Zurück auf eine frühere Fassung“).
Vor dem Push: alle Suiten ausser test_ui grün (zuletzt je Paket), `test_ui.py` komplett 70/70 — eine Prüfung schliesst jetzt das neue
Fenster „Dateien fehlen“ und prüft dabei, dass es kommt (+1).

## Katalog fertig — drei Iterationen (Auftrag 12.10.2026, Branch `claude/partatlas-katalog-fertig-amxqfg`)

Auftrag des Anwenders: den Katalog fertig machen, Qualität und Bedienung einer fertigen Anwendung, Grenze „vor Anbindung Drucker“.
Drei Iterationen, vor jeder höchstens fünf Fragen, währenddessen eine. Antworten vor Iteration 1: **partAtlas löscht weiterhin nie**
(Ordner anlegen/umbenennen/verschieben ja); **Drucke Stufe b gehört dazu** (ohne Drucker); **gleiches Teil in mehreren Formaten bleibt je
eine Kachel**, die anderen Formate erscheinen als Reiter „Varianten“ im Inspektor; **nur Branch, `main` erst am Schluss** (test_ui komplett
nur dann).

Plan: (1) Tags verwalten, Papierkorb für Sammlungen/Baugruppen/Drucke/Tags, Auswahl wie im Explorer, Vorschaubild-Vorrang und einzeln
neu erzeugen, Sicherungen mit Zurückholen in der Oberfläche. (2) Druckeinstellungen aus 3MF, Dokumente/Anhänge, Baugruppen-Notizen,
gemerkte Suchen, Drucke Stufe b, Varianten. (3) Backup als ZIP, Ordner-Operationen, Qualitätsdurchgang, Handbuch, alle Suiten, 1.0.

**Iteration 1**
- **Tags verwalten (0.56.0):** Fenster „Tags verwalten“ (⋯ am Abschnitt Tags, „Alle n Tags …“ unter den 30 häufigsten, Rechtsklick auf
  einen Tag, Einstellungen › Einlesen): alle Tags mit Anzahl und „davon automatisch“, Suche, Sortierung; umbenennen, zusammenführen,
  löschen (Papierkorb, Kanten bleiben → zurückholbar), „Alle automatischen entfernen“ (eigene bleiben, Sicherung vorher, wahlweise
  Auto-Tags ausschalten). Die Kante `HAS_TAG` trägt jetzt `auto` (true/false); ältere ohne das Feld gelten als automatisch, wenn die
  Regeln (`tags.vorschlaege`) sie heute vorschlagen würden. Gelöschte und zusammengeführte Namen stehen in `auto_tags_gesperrt`
  (Einstellungen, im Fenster aufhebbar) und kommen beim Einlesen nicht wieder; an einem Modell entfernte stehen in `tags_ab` am Modell.
  Ein von Hand neu gesetzter Tag, der im Papierkorb liegt, kommt ohne seine alten Zuordnungen zurück. Neue Suite `test_tags.py` 15/15,
  drei Gegenproben fallen (Sperre, alte Kanten, eigene als automatisch).
- **Papierkorb für alles (0.57.0):** Bereinigen › Papierkorb zeigt über den Modellen je Art eine aufklappbare Gruppe — Sammlungen,
  Baugruppen, Drucke, Tags, eigene Kaufteile — mit Angabe (Modelle, Positionen, Datum/Ergebnis), Löschdatum, „Wiederherstellen“ und
  „Alle wiederherstellen“. Server `papierkorb.py` (`/api/papierkorb/weitere`, `/wiederherstellen`). Ein gelöschter Druck behält jetzt
  seine Fotos im Vault (bis 0.55 gingen sie nach `vault_archive/`; beim Zurückholen alter Drucke kommen sie von dort zurück, Wächter
  `ERLAUBT` ergänzt). Ein zurückgeholter Tag wird wieder vorgeschlagen. Neue Suite `test_papierkorb.py` 11/11; Gegenproben (Fotos
  archiviert, kein Nachziehen der Zähler, leere Drucke gezeigt) fallen; zwei Filter ohne fallende Gegenprobe entfernt.
- **Auswahl wie im Explorer (0.58.0):** Klick wählt eines und hebt die Mehrfachauswahl auf; Strg+Klick nimmt dazu/heraus (das gerade
  gezeigte Modell kommt mit, wie die vorher einzeln gewählte Datei im Explorer); Umschalt+Klick ersetzt die Auswahl durch den Bereich
  vom Ausgangspunkt (Strg+Umschalt: dazu); Kästchen wie bisher. Strg+A alles in der Ansicht; Pfeiltasten bewegen (Raster: vier
  Richtungen über Gruppenbänder hinweg, Liste/Karten: auf/ab), Umschalt+Pfeil erweitert, Pos1/Ende, Leertaste schaltet das gezeigte um,
  Enter öffnet im Standardprogramm. Rahmen aufziehen auf freier Fläche (Lücken, Rand, unter der letzten Zeile), gerechnet aus den
  Zeilenlagen des virtuellen Rasters (`raster.imRechteck`), rollt am Rand mit; Strg/Umschalt nimmt dazu; Klick auf freie Fläche hebt
  auf. test_ui +1 (gezielt mit `ui_gezielt.py` im Scratchpad: Abschnitt aus `oberflaeche()` mit gleichem Aufbau), drei Gegenproben
  fallen; der folgende Mehrfachauswahl-Block gezielt 3/3. **test_ui komplett steht aus** (vor `main`).
- **Vorschaubilder (0.59.0, Capacities „Präferenz für vorhandene Bilder“ und „Handling einzeln“):** das Bild aus der Datei steht immer vorn
  (vorher bei STEP/FCStd das berechnete). Berechnet wird nur ohne Bild in der Datei; FreeCAD rechnet für ein FCStd mit Thumbnail nur Netz
  und Maße (`Katalog.cad_bild_noetig`, `_cad_bild(bild=False)` → „uebersprungen“). Einstellungen › Einlesen › Vorschaubilder: „nur ohne
  Bild“ (Vorgabe) / „immer“ (`vorschau_berechnen`; dann rechnet der Worker auch für 3MF mit Bild, und das berechnete steht vorn).
  Einzeln: Rechtsklick auf Kachel oder Bild › „Vorschaubild berechnen“ (`POST /api/modelle/{id}/vorschau/berechnen`; Netzformate und
  CAD mit Netz gleich, CAD ohne Netz über FreeCAD, FCStd nur mit Zusage) — das neue wird Vorschaubild (`vorschau_wunsch` an der Datei).
  3D-Ansicht: Kamera-Knopf speichert die gedrehte Ansicht quadratisch als eigenes Bild und setzt es als Vorschaubild (WebGL und ohne
  GPU). Dabei gefunden: `get_node(readonly=True)` ist der lebende Knoten — nach `update_node` war der Wunsch schon gelöscht.
  Neue Suite `test_vorschau.py` 8/8, vier Gegenproben fallen; test_scan: eine Prüfung beschrieb das alte Verhalten (berechnet vor
  Thumbnail), auf das neue umgestellt. Der Kamera-Knopf nur im Browser geprüft (WebGL über SwiftShader), kein test_ui.
- **Backup & Wiederherstellung, Teil „Automatische Sicherung“ (0.60.0, KONZEPT §3.3a Paket 1):** eigener Reiter in den Einstellungen
  (ersetzt den Absatz unter Einlesen samt Kommandozeilen-Hinweis): Erklärsatz, Tabelle Zeit · Anlass in Worten · Grösse · „Zurückholen …“,
  „Behalten: die letzten 5 und je Tag die neueste für 30 Tage“ (einstellbar, `sicherung_neueste`/`sicherung_tage`; vorher 20 und je Tag
  die erste für 60), „Jetzt sichern“, „Ordner zeigen“. Zurückholen im laufenden Betrieb (`POST /api/sicherungen/{name}/zurueckholen`):
  Einlesen anhalten, jetzigen Stand sichern, Datenbank schliessen, tauschen (`sicherung.tauschen`, auch von der Kommandozeile), neu
  öffnen; währenddessen 503 wie beim Start; die Seite lädt danach neu. Gemessen hier: 0,14 s bei 300 Modellen. Anlass in Worten
  (`info.json` je Sicherung, mit Grösse — die Liste zählt keine Dateien mehr: das war der Punkt „Sicherungen öffnet in 5–7 s“ der
  Performance-Liste). Dabei gefunden: mit kleiner Aufbewahrung räumte die Sicherung „vor dem Zurückholen“ genau die zurückzuholende weg —
  jetzt räumt sie erst danach auf. Eine Attrappe in test_scan an die neue Signatur angepasst. test_schutz 28/28 (+4; Aufbewahrung je Tag, Einstellung, Anlass, Zurückholen in der Oberfläche),
  drei Gegenproben fallen. Nicht gebaut: harte Verweise statt Kopien (§3.3a, Vorschlag, vorher prüfen).

**Iteration 1 abgeschlossen (12.10.2026, 0.56–0.60):** alle Suiten ausser test_ui grün — api 86, aufraeumen 13, baugruppen 48, cad 14,
drucke 28, eigene 17, formate 25, papierkorb 11 (neu), sammlungen 18, scan 110, schutz 28, suche 28, tags 15 (neu), verwalten 76,
vorschau 8 (neu), zuordnen 12. test_ui nur gezielt (Auswahl 1 neu, Mehrfachauswahl 3/3); komplett vor `main` am Schluss.

**Iteration 2** — Antworten vorher: Anhänge als **Kopie im Bestand**; Slicer **Bambu Studio** und **Anycubic Slicer Next** (Orca-Abkömmling);
Varianten **gleicher Name, gleicher Ordner**; gemerkte Suchen als **intelligente Sammlungen**.
- **Varianten (0.61.0):** Reiter „Varianten“ im Inspektor (mit Zahl): dasselbe Teil in anderen Formaten — automatisch gleicher Name (ohne
  Endung, Gross-/Kleinschreibung egal) im gleichen Ordner; dazu von Hand: mehrere wählen › Rechtsklick › „Als Varianten verknüpfen“ (Kante
  `SAME_PART`, ungerichtet, höchstens 12). × löst (auch automatische: `varianten_ab` an beiden Modellen). Klick wechselt zum anderen Format.
  Nebenbei: der Reiter „Verwendet“ war nie als gewählt markiert (Regel im CSS fehlte); Reiterleiste mit Abstand statt gleich breiter Felder.
  Neue Suite `test_varianten.py` 5/5, drei Gegenproben fallen.
- **Reiter „Slicer“ (0.62.0, Capacities „Mehr Daten aus den 3MF-Files“):** bei 3MF-Dateien ein Reiter mit den Einstellungen des Projekts:
  Slicer und Fassung, das Wichtigste gruppiert in Worten mit Einheit (Drucker, Düse, Bett, Profil, Filament; Schichthöhe, Wände, oben/unten;
  Füllung; Stützen, Brim; Temperaturen — Bett zur gewählten Platte; Geschwindigkeit, Lüfter), abweichende Einstellungen je Objekt, darunter
  „Alle Werte“ zum Durchsuchen. Neues Modul `slicer.py`: Bambu/Orca/Anycubic (`Metadata/project_settings.config`, JSON) und PrusaSlicer
  (`Slic3r_PE.config`); G-Code (CONFIG_BLOCK bzw. prusaslicer_config, Kopf mit Gewicht und Zeit; nur Anfang und Ende gelesen),
  `profil_hash` ohne Namen/Herkunft/Fassung (Liste geschätzt), `unterschiede` — beides für Drucke Stufe b. **Gelesen erst beim Öffnen des
  Reiters**, nicht beim Einlesen: einige hundert Werte je Datei gehören nicht in den Graphen. Neue Suite `test_slicer.py` 13/13 (nachgebaute
  Dateien, keine echten von Bambu/Anycubic — mit einer echten Datei des Anwenders prüfen), drei Gegenproben fallen.
- **Drucke Stufe b (0.63.0, KONZEPT §4.6):** siehe dort. Server `Drucke.datei_anhaengen/datei_von/datei_loesen/einstellungen/vergleich`,
  Routen `/api/drucke/{id}/datei` (POST mit `?name=`, GET, DELETE), `/einstellungen`, `/oeffnen`, `/api/drucke/vergleich?a=&b=`.
  Oberfläche: „＋ G-Code / Projekt“ am Druck oder Datei auf den Druck ziehen (ohne Druck: neuer Druck), Dateizeile mit Einstellungen,
  Vergleichen, Im Slicer, ⤓, Lösen. test_drucke 39/39 (+11), drei Gegenproben fallen; Wächter in test_schutz um zwei Einträge
  ergänzt (Ablegen im Vault nur, wenn dort noch nichts liegt). **Für das Backup (Iteration 3):** `vault/gcode/` und `vault/quellen/`
  sind Daten des Anwenders → eigene Zeile, Vorgabe an. Nicht mit echten Dateien von Bambu Studio/Anycubic geprüft.
- **Anhänge und Notizen (0.64.0):** `anhaenge.py` (Liste `anhaenge` am Modell bzw. an der Baugruppe, Datei unverändert in
  `vault/anhaenge/<Titel>__<Hash>`, derselbe Inhalt nur einmal; entfernen → `vault_archive/`, auch beim endgültigen Entfernen eines
  Modells; „Öffnen“ = Kopie in `arbeit/geoeffnet/` mit dem Programm des Rechners). Ansehen im Browser nur PDF/Bilder/Text, mit
  `Content-Security-Policy: sandbox`; SVG/HTML u. a. nur als Download (könnten Skript enthalten). Notiz am Modell (Übersicht, ≤ 20 000
  Zeichen), Notizen an der Baugruppe (Markdown, Schreiben/Vorschau, ≤ 50 000, lange Texte über `vault_text`); beides gespeichert beim
  Tippen (1 s) und beim Verlassen; Live-Nachladen zeichnet ein Notizfeld unter den Fingern nicht neu. Suche: Feld `notiz` (Notiz und
  Namen der Anhänge), `notiz:` als Filter. Neue Suite `test_anhaenge.py` 13/13, drei Gegenproben fallen; Wächter ergänzt.
  **Für das Backup (Iteration 3):** `vault/anhaenge/` → eigene Zeile, Vorgabe an.
- **Gemerkte Suchen (0.65.0):** intelligente Sammlungen = `COLLECTION` mit `regel` {q, tags, material, format, ordner} (genau die Filter
  der Ansicht; ein Ordner allein ist keine Suche). „☆ Suche merken …“ in der Filterzeile, sobald Suchtext, Chips oder Format gelten;
  danach „gemerkt als ⌕ Name“. In der Seitenleiste vor den gewöhnlichen Sammlungen, mit der Zahl der Treffer jetzt; ein Klick setzt die
  Filter (sichtbar und änderbar — kein undurchsichtiger Ordner), Rechtsklick: umbenennen, jetzige Filter übernehmen, löschen (Papierkorb:
  „Gemerkte Suche“). Hineinlegen von Modellen abgewiesen. test_sammlungen 23/23 (+5), zwei Gegenproben fallen.

**Iteration 2 abgeschlossen (12.10.2026, 0.61–0.65):** alle Suiten ausser test_ui grün — anhaenge 13 (neu), api 86, aufraeumen 13,
baugruppen 48, cad 14, drucke 39, eigene 17, formate 25, papierkorb 11, sammlungen 23, scan 110, schutz 28, slicer 13 (neu), suche 28,
tags 15, varianten 5 (neu), verwalten 76, vorschau 8, zuordnen 12. test_ui gezielt (Inspektor und Drucke, 9/9; Werkzeug
`ui_gezielt.py` im Scratchpad nimmt jetzt mehrere Abschnitte). Neue Prüfungen in test_ui für Varianten, Slicer, Anhänge, gemerkte Suchen:
keine — ihr Verhalten prüfen die Server-Suiten; die Oberfläche nur im Bild angesehen.

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
   **Format-Etikett auf den Kacheln (0.52.3, Wunsch des Anwenders):** Einstellungen › Ansicht (neuer Abschnitt) › „Dateiformat auf dem
   Vorschaubild zeigen“ — unten links STL/3MF/STEP … in der Farbe des Formats; wirkt sofort, gemerkt je Browser (`partatlas.formatEtikett`),
   Vorgabe aus. Im Bild geprüft, kein Test.
   **Einstellungen › Ansicht erweitert (0.52.4):** „Unter dem Namen“ — Grösse, Gewicht, Material, Tags je an/aus (Vorgabe Grösse und
   Gewicht), die Kachel wächst je Zeile um 18 px (`kachelHoehe`), sofort, je Browser (`partatlas.kachelZeilen`). „Farbe der Vorschaubilder“
   als Auswahl **vorgesehen, noch nicht angewendet** (Anwender: „nur eine Auswahl vorsehen“): gespeichert als `vorschau_farbe` (Server,
   #RRGGBB geprüft), der Dialog sagt das. **Später:** Worker rechnet Bilder ohne eigene Farbe in der Datei mit dieser Farbe neu (Farben aus
   der Datei gehen vor); 3D-Ansicht im Browser ebenso. Nicht im Bild geprüft (Anwender hat abgebrochen); test_api 86/86, test_verwalten 76/76.
   **Leerzeile unter dem Namen weg, Kachelgrösse (0.52.5/0.52.6):** leere Zeilen (z. B. ohne Gewicht) fallen weg; Ansicht › Kacheln:
   Klein 144 / Mittel 178 (Vorgabe) / Gross 233 px, Bild wächst quadratisch mit (`--karte-b`), je Browser (`partatlas.kachelGroesse`).
   Nur Syntax geprüft (Anwender: nicht übertesten).
   **Seite sofort erreichbar beim Start (0.53.0, Anwender unter Windows: 47 s „Seite nicht erreichbar“):** `python -m partatlas` öffnet
   den Port sofort, der Bestand wird im Thread geöffnet (`erstelle_app(im_hintergrund=True)`, Tests im Prozess weiter vorher). Bis dahin
   zeigt „/“ `web/oeffnen.html` („Bestand wird geöffnet …“, fragt jede Sekunde, lädt dann die Oberfläche; Fehler beim Öffnen steht dort),
   /api/* antwortet 503. Offene Tabs verbinden die Live-Meldungen nach einem 503 selbst neu. Neue Protokollzeile „Datenbank gelesen in
   x s (n Dateien)“. **Ursache offen:** hier öffnen 1 000 Modelle (190 Dateien) in 0,06 s; Verdacht Virenscanner je Datei — das nächste
   Windows-Protokoll entscheidet; Abhilfe dann in flatgraph (weniger, grössere Dateien = Umzug der Speicherform). Geprüft: test_api 86/86,
   Warteseite gezielt (verzögertes Öffnen).
   Erster Windows-Lauf danach: Datenbank 3,5 s (2 265 Dateien), die 47 s kamen nicht wieder (vermutlich kalter Start). **Sicherung beim
   Start mit Abgleich (0.53.1):** statt „höchstens alle 10 Minuten“ nur, wenn sich seit der letzten etwas geändert hat — Fingerabdruck aus
   Pfad, Grösse, Änderungszeit (nur `stat`), Datei `stand` in jeder Sicherung. Spart beim Anwender 6 s je Start ohne Änderung.
   test_schutz 23/23, Gegenprobe (Abgleich ausgeschaltet → fällt).
4. **Backup & Wiederherstellung (KONZEPT §3.3a) später** — grösser als gedacht, nicht direkt nach dem Umbau des Einlesens. Pakete:
   (1) Reiter mit automatischer Sicherung (nur Datenbank), Liste und Zurückholen, 5 / 30 Tage; (2) Backup als ZIP, einstellbar;
   (3) Erinnerung nach 30 Tagen.

## 3D-Ansicht ohne funktionierendes WebGL (9.10.2026, Linux-Tester)

Tester: GeForce 9 (nv96), nouveau, X11 (wegen Anycubic Slicer Next). WebGL 2 zeigt ein Bild und verliert dann den Kontext;
Firefox und Chromium gleich, „Software-Rendering“ in Firefox ändert nichts (betrifft nur das Zusammensetzen der Seite, nicht WebGL).
Zum Ausprobieren ohne Code: `LIBGL_ALWAYS_SOFTWARE=1 firefox` (WebGL über llvmpipe) — Ergebnis offen.

**Paket 1 erledigt (0.54.2):** `webglMoeglich` verlangt WebGL 2 (three.js r170 kann kein WebGL 1 mehr). Bricht WebGL ab
(`webglcontextlost`) oder lässt sich kein Renderer anlegen, baut die Galerie ohne 3D-Ansicht neu auf (Bild statt leerer Fläche,
Hinweis) und versucht es auf dieser Seite nicht wieder. test_ui +1, gezielt geprüft; Gegenproben (Lauscher weg, Merker weg) fallen.

**Paket 2 erledigt (0.55.0):** Software-Viewer `web/viewer_ohne_gpu.js` (Canvas 2D, Dreiecke nach Tiefe sortiert, flach und beidseitig
beleuchtet, Raster, Drehen/Verschieben/Zoomen, langsames Selbstdrehen wie im WebGL-Viewer; gezeichnet nur bei Änderung, Pixelfaktor 1).
Netze über 30 000 Dreiecke werden in der Oberfläche vereinfacht (Ecken auf ein Raster gezogen; 500 000 Dreiecke hier 0,3 s), beim
Drehen die grobe Stufe (6 000), sobald die feine länger als 40 ms brauchte. Weiche `dreiD()` in `app.js`: ohne WebGL 2 oder nach einem
Abbruch dieses Modul, Hinweis einmal. Die test_ui-Prüfung aus Paket 1 prüft jetzt: nach dem Abbruch gezeichnete Ansicht ohne
Grafikkarte, beim nächsten Modell direkt. Gezielt geprüft, im Bild angesehen (Quader, Vase); Gegenprobe (Weiche weg) fällt.
Auf dem alten Rechner des Testers nicht gemessen.

**Offen, Pakete 3–4:** ausgedünntes Netz vom Server (`/netz?duenn=1`, vorhandenes Ausdünnen — spart dem alten Rechner das Laden und
Vereinfachen grosser Netze), Schalter Einstellungen › Ansicht › „3D-Ansicht ohne Grafikkarte“ (für Treiber, die ohne Fehlermeldung
falsch zeichnen), eine Prüfung mit Chromium ohne WebGL.

**Herausnehmen:** `web/viewer_ohne_gpu.js` löschen; in `app.js` `dreiD()` wieder nur `viewer.js`, `dreiDSchliessen` auf ein Modul,
`webglAbgebrochen` → wie 0.54.2 Galerie ohne 3D (`kann3d` wieder mit `v.webglMoeglich()`); die test_ui-Prüfung auf „Bild statt
3D“ zurück (Fassung 0.54.2). Paket 1 bleibt in jedem Fall.

**Desktop-App (Gespräch 9.10.2026, noch kein Ticket):** Ziel ein echtes Programm mit Updates wie VS Code. Richtung Tauri
(Browser-App-Modus und Electron vom Anwender verworfen). Erstes Risiko: WebGL unter WebKitGTK auf Manjaro — vorher mit Epiphany
(nutzt WebKitGTK) prüfen. Kein .deb/macOS; Windows-Installer + AppImage; PyInstaller `onedir`; freier Port.

## Nach 1.0, als Erstes: Desktop-Programm mit Tauri (Anwender, 16.10.2026) — vor neuen Funktionen

**Ziel ist ein Programm, das man installiert und per Doppelklick startet, das sich selbst aktualisiert — nicht der Weg mit git pull und
`python -m partatlas` im Terminal.** Der Terminal-Weg bleibt für uns zum Entwickeln und Testen; 1.0 mit Terminal ist ein Entwicklerstand,
die erste Fassung für Fremde ist die erste Desktop-Fassung (das README spricht Fremde dann mit dem Download an, nicht mehr mit `git clone`).
Reihenfolge **vor** Versionsverlauf, Backup/Wiederherstellen und allem Neuen; erst nach der Rückmeldung unter Windows zu 1.0 (start.bat)
und den echten Slicer-Dateien. Richtung entschieden am 9.10.2026 (Tauri; Electron und Browser-App-Modus verworfen), nie ausprobiert.
Aufwand insgesamt 4–5:
1. **Spike** (2): Tauri-Fenster auf das laufende partAtlas (`http://127.0.0.1:<Port>`, System-Webview: Windows WebView2 = Chromium, Linux
   WebKitGTK). Prüfen: WebGL/3D-Ansicht in WebKitGTK (der Tester hat WebGL-Probleme: nouveau, GeForce 9), `window.open` in einen neuen Tab
   (Handbuch/F1, SVG/HTML-Anhänge — ein Tauri-Fenster hat keine Tabs: zweites Fenster oder Systembrowser), Ordnerdialog (kommt heute vom
   Python-Server: zenity/PowerShell), Download ⤓, Strg+V von Bildern, Ziehen von Dateien ins Fenster, Rechtsklickmenüs, F1/F2/Strg+Z.
2. **Eine Datei** (2): partAtlas mit PyInstaller `onedir` bündeln (numpy, Pillow, reportlab, flatgraph; Grösse messen; Windows-Virenwarnungen
   bei PyInstaller bekannt), freier Port, nur eine Instanz (der Bestand lässt nur einen Besitzer zu), sauberes Beenden mit dem Fenster.
3. **Installer** (1–2): Windows-Installer, Linux AppImage; Programm im Startmenü. Kein .deb, kein macOS.
4. **Updates** (2): Tauri-Updater — braucht einen Signaturschlüssel und einen Ort für die Fassungen (Vorschlag: GitHub-Releases);
   unter Windows wahrscheinlich Codesignatur gegen SmartScreen (Kosten). Bis dahin: Windows zuerst (der Anwender testet dort), Linux danach.
**Entschieden (17.10.2026): Linux als AppImage, nicht Flatpak.** Gründe: der Tauri-Bundler baut es mit `tauri build` und der Tauri-Updater kann
AppImage selbst aktualisieren; keine Sandbox (partAtlas startet Slicer/FreeCAD und `xdg-open`, liest beliebige Ordner, zeigt zenity/kdialog,
erkennt AppImages — in einem Flatpak wäre dafür Zugriff aufs Home, `flatpak-spawn --host` und Portale nötig, `programme.py` und
`dateidialog.py` wären anzufassen: Aufwand 3–4 statt 1); der Tester: „AppImage laufen zuverlässiger, Flatpaks sind distributionsabhängig,
wie eine Sandbox und grösser“. Flatpak nur, wenn jemand es verlangt. Bauen später in GitHub Actions (`tauri-action`: Windows-Installer und
AppImage aus einer Workflow-Datei). Bekannte AppImage-Fallen: braucht `libfuse2` auf neueren Ubuntu-Fassungen; Tauri-Darstellungsprobleme
mit EGL/NVIDIA/Wayland (Umgebungsvariablen) — der Tester mit alter Grafikkarte zeigt sie früh.
**Grösse (17.10.2026, gemessen und angegeben):** partAtlas mit Python per PyInstaller `onedir` (Linux, feste Paketfassungen, läuft, meldet
1.0.1): 93 MB entpackt, **38 MB gepackt**; numpy ≈ 41 MB (mit `numpy.libs`), Pillow ≈ 15 MB, Python ≈ 10 MB, Oberfläche samt three.js und
Handbuch 3 MB. Starter: `runpy.run_module("partatlas", run_name="__main__")`, weil `__main__.py` relative Importe nutzt. Angabe des Anwenders
zum 3MF Katalog (mit STEP-Vorschau): Linux 95 MB, Windows 27 MB. Unsere **Schätzung** (nicht gemessen): Windows-Installer ≈ 40–50 MB, Linux-
AppImage ≈ 80–110 MB (Webview gepackt ≈ 40–70 MB). Abspecken (numpy) erst, wenn die Grösse jemanden stört.
**Messung STEP/Open CASCADE (17.10.2026, hier gemessen, Linux, ungeprüft an echten CAD-Dateien):** das Python-Paket `cadquery-ocp` ist riesig
(746 MB entpackt mit allem, was es zum Laden braucht — VTK ≈ 300 MB, Bildbibliotheken, `OCP.so` 152 MB —, gepackt 79–123 MB); die
Open-CASCADE-Module, die STEP lesen, vernetzen und STL schreiben (TKDESTEP, TKMesh, TKDESTL und ihre Abhängigkeiten) sind 66 MB entpackt,
**13–17 MB gepackt**; `occt-import-js` (WebAssembly, LGPL-2.1, in der Oberfläche) 7,3 MB, **3,0 MB gepackt**. Funktion mit einem selbst
geschriebenen Teil (Rundungen, Bohrungen): OCP 844 Dreiecke in 0,02 s, WASM 1 260 Dreiecke in 0,5 s, Maße 60 × 40 × 20 mm, Volumen
passend. **Nicht geprüft:** echte CAD-Exporte, Zusammenbauten mit Farben, grosse Dateien; die STEP-Dateien der Demo-Sammlung sind
Attrappen. Folge: Open CASCADE einbinden ist klein genug (WASM Aufwand ≈ 3, Rust-Hülle ≥ 4); FreeCAD wäre dann nur Fallback (FCStd).
Wenn, dann STEP weiter zuletzt und im Hintergrund, und auf einer alten Maschine prüfen.
**Rückmeldung des Testers (17.10.2026, alte Maschine, Manjaro):** der 3MF Katalog 0.15.4 (AppImage) las 5 793 Dateien (stl, 3mf, stp)
über eine Stunde bei fast 100 % CPU, nach geschätzt 2–3 % abgebrochen; danach beendete er sich von selbst, auch nach Neustart. partAtlas
„funktioniert anders, besser und viel schneller“. Ursache beim 3MF Katalog unbekannt (Vermutung: STEP-Vorschau beim Einlesen). Zu holen: die
Zeit von partAtlas für denselben Ordner (Protokollzeile „Lauf … fertig in … s“) als Messwert. **Nachtrag 17.10.:** der Tester hat denselben
Ordner (5 793 Dateien) mit partAtlas schon eingelesen: es ging, dauerte, „aber nicht so lang“, lief robust, und der Rechner blieb bedienbar
— „deutlich besser gelöst“. Die Dauer in Minuten fehlt weiter. Der 3MF Katalog hat Filamentverwaltung, kann
kein FCStd.
Offen: Wo liegen die Fassungen (Vorschlag GitHub-Releases)? Ein Rechner mit Rust-Werkzeugen und Bildschirm ist nötig (der Cloud-Container
hat keinen Bildschirm, WebView2 gibt es nur unter Windows); ob sich hier ein Linux-Spike bauen lässt, ist ungeprüft.

## Nach 1.0 zuerst: Versionsverlauf je Modell (Anwender, 16.10.2026: „hoch relevant“)

Anlass: ein Kollege des Anwenders („warum ist partAtlas nicht wie git für Druckmodelle?“). Die Lücke heute: wird eine Datei am selben Ort
neu gespeichert, bleibt das Modell (Tags, Drucke, Baugruppen), aber der **vorherige Inhalt ist weg** — ausser er wurde gedruckt (Kopie in
`vault/quellen`). Entwurf, Vorbild Dropbox/Time Machine, nicht git:
- automatisch: ändert sich der Inhalt am selben Ort, kommt der alte Inhalt in den Bestand (nach Fingerabdruck, jeder Inhalt einmal);
- Reiter „Versionen“ im Inspektor: Datum, Grösse, Masse, Vorschaubild, „gedruckt“ wenn ein Druck daran hängt;
- „Diese Fassung wiederherstellen“ als Kopie daneben (`Halter (Fassung 3.10.).stl`), nie über die jetzige Datei;
- später Vergleich: Masse/Volumen nebeneinander, beide Fassungen übereinander in der 3D-Ansicht.
Nicht: echtes git darunter (Binärdateien, fremde Abhängigkeit), Commits/Branches/Texte von Hand. Dagegen: Platz (50-MB-STEP × 10 =
500 MB) → Regeln einstellbar (letzte n Fassungen, Grenze in MB); das Backup des Bestands wird grösser; neue Zeile in backup.ZEILEN.
Aufwand 3–4. Erkennung „geändert am selben Ort“ gibt es schon (scan.py, „Dieselbe Datei neu gespeichert“).

## Später, nach 1.0: Ideen aus anderen Werkzeugen (Anwender, 16.10.2026)

Anlass: Extrudio (G-Code → fotorealistische Bilder, Cloud, bezahlt) und Creallo Atlas (lokaler Betrachter, 13 Formate, Messen, Schnitt,
Kostenschätzung aus Volumen und Oberfläche). Beide nicht anbinden (Cloud bzw. fremder Dienst); übernommen werden nur Ideen.
- **G-Code-Vorschau am Druck:** aus dem G-Code im Vault (Drucke Stufe b) die Bahnen Schicht für Schicht in der 3D-Ansicht zeichnen,
  mit Schieberegler — zeigt, was gedruckt wurde, nicht das CAD-Modell. Lokal, ohne Rendern wie Extrudio. Aufwand 3–4, zu Phase 2.
- **Filamentkosten je Modell:** Gewicht (kennt partAtlas) × Preis je kg des Materials; Preis je Material in den Einstellungen, später
  je Spule (Lager). Aufwand 2, zu Phase 3.
- **Messen und Schnitt in der 3D-Ansicht:** Abstand zweier Punkte, Schnittebene. Aufwand 3.
- **Mehr Formate** (Anwender: „eine gute Sache“). Heute: 3MF, STL, OBJ, STEP/STP, FCStd (`formate.FORMATE`). Kandidaten, Schätzung:
  IGES/IGS über FreeCAD wie STEP (Aufwand 1–2, Nutzen für CAD-Anwender, zuerst); AMF (XML, oft gezippt, Netz direkt) und PLY (Netz,
  binär/ASCII), je Aufwand 2; glTF/GLB (Aufwand 2–3). Proprietäre CAD-Formate (SLDPRT, F3D, IPT) nur als Eintrag ohne Netz und Vorschau —
  fraglich, ob das nützt. Keine fremde CAD-Bibliothek (Open CASCADE direkt): bleibt bei FreeCAD als optionalem Programm.
- **Name:** Creallo „Atlas“ — Verwechslung gering eingeschätzt (anderes Produkt, eigenes Wort). Vor öffentlicher Verteilung von 1.0 eine
  kurze Markensuche nach „partAtlas“ (DPMA, EUIPO); keine Rechtsberatung.

## Später: Performance-Feinschliff (Anwender, 8.10.2026: „irgendwann“, nicht jetzt)

- ~~Einstellungen › Sicherungen öffnet in 5–7 s~~ — erledigt in 0.60 (Grösse in `info.json` beim Anlegen).
- **Kalter Start unter Windows** (einmal 47 s Datenbank lesen, danach 2–3,5 s bei 2 265 Dateien): nur angehen, wenn es wiederkommt;
  dann in flatgraph weniger, grössere Dateien (Umzug der Speicherform).
- **flatgraph: Fachgrösse** (`FACH_GROESSE = 25`, Repo flatgraphdb): unter Linux gemessenes Optimum (25 je Fach; 400 je Fach öffnet
  kalt 0,51 s statt ~1 s, kostet aber 4 ms je geschriebenem Knoten). Unter Windows zählt jede Datei mehr (Virenscanner) — dort nachmessen,
  ob grössere Fächer lohnen; klären, ob ein Wechsel einen Umzug der Speicherform braucht.
- Aus v0.60 (s. o.): Gruppengrösse 200 beim Löschen messen; Ordner entfernen mit vielen Dateien.

## Stand: 0.55.0 auf `main` (9.10.2026, für den Tester)

- 3D-Ansicht: bricht WebGL ab oder fehlt WebGL 2 (Linux-Tester, GeForce 9 mit nouveau), zeichnet partAtlas die Ansicht ohne
  Grafikkarte (Canvas 2D, gröber), mit einmaligem Hinweis; kein neuer WebGL-Versuch bis zum Neuladen (0.54.2, 0.55.0).
- Alle Suiten vor dem Push: 13 ohne test_ui bestanden, `test_ui.py` 68/68. Die neue Prüfung brauchte zwei Korrekturen im Test
  (Reiter „Übersicht“ wählen; Arm.stl ist dort schon entfernt, deshalb die Vase zweimal) — die App war nicht betroffen.
- Vom Tester erbeten: 3D-Ansicht auf seinem Rechner ansehen (flüssig genug?), danach Entscheid über Pakete 3–4.

## Stand davor: 0.54.1 auf `main` (8.10.2026, für den Tester)

- Aufklapp-Pfeile (Ordnerbaum, Gruppenköpfe) als gezeichneter Winkel statt der Zeichen ▸/▾,
  die in kleiner Schrift nur wie ein Punkt wirkten. `test_ui.py` 67/67.
- Kachelgröße auch rechts in der Statuszeile: kleiner Knopf, Menü Klein/Mittel/Groß (nur im Raster sichtbar).
  Einstellungen › Ansicht bleibt und ändert dasselbe. Nur im Browser von Hand geprüft, `test_ui.py` nicht gelaufen.
- Listenkopf: eigene Fläche, kräftigerer Unterstrich, sichtbare Trennlinien zwischen den Spalten (beim Überfahren
  Akzent-Griff zum Breitenziehen). Nur Sichtprüfung hell/dunkel.

## Stand davor: 0.53.1 auf `main` (8.10.2026, für den Tester)

Gruppenbänder, Format-Etikett, Kachelzeilen und -grösse (0.52.2–0.52.6), Seite sofort erreichbar beim Start (0.53.0), Sicherung beim
Start nur bei Änderungen (0.53.1). Auf Wunsch des Anwenders ohne vollen test_ui-Lauf; geprüft je Paket (test_api 86/86, test_schutz 23/23).

## Stand davor: 0.52.1 auf `main` (8.10.2026, für den Tester)

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
