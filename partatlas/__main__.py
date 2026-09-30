import logging
import os

import uvicorn

from .main import erstelle_app

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    port = int(os.environ.get("PARTATLAS_PORT", "8765"))
    print(f"partAtlas: http://127.0.0.1:{port}")
    # Nur localhost, solange es kein Passwort gibt (KONZEPT §2).
    uvicorn.run(erstelle_app(), host="127.0.0.1", port=port, log_level="warning")
