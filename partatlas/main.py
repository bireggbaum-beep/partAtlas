"""
Der Server: ein Prozess, ein Bestand, Oberfläche im Browser (KONZEPT §2).

    python -m partatlas            http://127.0.0.1:8765

Ohne Passwort lauscht er nur auf 127.0.0.1 — lieber unbrauchbar als offen
(wie pDMS). Zugriff aus dem Heimnetz kommt mit dem Passwort (offen).
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import slicer
from .bestand import Bestand
from .katalog import Katalog, KatalogFehler
from .live import Verteiler
from .scan import Scanner
from .version import VERSION

WEB = os.path.join(os.path.dirname(__file__), "web")
log = logging.getLogger("partatlas")


def erstelle_app(bestand_pfad=None, scan_beim_start=True, prozesse=None):
    verteiler = Verteiler()
    zustand = {}

    @asynccontextmanager
    async def leben(app):
        verteiler.binden(asyncio.get_running_loop())
        b = Bestand(bestand_pfad, bei_aenderung=verteiler.graph)
        k = Katalog(b)
        s = Scanner(b, k, melden=lambda st: verteiler.senden("scan", st), prozesse=prozesse)
        zustand.update(bestand=b, katalog=k, scanner=s)
        if scan_beim_start and k.wurzeln():
            s.starten()
        yield
        s.warten(30)
        b.schliessen()

    app = FastAPI(title="partAtlas", version=VERSION, lifespan=leben)
    app.state.zustand = zustand

    def K():
        return zustand["katalog"]

    # -- Wache: schreibende Anfragen nur von der eigenen Oberfläche. Ein
    # fremder Tab im selben Browser könnte sonst Dateien umbenennen oder
    # löschen (pDMS: zugang.wache).
    @app.middleware("http")
    async def wache(request: Request, call_next):
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            seite = request.headers.get("sec-fetch-site")
            herkunft = request.headers.get("origin")
            if seite and seite not in ("same-origin", "none"):
                return JSONResponse({"fehler": "Fremde Herkunft"}, status_code=403)
            if herkunft and urlsplit(herkunft).netloc != request.headers.get("host"):
                return JSONResponse({"fehler": "Fremde Herkunft"}, status_code=403)
        return await call_next(request)

    @app.exception_handler(KatalogFehler)
    async def katalogfehler(request, e):
        return JSONResponse({"fehler": str(e)}, status_code=400)

    @app.exception_handler(KeyError)
    async def fehlt(request, e):
        return JSONResponse({"fehler": f"Nicht gefunden: {e}"}, status_code=404)

    # ---------------------------------------------------------------- Stand

    @app.get("/api/stand")
    def stand():
        return {"version": VERSION, "bestand": zustand["bestand"].wurzel,
                "scan": zustand["scanner"].status}

    @app.get("/api/live")
    async def live():
        return StreamingResponse(verteiler.strom(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache"})

    # ---------------------------------------------------------------- Wurzeln und Scan

    @app.get("/api/wurzeln")
    def wurzeln():
        return [{"id": k, **v} for k, v in K().wurzeln().items()]

    @app.post("/api/wurzeln")
    async def wurzel_neu(request: Request):
        daten = await request.json()
        wid = K().wurzel_hinzufuegen(daten.get("pfad", ""))
        zustand["scanner"].starten()
        return {"id": wid}

    @app.delete("/api/wurzeln/{wid}")
    def wurzel_weg(wid: str):
        K().wurzel_entfernen(wid)
        return {"ok": True}

    @app.post("/api/scan")
    def scan():
        return {"gestartet": zustand["scanner"].starten()}

    # ---------------------------------------------------------------- Modelle

    @app.get("/api/modelle")
    def modelle(q: str = "", tag: str = "", ordner: str = "", format: str = "", ansicht: str = "alle"):
        return K().modelle(suche=q or None, tag=tag or None, ordner=ordner or None,
                           fmt=format or None, ansicht=ansicht)

    @app.get("/api/zaehler")
    def zaehler():
        k = K()
        alle = k.modelle()
        formate = {}
        for m in alle:
            formate[m["format"]] = formate.get(m["format"], 0) + 1
        return {
            "alle": len(alle), "favoriten": sum(m["favorit"] for m in alle),
            "duplikate": sum(m["duplikat"] for m in alle), "fehlt": sum(m["fehlt"] for m in alle),
            "unlesbar": sum(m["fehler"] for m in alle),
            "papierkorb": len(k.modelle(ansicht="papierkorb")), "formate": formate,
        }

    @app.get("/api/modelle/{mid}")
    def modell(mid: str):
        k = K()
        daten = k.modell(mid)
        k.angesehen(mid)
        return daten

    @app.patch("/api/modelle/{mid}")
    async def modell_aendern(mid: str, request: Request):
        daten = await request.json()
        k = K()
        if "name" in daten:
            k.umbenennen(mid, daten.pop("name"))
        k.modell_aendern(mid, daten)
        return k.modell(mid)

    @app.post("/api/modelle/{mid}/tags")
    async def tag_neu(mid: str, request: Request):
        daten = await request.json()
        return {"tag": K().tag_setzen(mid, daten.get("tag", ""))}

    @app.delete("/api/modelle/{mid}/tags/{tag}")
    def tag_weg(mid: str, tag: str):
        K().tag_loesen(mid, tag)
        return {"ok": True}

    @app.get("/api/modelle/{mid}/loeschen")
    def loeschvorschau(mid: str):
        return K().loeschvorschau(mid)

    @app.post("/api/modelle/{mid}/loeschen")
    def loeschen(mid: str):
        K().loeschen(mid)
        return {"ok": True}

    @app.post("/api/modelle/{mid}/wiederherstellen")
    def wiederherstellen(mid: str):
        K().wiederherstellen(mid)
        return {"ok": True}

    @app.post("/api/papierkorb/leeren")
    def papierkorb_leeren():
        return {"geloescht": K().papierkorb_leeren()}

    @app.get("/api/tags")
    def tags():
        return K().tags()

    @app.get("/api/ordner")
    def ordner():
        return K().ordnerbaum()

    @app.get("/api/vorschau/{h}.png")
    def vorschaubild(h: str):
        if not all(c in "0123456789abcdef" for c in h) or len(h) != 64:
            raise HTTPException(404)
        pfad = zustand["bestand"].vorschau_pfad(h)
        if not os.path.exists(pfad):
            raise HTTPException(404)
        return FileResponse(pfad, media_type="image/png",
                            headers={"Cache-Control": "max-age=31536000, immutable"})

    # ---------------------------------------------------------------- Slicer

    @app.get("/api/slicer")
    def slicer_liste():
        return slicer.alle(zustand["bestand"].einstellungen())

    @app.post("/api/modelle/{mid}/slicer")
    async def slicer_oeffnen(mid: str, request: Request):
        daten = await request.json()
        erlaubt = {s["pfad"] for s in slicer.alle(zustand["bestand"].einstellungen())}
        programm = daten.get("pfad")
        if programm not in erlaubt:
            raise KatalogFehler("Diesen Slicer kennt partAtlas nicht.")
        m = K().modell(mid)
        datei = next((o["absolut"] for o in m["orte"] if o["absolut"] and os.path.exists(o["absolut"])), None)
        if not datei:
            raise KatalogFehler("Die Datei ist nicht da.")
        slicer.oeffnen(programm, datei)
        return {"ok": True}

    # ---------------------------------------------------------------- Oberfläche

    @app.get("/")
    def start():
        return FileResponse(os.path.join(WEB, "index.html"), headers={"Cache-Control": "no-cache"})

    app.mount("/web", StaticFiles(directory=WEB), name="web")
    return app
