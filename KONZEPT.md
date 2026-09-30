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

- **Rechner:** Manjaro (bevorzugt) und Windows 10. Linux ist Zielsystem,
  Windows soll laufen. (Raspberry Pi war nie Anwenderwunsch — gestrichen.)
- **Aufbau wie pDMS:** ein Python-Prozess (FastAPI) auf dem Rechner des
  Anwenders, Oberfläche im Browser. Start von Hand oder als
  systemd-Benutzerdienst.
- **Tauri** als optionale Desktop-Hülle um dieselbe Oberfläche: Fenster
  wie ein Programm, Ziehen aus dem Dateimanager. Der Browser bleibt, auch
  für Tablet und Handy im Heimnetz.
- **„Im Slicer öffnen“** startet der Server direkt (`orcaslicer <datei>`),
  weil Server und Slicer auf demselben Rechner laufen. Erkennung der
  Slicer wie im 3MF Katalog.
- **Ein Prozess besitzt den Bestand** (flatgraph: eine offene Instanz je
  Bestand, `BestandBelegt`). Renderer und Einlesen dürfen eigene Prozesse
  sein, liefern aber nur Ergebnisse zu; geschrieben wird im Hauptprozess.
- **Wache wie pDMS:** ohne Passwort nur `127.0.0.1`; mit Passwort im
  Heimnetz; schreibende Anfragen nur von der eigenen Oberfläche
  (`Origin`/`Sec-Fetch-Site`). Ein Druckstart heizt eine Maschine auf
  über 200 °C — er braucht immer eine Bestätigung mit Druckername.
- **Arbeitsspeicher** ist kein Kriterium (siehe §8 für die Zahl).

---

## 3. Dateien und Bestand

### 3.1 Die Sammlung des Anwenders

- Der Anwender wählt **einen oder mehrere Wurzelordner**. Ihre Struktur
  wird eingelesen und bleibt seine.
- Die Ordneransicht wird **aus den Pfaden abgeleitet**, nicht gespeichert:
  jede Datei trägt Wurzel und relativen Pfad.
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
| `vault/` | G-Code und die Quelldatei, aus der er entstand | nicht wiederherstellbar | ja |
| `cache/` | Vorschaubilder, Renderings, entpackte Archive | wird neu erzeugt | nein |

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
6. **Live-Oberfläche:** `bei_aenderung` (VERTRAG §2.7) meldet jede
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
| `PRINT_JOB` | `next_id`, nie wiederverwendet | Zeit, Dauer, Ergebnis, Notiz, Foto, TSDB-Stream + Zeitraum | `print_log`, `printer_jobs` |
| `PRINTER_DEVICE` | fortlaufend | Name, Anschluss, Adresse, Bett, Düse | `printers`, `printer_connections` |
| `AMS_SLOT` | fortlaufend | Fach einer Einheit | `material_units` |
| `MATERIAL_SPOOL` | fortlaufend | Spule/Flasche: Rest, Preis, Lagerort, Farbe | `filament_spools` |
| `MATERIAL_MASTER` | fortlaufend | Filamenttyp | — |

Warteschlange: Feld `queue_position` am Modell wie im 3MF Katalog, bis
die Flotte (Phase 4) eine eigene Sammlung braucht.

### 6.2 Kanten

```
MODEL_ASSET    ─[HAS_PART]──────────▶ PART_GEOMETRY
MODEL_ASSET    ─[HAS_TAG]───────────▶ TAG_ITEM
MODEL_ASSET    ─[IN_COLLECTION]─────▶ COLLECTION        meta: position
MODEL_ASSET    ─[HAS_GCODE]─────────▶ GCODE_ARTIFACT
GCODE_ARTIFACT ─[SLICED_FROM]───────▶ PART_GEOMETRY     die Quelle im Vault
GCODE_ARTIFACT ─[BASED_ON_PROFILE]──▶ PRINT_PROFILE
GCODE_ARTIFACT ─[REQUIRES_MATERIAL]─▶ MATERIAL_MASTER
GCODE_ARTIFACT ─[COMPILED_FOR]──────▶ PRINTER_DEVICE
PRINT_JOB      ─[EXECUTED_GCODE]────▶ GCODE_ARTIFACT
PRINT_JOB      ─[EXECUTED_ON]───────▶ PRINTER_DEVICE
PRINT_JOB      ─[USED_SPOOL]────────▶ MATERIAL_SPOOL
MODEL_ASSET    ─[REFERENCE]─────────▶ PRINT_JOB         höchstens eine je Drucker
PRINTER_DEVICE ─[HAS_SLOT]──────────▶ AMS_SLOT
AMS_SLOT       ─[LOADED_WITH]───────▶ MATERIAL_SPOOL
MATERIAL_SPOOL ─[IS_TYPE_OF]────────▶ MATERIAL_MASTER
MODEL_ASSET    ─[REMIX_OF]──────────▶ MODEL_ASSET
MODEL_ASSET    ─[SPARE_PART_FOR]────▶ MODEL_ASSET
MODEL_ASSET    ─[FITS]──────────────  MODEL_ASSET       ungerichtet
```

Vorschaubilder stehen nicht im Graphen: `cache/` unter dem Hash der
Datei.

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

---

## 9. Offen

Ungeprüft, zu klären vor der genannten Phase:

| Punkt | vor Phase |
|---|---|
| Bambu Studio: steht die volle Konfiguration im G-Code? | 2 |
| Druck bei ausgeschaltetem PC: Nachtrag aus der Moonraker-Historie beim Start; bei Bambu unbekannt | 2 |
| Render-Zeit je Modell mit Software-Rasterizer auf dem Rechner des Anwenders | 1 |
| flatTSDB: Stand und Ort der Bibliothek | 3 |
| Bambu LAN: seit den Firmware-Änderungen 2025 womöglich nur im Entwicklermodus | 4 |
| OrcaSlicer: Slicen über die Kommandozeile mit fremder Konfiguration | 4 |
| Windows: Verzeichnis-`fsync` fehlt (VERTRAG §2.2), ungeprüft | 1 |
| Lizenz: Übernahme der Oberfläche des 3MF Katalogs (MIT → Hinweis mitführen) | 1 |
