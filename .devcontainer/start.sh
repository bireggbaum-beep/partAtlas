#!/usr/bin/env bash
#
# partAtlas starten — im Codespace automatisch bei jedem Containerstart
# (postStartCommand), von Hand im Terminal:
#
#     bash .devcontainer/start.sh          startet, wenn nichts läuft
#     bash .devcontainer/start.sh --neu    beendet einen laufenden und startet neu
#     bash .devcontainer/start.sh --stop   nur beenden
#
# Beim ersten Start entsteht eine Demo-Sammlung (~/partatlas-demo, rund 60
# Modelle) und wird als Wurzelordner eingetragen, damit gleich etwas zu
# sehen ist. Ohne das — um den ersten Start der Oberfläche zu sehen —:
#
#     PARTATLAS_OHNE_DEMO=1 bash .devcontainer/start.sh --neu
#
# Nach dem Löschen des Bestands (~/.local/share/partatlas) beginnt es von vorn.
#
# ACHTUNG: partAtlas hat noch kein Passwort (KONZEPT §2), und der
# Ordner-Wähler listet das Dateisystem. Den Port 8765 im Tab „Ports“
# PRIVAT lassen, nie auf „Öffentlich“ stellen.
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${PARTATLAS_PORT:-8765}"
DEMO="${PARTATLAS_DEMO:-$HOME/partatlas-demo}"
LOGDIR="${PARTATLAS_LOG:-$ROOT/_partatlas_log}"
LOG="$LOGDIR/server.log"
MUSTER="python -m partatla[s]"

cd "$ROOT" || exit 1
mkdir -p "$LOGDIR"

laeuft() { curl -fsS -m 2 "http://127.0.0.1:$PORT/api/stand" -o /dev/null 2>/dev/null; }

beenden() {
  # Das Muster mit Klammer, damit pkill nicht die eigene Kommandozeile trifft.
  pkill -f "$MUSTER" 2>/dev/null
  for _ in $(seq 1 20); do
    pgrep -f "$MUSTER" >/dev/null 2>&1 || return 0
    sleep 0.5
  done
  pkill -9 -f "$MUSTER" 2>/dev/null
  sleep 1
}

case "${1:-}" in
  --stop)
    beenden
    echo "partAtlas beendet."
    exit 0
    ;;
  --neu)
    beenden
    ;;
  *)
    if laeuft; then
      echo "partAtlas läuft bereits auf Port $PORT — nichts zu tun."
      exit 0
    fi
    # Antwortet nicht, aber ein Prozess ist da: eine Leiche, die den Bestand
    # hält. Weg damit, sonst startet der neue nicht.
    if pgrep -f "$MUSTER" >/dev/null 2>&1; then
      echo "Ein partAtlas-Prozess ist da, antwortet aber nicht — wird beendet."
      beenden
    fi
    ;;
esac

if ! python -c "import uvicorn, fastapi, flatgraph" >/dev/null 2>&1; then
  echo "Abhängigkeiten fehlen — installiere sie nach…"
  pip install -q -r requirements.txt || exit 1
fi

echo "--- Start $(date '+%Y-%m-%d %H:%M:%S') ---" >>"$LOG"
PARTATLAS_PORT="$PORT" nohup python -m partatlas >>"$LOG" 2>&1 &
PID=$!

for _ in $(seq 1 60); do
  if laeuft; then
    echo "partAtlas läuft (PID $PID) auf Port $PORT. Protokoll: $LOG"
    break
  fi
  kill -0 "$PID" 2>/dev/null || {
    echo "partAtlas ist nicht hochgekommen. Die letzten Zeilen aus $LOG:"
    tail -n 25 "$LOG"
    exit 1
  }
  sleep 1
done
laeuft || { echo "partAtlas antwortet nicht. Protokoll: $LOG"; tail -n 25 "$LOG"; exit 1; }

# Demo-Sammlung, einmal: nur wenn noch kein Wurzelordner eingetragen ist.
if [ -z "${PARTATLAS_OHNE_DEMO:-}" ]; then
  if [ "$(curl -fsS -m 5 "http://127.0.0.1:$PORT/api/wurzeln" 2>/dev/null)" = "[]" ]; then
    [ -d "$DEMO" ] || python werkzeuge/demo_sammlung.py "$DEMO" --anzahl 60 >/dev/null
    curl -fsS -m 10 -X POST -H 'Content-Type: application/json' \
      -d "{\"pfad\": \"$DEMO\"}" "http://127.0.0.1:$PORT/api/wurzeln" >/dev/null \
      && echo "Demo-Sammlung eingetragen: $DEMO"
    python werkzeuge/demo_drucke.py --port "$PORT" >/dev/null 2>&1 &
  fi
fi
