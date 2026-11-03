"""einstellungen.json: zwei Threads, die gleichzeitig verschiedene Einstellungen schreiben, nehmen sich nichts weg (Einlesen und Oberfläche)."""
import os
import tempfile
import threading

import muster
from muster import check
from partatlas.bestand import Bestand

if __name__ == "__main__":
    b = Bestand(os.path.join(tempfile.mkdtemp(), "bestand"))
    try:
        def schreiber(schluessel, n):
            for i in range(n):
                b.einstellungen_setzen(**{schluessel: i})
        faeden = [threading.Thread(target=schreiber, args=(f"k{j}", 150)) for j in range(4)]
        for f in faeden:
            f.start()
        for f in faeden:
            f.join()
        e = b.einstellungen()
        check("Vier Threads schreiben je ihren Schlüssel: am Ende steht jeder mit seinem letzten Wert", all(e.get(f"k{j}") == 149 for j in range(4)))
    finally:
        b.schliessen()
    muster.ende()
