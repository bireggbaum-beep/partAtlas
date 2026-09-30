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

## Testen

```bash
for t in tests/test_*.py; do python "$t" | tail -1; done
```

Selbstgeschrieben wie flatgraph und pDMS: jede Suite endet mit „n/n Checks
bestanden“, Exit 1 bei einem Fehlschlag. Gegenprobe an einer mutierten
Kopie: `PARTATLAS_QUELLE=/pfad/zur/kopie python tests/…`.
