# partAtlas

Katalog für 3D-Druck-Sammlungen auf [flatgraph](https://github.com/bireggbaum-beep/flatgraphdb) —
Demo-Pilot, Vorbild ist der 3MF Katalog Manager. Führend ist `KONZEPT.md`.

## Starten

```bash
pip install -r requirements.txt
python -m partatlas                 # http://127.0.0.1:8765
```

Bestand unter `~/.local/share/partatlas`, anderer Ort mit `PARTATLAS_BESTAND=…`.
In der Oberfläche: **Importieren → Ordner hinzufügen**, Pfad eingeben.

Zum Ausprobieren ohne eigene Sammlung:

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
