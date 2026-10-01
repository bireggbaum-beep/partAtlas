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

DEMO="$HOME/partatlas-demo"
if [ "${1:-}" = "--demo" ] && [ ! -d "$DEMO" ]; then
  .venv/bin/python werkzeuge/demo_sammlung.py "$DEMO" --anzahl 60
fi

( for _ in $(seq 1 40); do curl -fs "$URL/" >/dev/null 2>&1 && break; sleep 0.5; done
  # Demo: Sammlung als Wurzelordner eintragen (einmal) und erfundene Drucke dazu.
  if [ "${1:-}" = "--demo" ] && [ "$(curl -fs "$URL/api/wurzeln")" = "[]" ]; then
    curl -fs -X POST -H 'Content-Type: application/json' -d "{\"pfad\": \"$DEMO\"}" "$URL/api/wurzeln" >/dev/null
    .venv/bin/python werkzeuge/demo_drucke.py --port "$PORT" >/dev/null 2>&1 &
  fi
  xdg-open "$URL" >/dev/null 2>&1 || true ) &
echo "partAtlas: $URL   (beenden mit Strg+C)"
exec .venv/bin/python -m partatlas
