@echo off
rem partAtlas unter Windows starten (Doppelklick): beim ersten Mal die eigene Python-Umgebung anlegen und die Pakete holen,
rem danach nur noch starten und den Browser oeffnen. Gegenstueck zu start.sh unter Linux.
rem Beenden: Strg+C in diesem Fenster (oder das Fenster schliessen).
chcp 65001 >nul
setlocal
cd /d "%~dp0"
if "%PARTATLAS_PORT%"=="" (set "PORT=8765") else (set "PORT=%PARTATLAS_PORT%")
set "URL=http://127.0.0.1:%PORT%"

rem Python: zuerst der Starter "py" (python.org), sonst "python" im PATH; mindestens 3.10.
set "PY="
py -3 -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1 && set "PY=py -3"
if not defined PY python -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1 && set "PY=python"
if not defined PY (
  echo partAtlas braucht Python 3.10 oder neuer: https://www.python.org/downloads/
  echo Beim Installieren "Add python.exe to PATH" ankreuzen, dann diese Datei noch einmal starten.
  goto ende
)
where git >nul 2>&1 || (
  echo git fehlt — es holt beim ersten Mal die Datenbank flatgraph: https://git-scm.com/download/win
  goto ende
)

rem Laeuft partAtlas schon, wird kein zweites gestartet. Ist es eine andere Fassung als die auf der Platte (nach "git pull"),
rem wird das gesagt: das alte Fenster beenden (Strg+C) und diese Datei noch einmal starten. Beendet wird hier nichts von selbst.
set "LAEUFT="
for /f "usebackq delims=" %%v in (`powershell -NoProfile -Command "try { (Invoke-RestMethod -TimeoutSec 3 '%URL%/api/stand').version } catch { }"`) do set "LAEUFT=%%v"
for /f "tokens=2 delims==" %%v in ('findstr /b "VERSION" partatlas\version.py') do set "PLATTE=%%~v"
set "PLATTE=%PLATTE: =%"
set "PLATTE=%PLATTE:"=%"
if defined LAEUFT (
  if "%LAEUFT%"=="%PLATTE%" (
    echo partAtlas %LAEUFT% laeuft schon: %URL%
    start "" "%URL%"
    goto ende
  )
  echo partAtlas %LAEUFT% laeuft noch, auf der Platte liegt %PLATTE%.
  echo Beende das alte partAtlas-Fenster mit Strg+C und starte diese Datei noch einmal.
  goto ende
)

rem Eigene Umgebung im Ordner .venv; neu installiert wird nur, wenn sich requirements.txt geaendert hat.
if not exist ".venv\Scripts\python.exe" (
  echo Python-Umgebung wird angelegt ...
  %PY% -m venv .venv || goto ende
)
set "STAND="
for /f "delims=" %%h in ('certutil -hashfile requirements.txt SHA256 ^| findstr /v ":"') do set "STAND=%%h"
set "ALT="
if exist ".venv\.stand" set /p ALT=<".venv\.stand"
if not "%STAND%"=="%ALT%" (
  echo Pakete werden installiert ^(einmalig, ein paar Minuten^) ...
  ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt || goto ende
  >".venv\.stand" echo %STAND%
)

rem Den Browser oeffnen, sobald der Server antwortet (im Hintergrund), dann partAtlas in diesem Fenster.
start "" /b powershell -NoProfile -WindowStyle Hidden -Command "for ($i = 0; $i -lt 80; $i++) { try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 '%URL%/' | Out-Null; Start-Process '%URL%'; break } catch { Start-Sleep -Milliseconds 500 } }"
echo partAtlas: %URL%   (beenden mit Strg+C)
".venv\Scripts\python.exe" -m partatlas

:ende
rem Das Fenster bleibt offen, damit eine Meldung zu lesen ist.
echo.
pause
