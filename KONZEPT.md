# partAtlas — Konzept

Stand 30.09.2026. Ersetzt `partAtlas.pdf` (URS v1.5.0, ein Entwurf mit
Schätzungen ohne tiefere Analyse); das PDF bleibt als Ausgangsstand liegen.
Was hier steht, ist entschieden, gemessen oder ausdrücklich als offen
markiert.

---

## 1. Worum es geht

partAtlas ist ein **Demo-Pilot für flatgraph** (`bireggbaum-beep/flatgraphdb`):
ein Katalog für 3D-Druck-Sammlungen mit Druckhistorie, der zeigt, was eine
dateibasierte Graphdatenbank ohne SQLite kann.

Vorbild ist der **3MF Katalog Manager** (Bexxs75, MIT, gelesen in Stand
`b9985cb` vom 29.09.2026). Seine Oberfläche ist dem Anwender bekannt und
beliebt und wird **1:1 als Basis übernommen**; umgebaut wird sie erst, wenn
es soweit ist. Unter der Oberfläche ersetzt partAtlas SQLite durch
flatgraph und geht dort weiter, wo der 3MF Katalog aufhört.

### Was der 3MF Katalog heute kann (Parität für Phase 1)

Tauri 2 (Rust) + React, SQLite, rund 50 000 Zeilen.

- Katalogisiert vorhandene Ordner **an Ort und Stelle**; Ordner in der App
  sind echte Verzeichnisse — Verschieben, Umbenennen, Löschen wirken auf
  der Platte. Gelöschtes geht in einen eigenen Papierkorb (7 Tage).
- 3MF, STL, OBJ, STEP (Open CASCADE); Masse, Volumen, Objektzahl.
- Vorschau: eingebettetes 3MF-Bild, sonst Schnappschuss per three.js
  **in der Oberfläche** (WebGL), als PNG-BLOB in der Datenbank.
- Filament je Platte aus `Metadata/slice_info.config` (Orca/Bambu).
- Automatische Tags, Suche, Sammlungen, Favoriten, Duplikate per
  Inhalts-Hash, Archive entpacken (zip, 7z, rar, tar …).
- Filament- und Resinlager, Drucker mit AMS/MMU/CFS/ACE-Fächern,
  „Reicht das Filament?“, Warteschlange, Druckprotokoll mit Foto.
- „Im Slicer öffnen“: erkennt Bambu Studio, Orca, Prusa, SuperSlicer, Cura.
- Moonraker **nur lesend**: Druckhistorie holen, G-Code-Namen dem Modell
  zuordnen (sicher/unsicher), nach Bestätigung von der Spule abbuchen.

### Was er nicht kann — hier setzt partAtlas an

- Kein G-Code-Archiv, keine Einstellungen je Druck, kein Neudruck.
- Kein Drucken per LAN, keine Telemetrie, keine Flotte.
- Beobachtet (Zitate im PDF): bei 5 700 Dateien „nicht gescheit“,
  „bei 90 % keine Bilder“. **Vermutete** Ursachen aus dem Code, nicht
  gemessen: Schnappschüsse brauchen WebGL auf dem Rechner des Anwenders;
  `ModelGrid.tsx` rendert ohne virtuelles Scrollen.
- Löschen kaskadiert still: `print_log` hängt mit `ON DELETE CASCADE` an
  der Datei — endgültig gelöscht heisst Druckprotokoll weg.
- Tote Spalten (`sync_status`, `cloud_id`) bleiben, weil eine Migration
  zum Entfernen zu riskant war.

---

## 2. Anwender und Betrieb

- **Der Anwender:** technikaffin, aber kein Programmierer — Manjaro als
  Windows-Ersatz, nicht als Terminal. Er optimiert Parameter und will alles
  kontrollieren, über eine Oberfläche statt über Code: wie bei einer
  Firewall-Konfiguration.
- **Ton der Oberfläche: ein gutes Werkzeug.** Freundlich und angenehm zu
  bedienen, den Anwender ernst nehmend — nicht kindisch, nicht
  übertechnisch. Fachbegriffe, wo sie genauer sind (Scan, Hash,
  Slicer-Metadaten), Zahlen genau. Der Start darf einladend sein.
- **Rechner:** Manjaro (bevorzugt) und Windows 10. Linux ist Zielsystem,
  Windows soll laufen. (Raspberry Pi war nie Anwenderwunsch — gestrichen.)
- **Aufbau wie pDMS:** ein Python-Prozess (FastAPI) auf dem Rechner des
  Anwenders, Oberfläche im Browser. Start von Hand oder als
  systemd-Benutzerdienst.
- **Tauri** als optionale Desktop-Hülle um dieselbe Oberfläche: Fenster
  wie ein Programm, Ziehen aus dem Dateimanager. Der Browser bleibt, auch
  für Tablet und Handy im Heimnetz.
- **„Öffnen in …“** startet der Server direkt (`orcaslicer <datei>`,
  `freecad <datei>`), weil Server und Programme auf demselben Rechner
  laufen. Erkannt werden Slicer wie im 3MF Katalog und FreeCAD (PATH,
  Flatpak, AppImage, /opt; unter Windows Programme\FreeCAD*). Je Format
  ein Standard: STEP ins CAD, sonst in den Slicer, in den Einstellungen
  umstellbar; eigene Programme dort eintragen. „Mit dem System öffnen“
  (xdg-open) geht immer. Gestartet wird nur ein bekanntes Programm, nie
  ein Pfad aus der Anfrage.
- **Ein Prozess besitzt den Bestand** (flatgraph: eine offene Instanz je
  Bestand, `BestandBelegt`). Renderer und Einlesen dürfen eigene Prozesse
  sein, liefern aber nur Ergebnisse zu; geschrieben wird im Hauptprozess.
- **Wache wie pDMS:** ohne Passwort nur `127.0.0.1`; mit Passwort im
  Heimnetz; schreibende Anfragen nur von der eigenen Oberfläche
  (`Origin`/`Sec-Fetch-Site`). Ein Druckstart heizt eine Maschine auf
  über 200 °C — er braucht immer eine Bestätigung mit Druckername.
