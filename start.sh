#!/usr/bin/env bash
# partAtlas starten: beim ersten Mal die eigene Python-Umgebung anlegen und
# die Pakete holen, danach nur noch starten und den Browser öffnen.
#   ./start.sh          starten (läuft schon eine ältere Fassung, wird gefragt, ob neu gestartet werden soll)
#   ./start.sh --neu    eine laufende Fassung ohne Rückfrage beenden und neu starten
#   ./start.sh --demo   vorher eine Demo-Sammlung nach ~/partatlas-demo legen
set -eu
cd "$(dirname "$0")"
PORT="${PARTATLAS_PORT:-8765}"
URL="http://127.0.0.1:$PORT"
NEU=0; DEMO_WUNSCH=0
for a in "$@"; do
  case "$a" in
    --neu) NEU=1 ;;
    --demo) DEMO_WUNSCH=1 ;;
    *) echo "Unbekannt: $a (möglich: --neu, --demo)"; exit 1 ;;
  esac
done

if ! command -v python3 >/dev/null || ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then
  echo "partAtlas braucht Python 3.10 oder neuer (Manjaro: sudo pacman -S python)."; exit 1
fi
if ! command -v git >/dev/null; then
  echo "git fehlt, es holt die Datenbank flatgraph (Manjaro: sudo pacman -S git)."; exit 1
fi

# Dateiauswahl (Ordner, Programme): der Dialog des Rechners braucht zenity oder kdialog.
if ! command -v zenity >/dev/null && ! command -v kdialog >/dev/null; then
  echo "Hinweis: für die Dateiauswahl fehlt zenity oder kdialog (Manjaro: sudo pacman -S zenity)."
  echo "         partAtlas läuft trotzdem, zeigt dann aber einen einfachen eigenen Ordnerwähler."
fi

# Der Server ist ein Python-Prozess ("python -m partatlas", kein Programm mit eigenem Namen): nach `git pull` läuft er mit der alten
# Fassung weiter, bis er beendet wird. Darum nennt dieses Skript, welche Fassung läuft und welche auf der Platte liegt.
fassung_platte() { sed -n 's/^VERSION = "\(.*\)"/\1/p' partatlas/version.py; }
# Jede Abfrage mit Zeitgrenze: hängt der Server, darf dieses Skript nicht mit hängen (ohne -m wartete curl unbegrenzt).
antwortet() { curl -fs -m 3 "$URL/" >/dev/null 2>&1; }
fassung_laufend() { curl -fs -m 3 "$URL/api/stand" 2>/dev/null | sed -n 's/.*"version" *: *"\([^"]*\)".*/\1/p' | head -n1; }
pid_am_port() {
  if command -v lsof >/dev/null; then lsof -t -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | head -n1
  elif command -v ss >/dev/null; then ss -ltnpH "sport = :$PORT" 2>/dev/null | sed -n 's/.*pid=\([0-9]*\).*/\1/p' | head -n1
  fi
}
browser_oeffnen() { xdg-open "$URL" >/dev/null 2>&1 || true; }

ist_partatlas() { [ -n "$1" ] && ps -o command= -p "$1" 2>/dev/null | grep -q partatlas; }
beenden() {   # $1 = Prozess; erst bitten, dann (nach Rückfrage oder --neu) erzwingen
  kill "$1" 2>/dev/null || true
  for _ in $(seq 1 30); do kill -0 "$1" 2>/dev/null || return 0; sleep 0.5; done
  if [ "$NEU" = 1 ]; then ANTWORT=j
  elif [ -t 0 ]; then read -r -p "partAtlas (Prozess $1) reagiert nicht aufs Beenden. Erzwingen? [J/n] " ANTWORT
  else ANTWORT=n; fi
  case "$ANTWORT" in n|N|nein|Nein) echo "Nicht beendet. Von Hand:  kill -9 $1"; exit 1 ;; esac
  kill -9 "$1" 2>/dev/null || true; sleep 1
}

