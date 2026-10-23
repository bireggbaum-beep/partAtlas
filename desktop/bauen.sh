#!/bin/sh
# Baut das Desktop-Programm für Linux/Manjaro: ein Archiv, das die Webansicht (webkit2gtk-4.1) des Systems benutzt. Voraussetzungen: Python mit den Paketen aus requirements.txt und PyInstaller,
# Rust (cargo), Node, und für Tauri unter Debian/Ubuntu: libwebkit2gtk-4.1-dev libgtk-3-dev librsvg2-dev patchelf.
set -e
cd "$(dirname "$0")"
HERE=$(pwd)
PY="${PYTHON:-python3}"
VERSION=$("$PY" -c "import sys; sys.path.insert(0, '..'); from partatlas.version import VERSION; print(VERSION)")
rm -rf build-dienst src-tauri/dienst
"$PY" -m PyInstaller --noconfirm --clean --name partatlas --onedir --console \
    --paths "$HERE/.." --collect-submodules partatlas --hidden-import partatlas.__main__ \
    --add-data "$HERE/../partatlas/web:partatlas/web" \
    --distpath src-tauri/dienst --workpath build-dienst --specpath build-dienst "$HERE/launch.py"
npm install --no-audit --no-fund
# Fassung aus partatlas/version.py in die Tauri-Einstellungen, damit Programm und Server dieselbe Zahl tragen
sed -i "s/\"version\": \"[^\"]*\"/\"version\": \"$VERSION\"/" src-tauri/tauri.conf.json
npx tauri build --no-bundle

# Ohne mitgelieferte Webansicht: eine mitgelieferte passt bei Arch/Manjaro nicht zum Grafiktreiber (schwarzes Fenster, Absturz des
# Rechners beim AppImage). Entpacken, dann ./partatlas-fenster
rm -rf archiv && mkdir -p archiv/partatlas
cp src-tauri/target/release/partatlas-desktop archiv/partatlas/partatlas-fenster
cp -r src-tauri/dienst archiv/partatlas/dienst
tar -C archiv -czf "partatlas-linux-$VERSION.tar.gz" partatlas