- **Arbeitsspeicher** ist kein Kriterium (siehe §8 für die Zahl).

---

### Gestaltungsregeln

Ein gutes Werkzeug (§2) sieht geordnet aus, ohne dass man erklären muss, warum. Deshalb gibt es wenige feste
Regeln statt einzelner Augenmasse-Entscheidungen. Sie stehen als Variablen in `app.css` (`--s1` … `--s8`).

1. **Ein Maßsystem.** Abstände, Höhen und Breiten kommen aus der Fibonacci-Reihe
   **3 · 5 · 8 · 13 · 21 · 34 · 55 · 89 · 144**. Das Verhältnis benachbarter Glieder nähert sich dem goldenen
   Schnitt (1,618); so wirken Abstufungen stimmig, ohne dass jemand rechnen muss. Innerhalb einer
   Gruppe 3–8, zwischen Gruppen 13, zwischen Abschnitten 21–34. Keine Zwischenwerte „nach Gefühl“.
2. **Gemeinsame Kanten.** Was in einer Zeile steht, teilt Kanten mit dem grössten Element der Zeile: Oberkante
   und Unterkante des Bildes sind Oberkante der ersten und Unterkante der letzten Textzeile (Karten: 89 hoch,
   13 Rand oben und unten = 115). Gleicher Rand links und rechts (13).
3. **Mittellinie.** Aktionen sitzen auf der Mittellinie der Zeile, in einer **eigenen Spalte** am rechten Rand —
   nie über Text, nie „irgendwo rechts unten“. Ein Knopf ist 26 gross (16 Symbol + 5 Luft rundum), zwei
   Knöpfe mit 3 Abstand ergeben 55 — in der Liste nebeneinander, in den Karten übereinander.
4. **Symbole** sind Linie, flach, einfarbig, 16 × 16, 1,4 Strichstärke, runde Enden — wie die Ansichtsleiste.
5. **Eine Rolle je Ansicht.** Das Raster zeigt Bilder, die **Karten** zeigen die Fülle (Name, Maße, Status, Material,
   Tags, Ordner), die **Liste** ist die schlanke Tabelle zum Sortieren (Name, Format, Grösse, Gewicht, Status).
   Was die Karten zeigen, kommt nicht noch einmal in die Liste.

6. **Die Raster-Kachel** ist 144 × 233: zwei benachbarte Glieder der Reihe (144 + 89 = 233, Verhältnis 1 : φ). Oben das
   quadratische Bild (144), darunter ein Textfeld von 89 mit Rand 13 und den Zeilen 21 / 18 / 18. Was auf dem
   Bild liegt (Punkt, Haken, Herz, Plakette), hält 8 Abstand zur Kante. Raster: Rand und Lücke 13.

7. **Der Inspektor** ist 377 breit, die linke Seitenleiste 233 (1 : φ; beide bleiben ziehbar). Eine linke Kante bei 13 für
   alles, Etiketten in einer Spalte von 89, Auswahlfelder gleich breit (144). Senkrecht 21 zwischen Abschnitten, 8 innerhalb,
   13 zwischen den Teilen des Kopfs. Höhen: 34 für Hauptaktion und Reiter, 26 für alles Übrige zum Bedienen, 55 für die
   Bilder der Leiste. Die Vorschau hat 1 : φ zur Breite, bis man sie selbst zieht.

8. **Lesbarkeit.** Jeder Text hat mindestens **4,5 : 1** Kontrast zum Grund (WCAG AA), auch der graue (`--ink-3`: dunkel
   etwa 6 : 1, hell etwa 6 : 1; `--ink-2` etwa 9 : 1 bzw. 8 : 1). Schrift nicht unter **12 px**; im Einstellungsdialog 14,5.
   Auslöser war die Rückmeldung eines Testers: grau und klein war dort kaum zu lesen. Wer eine Farbe ändert, rechnet den
   Kontrast nach, statt nach Gefühl zu gehen.

Ebenfalls im Maßsystem: Rail (55 breit, 5 Abstand, 13 Rand), Kopfzeile, Tag- und Filterleiste.
Noch nicht umgestellt: Seitenleiste links (Felder, Zeilen), Dialoge, Kopfzeilenhöhe (44), Baugruppen-Ansicht.

## 3. Dateien und Bestand

### 3.1 Die Sammlung des Anwenders

- Der Anwender wählt **einen oder mehrere Wurzelordner**. Ihre Struktur
  wird eingelesen und bleibt seine.
- Die Ordneransicht wird **aus den Pfaden abgeleitet**, nicht gespeichert:
  jede Datei trägt Wurzel und relativen Pfad.
- **Die Datei führt, der Container folgt.** Ein Modell ist ein Container,
  die Datei liegt darin; im Alltag verhält sich beides wie eins. Der
  Anwender denkt in Dateien — er legt ab, verschiebt, überschreibt,
  löscht —, und die Datenbank macht mit. Was nur der Container kennt
  (Tags, Material, Sammlungen, Baugruppen, eigene Bilder, Quelle, später die
  Druckhistorie), bearbeitet er bewusst in partAtlas.

  | Mit der Datei | Der Container |
  |---|---|
  | neu in einen Ordner gelegt | neuer Container |
  | verschoben, umbenannt (App oder Dateimanager) | folgt, alles bleibt dran |
  | Kopie mit gleichem Inhalt | ein Container, zwei Orte („Duplikat“) |
  | überschrieben (gleicher Ort, neuer Inhalt) | derselbe Container mit neuem Inhalt — sofern der alte Inhalt nirgends mehr liegt; sonst ist es eine abgezweigte Kopie mit eigenem Container (0.14) |
  | in partAtlas gelöscht | mit in den Papierkorb (Dialog zeigt, was dranhängt) |
  | im Dateimanager gelöscht | bleibt, auf der Kachel deutlich als „Datei fehlt“ |
