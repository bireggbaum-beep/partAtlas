#!/bin/sh
# Baut partAtlas als eine einzelne Datei zum Anklicken (Linux: partatlas, Windows: partatlas.exe), ohne Fenster-Hülle: sie startet den
# Server, öffnet den Standardbrowser und beendet sich, wenn keine Seite mehr offen ist (partatlas/starter.py).
# Voraussetzung: Python mit den Paketen aus requirements.txt und PyInstaller.
set -e
cd "$(dirname "$0")"
HERE=$(pwd)
PY="${PYTHON:-python3}"
VERSION=$("$PY" -c "import sys; sys.path.insert(0, '..'); from partatlas.version import VERSION; print(VERSION)")
rm -rf build-einzeldatei dist-einzeldatei
"$PY" -m PyInstaller --noconfirm --clean --name partatlas --onefile --console \
    --paths "$HERE/.." --collect-submodules partatlas --hidden-import partatlas.__main__ \
    --add-data "$HERE/../partatlas/web:partatlas/web" \
    --distpath dist-einzeldatei --workpath build-einzeldatei --specpath build-einzeldatei "$HERE/launch.py"
echo "Fertig: dist-einzeldatei/partatlas (Fassung $VERSION)"