# Der Port ist belegt, aber nichts antwortet: ein hängender Server. Nicht einfach einen zweiten starten (der fände den Port besetzt),
# sondern ihn benennen und nach Rückfrage beenden.
if ! antwortet && PID="$(pid_am_port)" && [ -n "$PID" ]; then
  if ! ist_partatlas "$PID"; then
    echo "Port $PORT ist belegt (Prozess $PID), aber nicht von partAtlas. Anderen Port: PARTATLAS_PORT=8766 ./start.sh"; exit 1
  fi
  if [ "$NEU" = 1 ]; then ANTWORT=j
  elif [ -t 0 ]; then read -r -p "partAtlas (Prozess $PID) antwortet nicht. Beenden und neu starten? [J/n] " ANTWORT
  else echo "partAtlas (Prozess $PID) antwortet nicht. Neu starten: ./start.sh --neu"; exit 1; fi
  case "$ANTWORT" in n|N|nein|Nein) exit 1 ;; esac
  echo "partAtlas wird beendet (Prozess $PID) …"
  beenden "$PID"
fi

# Läuft es schon, wird nie ein zweiter Prozess gestartet.
if antwortet; then
  LAUFEND="$(fassung_laufend)"; PLATTE="$(fassung_platte)"
  if [ "$NEU" = 0 ] && { [ -z "$LAUFEND" ] || [ "$LAUFEND" = "$PLATTE" ]; }; then
    echo "partAtlas ${LAUFEND:+$LAUFEND }läuft schon: $URL"; browser_oeffnen; exit 0
  fi
  # Entweder eine andere Fassung als die auf der Platte, oder --neu: neu starten, nach Rückfrage.
  if [ "$NEU" = 1 ]; then ANTWORT=j
  elif [ -t 0 ]; then
    echo "partAtlas $LAUFEND läuft noch, auf der Platte liegt $PLATTE."
    read -r -p "Beenden und mit $PLATTE neu starten? [J/n] " ANTWORT
  else
    echo "partAtlas $LAUFEND läuft noch, auf der Platte liegt $PLATTE. Neu starten: ./start.sh --neu"; browser_oeffnen; exit 0
  fi
  case "$ANTWORT" in
    n|N|nein|Nein) echo "partAtlas $LAUFEND bleibt: $URL"; browser_oeffnen; exit 0 ;;
  esac
  PID="$(pid_am_port)"
  # Nur beenden, was wirklich partAtlas ist — am Port könnte etwas anderes hören.
  if ! ist_partatlas "$PID"; then
    echo "Der Prozess an Port $PORT ist nicht auffindbar oder kein partAtlas; er wird nicht beendet."
    echo "Von Hand: Strg+C im Terminal, in dem es läuft, oder  pkill -f 'python -m partatlas'"; exit 1
  fi
  echo "partAtlas $LAUFEND wird beendet (Prozess $PID) …"
  beenden "$PID"
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
if [ "$DEMO_WUNSCH" = 1 ] && [ ! -d "$DEMO" ]; then
  .venv/bin/python werkzeuge/demo_sammlung.py "$DEMO" --anzahl 60
fi

( for _ in $(seq 1 40); do antwortet && break; sleep 0.5; done
  # Demo: Sammlung als Wurzelordner eintragen (einmal) und erfundene Drucke dazu.
  if [ "$DEMO_WUNSCH" = 1 ] && [ "$(curl -fs -m 5 "$URL/api/wurzeln")" = "[]" ]; then
    curl -fs -m 30 -X POST -H 'Content-Type: application/json' -d "{\"pfad\": \"$DEMO\"}" "$URL/api/wurzeln" >/dev/null
    .venv/bin/python werkzeuge/demo_drucke.py --port "$PORT" >/dev/null 2>&1 &
  fi
  browser_oeffnen ) &
echo "partAtlas: $URL   (beenden mit Strg+C)"
exec .venv/bin/python -m partatlas