- **Eine Datei wird an ihrem Inhalt erkannt** (SHA-256 als Kennung).
  Verschoben oder umbenannt außerhalb der App → der nächste Scan findet sie
  wieder, Tags und Historie bleiben dran. Verschwunden → Knoten wird als
  „fehlt“ markiert, nicht gelöscht; die Druckhistorie bleibt.
- **Schreiben im Ordner wie beim 3MF Katalog** (Verschieben, Umbenennen,
  Löschen in den Papierkorb), aber nur über sichere Wege: auf demselben
  Dateisystem `rename`; über Dateisystemgrenzen kopieren, `fsync`, dann
  erst die Quelle entfernen. Nie etwas überschreiben.

### 3.2 Der Bestand von partAtlas

| Bereich | Inhalt | Verlust heisst | Sicherung |
|---|---|---|---|
| `datenbank/` | flatgraph: Modelle, Tags, Drucke, Spulen, Drucker | alles Eigene weg | ja |
| `vault/` | Anhänge: `vorschau/<hash>.extrahiert.png` (Bild aus der Datei) und `vorschau/<hash>.berechnet.png` (von partAtlas gerendert) gehören zur Datei; `bilder/` die Bilder des Anwenders; ab Phase 2 G-Code und die Quelldatei, aus der er entstand | eigene Bilder und G-Code nicht wiederherstellbar; extrahierte sofort, berechnete in rund einer halben Stunde neu (geschätzt) | ja |
| `vault_text/` | lange Texte (ab 1 000 Zeichen, z. B. die Beschreibung einer Baugruppe), erst beim Lesen geladen | Text weg | ja |

- **Was der Vault ist** (flatgraph): der Ort in der Datenbank für Binärdaten
  und Langtexte, die nicht im Arbeitsspeicher liegen, sondern erst bei
  Bedarf gelesen werden. Ein Knoten hält nur den Verweis (Feld `datei`
  bzw. `@vault_text/…`). Nicht gemeint ist ein allgemeiner Ablageordner:
  was im Vault liegt, gehört zu einem Knoten, und beim Löschen sieht man es
  in `loeschfolgen()` (z. B. „1 Bild“).
- **Drei Arten Bilder:** *extrahiert* (steckt in der Datei, z. B. das
  3MF-Vorschaubild), *berechnet* (partAtlas rendert es aus dem Netz) und
  *eigene* (vom Anwender). Die ersten beiden gehören zur Datei
  (`PART_GEOMETRY.vorschau_extrahiert` / `.vorschau_berechnet`), die Art
  steht im Dateinamen — ein neu gerendertes Bild überschreibt nie das aus
  der Datei. Die eigenen hängen am Modell wie ein PDF am Dokument in pDMS:
  eine Liste `bilder` mit Verweisen, kein Knoten je Bild; das erste ist
  das Titelbild.
- **Endgültig löschen:** Vorschauen gehen mit der Datei weg (abgeleitet).
  Eigene Bilder gehen nach `vault_archive/`, auch beim Entfernen eines
  einzelnen Bilds — was der Anwender hineingetan hat, verschwindet nie.
- **Löschen mit informierter Entscheidung:** der Dialog zeigt aus der
  Nachbarschaft im Graphen, was am Modell hängt — Dateien, eigene Bilder,
  Baugruppen (fehlt dort in der Stückliste), Warteschlange, Sammlungen und
  Tags, je mit der Zahl der anderen Modelle daran. Ankreuzen lässt sich nur,
  was eine echte Wahl ist: Tags und Sammlungen, an denen sonst nichts hängt
  („ganz löschen“, Tags mit Warnung). Der Server prüft das noch einmal.
  Gleicher Dialog für mehrere Modelle.
- **Galerie im Inspektor:** eigene Bilder, 3D-Ansicht, Bild aus der Datei,
  Vorschau zum Durchblättern (Pfeile, Kacheln, ←/→, Wischen); eigene Bilder
  per ＋, Hineinziehen oder Strg+V, mehrere auf einmal; „Als Titelbild“.
- **Vault ist unveränderlich und wächst nur.** Jede Datei über
  Arbeitsdatei, `fsync`, `os.replace`; nie überschrieben.
- **Name = Titel + Hash**, z. B. `gcode/Arm_Front__3f9a1c2e.gcode`: ohne
  App lesbar (wie pDMS), eindeutig und prüfbar (wie flatgraph
  `vault_text`).
- **Die Quelldatei kommt in den Vault, sobald es einen G-Code zu ihr
  gibt** — nicht alle 5 000. Wer neu slicen will, braucht sie auch dann,
  wenn der Anwender seinen Ordner aufgeräumt hat.
- **Woher der G-Code kommt:** beim Scan im Ordner gefunden oder in der
  Oberfläche auf die Modellkarte gezogen. Die Zuordnung beim Scan rät
  (Dateiname, Slicer-Kopf, wie `printer_link/matching.rs` im 3MF Katalog)
  und wird vom Anwender bestätigt, bevor der G-Code in den Vault geht.

---

## 4. Druckhistorie, Referenz, Nochmal

Der Kern von partAtlas. Aus eigener Erfahrung: acht Versuche, und keiner
weiss mehr, mit welchen Einstellungen.

### 4.1 Jeder Druck mit seinen Einstellungen

- **Die Einstellungen stehen im G-Code:** OrcaSlicer, PrusaSlicer und
  Bambu Studio schreiben die ganze Konfiguration als Kommentarblock ans
  Ende. partAtlas liest sie aus; der Anwender trägt nichts ein.
  *(Für Bambu Studio ungeprüft.)*
- **Gleiche Einstellungen, gleicher Knoten:** die ausgelesene
  Konfiguration wird normalisiert und gehasht; der Hash ist die Kennung des
  `PRINT_PROFILE`. Alle Drucke mit identischen Einstellungen hängen am
  selben Knoten — „wie oft mit genau diesen Einstellungen, mit welchem
  Ergebnis?“ ist ein Schritt im Graphen.
- **Unterschied zweier Versuche:** Versuch 3 gegen Versuch 8 zeigt nur,
  was sich unterscheidet („Düse 215 → 225 °C, Lüfter 100 → 60 %“).
