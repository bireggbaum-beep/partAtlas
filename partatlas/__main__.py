import logging
import logging.handlers
import os

import uvicorn

from .bestand import standard_ort
from .main import erstelle_app
from .version import VERSION

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    # Dasselbe zusätzlich in eine Datei im Bestand: wer partAtlas per Doppelklick oder im Hintergrund startet, sieht die Konsole nicht,
    # und ein Tester braucht für eine Fehlermeldung etwas, das er schicken kann. Klein gehalten (3 × 1 MB).
    ort = os.path.abspath(os.environ.get("PARTATLAS_BESTAND") or standard_ort())
    os.makedirs(ort, exist_ok=True)
    datei = logging.handlers.RotatingFileHandler(os.path.join(ort, "partatlas.log"), maxBytes=1 << 20, backupCount=2, encoding="utf-8")
    datei.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
    logging.getLogger().addHandler(datei)
    logging.getLogger("partatlas").info("partAtlas %s gestartet, Bestand %s", VERSION, ort)
    port = int(os.environ.get("PARTATLAS_PORT", "8765"))
    print(f"partAtlas: http://127.0.0.1:{port}")
    # Nur localhost, solange es kein Passwort gibt (KONZEPT §2).
    uvicorn.run(erstelle_app(), host="127.0.0.1", port=port, log_level="warning")
