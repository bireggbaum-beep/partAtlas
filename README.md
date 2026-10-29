# partAtlas

Ein Katalog für deine 3D-Druck-Sammlung. partAtlas liest deine Ordner ein (STL, 3MF, OBJ, STEP, FCStd), zeigt Vorschaubilder und eine
3D-Ansicht und hält fest, was du daraus machst: Tags, Sammlungen, Baugruppen mit Stückliste, Drucke mit Ergebnis und Einstellungen.
Es läuft auf deinem Rechner im Browser, ohne Konto und ohne Internet. Deine Dateien bleiben, wo sie sind — partAtlas kopiert sie nicht
und löscht in deinen Ordnern nie etwas. Gebaut auf [flatgraph](https://github.com/bireggbaum-beep/flatgraphdb); führend für die
Entwicklung ist `KONZEPT.md`, die Bedienung beschreibt das Handbuch (in partAtlas: **?** links unten oder **F1**; Datei `partatlas/web/handbuch/index.html`).

## Installieren und starten — Windows

Voraussetzung, einmalig:
- **Python 3.10 oder neuer** von [python.org](https://www.python.org/downloads/) — beim Installieren „Add python.exe to PATH“ ankreuzen.
- **Git** von [git-scm.com](https://git-scm.com/download/win) (holt beim Installieren die Datenbank flatgraph).

Dann den Ordner holen, in der **PowerShell**:

```powershell
git clone https://github.com/bireggbaum-beep/partAtlas
```

und im Ordner `partAtlas` **`start.bat` doppelklicken**. Beim ersten Mal legt sie die Umgebung an und holt die Pakete (ein paar
Minuten), danach startet partAtlas und der Browser öffnet **http://127.0.0.1:8765**. Beenden mit Strg+C im Fenster (die Frage
„Batchvorgang abbrechen?“ mit J beantworten) oder das Fenster schliessen. Läuft partAtlas schon, öffnet `start.bat` nur den Browser.

**Aktualisieren** (neue Fassung holen): partAtlas beenden, dann in der PowerShell im Ordner `partAtlas`

```powershell
git pull
```

und wieder `start.bat` doppelklicken — neue Pakete holt sie selbst. Läuft beim Start noch die alte Fassung, sagt sie es.

Ohne `start.bat`, von Hand in der PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m partatlas
```

## Installieren und starten — Linux (Manjaro u. a.)

Voraussetzung: Python 3.10+, git und für die Dateiauswahl zenity oder kdialog (`sudo pacman -S python git zenity`).

```bash
git clone https://github.com/bireggbaum-beep/partAtlas && cd partAtlas
./start.sh --demo      # beim ersten Mal: Umgebung anlegen, Demo-Sammlung, Browser
```

Danach genügt `./start.sh`. Zum **Aktualisieren** (neue Fassung holen):

```bash
cd partAtlas
git pull
./start.sh             # kein --demo nötig; die eigene Sammlung bleibt erhalten
```

Läuft noch die alte Fassung, sagt `start.sh` es („partAtlas 0.45.1 läuft noch, auf der Platte liegt 0.46.0“) und fragt, ob es sie beenden
und neu starten soll. Ohne Rückfrage: `./start.sh --neu`. Antwortet eine laufende Fassung nicht mehr, sagt `start.sh` auch das und
beendet sie nach Rückfrage, notfalls erzwungen. Der Server ist ein Python-Prozess (`python -m partatlas`) und heisst deshalb in der
Systemüberwachung „python“, nicht „partAtlas“. Von Hand beenden: Strg+C im Terminal, in dem es läuft, oder `pkill -f "python -m partatlas"`.

Im Browser einmal **Strg+Umschalt+R** (neu laden ohne Zwischenspeicher). Oben links steht neben dem Logo die
Fassung. Slicer und CAD (PrusaSlicer, Orca, Cura, FreeCAD …)
findet partAtlas im PATH, bei Flatpak und als AppImage in `~/Applications`
oder `~/AppImages`; „Öffnen in …“ startet sie auf dem eigenen Rechner.

## Wo deine Daten liegen

Deine Modelldateien bleiben in deinen Ordnern. Was partAtlas dazu weiss — Tags, Drucke, Baugruppen, Sammlungen, Notizen, Anhänge,
eigene Bilder — liegt im **Bestand**: unter Windows `C:\Users\<Name>\.local\share\partatlas`, unter Linux `~/.local/share/partatlas`
(anderer Ort mit `PARTATLAS_BESTAND=…`). **Nimm diesen Ordner in dein eigenes Backup auf**; Einstellungen › Backup & Wiederherstellung
zeigt ihn mit „Ordner zeigen“. Gegen eigene Fehlgriffe legt partAtlas darin automatische Sicherungen an, die sich dort zurückholen lassen.

## Erste Schritte

In der Oberfläche: **Importieren → Ordner hinzufügen** öffnet den Ordnerdialog des Rechners; partAtlas liest den Ordner samt
Unterordnern ein. Zum Ausprobieren ohne eigene Sammlung:

```bash
python werkzeuge/demo_sammlung.py ~/partatlas-demo --anzahl 60
```

## Im Codespace

`.devcontainer/` richtet alles ein: Pakete installieren, partAtlas bei jedem
Containerstart starten (nie ein zweiter Prozess), beim ersten Mal eine
Demo-Sammlung als Wurzelordner eintragen, Port 8765 im Browser öffnen.

```bash
bash .devcontainer/start.sh --neu                         # neu starten
PARTATLAS_OHNE_DEMO=1 bash .devcontainer/start.sh --neu   # ohne Demo (erster Start der Oberfläche)
bash .devcontainer/start.sh --stop
```

Den Port im Tab „Ports“ **privat** lassen: partAtlas hat noch kein Passwort,
und der Ordner-Wähler listet das Dateisystem. „Öffnen in Slicer/CAD“ und
„Im Ordner zeigen“ tun im Codespace nichts (kein Desktop).

## Testen

```bash
pip install -r requirements-test.txt
for t in tests/test_*.py; do python "$t" | tail -1; done
```

`test_ui.py` startet den Server als eigenen Prozess und prüft im echten
Chromium (`PARTATLAS_CHROMIUM`, wenn Playwrights eigenes fehlt).

Selbstgeschrieben wie flatgraph und pDMS: jede Suite endet mit „n/n Checks
bestanden“, Exit 1 bei einem Fehlschlag. Gegenprobe an einer mutierten
Kopie: `PARTATLAS_QUELLE=/pfad/zur/kopie python tests/…`.

## Zurück auf eine frühere Fassung

Jede Fassung, die auf `main` kam, lässt sich wieder holen. Der Stand vor 1.0.7 liegt im Zweig `fassung-1.0.6`, der vor 1.0.6 in `fassung-1.0.5`, der vor 1.0.5 in `fassung-1.0.4`, der vor 1.0.4 in `fassung-1.0.3`, der vor 1.0.3 in `fassung-1.0.2`, der vor 1.0.2 in `fassung-1.0.1`, der vor 1.0.1 in `fassung-1.0.0`, der vor 1.0 in `fassung-0.95.7`, der vor 0.95 in
`fassung-0.55.0`. partAtlas beenden (Strg+C im Fenster), dann im Ordner `partAtlas`:

```bash
git fetch origin && git checkout fassung-1.0.5   # die alte Fassung (1.0.6 öffnet manche Bestände nicht)
./start.sh                                         # Windows: .venv\Scripts\python -m partatlas (start.bat gibt es dort noch nicht)
git checkout main                                  # später wieder zur neuen
```

Die Datenbank bleibt dabei lesbar (keine neue Speicherform): eine ältere Fassung übersieht nur, was sie noch nicht kennt. Wer auch den
Katalog zurück will: Einstellungen › Backup & Wiederherstellung › eine automatische Sicherung von vor dem Wechsel „Zurückholen“.