- **Ergebnis je Druck:** gut / mit Fehlern / abgebrochen, Notiz, Foto.

### 4.2 Sensordaten zum Druck

Jeder Druck zeigt seine Temperatur- und Lüfterkurven neben den
Einstellungen: ob Versuch 5 an den Einstellungen scheiterte oder daran,
dass das Bett nie auf Temperatur kam. Gespeichert in flatTSDB, verknüpft
über Stream-Kennung und Zeitraum am `PRINT_JOB`.

### 4.3 Referenz je Drucker und „Nochmal“

- Der Anwender markiert einen Druck als **Referenz — eine je Modell und
  Drucker**. Voron und Bambu haben verschiedene G-Codes; jeder kann seinen
  besten Druck haben.
- **„Nochmal“** schickt den G-Code der Referenz bitgenau aus dem Vault an
  den Drucker. Kein Slicer.
- **Grenze:** ein G-Code passt nur auf den Drucker, für den er erzeugt
  wurde, mit derselben Düse. Geprüft über `COMPILED_FOR` und den
  Slicer-Kopf, bevor gesendet wird.

### 4.4 STL

- Beim Einlesen: Masse, Volumen, Hash, Vorschau — auf dem Server
  gerendert (Software-Rasterizer), kein WebGL beim Anwender nötig.
- Zum Drucken muss ein STL gesliced werden. **Ausbau:** die Einstellungen
  einer Referenz über die Kommandozeile des Slicers auf ein neues STL
  anwenden → G-Code ohne die Slicer-Oberfläche. PrusaSlicer kann das;
  *OrcaSlicer ungeprüft.*

### 4.5 Baugruppen

Viele Modelle einer Sammlung sind Teile eines Ganzen — eine Drohne, ein
Voron-Mod, eine Werkzeugwand. Der 3MF Katalog kennt dafür nur Sammlungen:
eine Liste. Eine Baugruppe ist eine **Stückliste**:

- **Positionen mit Menge**: Druckteile, Unterbaugruppen, Kaufteile.
  Mengen multiplizieren sich über die Ebenen (4× Arm-Modul mit je 2
  Haltern = 8 Halter). Eine Unterbaugruppe weiss, wie oft sie insgesamt
  gebraucht wird; ihre Zähler gelten über alle Exemplare.
- **Kaufteile aus einem Normteil-Katalog**: Schrauben (DIN 912, 7991,
  ISO 7380 …), Muttern, Scheiben, Gewindeeinsätze, Magnete, Lager,
  Profil, Elektronik — rund 200 Teile, dazu eigene.
- **Summen über alle Ebenen**: Filament je Material mit seinen Farben
  und dem Anteil einer 1-kg-Rolle („TPU 86 g in Rot und Schwarz, ein
  Rest“), Druckzeit, Einkaufsliste der Kaufteile. Ohne Slicer-Daten wird
  das Gewicht geschätzt (1,2 mm Hülle + 15 % Füllung) und so benannt.
- **Standard statt Nachfragen**: ohne Angabe gelten Standardmaterial,
  -farbe und Rollengrösse aus den Einstellungen (⚙, wie in pDMS). Wer
  nur PLA+ druckt, stellt das einmal ein. Angenommenes steht dezent als
  „Standard“ dabei; Material und Farbe je Druckteil per Klick.
- **Ansicht wie eine technische Zeichnung** (seit 2.10.2026): oben ein Schriftfeld mit Name, Beschreibung und fünf
  Feldern (Druckteile, Kaufteile, Filament, Druckzeit, „steckt in“), darunter Reiter **Stückliste · Notizen ·
  Anhänge**. Die Stückliste ist eine nummerierte Tabelle in der Reihenfolge des PDFs; die Zähler „gedruckt / beschafft“
  und der Fortschrittsbalken sind entfallen — was gedruckt wurde, steht an den Drucken des Modells (§4.6). Jedes Druckteil
  lässt sich beim Überfahren im Slicer oder CAD öffnen. **Notizen** (Markdown) und **Anhänge** (Montageanleitung,
  Konstruktionszeichnungen aus CorelDRAW & Co., Datenblätter; Dateien bleiben unverändert im Bestand) sind in der
  Aufteilung vorgesehen, aber noch nicht verdrahtet.
- **Mitte Stückliste, rechts Übersicht**: die Mitte zeigt Kopf,
  Aktionen und Stückliste. Die rechte Seitenleiste, sonst die
  Modellvorschau, trägt die Übersicht: Filament je Material mit
  Farbtupfern, Druckzeit je Teil, Einkaufsliste, Ausgabe (PDF, CSV,
  Markdown). Filament und Druckzeit folgen demselben Schema: ein
  Gesamtbalken aus den Teilen, darunter je Zeile Menge bzw. Dauer. Ein
  Klick auf ein Teil zeigt rechts das Modell, „← Baugruppe“ führt zurück.
- **Stückliste als PDF** (A4, Helvetica, keine Schriftdatei nötig):
  Kopf mit Kennzahlen, Strukturstückliste mit Positionsnummern über die
  Ebenen (1, 1.1 …) und Abhakkästchen, Mengenübersicht der Druckteile
  über alle Ebenen, Einkaufsliste der Kaufteile, Filament je Material
  und Farbe, „Seite x von y“.
- **Weniger tippen**: aus einem Ordner, einer Sammlung oder der Auswahl
  anlegen; Mengen aus Dateinamen (`Arm_x4`, `4x_Arm`); Ordner, die wie
  Baugruppen aussehen, werden vorgeschlagen. Kacheln auf eine Baugruppe
  ziehen fügt sie hinzu.
- „Fehlende in die Warteschlange“, Export als CSV und Markdown,
  „steckt in …“ an jedem Modell und in der Löschvorschau.

### 4.6 Drucke in Phase 1 (Entwurf, ohne Drucker)

*Entwurf vom 01.10.2026. Stufe a ist gebaut (0.19), Stufe b offen.*

