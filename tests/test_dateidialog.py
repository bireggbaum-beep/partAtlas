"""Der Dateidialog: immer nur einer, ein offener hält das Beenden nicht auf, Abbrechen und Antwort kommen richtig zurück."""
import sys
import threading
import time

import muster
from muster import check
from partatlas import dateidialog

if __name__ == "__main__":
    muster.zeitgrenze(60)
    py = sys.executable

    check("Antwort des Dialogs kommt zurück", dateidialog._lauf([py, "-c", "print('/tmp/x')"]) == "/tmp/x")
    check("Abbrechen im Dialog (nichts gewählt): None", dateidialog._lauf([py, "-c", "pass"]) is None)
    check("Dialog mit Fehlercode: None", dateidialog._lauf([py, "-c", "print('/tmp/x'); raise SystemExit(1)"]) is None)

    # Ein Dialog, der offen bleibt, bis jemand ihn schliesst.
    ergebnis = []
    t = threading.Thread(target=lambda: ergebnis.append(dateidialog._lauf([py, "-c", "import time; time.sleep(60)"])))
    t.start()
    for _ in range(100):
        if dateidialog._offen is not None:
            break
        time.sleep(0.05)
    try:
        dateidialog._lauf([py, "-c", "pass"])
        zweiter = "kein Fehler"
    except dateidialog.DialogOffen:
        zweiter = "DialogOffen"
    check("Ein zweiter Dialog, solange einer offen ist, wird abgelehnt statt dahinter zu hängen", zweiter == "DialogOffen")
    dateidialog.abbrechen()
    t.join(10)
    check("abbrechen() beendet den offenen Dialog, der Thread kommt zurück (sonst hielte er das Beenden auf)",
          not t.is_alive() and ergebnis == [None])
    check("Danach geht wieder ein Dialog", dateidialog._lauf([py, "-c", "print('/tmp/y')"]) == "/tmp/y")
    muster.ende()
