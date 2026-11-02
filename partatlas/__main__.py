import logging
import logging.handlers
import os
import sys
import threading

import uvicorn

import time

from . import dateidialog, einmal
from .bestand import standard_ort
from .main import erstelle_app
from .version import VERSION

if __name__ == "__main__":
    FORMAT = "%(asctime)s %(threadName)s %(name)s %(levelname)s %(message)s"
    logging.basicConfig(level=logging.INFO, format=FORMAT)
    # Dasselbe zusätzlich in eine Datei im Bestand: wer partAtlas per Doppelklick oder im Hintergrund startet, sieht die Konsole nicht,
    # und ein Tester braucht für eine Fehlermeldung etwas, das er schicken kann. Klein gehalten (3 × 4 MB).
    ort = os.path.abspath(os.environ.get("PARTATLAS_BESTAND") or standard_ort())
    os.makedirs(ort, exist_ok=True)
    datei = logging.handlers.RotatingFileHandler(os.path.join(ort, "partatlas.log"), maxBytes=4 << 20, backupCount=2, encoding="utf-8")
    datei.setFormatter(logging.Formatter(FORMAT))
    logging.getLogger().addHandler(datei)
    # Was in einem Thread schiefgeht (das Einlesen läuft in einem), landet sonst nur auf der Konsole — die der Anwender nicht sieht.
    threading.excepthook = lambda a: logging.getLogger("partatlas").error(
        "Unbehandelter Fehler im Thread %s", a.thread.name if a.thread else "?", exc_info=(a.exc_type, a.exc_value, a.exc_traceback))
    sys.excepthook = lambda t, v, tb: logging.getLogger("partatlas").critical("Unbehandelter Fehler", exc_info=(t, v, tb))
    logging.getLogger("partatlas").info("partAtlas %s gestartet, Bestand %s", VERSION, ort)
    port = int(os.environ.get("PARTATLAS_PORT", "8765"))
    # Läuft schon einer mit diesem Bestand (auch auf einem anderen Port): ihn zeigen statt einen zweiten zu starten, der nur „belegt“ sähe.
    schon = einmal.laufender(ort)
    if schon:
        einmal.dorthin(schon)
        sys.exit(0)
    print(f"partAtlas: http://127.0.0.1:{port}")
    # Nur localhost, solange es kein Passwort gibt (KONZEPT §2).
    # log_config=None: uvicorn richtet sein eigenes Protokoll nicht ein; seine Fehlermeldungen (etwa eine Anfrage, die mit 500 endet) gehen
    # dann wie alles andere in die Datei.
    app = erstelle_app(im_hintergrund=True, fassung_pruefen=True)

    class Server(uvicorn.Server):
        async def startup(self, sockets=None):
            await super().startup(sockets)
            # Erst hier ist der Port offen. Vorher stand „nimmt Anfragen an“ schon vor dem Öffnen — auch wenn der Port belegt war und
            # partAtlas gleich danach wieder endete (Protokoll des Anwenders, 7.10.2026).
            if self.started:
                logging.getLogger("partatlas").info("partAtlas nimmt Anfragen an: http://127.0.0.1:%d", port)
        def handle_exit(self, sig, frame):
            # Beim Beenden wartet uvicorn, bis jede Verbindung von selbst endet — die Live-Meldungen eines offenen Tabs (/api/live) enden
            # nie. partAtlas liess sich dann nur abschiessen (nachgestellt am 7.10.2026), und das Abbrechen eines laufenden Einlesens wurde
            # gar nicht erst erreicht. Darum zuerst die Live-Verbindungen schliessen; die Zeitgrenze unten fängt ab, was sonst noch hängt.
            app.state.verteiler.beenden()
            # Ein offener Ordnerdialog hält sonst den Prozess am Leben: Python wartet auf den Thread, der auf ihn wartet.
            dateidialog.abbrechen()
            super().handle_exit(sig, frame)

    server = Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", log_config=None, timeout_graceful_shutdown=5))

    def wache():
        """Ist der Bestand offen: vermerken, wo partAtlas läuft. Hat ihn ein anderer (beide fast gleichzeitig gestartet): den zeigen und enden,
        statt als leere Seite stehen zu bleiben."""
        st = app.state.oeffnen_stand
        while not (st["bereit"] or st["fehler"]):
            time.sleep(0.2)
        if st["bereit"]:
            einmal.eintragen(ort, port, VERSION)
        elif "BestandBelegt" in st["fehler"]:
            for _ in range(25):                 # der andere trägt sich erst ein, wenn er offen ist
                schon = einmal.laufender(ort)
                if schon:
                    einmal.dorthin(schon)
                    break
                time.sleep(0.2)
            else:
                print("partAtlas hat diesen Bestand schon offen (in einem anderen Fenster oder Terminal). Dieser Start endet.")
            server.should_exit = True

    threading.Thread(target=wache, name="Bestand belegt?", daemon=True).start()
    try:
        server.run()
    except KeyboardInterrupt:
        pass            # Strg+C: uvicorn wirft es nach dem geordneten Beenden noch einmal; als „Unbehandelter Fehler“ sah das nach Absturz aus
    finally:
        einmal.austragen(ort)