**Grundgedanke.** Das Modell ist die Geometrie. Ein **Druck** ist ein
einzelnes Mal, dass sie auf dem Drucker lag — mit allem, was dazu gehört:
Einstellungen, Gewicht, Dauer, Filament, Foto, Ergebnis, Notiz. „Gedruckt“
ist keine Eigenschaft des Modells mehr, sondern folgt aus seinen Drucken;
ein Modell ist **noch nicht gedruckt**, solange es keinen hat, und die
Kachel zeigt, **wie oft** es gedruckt wurde. Wie ein Fotomanager: was die
Kamera nicht liefert, trägt der Anwender selbst ein. Ein Anbindungslayer
ist dafür nicht nötig; er füllt diese Drucke ab Phase 2 nur von selbst.

- **Ein Druck ist ein `PRINT_JOB`** (§6.1) — derselbe Knoten wie in
  Phase 2. Neu ist nur, dass er auch ohne Drucker und ohne G-Code
  entstehen kann. Felder: Datum, Dauer, Gewicht, Filament
  (`[{typ, farbe, g}]`), Ergebnis (`gut` / `mit Fehlern` / `abgebrochen`),
  Notiz, Bilder (wie die des Modells, §3.2), Herkunft (`hand` / `datei`).
- **Ein Druck hängt an einem oder mehreren Modellen** (Kante
  `PRINTED_IN`, §6.2). Der Normalfall ist ein Modell. Mehrere gibt es
  bei einer Platte: drei Bibliotheksmodelle nebeneinander im Slicer,
  ein G-Code, ein Foto, ein Gewicht für alle. Der Zähler jedes der drei
  Modelle steigt um eins. Das Speichern ist so gebaut, dass es mehrere
  tragen kann, **auch wenn die Oberfläche zuerst nur den Einzelfall
  anbietet** — die Speicherform lässt sich später nicht zurückdrehen.
  Die Oberfläche folgt: Kacheln wählen → „Zusammen gedruckt …“.
- **Zähler und Status** werden gezählt, nicht gespeichert: Drucke mit
  Ergebnis `gut` oder `mit Fehlern`; `abgebrochen` zählt nicht. Das alte
  Feld `gedruckt` am Modell entfällt. Wer ohne Daten „gedruckt“ klickt,
  legt einen **leeren Druck** an (Datum, höchstens ein Foto) — der
  Zähler stimmt ohne Sonderfall.
- **Modellwerte (Gewicht, Zeit, Filament, Farbe)** zeigt die Kachel vom
  **Referenzdruck**, sonst aus der Datei, wie heute; die Herkunft steht
  dabei („aus Referenzdruck“ / „aus Datei“). Handwerte am Modell gibt es
  nicht mehr: wer ein Gewicht von Hand kennt, trägt es im Druck ein.
  Ohne Drucker gilt die Referenz **je Modell** (eine); ab Phase 2 je
  Modell und Drucker (§4.3).
- **Plattenwerte gehören der Platte.** Hängt ein Druck an mehreren
  Modellen, wird sein Gewicht nicht auf sie verteilt. Baugruppensummen
  rechnen für diese Modelle weiter mit dem Dateiwert.
- **Baugruppen bleiben, wie sie sind.** Der Zähler „erledigt“ an der
  Position (§4.5) ist der Fortschritt der **Baugruppe** („für dieses
  Projekt vier gebraucht, zwei fertig“) und hängt nicht am Zähler des
  Modells. Ab Phase 2 zählt die Druckhistorie mit.
- **„Im Slicer öffnen“** öffnet immer **ein** Programm. Bei einem Modell
  wie heute. Bei einem Druck mit Datei (G-Code, Slicer-Projekt) öffnet er
  diese **eine** Datei, auch wenn der Druck an drei Modellen hängt. Bei
  mehreren gewählten Modellen gibt es „Zusammen im Slicer öffnen“: ein
  Prozess, alle Dateien als Argumente. *Ungeprüft:* ob PrusaSlicer,
  OrcaSlicer, Bambu Studio und Cura mehrere Dateien auf der
  Kommandozeile in **einem** Fenster aufnehmen, oder ob sie je Datei eine
  Instanz starten (heute übergibt `programme.oeffnen` genau eine Datei).

**Stufe a — Drucke von Hand (gebaut, 0.19).** Druck anlegen (an einem Modell oder an
einer Auswahl), Felder und Fotos von Hand, Referenz markieren, Zähler und
Status auf Kachel und Inspektor. Kein G-Code. Das ist die Demo für den
Piloten. Bestehende Haken „gedruckt“ werden beim Umzug je zu einem
leeren Druck (wie die Umstellung der eigenen Bilder in 0.11).

**Stufe b — Datei zum Druck (offen).** G-Code oder Slicer-Projekt auf einen Druck
ziehen: im Vault abgelegt (`GCODE_ARTIFACT`, Kennung = Hash),
Einstellungen und Filament ausgelesen (§4.1), `PRINT_PROFILE` per Hash,
Vergleich zweier Drucke. Aus einer Datei mit mehreren Objekten wird vorgeschlagen,
an welchen Modellen der Druck hängt; der Anwender bestätigt.

**Ab Phase 2:** Anbindung, Sensordaten (§4.2), „Nochmal“ (§4.3). Sie
legen Drucke selbst an, mit `EXECUTED_ON` und Kurven; an der Form des
Druck-Objekts ändert sich nichts.

**Entschieden (01.10.2026):** Auf der Oberfläche heisst es **„Druck“**.
Ein Druck mit Fehlern zählt in „wie oft gedruckt“ (er hat stattgefunden);
den Haken „gedruckt“ zeigt die Kachel erst bei einem guten. Die Drucke
stehen im Inspektor in einem **eigenen Reiter** — die rechte Seitenleiste
bekommt dafür Reiter (OFFEN.md d), zuerst entworfen, dann gebaut.

---

## 5. Was partAtlas an flatgraph zeigt

Jeder Punkt ist in der Oberfläche sichtbar oder im Bestand nachprüfbar.
Zahlen aus `flatgraphdb/VERTRAG.md` und §8.

