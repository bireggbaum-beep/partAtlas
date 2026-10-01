#!/usr/bin/env bash
# partAtlas starten: beim ersten Mal die eigene Python-Umgebung anlegen und
# die Pakete holen, danach nur noch starten und den Browser öffnen.
#   ./start.sh          starten
#   ./start.sh --demo   vorher eine Demo-Sammlung nach ~/partatlas-demo legen
set -eu
cd "$(dirname "$0")"
PORT="${PARTATLAS_PORT:-8765}"
URL="http://127.0.0.1:$PORT"

if ! command -v python3 >/dev/null || ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then
  echo "partAtlas braucht Python 3.10 oder neuer (Manjaro: sudo pacman -S python)."; exit 1
fi
if ! command -v git >/dev/null; then
  echo "git fehlt, es holt die Datenbank flatgraph (Manjaro: sudo pacman -S git)."; exit 1
fi

# Läuft es schon, wird nur der Browser geöffnet — nie ein zweiter Prozess.
if curl -fs "$URL/" >/dev/null 2>&1; then
  echo "partAtlas läuft schon: $URL"; xdg-open "$URL" >/dev/null 2>&1 || true; exit 0
fi

# Eigene Umgebung (Manjaro erlaubt kein pip im System, PEP 668). Neu
# installiert wird nur, wenn sich requirements.txt geändert hat.
[ -d .venv ] || python3 -m venv .venv
STAND="$(sha256sum requirements.txt | cut -d' ' -f1)"
if [ "$(cat .venv/.stand 2>/dev/null)" != "$STAND" ]; then
  echo "Pakete werden installiert (einmalig, ein paar Minuten) …"
  .venv/bin/pip install -q -r requirements.txt
  echo "$STAND" > .venv/.stand
fi

if [ "${1:-}" = "--demo" ] && [ ! -d "$HOME/partatlas-demo" ]; then
  .venv/bin/python werkzeuge/demo_sammlung.py "$HOME/partatlas-demo" --anzahl 60
  echo "Demo-Sammlung liegt in ~/partatlas-demo — in der Oberfläche unter Importieren → Ordner hinzufügen."
fi

( for _ in $(seq 1 40); do curl -fs "$URL/" >/dev/null 2>&1 && { xdg-open "$URL" >/dev/null 2>&1 || true; break; }; sleep 0.5; done ) &
echo "partAtlas: $URL   (beenden mit Strg+C)"
exec .venv/bin/python -m partatlas