1. **Druckhistorie über den Graphen** (§4): Modell → Drucke → G-Code →
   Einstellungen → Sensordaten; gleiche Einstellungen teilen einen Knoten.
2. **Löschen mit Vorschau statt stillem Kaskadieren:** `loeschfolgen()`
   zeigt vorher, was mitgeht („3 Drucke, 2 G-Codes, 1 Foto“); zweistufig
   mit Papierkorb (VERTRAG §2.4). Das Gegenstück zu `ON DELETE CASCADE`.
3. **Rückverfolgung in Mikrosekunden:** „welche Drucke mit Spule #9041, von
   welchen Modellen?“, „was hat der Voron seit Juli gedruckt?“ —
   `traverse`/`collect_related`; Nachbarschaft wächst nicht mit dem Bestand.
4. **Neue Beziehungen ohne Migration:** „ist Remix von“, „Ersatzteil
   für“, „gehört zu Baugruppe“, ungerichtet „passt zu“ (VERTRAG §2.8) —
   je eine Kantenart, keine tote Spalte.
5. **Bestand ohne App lesbar:** JSON-Dateien, per `grep` durchsuchbar;
   Vault mit Titeln im Dateinamen.
6. **Baugruppen** (§4.5): Stückliste als Kanten mit Menge; was die
   ganze Baugruppe braucht, ist ein Gang durch den Graphen, der die
   Mengen multipliziert; „wo steckt dieses Teil“ sind die eingehenden
   Kanten. In SQLite je eine rekursive Abfrage.
7. **Suche wie in pDMS** (0.8.0): Wortindex im Arbeitsspeicher, Kopie
   aus pDMS; nachgeführt über `bei_aenderung` — ein umbenannter Tag,
   eine umbenannte Baugruppe erreicht jedes Modell daran über die
   Nachbarschaft. Zwei Anwender derselben Kopie sind der Beleg für den
   Umzug nach flatgraph (§9).
8. **Live-Oberfläche:** `bei_aenderung` (VERTRAG §2.7) meldet jede
   Änderung — Druckerstatus, Abbuchung, neues Modell — per SSE in den
   Browser.

---

## 6. Datenmodell (flatgraph)

Sammlungs- und Kantennamen folgen der flatgraph-Namensregel (VERTRAG §7).

### 6.1 Sammlungen

| Sammlung | Kennung | Inhalt | 3MF Katalog |
|---|---|---|---|
| `ROOT_FOLDER` | fortlaufend | gewählter Wurzelordner, Pfad | — |
| `MODEL_ASSET` | fortlaufend | logisches Modell: Titel, Favorit, Quelle-URL, Druckstatus | `files` (Teil) |
| `PART_GEOMETRY` | SHA-256 der Datei | Datei: Wurzel, relativer Pfad, Format, Masse, Volumen, Objekte, „fehlt“ | `files` (Teil) |
| `TAG_ITEM` | Name | Tag, Farbe | `tags` |
| `COLLECTION` | fortlaufend | Sammlung mit Reihenfolge | `collections` |
| `GCODE_ARTIFACT` | SHA-256 der Datei | Vault-Pfad, Slicer, Druckzeit, Filament je Material | — |
| `PRINT_PROFILE` | Hash der Einstellungen | normalisierte Slicer-Konfiguration | — |
| `PRINT_JOB` | `next_id`, nie wiederverwendet | Datum, Dauer, Gewicht, Filament, Ergebnis, Notiz, Bilder, Herkunft (`hand`/`datei`); ab Phase 2 TSDB-Stream + Zeitraum (§4.6) | `print_log`, `printer_jobs` |
| `ASSEMBLY` | fortlaufend | Baugruppe: Name, Beschreibung | — |
| `PURCHASED_PART` | sprechend (`din912-m3x10`) | Kaufteil: Name, Kategorie, Norm, Einheit | — |
| `PRINTER_DEVICE` | fortlaufend | Name, Anschluss, Adresse, Bett, Düse | `printers`, `printer_connections` |
| `AMS_SLOT` | fortlaufend | Fach einer Einheit | `material_units` |
| `MATERIAL_SPOOL` | fortlaufend | Spule/Flasche: Rest, Preis, Lagerort, Farbe | `filament_spools` |
| `MATERIAL_MASTER` | Name in Grossbuchstaben (`PETG`, `PLA+`) | Filamenttyp; Grundbestand von zwölf, weitere legt der Anwender an (0.10) | — |

Warteschlange: Feld `queue_position` am Modell wie im 3MF Katalog, bis
die Flotte (Phase 4) eine eigene Sammlung braucht.

### 6.2 Kanten

```
MODEL_ASSET    ─[HAS_PART]──────────▶ PART_GEOMETRY
MODEL_ASSET    ─[HAS_TAG]───────────▶ TAG_ITEM
MODEL_ASSET    ─[INTENDED_MATERIAL]─▶ MATERIAL_MASTER   vom Anwender, auch mehrere (0.10)
PART_GEOMETRY  ─[REQUIRES_MATERIAL]─▶ MATERIAL_MASTER   aus den Slicer-Daten der 3MF (0.10)
MODEL_ASSET    ─[IN_COLLECTION]─────▶ COLLECTION        meta: position
MODEL_ASSET    ─[HAS_GCODE]─────────▶ GCODE_ARTIFACT
GCODE_ARTIFACT ─[SLICED_FROM]───────▶ PART_GEOMETRY     die Quelle im Vault
GCODE_ARTIFACT ─[BASED_ON_PROFILE]──▶ PRINT_PROFILE
GCODE_ARTIFACT ─[REQUIRES_MATERIAL]─▶ MATERIAL_MASTER
GCODE_ARTIFACT ─[COMPILED_FOR]──────▶ PRINTER_DEVICE
PRINT_JOB      ─[EXECUTED_GCODE]────▶ GCODE_ARTIFACT
PRINT_JOB      ─[EXECUTED_ON]───────▶ PRINTER_DEVICE
PRINT_JOB      ─[USED_SPOOL]────────▶ MATERIAL_SPOOL
MODEL_ASSET    ─[PRINTED_IN]────────▶ PRINT_JOB         ein Druck an einem oder mehreren Modellen (§4.6)
MODEL_ASSET    ─[REFERENCE]─────────▶ PRINT_JOB         höchstens eine je Drucker (Phase 1: je Modell)
PRINTER_DEVICE ─[HAS_SLOT]──────────▶ AMS_SLOT
AMS_SLOT       ─[LOADED_WITH]───────▶ MATERIAL_SPOOL
MATERIAL_SPOOL ─[IS_TYPE_OF]────────▶ MATERIAL_MASTER
ASSEMBLY       ─[CONTAINS]──────────▶ MODEL_ASSET | ASSEMBLY | PURCHASED_PART
                                                        meta: menge, erledigt, material, farbe, notiz, position
MODEL_ASSET    ─[REMIX_OF]──────────▶ MODEL_ASSET
MODEL_ASSET    ─[SPARE_PART_FOR]────▶ MODEL_ASSET
MODEL_ASSET    ─[FITS]──────────────  MODEL_ASSET       ungerichtet
```

Bilder sind keine Knoten (§3.2): die Vorschauen sind Felder der Datei,
die eigenen Bilder eine Liste `bilder: [{k, datei, angelegt}]` am Modell.
Sie gehen mit dem Modell in den Papierkorb und kommen mit ihm zurück.

---

## 7. Phasen

1. **Katalog auf flatgraph** — Parität mit dem 3MF Katalog im Katalogteil
   (§1), plus: Vorschau auf dem Server gerendert, virtuelles Raster,
   Wurzelordner, Löschen mit Vorschau, Live-Oberfläche.
2. **G-Code und Druckhistorie** — Vault, Zuordnung mit Bestätigung,
   Einstellungen auslesen, `PRINT_PROFILE` per Hash, Vergleich zweier
   Drucke, Ergebnis/Foto, Referenz je Drucker, „Nochmal“ per Moonraker.
3. **Lager und Telemetrie** — Spulen, Fächer, „Reicht das Filament?“,
   Abbuchen, Sensordaten in flatTSDB und die Kurven am Druck.
4. **Flotte** — Bambu LAN, PrusaLink, mehrere Drucker gleichzeitig,
   Eignungsprüfung (Bauraum, Düse, Material), gemeinsame Warteschlange;
   STL mit Referenzeinstellungen slicen.

### Stand Phase 1 (30.09.2026)

**Da:** Wurzelordner (mehrere), Scan mit Hash als Kennung (Verschieben,
Umbenennen, Kopien, fehlende Dateien), Leser für STL/OBJ/3MF (Komponenten,
Transformationen, Bild, Platten aus `slice_info`), STEP (Maße, Vorschau und 3D-Ansicht über FreeCAD ohne Fenster, wenn es
installiert ist; sonst nur aufgenommen) und FCStd (Vorschau aus dem Thumbnail der Datei; nach Zusage des Anwenders auch Maße, Vorschau und 3D-Ansicht über FreeCAD),
Vorschau auf dem Server in der Filamentfarbe, automatische Tags wie im
3MF Katalog, Suche wie in pDMS (Teilwörter, alle Wörter, "Wortfolge",
-wort, Feldfilter tag:/ordner:/baugruppe:/sammlung:/material:/format:/
designer:/gedruckt:/favorit:, Relevanz nach Feld), Leiste über dem
Raster mit Material- und Tag-Chips (je mit ODER, Anzahl je Chip, wer mehr
gewählte Chips trifft, steht oben), Ordner-/Format-Filter, Favorit, Gedruckt,
Umbenennen auf der Platte, Löschen mit Vorschau → Papierkorb →
Wiederherstellen, „Öffnen in …“ (Slicer, FreeCAD, System; Standard je Format), Live-Oberfläche per SSE,
virtuelles Raster, Wache gegen fremde Herkunft.
3D-Ansicht direkt im Inspektor (three.js r170 aus dem npm-Paket, vom
eigenen Server ausgeliefert; umschaltbar auf das Bild, ohne WebGL nur das
Bild), Sammlungen (Kante mit Position, Ziehen zum Hinzufügen und
Umsortieren), Warteschlange (Feld am Modell, Liste links, Ziehen, fällt
bei „gedruckt“ heraus).

Mehrfachauswahl (Kästchen, Umschalt-Klick, Leiste mit Warteschlange,
Sammlung, Tag, Gedruckt, Favorit, Verschieben, Löschen; Escape, Entf),
Listenansicht mit sortierbarem Kopf, Verschieben in einen Ordner (Dialog
oder Kachel auf den Ordner ziehen, nie überschreiben, Duplikate nicht),
neuer Unterordner, Quelle als http(s)-Link, eigenes Bild (als PNG neu
geschrieben, im Vault), Hochladen per Dialog oder aus dem Dateimanager
ins Fenster ziehen, Archive entpacken (zip, tar; Positivliste der
Endungen, kein ../, keine Links; Original auf Wunsch in den Papierkorb).
Ein Scan-Auftrag während eines Laufs startet danach einen Nachlauf —
vorher gingen so hochgeladene Dateien verloren.

Über den 3MF Katalog hinaus: Baugruppen mit Stückliste, Kaufteil-Katalog,
Fortschritt, Einkaufsliste (§4.5).

**Fehlt noch zur Parität:** Papierkorb nach 7 Tagen leeren (braucht
flatgraph, siehe §9), 7z und rar entpacken (fremde Pakete).

**Zurückgestellt:** Passwort für den Zugriff aus dem Heimnetz — erst wenn
alles andere steht. Bis dahin nur `127.0.0.1`.

Die Zeilenschätzung aus v1.5.0 (16 110 SLOC) ist verworfen: die
Aufteilung nach Schichten (8 400 / 4 850) widersprach der Modulliste
(≈ 7 760 / 5 500), die Testquote (18 %) der Zusage (20–25 %). Neu
geschätzt wird, wenn Phase 1 steht.

---

## 8. Gemessen

**flatgraph 4.0.0 (`d2ae82f`, Speicherform 3) mit diesem Datenmodell**,
30.09.2026, Linux-Container (4 Kerne, ext4), Python 3.11. Skript:
`messung/partatlas_mess.py`. Median aus 15 Läufen, Öffnen 7 warm / 5 kalt.

Angenommener Bestand — 10 000 Modelle mit Historie: 15 000 Dateien,
8 000 G-Codes, 16 000 Drucke, 3 Tags je Modell, Profile, Material,
Spulen, 5 Drucker, 20 Fächer. **50 000 Knoten, 125 440 Kanten.**

| Frage | Ergebnis |
|---|---|
| Arbeitsspeicher nach dem Öffnen (RSS) | 200 MB (Python allein 12) |
| davon Kanten + Nachbarschaftsindex / Knoten | ≈ 93 MB / ≈ 45 MB |
| Öffnen warm / kalt | 1,0 s / 1,5 s |
| Platte | 43,6 MB, 7 021 Dateien |
| Aufbau in einer Transaktion | 13,5 s |
| Namenssuche erste / warm | 8,4 / 1,2 ms |
| Suche in 200-Byte-Beschreibung erste / warm | 16 / 5,2 ms |
| Tag-Filter (434 Treffer) | 0,17 ms |
| Bauraum-Prüfung über alle Modelle | 4,7 ms |
| Inspector (Modell, Teile, Tags, G-Code, Drucke) | 0,014 ms |
| Filament-Ampel (Drucker → Fächer → Spulen) | 0,011 ms |
| Protokoll eines Druckers (3 192 Drucke) | 2,2 ms |
| Ein Modell einlesen (eigene Transaktion) | 10,6 ms |
| Druckende (Druck anlegen, Spule abbuchen) | 7,5 ms |

Was daraus folgt: jede Abfrage der Oberfläche liegt unter 20 ms. Erstes
Einlesen in einer Transaktion (≈ 15 s für 5 700 Dateien), nicht Datei für
Datei (hochgerechnet ≈ 1 min).

### Phase 1 am echten Scan

30.09.2026, derselbe Container, 3 Arbeitsprozesse. Sammlung aus
`werkzeuge/demo_sammlung.py --anzahl 5700` (84 MB; einfache Formen mit
einigen tausend Dreiecken — echte Modelle sind grösser).

| Frage | Ergebnis |
|---|---|
| Erster Scan: alle 5 593 Modelle im Katalog sichtbar | 9,5 s |
| … alle Vorschauen gerendert | 260 s |
| Zweiter Scan ohne Änderung | 0,1 s |
| Server nach dem Scan (RSS) | 127 MB |
| Bestand: Datenbank / Vorschauen im Vault | 11 MB / 43 MB |
| `/api/modelle` alle 5 593 Kacheln (2 MB JSON) | 346 ms |
| Suche „zahnrad“ / Tag-Filter „petg“ | 16 / 54 ms |
| Wortindex aufbauen (5 593 Modelle, 5 653 Wörter), 0.8.0 | 0,15 s |
| Suche „halter“ (1 080 Treffer) / „a“ (5 130) / „arm front“ (188), nur Index | 8 / 39 / 3 ms |
| … dieselben mit Kacheln (`modelle()`) | 51 / 140 / 6 ms |
| Modell für den Inspektor | 4,4 ms |
| Browser: erste Kacheln nach dem Laden | 1,4 s; 30 Kacheln im DOM, beim Scrollen gleich viele |
| Vorschau eines Torus mit 180 000 Dreiecken, ein Kern | 1,3 s |

Schätzung, nicht gemessen: echte Modelle mit 100 000 bis 2 Mio. Dreiecken
(beim Rendern auf 400 000 ausgedünnt) brauchen um 1 s je Vorschau; 5 700
davon auf 3 Prozessen also rund eine halbe Stunde — im Hintergrund, der
Katalog ist vorher benutzbar.

---

## 9. Offen

Ungeprüft, zu klären vor der genannten Phase:

| Punkt | vor Phase |
|---|---|
| Bambu Studio: steht die volle Konfiguration im G-Code? | 2 |
| Wortindex nach flatgraph (VERTRAG, 4.1), dann pDMS und partAtlas darauf | — |
| Gespeicherte Suchen (pDMS hat sie) | — |
| Seitenleiste bei grossen Beständen: der Ordnerbaum mit 5 700 Teilen füllt sie allein; Abschnitte helfen nur teilweise | — |
| Anycubic Slicer: Programmnamen und Orte an einer echten Installation | — |
| Druck bei ausgeschaltetem PC: Nachtrag aus der Moonraker-Historie beim Start; bei Bambu unbekannt | 2 |
| Render-Zeit mit echten Modellen auf dem Rechner des Anwenders (hier nur erzeugte Formen gemessen) | 1 |
| STEP über FreeCAD ohne Fenster: der Aufruf an einem echten FreeCAD (Paket, Flatpak, AppImage, Windows) und die Zeit für grosse Teile | 1 |
| flatTSDB: Stand und Ort der Bibliothek | 3 |
| Bambu LAN: seit den Firmware-Änderungen 2025 womöglich nur im Entwicklermodus | 4 |
| OrcaSlicer: Slicen über die Kommandozeile mit fremder Konfiguration | 4 |
| Windows: Verzeichnis-`fsync` fehlt (VERTRAG §2.2), ungeprüft | 1 |
| flatgraph: Müllsammler nur für Knoten, die länger als N Tage im Papierkorb liegen — heute räumt `run_garbage_collection` alles ab, also auch gestern Gelöschtes | 1 |
| 7z und rar: `py7zr` bzw. `rarfile` + `unrar` — fremde Pakete, Lizenz von unrar prüfen | 1 |
| Lizenz: Hinweis auf den 3MF Katalog (MIT) steht in `web/app.css`; beim Übernehmen weiterer Teile mitführen | 1 |
