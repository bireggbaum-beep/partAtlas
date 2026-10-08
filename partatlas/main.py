"""
Der Server: ein Prozess, ein Bestand, Oberfläche im Browser (KONZEPT §2).

    python -m partatlas            http://127.0.0.1:8765

Ohne Passwort lauscht er nur auf 127.0.0.1 — lieber unbrauchbar als offen
(wie pDMS). Zugriff aus dem Heimnetz kommt mit dem Passwort (offen).
"""
import asyncio
import functools
import json
import logging
import os
import platform
import re
import subprocess
import sys
import threading
import time
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

import numpy as np

from .eigene import Eigene
from . import aufraeumen, dateidialog, durchsuchen, formate, programme, sicherung, zuordnen
from .baugruppen import Baugruppen
from .bestand import Bestand
from .katalog import Katalog, KatalogFehler
from .live import Verteiler
from .scan import Scanner
from .stueckliste import PDF_STANDARD, Stueckliste
from .version import VERSION

WEB = os.path.join(os.path.dirname(__file__), "web")
log = logging.getLogger("partatlas")
LANGSAM_S = 3.0          # eine Anfrage, die so lange dauert, steht im Protokoll: so sieht man, was den Server aufhielt
BEENDEN_S = 10           # so lange wartet das Beenden auf ein abgebrochenes Einlesen
CLIENTFEHLER_MAX = 50    # Fehler aus dem Browser je Serverlauf, damit eine Fehlerschleife das Protokoll nicht füllt


async def json_koerper(request: Request):
    """Den Körper liest die Ereignisschleife; die Route selbst ist ein gewöhnliches `def` und läuft im Thread-Pool. Eine `async`-Route,
    die danach synchron arbeitet (Datenbank, Platte, FreeCAD, Dateidialog), hält die ganze Schleife an: alle Tabs, die Live-Meldungen,
    das Beenden. Ein leerer Körper ist ein leeres Objekt."""
    roh = await request.body()
    try:
        return json.loads(roh) if roh else {}
    except ValueError:
        raise HTTPException(400, "Kein gültiges JSON")


async def roh_koerper(request: Request):
    """Wie `json_koerper`, für Dateien und Bilder."""
    return await request.body()


def _startinfo(b, k, s):
    """Eine Zeile je Umstand, der später für die Fehlersuche gebraucht wird; schlägt etwas davon fehl, startet partAtlas trotzdem."""
    try:
        log.info("Umgebung: Python %s, %s, Prozessorkerne %s, Arbeiter für das Einlesen %s", platform.python_version(), platform.platform(),
                 os.cpu_count(), s.prozesse)
        einst = b.einstellungen()
        wurzeln = k.wurzeln()
        log.info("Katalog: %d Modelle, %d Dateien, %d Wurzelordner: %s", len(b.db.list_nodes("MODEL_ASSET", readonly=True)),
                 len(b.db.list_nodes("PART_GEOMETRY", readonly=True)), len(wurzeln), ", ".join(w["pfad"] for w in wurzeln.values()) or "—")
        log.info("Einstellungen: Beim Start einlesen=%s, FCStd über FreeCAD=%s", einst.get("scan_beim_start", False), einst.get("fcstd_freecad"))
        log.info("Ausstehend im Bestand: %d Vorschaubilder, %d Umwandlungen über FreeCAD", len(k.ausstehende_vorschauen()), len(k.ausstehende_cad()))
    except Exception:
        log.exception("Angaben zum Start liessen sich nicht ermitteln")


def _dateien(pfad):
    return sum(len(fs) for _, _, fs in os.walk(pfad))


def erstelle_app(bestand_pfad=None, scan_beim_start=None, prozesse=None, im_hintergrund=False):
    """`im_hintergrund`: der Port ist sofort offen und der Bestand wird in einem Thread geöffnet; bis er bereit ist, zeigt „/“ eine
    Warteseite und /api/* antwortet 503. Unter Windows dauerte das Öffnen bei 8 600 Modellen 47 s, in denen die Seite nicht erreichbar
    war (Protokoll des Anwenders, 8.10.2026). Die Tests im selben Prozess öffnen weiter vorher — sie fragen gleich danach ab."""
    verteiler = Verteiler()
    zustand = {}
    oeffnen_stand = {"bereit": False, "fehler": None}

    def oeffnen():
        t0 = time.monotonic()
        b = Bestand(bestand_pfad, bei_aenderung=verteiler.graph)
        # Die Dauer und die Zahl der Dateien belegen, ob es am Lesen vieler kleiner Dateien liegt (Virenscanner unter Windows).
        log.info("Datenbank gelesen in %.1f s (%d Dateien)", time.monotonic() - t0, _dateien(os.path.join(b.wurzel, "datenbank")))
        # Vor allem anderen, auch vor dem Nachziehen alter Bestände in Katalog(): der Stand, mit dem diese Sitzung beginnt.
        try:
            sicherung.sichern(b, "start")
        except OSError as e:
            log.error("Keine Sicherung beim Start möglich: %s", e)
        k = Katalog(b)
        s = Scanner(b, k, melden=lambda st: verteiler.senden("scan", st), melden_worker=lambda st: verteiler.senden("worker", st), prozesse=prozesse)
        bg = Baugruppen(k)
        zustand.update(bestand=b, katalog=k, scanner=s, baugruppen=bg, eigene=Eigene(k, bg))
        s.schleifenprobe = verteiler.antwortzeit
        _startinfo(b, k, s)
        # Beim Start einlesen: Einstellung des Anwenders, Vorgabe AUS. Eine grosse Library auf einer langsamen Platte rattert sonst bei jedem Start;
        # wer es will, schaltet es ein oder liest mit ⟳ bei der Bibliothek ein. Ausdrücklich übergeben (Tests) geht vor.
        beim_start = bool(b.einstellungen().get("scan_beim_start", False)) if scan_beim_start is None else scan_beim_start
        if beim_start and k.wurzeln():
            log.info("Beim Start: ganzes Einlesen (Einstellung „Beim Start einlesen“)")
            s.starten()
        elif k.wurzeln() and s.hat_offenes():
            log.info("Beim Start: Hintergrundlauf für das, was noch aussteht (ohne die Ordner zu durchsuchen)")
            # Auch ohne „Beim Start einlesen“: was im Hintergrund noch aussteht (Vorschaubilder, FreeCAD), wird fortgesetzt — ohne die Ordner
            # zu durchsuchen. Die Warteschlange ist der Zustand „ausstehend“ im Bestand, sie überlebt Abbruch und Neustart.
            s.starten(nur_cad=True)
        # Ohne `im_hintergrund` ist der Port hier noch nicht offen; „nimmt Anfragen an“ schreibt __main__, wenn er es wirklich ist.
        oeffnen_stand["bereit"] = True
        log.info("Katalog geöffnet")

    def oeffnen_sicher():
        try:
            oeffnen()
        except Exception as e:
            oeffnen_stand["fehler"] = f"{type(e).__name__}: {e}"
            log.exception("Der Bestand liess sich nicht öffnen")

    @asynccontextmanager
    async def leben(app):
        verteiler.binden(asyncio.get_running_loop())
        if im_hintergrund:
            faden = threading.Thread(target=oeffnen_sicher, name="Bestand öffnen", daemon=True)
            faden.start()
        else:
            faden = None
            oeffnen()
        yield
        if faden:
            faden.join()           # flatgraph lässt sich beim Lesen nicht unterbrechen; danach sauber schliessen
        if not oeffnen_stand["bereit"]:
            log.info("partAtlas beendet (Bestand war nicht geöffnet)")
            return
        b, s = zustand["bestand"], zustand["scanner"]
        log.info("partAtlas wird beendet (Einlesen läuft: %s, Phase „%s“)", s.status.get("laeuft"), s.status.get("phase"))
        # Beenden bricht ein laufendes Einlesen ab (was fertig ist, steht in der Datenbank), statt bis zu 30 s darauf zu warten: sonst
        # reagiert partAtlas auf Strg+C scheinbar nicht — vor allem, wenn FreeCAD an einer Datei arbeitet oder hängt — und FreeCAD bliebe
        # beim harten Beenden als eigener Prozess zurück.
        s.abbrechen()
        if not s.warten(BEENDEN_S):
            # Datenverlust droht nicht: was das Einlesen danach noch schreiben will, scheitert an der geschlossenen Datenbank, und jede
            # Transaktion steht ganz oder gar nicht auf der Platte. Es steht nur da, damit man sieht, wenn das Abbrechen nicht greift.
            log.warning("Das Einlesen hat nicht binnen %s s aufgehört (Phase „%s“); partAtlas wird trotzdem beendet", BEENDEN_S, s.status.get("phase"))
        b.schliessen()
        log.info("partAtlas beendet")

    app = FastAPI(title="partAtlas", version=VERSION, lifespan=leben)
    app.state.zustand = zustand
    app.state.verteiler = verteiler

    def K():
        return zustand["katalog"]

    def am_stueck(f):
        """Eine Abfrage, die die Datenbank in vielen Einzelschritten liest (Tags je Tag, Papierkorb je Modell …), nimmt die Sperre von
        flatgraph EINMAL (Transaktion ohne Schreiben, VERTRAG §3.1). Sonst wartet jeder Einzelschritt auf eine Lücke zwischen zwei
        Schreibgruppen eines Massenlöschens oder Einlesens: Tags und Zähler warteten 14–18 s (Protokoll des Anwenders, 8.10.2026).
        Nur für Abfragen ohne Plattenarbeit — wer Bilder ausliefert, hielte sonst das Schreiben auf."""
        @functools.wraps(f)
        def innen(*args, **kwargs):
            with K().db.transaction():
                return f(*args, **kwargs)
        return innen

    def B():
        return zustand["baugruppen"]

    def E():
        return zustand["eigene"]

    # -- Wache: schreibende Anfragen nur von der eigenen Oberfläche. Ein
    # fremder Tab im selben Browser könnte sonst Dateien umbenennen oder
    # löschen (pDMS: zugang.wache).
    gesehene_browser, clientfehler = set(), [0]

    @app.middleware("http")
    async def protokoll(request: Request, call_next):
        """Was im Protokoll stehen soll, damit sich nachvollziehen lässt, was passiert ist, ohne dass jemand ein Terminal ansieht: jeder neue
        Browser (Name und Fassung), jede Anfrage, die etwas ändert (Weg, Status, Dauer — ohne Inhalt), und jede, die langsam ist."""
        t0 = time.monotonic()
        ua = request.headers.get("user-agent", "")
        if ua and ua not in gesehene_browser:
            gesehene_browser.add(ua)
            log.info("Seite geöffnet von: %s", ua)
        try:
            antwort = await call_next(request)
        except Exception as e:
            # Den ganzen Stapel schreibt uvicorn selbst ins Protokoll; hier steht, welche Anfrage es war.
            log.error("Anfrage %s %s ist mit einem Fehler abgebrochen: %s: %s", request.method, request.url.path, type(e).__name__, e)
            raise
        dauer = time.monotonic() - t0
        if dauer >= LANGSAM_S:
            log.warning("Langsame Anfrage: %s %s dauerte %.1f s (Status %s)", request.method, request.url.path, dauer, antwort.status_code)
        elif request.method not in ("GET", "HEAD", "OPTIONS"):
            log.info("Anfrage %s %s → %s (%.2f s)", request.method, request.url.path, antwort.status_code, dauer)
        return antwort

    @app.middleware("http")
    async def bereit(request: Request, call_next):
        if oeffnen_stand["bereit"] or request.url.path.startswith("/web/") or request.url.path == "/api/clientfehler":
            return await call_next(request)
        if request.url.path == "/":
            # 200, nicht 503: start.sh erkennt am Startpunkt, dass partAtlas läuft, und startet keinen zweiten Prozess.
            return FileResponse(os.path.join(WEB, "oeffnen.html"), headers={"Cache-Control": "no-store"})
        fehler = oeffnen_stand["fehler"]
        return JSONResponse({"fehler": f"Der Bestand liess sich nicht öffnen: {fehler}" if fehler else "Der Bestand wird geöffnet …",
                             "oeffnet": not fehler, "version": VERSION}, status_code=503, headers={"Retry-After": "1"})

    @app.post("/api/clientfehler")
    async def clientfehler_melden(request: Request):
        """Ein Fehler in der Oberfläche (JavaScript) kommt ins Protokoll: im Browser sieht ihn sonst nur, wer die Konsole offen hat."""
        if clientfehler[0] < CLIENTFEHLER_MAX:
            clientfehler[0] += 1
            try:
                d = await request.json()
            except ValueError:
                d = {}
            log.warning("Fehler im Browser: %s (%s)", str(d.get("meldung", ""))[:500], str(d.get("ort", ""))[:200])
        return {"ok": True}

    @app.middleware("http")
    async def wache(request: Request, call_next):
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            seite = request.headers.get("sec-fetch-site")
            herkunft = request.headers.get("origin")
            if seite and seite not in ("same-origin", "none"):
                log.warning("Anfrage abgewiesen (fremde Herkunft %s): %s %s", seite, request.method, request.url.path)
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
                # Eine Kopie: der Scan-Thread trägt währenddessen Schlüssel ein, und das Umwandeln in JSON liefe sonst in „dictionary changed
                # size during iteration“. dict() kopiert in einem Zug.
                "scan": dict(zustand["scanner"].status), "worker": dict(zustand["scanner"].worker.status), "zuletzt_eingelesen": zustand["bestand"].einstellungen().get("zuletzt_eingelesen")}

    @app.get("/api/live")
    async def live():
        return StreamingResponse(verteiler.strom(lambda: [("scan", dict(zustand["scanner"].status)), ("worker", dict(zustand["scanner"].worker.status))]), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache"})

    # ---------------------------------------------------------------- Wurzeln und Scan

    def scan_starten():
        """Startet das Einlesen und gibt die Nummer des Laufs zurück, der die Änderung sieht — der Einlesen-Dialog folgt genau ihm."""
        lauf = zustand["scanner"].naechster_lauf()
        zustand["scanner"].starten()
        return lauf

    @app.get("/api/wurzeln")
    @am_stueck
    def wurzeln():
        return [{"id": k, **v} for k, v in K().wurzeln().items()]

    @app.post("/api/wurzeln")
    def wurzel_neu(daten: dict = Depends(json_koerper)):
        wid = K().wurzel_hinzufuegen(daten.get("pfad", ""))
        return {"id": wid, "lauf": scan_starten()}

    @app.post("/api/wurzeln/waehlen")
    def wurzel_waehlen():
        """Der Ordnerdialog des Rechners; hinzugefügt wird erst mit POST /api/wurzeln.
        Mit „keinDialog“ weiss die Seite, dass sie den eigenen Ordnerbaum zeigen muss."""
        try:
            pfad = dateidialog.ordner_waehlen("Ordner mit 3D-Modellen auswählen")
        except dateidialog.KeinDialog:
            return {"keinDialog": True}
        if not pfad:
            return {"abgebrochen": True}
        modelle, vollstaendig = durchsuchen.zaehlen(pfad)
        return {"pfad": pfad, "modelle": modelle, "vollstaendig": vollstaendig}

    @app.post("/api/wurzeln/uebersicht")
    def wurzel_uebersicht(koerper: dict = Depends(json_koerper)):
        """Was ein Ordner mitbringt, bevor er eingelesen wird: Modelldateien je Format (wie in pDMS vor dem Hinzufügen)."""
        pfad = os.path.abspath(os.path.expanduser(koerper.get("pfad", "")))
        if not os.path.isdir(pfad):
            raise KatalogFehler(f"Kein Ordner: {pfad}")
        modelle, vollstaendig, je_format = durchsuchen.zaehlen_je_format(pfad)
        return {"pfad": pfad, "modelle": modelle, "vollstaendig": vollstaendig, "je_format": je_format}

    @app.get("/api/wurzeln/entfernt")
    @am_stueck
    def wurzeln_entfernt():
        return K().entfernte_wurzeln()

    @app.post("/api/wurzeln/{wid}/wiederherstellen")
    def wurzel_zurueck(wid: str):
        K().wurzel_wiederherstellen(wid)
        return {"ok": True, "lauf": scan_starten()}

    @app.delete("/api/wurzeln/{wid}")
    def wurzel_weg(wid: str):
        K().wurzel_entfernen(wid)
        return {"ok": True}

    @app.post("/api/scan")
    def scan():
        lauf = zustand["scanner"].naechster_lauf()
        return {"gestartet": zustand["scanner"].starten(), "lauf": lauf}

    @app.post("/api/scan/abbrechen")
    def scan_abbrechen():
        return {"abgebrochen": zustand["scanner"].abbrechen()}

    # ---------------------------------------------------------------- Modelle

    @app.get("/api/modelle")
    @am_stueck
    def modelle(q: str = "", tag: str = "", ordner: str = "", format: str = "", ansicht: str = "alle",
                sammlung: str = "", tags: str = "", material: str = "", leiste: bool = False):
        # tags und material als Komma-Liste: die Chips der Leiste, je mit ODER.
        liste = lambda s: [x for x in s.split(",") if x]
        erg = K().modelle(suche=q or None, tag=tag or None, ordner=ordner or None,
                          fmt=format or None, ansicht=ansicht, sammlung=sammlung or None,
                          tags=liste(tags), materialien=liste(material), leiste=leiste)
        # Selbst in JSON wandeln: FastAPIs Umwandlung (`jsonable_encoder`) brauchte bei 9 000 Treffern 0,7 s von 1,3 s, `json.dumps` 0,1 s.
        # Auf einem älteren Rechner sind das die Sekunden zwischen Klick und Liste (Messung vom 5.10.2026, siehe OFFEN.md).
        return Response(json.dumps(erg, ensure_ascii=False, default=lambda o: sorted(o) if isinstance(o, (set, frozenset)) else str(o)),
                        media_type="application/json")

    @app.post("/api/modelle/aenderungen")
    @am_stueck
    def aenderungen(koerper: dict = Depends(json_koerper)):
        """Während des Einlesens: statt der ganzen Liste nur die Modelle hinter diesen Verweisen (aus den Live-Meldungen), gefiltert wie
        /api/modelle (`filter`: dieselben Felder). „weg“: gehört nicht (mehr) in diese Ansicht. POST, weil es tausende Verweise sein können."""
        f = koerper.get("filter") or {}
        liste = lambda s: [x for x in (s or "").split(",") if x]
        erg = K().aenderungen(list(koerper.get("refs") or [])[:5000], suche=f.get("q") or None, tag=f.get("tag") or None,
                              ordner=f.get("ordner") or None, fmt=f.get("format") or None, ansicht=f.get("ansicht") or "alle",
                              sammlung=f.get("sammlung") or None, tags=liste(f.get("tags")), materialien=liste(f.get("material")))
        return Response(json.dumps(erg, ensure_ascii=False, default=lambda o: sorted(o) if isinstance(o, (set, frozenset)) else str(o)),
                        media_type="application/json")

    @app.get("/api/zaehler")
    @am_stueck
    def zaehler():
        k = K()
        alle = k.modelle()
        formate = {}
        for m in alle:
            formate[m["format"]] = formate.get(m["format"], 0) + 1
        return {
            "alle": len(alle), "favoriten": sum(m["favorit"] for m in alle),
            "duplikate": sum(m["duplikat"] for m in alle), "fehlt": sum(m["fehlt"] and not m["ohne_datei"] for m in alle),
            "unlesbar": sum(m["fehler"] for m in alle),
            "papierkorb": len(k.modelle(ansicht="papierkorb")), "formate": formate,
            "warteschlange": sum(m["warteschlange"] is not None for m in alle),
            "neu": len(k.modelle(ansicht="neu")),
        }

    @app.get("/api/modelle/{mid}")
    @am_stueck
    def modell(mid: str):
        k = K()
        daten = k.modell(mid)
        daten["baugruppen"] = B().verwendet_in(f"MODEL_ASSET/{mid}")
        return daten

    @app.patch("/api/modelle/{mid}")
    def modell_aendern(mid: str, daten: dict = Depends(json_koerper)):
        k = K()
        if "name" in daten:
            k.umbenennen(mid, daten.pop("name"))
        k.modell_aendern(mid, daten)
        return k.modell(mid)

    @app.post("/api/modelle/{mid}/tags")
    def tag_neu(mid: str, daten: dict = Depends(json_koerper)):
        return {"tag": K().tag_setzen(mid, daten.get("tag", ""))}

    @app.get("/api/materialien")
    def materialien():
        return K().materialien()

    @app.post("/api/modelle/{mid}/material")
    def material_neu(mid: str, daten: dict = Depends(json_koerper)):
        k = K()
        with k.db.transaction():
            return {"material": k.material_vorsehen(mid, daten.get("material", ""))}

    @app.delete("/api/modelle/{mid}/material/{name}")
    def material_weg(mid: str, name: str):
        K().material_loesen(mid, name)
        return {"ok": True}

    @app.delete("/api/modelle/{mid}/tags/{tag}")
    def tag_weg(mid: str, tag: str):
        K().tag_loesen(mid, tag)
        return {"ok": True}

    @app.get("/api/modelle/{mid}/loeschen")
    def loeschvorschau(mid: str):
        return K().loeschvorschau(mid)

    @app.post("/api/modelle/{mid}/loeschen")
    def loeschen(mid: str, d: dict = Depends(json_koerper)):
        # Ohne Körper: nur das Modell. Mit {"tags": [...], "sammlungen": [...]}:
        # was nur an ihm hing, auf Wunsch mit.
        fehler = K().loeschen_mit([mid], d.get("tags") or (), d.get("sammlungen") or ())
        if fehler:
            raise KatalogFehler(fehler[0]["fehler"])
        return {"ok": True}

    @app.post("/api/modelle/{mid}/wiederherstellen")
    def wiederherstellen(mid: str):
        K().wiederherstellen(mid)
        return {"ok": True}

    @app.post("/api/modelle/{mid}/ohne_datei")
    def ohne_datei(mid: str, d: dict = Depends(json_koerper)):
        K().ohne_datei(mid, d.get("an", True))
        return {"ok": True}

    @app.post("/api/fehlende/suchen")
    def fehlende_suchen(koerper: dict = Depends(json_koerper)):
        r = K().fehlende_suchen(koerper.get("pfad", ""))
        # Liegt der Ordner schon im Katalog, verbindet der Scan die Treffer am Inhalt.
        if r["treffer"] and r["wurzel"]:
            zustand["scanner"].starten()
        return r

    @app.get("/api/modelle/{mid}/endgueltig")
    def endgueltig_vorschau(mid: str):
        return K().endgueltig_vorschau(mid)

    @app.post("/api/modelle/{mid}/endgueltig")
    def endgueltig(mid: str, d: dict = Depends(json_koerper)):
        # Die Tippbestätigung prüft auch der Server: ein Aufruf ohne sie
        # (ein Skript, ein verirrter Klick) entfernt nichts.
        if str(d.get("bestaetigung", "")).strip().lower() != "entfernen":
            raise KatalogFehler("Zum endgültigen Entfernen „entfernen“ eintippen.")
        K().endgueltig_entfernen(mid)
        verteiler.senden("neu_laden", {})
        return {"ok": True}


    # Netz für die 3D-Ansicht: Dreiecke als float32, little endian, 9 Werte
    # je Dreieck. Ausgedünnt, damit ein Modell mit 2 Mio. Dreiecken nicht
    # 72 MB in den Browser schiebt — für die Ansicht reichen 200 000.
    MAX_ANZEIGE = 200_000

    @app.get("/api/modelle/{mid}/netz")
    def netz(mid: str):
        m = K().modell(mid)
        datei = next((o["absolut"] for o in m["orte"] if o["absolut"] and os.path.exists(o["absolut"])), None)
        if not datei:
            raise HTTPException(404, "Datei nicht da")
        if formate.format_von(datei) in formate.OHNE_NETZ:
            # STEP: das Netz, das FreeCAD beim Einlesen geschrieben hat; ohne es gibt es nichts zu zeigen.
            datei = zustand["bestand"].netz_pfad(m["hash"])
            if not os.path.exists(datei):
                raise HTTPException(422, "Keine Geometrie")
        try:
            a = formate.analysiere(datei, mit_netz=True)
        except formate.FormatFehler as e:
            raise HTTPException(422, str(e))
        if a.netz is None or len(a.netz) == 0:
            raise HTTPException(422, "Keine Geometrie")
        n = a.netz
        if len(n) > MAX_ANZEIGE:
            n = n[np.random.default_rng(0).choice(len(n), MAX_ANZEIGE, replace=False)]
        return Response(np.ascontiguousarray(n, dtype="<f4").tobytes(), media_type="application/octet-stream",
                        headers={"X-Dreiecke": str(a.dreiecke), "Cache-Control": "no-cache"})

    # ---------------------------------------------------------------- Sammlungen

    @app.get("/api/sammlungen")
    @am_stueck
    def sammlungen():
        return K().sammlungen()

    @app.post("/api/sammlungen")
    def sammlung_neu(d: dict = Depends(json_koerper)):
        return {"id": K().sammlung_anlegen(d.get("name", ""), d.get("modelle", []))}

    @app.patch("/api/sammlungen/{sid}")
    def sammlung_umbenennen(sid: str, koerper: dict = Depends(json_koerper)):
        K().sammlung_umbenennen(sid, koerper.get("name", ""))
        return {"ok": True}

    @app.delete("/api/sammlungen/{sid}")
    def sammlung_loeschen(sid: str):
        K().sammlung_loeschen(sid)
        return {"ok": True}

    @app.post("/api/sammlungen/{sid}/modelle")
    def sammlung_dazu(sid: str, koerper: dict = Depends(json_koerper)):
        K().zur_sammlung(sid, koerper.get("modelle", []))
        return {"ok": True}

    @app.delete("/api/sammlungen/{sid}/modelle/{mid}")
    def sammlung_weg(sid: str, mid: str):
        K().aus_sammlung(sid, mid)
        return {"ok": True}

    @app.put("/api/sammlungen/{sid}/reihenfolge")
    def sammlung_ordnen(sid: str, koerper: dict = Depends(json_koerper)):
        K().sammlung_ordnen(sid, koerper.get("modelle", []))
        return {"ok": True}

    # ---------------------------------------------------------------- Warteschlange

    @app.get("/api/warteschlange")
    @am_stueck
    def warteschlange():
        return K().warteschlange()

    @app.post("/api/warteschlange")
    def warteschlange_dazu(koerper: dict = Depends(json_koerper)):
        for mid in koerper.get("modelle", []):
            K().in_warteschlange(mid)
        return {"ok": True}

    @app.delete("/api/warteschlange/{mid}")
    def warteschlange_weg(mid: str):
        K().aus_warteschlange(mid)
        return {"ok": True}

    @app.put("/api/warteschlange")
    def warteschlange_ordnen(koerper: dict = Depends(json_koerper)):
        K().warteschlange_ordnen(koerper.get("modelle", []))
        return {"ok": True}

    # ---------------------------------------------------------------- Ordner, Verschieben, Hochladen

    @app.get("/api/durchsuchen")
    def durchsuchen_route(pfad: str = ""):
        try:
            return durchsuchen.auflisten(pfad or None)
        except (FileNotFoundError, NotADirectoryError):
            raise KatalogFehler(f"Kein Ordner: {pfad}")

    @app.get("/api/verzeichnisse")
    def verzeichnisse():
        return K().verzeichnisse()

    @app.post("/api/verzeichnisse")
    def verzeichnis_neu(d: dict = Depends(json_koerper)):
        return {"id": K().ordner_anlegen(d.get("eltern", ""), d.get("name", ""))}

    @app.post("/api/modelle/{mid}/verschieben")
    def verschieben(mid: str, koerper: dict = Depends(json_koerper)):
        K().verschieben(mid, koerper.get("ordner", ""))
        return {"ok": True}

    @app.post("/api/hochladen")
    def hochladen(ordner: str, name: str, unterordner: str = "", roh: bytes = Depends(roh_koerper)):
        # Seit 0.50 keine Bedienung mehr (KONZEPT §3.4); bleibt für den späteren Ordnerbrowser.
        neu = K().hochladen(ordner, name, roh, unterordner)
        return {"dateien": len(neu), "lauf": scan_starten()}

    @app.get("/api/archive")
    def archive():
        return K().archive()

    @app.post("/api/archive/entpacken")
    def archiv_entpacken(d: dict = Depends(json_koerper)):
        ergebnis = K().archiv_entpacken(d.get("id", ""))
        return {**ergebnis, "lauf": scan_starten()}

    # ---------------------------------------------------------------- Bilder des Anwenders

    def _bild_antwort(pfad, klein=False):
        if not pfad or not os.path.exists(pfad):
            raise HTTPException(404)
        if klein:           # ?t=1: die kleine Fassung für Kacheln und Zeilen, ein paar KB statt MB
            pfad = zustand["bestand"].thumb(pfad)
        art = "image/webp" if pfad.endswith(".webp") else "image/png"
        # Die Kennung ist der Hash des Inhalts: ein anderes Bild hat eine andere Adresse.
        return FileResponse(pfad, media_type=art, headers={"Cache-Control": "max-age=31536000, immutable"})

    @app.get("/api/modelle/{mid}/bild")
    def titelbild(mid: str, t: int = 0):
        return _bild_antwort(K().bild_pfad(mid), bool(t))

    @app.get("/api/modelle/{mid}/bilder/{k}")
    def bild(mid: str, k: str, t: int = 0):
        return _bild_antwort(K().bild_pfad(mid, k), bool(t))

    @app.post("/api/modelle/{mid}/bilder")
    def bild_dazu(mid: str, roh: bytes = Depends(roh_koerper)):
        return {"k": K().bild_hinzufuegen(mid, roh)}

    @app.post("/api/modelle/{mid}/bilder/{k}/titel")
    def bild_titel(mid: str, k: str):
        K().bild_als_titel(mid, k)
        return {"ok": True}

    @app.post("/api/modelle/{mid}/vorschau/{art}/titel")
    def vorschau_titel(mid: str, art: str):
        K().vorschau_als_titel(mid, art)
        return {"ok": True}

    @app.delete("/api/modelle/{mid}/bilder/{k}")
    def bild_weg(mid: str, k: str):
        K().bild_entfernen(mid, k)
        return {"ok": True}

    # ---------------------------------------------------------------- Mehrere auf einmal

    # ---------------------------------------------------------------- Drucke (KONZEPT §4.6)

    @app.post("/api/drucke")
    def druck_neu(d: dict = Depends(json_koerper)):
        return {"id": K().drucke.anlegen(d.get("modelle"), d.get("felder"))}

    @app.patch("/api/drucke/{did}")
    def druck_aendern(did: str, koerper: dict = Depends(json_koerper)):
        K().drucke.aendern(did, koerper)
        return {"ok": True}

    @app.delete("/api/drucke/{did}")
    def druck_weg(did: str):
        K().drucke.loeschen(did)
        return {"ok": True}

    @app.post("/api/drucke/{did}/referenz")
    def druck_referenz(did: str, d: dict = Depends(json_koerper)):
        K().drucke.referenz(did, d.get("modell"), bool(d.get("an", True)))
        return {"ok": True}

    @app.post("/api/drucke/{did}/bilder")
    def druck_bild_dazu(did: str, roh: bytes = Depends(roh_koerper)):
        return {"k": K().drucke.bild_hinzufuegen(did, roh)}

    @app.get("/api/drucke/{did}/bilder/{k}")
    def druck_bild(did: str, k: str):
        return _bild_antwort(K().drucke.bild_pfad(did, k))

    @app.delete("/api/drucke/{did}/bilder/{k}")
    def druck_bild_weg(did: str, k: str):
        K().drucke.bild_entfernen(did, k)
        return {"ok": True}

    @app.post("/api/stapel")
    def stapel(d: dict = Depends(json_koerper)):
        # Löschen und Wiederherstellen vieler Modelle dauern bei 8 600 Modellen unter Windows eine halbe Minute: die Anzeige unten links
        # zeigt, wie weit sie sind (Live-Meldung „aktion“), statt dass man es nur an der wachsenden Zahl ahnt.
        aktion = d.get("aktion", "")
        was = {"loeschen": "Modelle entfernen", "wiederherstellen": "Wiederherstellen"}.get(aktion)
        melden = (lambda fertig, gesamt: verteiler.senden("aktion", {"was": was, "fertig": fertig, "gesamt": gesamt,
                                                                       "laeuft": fertig < gesamt})) if was else None
        try:
            return K().stapel(aktion, d.get("modelle", []), d.get("wert"), melden=melden)
        finally:
            if melden:
                verteiler.senden("aktion", {"was": was, "laeuft": False})

    @app.post("/api/stapel/loeschvorschau")
    def stapel_loeschvorschau(koerper: dict = Depends(json_koerper)):
        return K().loeschvorschau_viele(koerper.get("modelle", []))

    # ---------------------------------------------------------------- Einstellungen

    @app.get("/api/einstellungen")
    def einstellungen():
        e = zustand["bestand"].einstellungen()
        gewaehlt = e.get("programm") or {}
        gefunden = programme.erkennen()
        prog = {}
        for art in programme.ARTEN:
            p = programme.programm_fuer(art, e, gefunden)
            prog[art] = p and {**p, "automatisch": not (gewaehlt.get(art) and p["pfad"] == gewaehlt[art])}
        return {"auto_tags": True, "scan_beim_start": False, **e, "gilt": B().standard(), "materialien": K().materialien(),
                "pdf": {**PDF_STANDARD, **(e.get("pdf") or {})}, "programm": prog}

    @app.put("/api/einstellungen")
    def einstellungen_setzen(d: dict = Depends(json_koerper)):
        werte = {}
        if "standard_material" in d:
            with zustand["bestand"].db.transaction():
                werte["standard_material"] = K().material_knoten(d["standard_material"] or "PLA")
        if "standard_farbe" in d:
            f = d["standard_farbe"] or None
            if f and not re.fullmatch(r"#[0-9a-fA-F]{6}", f):
                raise KatalogFehler("Farbe als #RRGGBB angeben.")
            werte["standard_farbe"] = f
        if "vorschau_farbe" in d:
            # Für Vorschaubilder ohne eigene Farbe in der Datei. Vorgesehen, noch nicht angewendet (OFFEN.md): später rechnet der Worker
            # die betroffenen Bilder damit neu. None = die Vorgabe von partAtlas.
            f = d["vorschau_farbe"] or None
            if f and not re.fullmatch(r"#[0-9a-fA-F]{6}", f):
                raise KatalogFehler("Farbe als #RRGGBB angeben.")
            werte["vorschau_farbe"] = f
        if "auto_tags" in d:
            werte["auto_tags"] = bool(d["auto_tags"])
        if "scan_beim_start" in d:
            werte["scan_beim_start"] = bool(d["scan_beim_start"])
        if "fcstd_freecad" in d:     # None = fragen, "ja", "nein"
            if d["fcstd_freecad"] not in (None, "ja", "nein"):
                raise KatalogFehler("FCStd über FreeCAD: ja, nein oder fragen.")
            werte["fcstd_freecad"] = d["fcstd_freecad"]
        if "pdf" in d:     # nur bekannte Schalter, nur Wahrheitswerte
            werte["pdf"] = {k: bool(v) for k, v in (d["pdf"] or {}).items() if k in PDF_STANDARD}
        if "rolle_g" in d:
            try:
                werte["rolle_g"] = max(100, min(int(d["rolle_g"]), 10_000))
            except (TypeError, ValueError):
                raise KatalogFehler("Rollengrösse in Gramm.")
        if "programm" in d:     # {"slicer": Pfad, "cad": Pfad}; leer = wieder automatisch
            wahl = dict((zustand["bestand"].einstellungen().get("programm") or {}))
            for art in programme.ARTEN:
                if art not in (d["programm"] or {}):
                    continue
                pfad = str(d["programm"][art] or "").strip()
                if not pfad:
                    wahl.pop(art, None)
                elif programme.ausfuehrbar(pfad):
                    wahl[art] = pfad
                else:
                    raise KatalogFehler(f"Das ist kein ausführbares Programm: {pfad}")
            werte["programm"] = wahl
        zustand["bestand"].einstellungen_setzen(**werte)
        verteiler.senden("einstellungen", werte)
        return B().standard()

    # ---------------------------------------------------------------- Baugruppen

    @app.get("/api/baugruppen")
    @am_stueck
    def baugruppen():
        return B().liste()

    @app.get("/api/baugruppen/vorschlaege")
    @am_stueck
    def baugruppen_vorschlaege():
        return B().vorschlaege()

    @app.post("/api/baugruppen")
    def baugruppe_neu(d: dict = Depends(json_koerper)):
        if d.get("aus_sammlung"):
            return {"id": B().aus_sammlung(d["aus_sammlung"])}
        if d.get("aus_ordner"):
            return {"id": B().aus_ordner(d["aus_ordner"])}
        return {"id": B().aus_modellen(d.get("name", ""), d.get("modelle", []))}

    @app.get("/api/baugruppen/{bid}")
    def baugruppe(bid: str):
        return B().detail(bid)

    @app.patch("/api/baugruppen/{bid}")
    def baugruppe_aendern(bid: str, koerper: dict = Depends(json_koerper)):
        B().aendern(bid, koerper)
        return {"ok": True}

    @app.delete("/api/baugruppen/{bid}")
    def baugruppe_loeschen(bid: str):
        B().loeschen(bid)
        return {"ok": True}

    @app.post("/api/baugruppen/{bid}/positionen")
    def position_neu(bid: str, d: dict = Depends(json_koerper)):
        for ziel in d.get("refs") or [d.get("ref", "")]:
            B().hinzufuegen(bid, ziel, d.get("menge", 1))
        return {"ok": True}

    @app.patch("/api/baugruppen/{bid}/positionen")
    def position_aendern(bid: str, d: dict = Depends(json_koerper)):
        ziel = d.pop("ref", "")
        B().position_aendern(bid, ziel, d)
        return {"ok": True}

    @app.delete("/api/baugruppen/{bid}/positionen")
    def position_weg(bid: str, ref: str):
        B().position_entfernen(bid, ref)
        return {"ok": True}

    @app.put("/api/baugruppen/{bid}/reihenfolge")
    def positionen_ordnen(bid: str, koerper: dict = Depends(json_koerper)):
        B().ordnen(bid, koerper.get("refs", []))
        return {"ok": True}

    @app.post("/api/baugruppen/{bid}/material")
    def baugruppe_material(bid: str, d: dict = Depends(json_koerper)):
        if d.get("farbe") and not re.fullmatch(r"#[0-9a-fA-F]{6}", d["farbe"]):
            raise KatalogFehler("Farbe als #RRGGBB angeben.")
        B().material_fuer_offene(bid, (d.get("material") or "").strip()[:20] or "PLA", d.get("farbe"))
        return {"ok": True}

    @app.post("/api/baugruppen/{bid}/warteschlange")
    def baugruppe_warteschlange(bid: str):
        return {"eingereiht": B().fehlende_in_warteschlange(bid)}

    @app.get("/api/baugruppen/{bid}/export")
    def baugruppe_export(bid: str, format: str = "csv"):
        art = format if format in ("md", "pdf") else "csv"
        name = B().detail(bid)["name"]
        sicher = "".join(c if (c.isascii() and c.isalnum()) or c in "-_ " else "_" for c in name).strip() or bid
        if art == "pdf":
            return Response(Stueckliste(B(), zustand["bestand"].einstellungen().get("pdf")).pdf(bid), media_type="application/pdf",
                            headers={"Content-Disposition": f'inline; filename="Stueckliste {sicher}.pdf"'})
        return Response(B().export(bid, art), media_type="text/csv; charset=utf-8" if art == "csv" else "text/markdown; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{sicher}.{art}"'})

    @app.get("/api/kaufteile")
    def kaufteile(q: str = "", kategorie: str = ""):
        return B().kaufteile(q or None, kategorie or None)

    @app.post("/api/kaufteile")
    def kaufteil_neu(d: dict = Depends(json_koerper)):
        return {"id": B().kaufteil_anlegen(d.get("name", ""), d.get("kategorie") or "Eigene", d.get("einheit") or "Stück")}

    # Eigene Komponenten
    @app.get("/api/eigene")
    def eigene_liste(q: str = ""):
        return E().liste(q or None)

    @app.get("/api/eigene/arten")
    def eigene_arten():
        return E().arten()

    @app.post("/api/eigene")
    def eigene_neu(d: dict = Depends(json_koerper)):
        return {"id": E().anlegen(d.get("name", ""), d.get("art", ""), d.get("masse", ""), d.get("notiz", ""))}

    @app.get("/api/eigene/{eid}")
    def eigene_detail(eid: str):
        return E().detail(eid)

    @app.patch("/api/eigene/{eid}")
    def eigene_aendern(eid: str, koerper: dict = Depends(json_koerper)):
        E().aendern(eid, koerper)
        return E().detail(eid)

    @app.delete("/api/eigene/{eid}")
    def eigene_loeschen(eid: str):
        E().loeschen(eid)
        return {"ok": True}

    @app.get("/api/eigene/{eid}/bild")
    def eigene_bild(eid: str, t: int = 0):
        return _bild_antwort(E().bild_pfad(eid), bool(t))

    @app.post("/api/eigene/{eid}/bild")
    def eigene_bild_setzen(eid: str, roh: bytes = Depends(roh_koerper)):
        return {"k": E().bild_setzen(eid, roh)}
    @app.post("/api/eigene/{eid}/datei")
    def eigene_datei_setzen(eid: str, name: str, roh: bytes = Depends(roh_koerper)):
        bild = E().datei_setzen(eid, name, roh)
        return {**E().detail(eid), "bild_neu": bild}

    @app.get("/api/eigene/{eid}/datei")
    def eigene_datei(eid: str):
        pfad, name = E().datei_pfad(eid)
        if not pfad:
            raise HTTPException(404)
        return FileResponse(pfad, filename=name)

    @app.get("/api/tags")
    @am_stueck
    def tags():
        return K().tags()

    @app.get("/api/ordner")
    @am_stueck
    def ordner():
        return K().ordnerbaum()

    @app.get("/api/vorschau/{name}")
    def vorschaubild(name: str, t: int = 0):
        # <hash>.png = das beste Bild (für die Kachel), <hash>.<art>.png = genau dieses.
        m = re.fullmatch(r"([0-9a-f]{64})(?:\.(extrahiert|berechnet))?\.png", name)
        if not m:
            raise HTTPException(404)
        h, art = m.groups()
        pfad = zustand["bestand"].vorschau_pfad(h, art) if art else K().vorschau_datei(h)
        if not pfad:
            raise HTTPException(404)
        if not os.path.exists(pfad):
            raise HTTPException(404)
        return _bild_antwort(pfad, bool(t))

    # ---------------------------------------------------------------- Öffnen in …

    def _programme():
        e = zustand["bestand"].einstellungen()
        liste = programme.alle(e)
        return liste, programme.standard(liste, e)

    @app.get("/api/programme")
    def programme_liste():
        liste, std = _programme()
        return {"programme": liste, "standard": std, "arten": programme.ARTEN}

    @app.post("/api/programme/waehlen")
    def programm_waehlen(koerper: dict = Depends(json_koerper)):
        """Öffnet den Dateidialog des Rechners; gespeichert wird erst mit „Speichern“."""
        art = koerper.get("art")
        if art not in programme.ARTEN:
            raise KatalogFehler("Slicer oder CAD.")
        try:
            pfad = dateidialog.programm_waehlen(f"{programme.ARTEN[art]} auswählen")
        except dateidialog.KeinDialog as e:
            raise KatalogFehler(str(e))
        if not pfad:
            return {"abgebrochen": True}
        if not programme.ausfuehrbar(pfad):
            if os.path.isfile(pfad) and not sys.platform.startswith("win"):
                raise KatalogFehler("Die Datei ist nicht ausführbar. Im Dateimanager: Rechtsklick › Eigenschaften › Berechtigungen › "
                                    "„Als Programm ausführen“ — danach erneut auswählen.")
            raise KatalogFehler("Das ist kein ausführbares Programm.")
        return {**programme.eintrag_fuer(pfad, art), "automatisch": False}

    @app.get("/api/ordner/inhalt")
    def ordner_inhalt(id: str):
        i = K().ordner_inhalt(id)
        return {**i, "andere": i["andere"][:50], "andere_n": len(i["andere"])}

    @app.post("/api/ordner/loeschen")
    def ordner_loeschen(d: dict = Depends(json_koerper)):
        return K().ordner_loeschen(d.get("id", ""), d.get("tags") or (), d.get("sammlungen") or ())

    @app.post("/api/cad/erneut")
    def cad_erneut():
        n = K().cad_erneut()
        if n:
            zustand["scanner"].starten(nur_cad=True)
        return {"zurueckgesetzt": n}

    @app.post("/api/cad/starten")
    def cad_starten():
        """Nur die Umwandlung über FreeCAD, ohne alles neu einzulesen — nach der Zusage für FCStd."""
        return {"gestartet": zustand["scanner"].starten(nur_cad=True)}

    @app.get("/api/sicherungen")
    def sicherungen():
        return sicherung.liste(zustand["bestand"].wurzel)

    @app.post("/api/sicherungen")
    def sicherung_jetzt():
        return {"name": sicherung.sichern(zustand["bestand"], "von-hand", immer=True)}

    @app.post("/api/sicherungen/zeigen")
    def sicherungen_zeigen():
        pfad = zustand["bestand"].pfad(sicherung.ORDNER)
        try:
            programme.mit_system(pfad)
        except (OSError, subprocess.SubprocessError) as e:
            raise KatalogFehler(f"Dateimanager ließ sich nicht öffnen: {e}")
        return {"ok": True, "pfad": pfad}

    @app.post("/api/stapel/optionen")
    def stapel_optionen(d: dict = Depends(json_koerper)):
        return zuordnen.optionen(K(), B(), d.get("art"), d.get("modelle") or [])

    @app.post("/api/stapel/zuordnen")
    def stapel_zuordnen(d: dict = Depends(json_koerper)):
        return zuordnen.zuordnen(K(), B(), d.get("art"), d.get("modelle") or [], d.get("ziel"), d.get("neu"))

    @app.get("/api/aufraeumen")
    def aufraeumen_vorschlaege():
        return aufraeumen.vorschlaege(K(), B())

    @app.get("/api/aufraeumen/behalten")
    def aufraeumen_behaltene():
        return aufraeumen.behaltene(K())

    @app.post("/api/modelle/{mid}/behalten")
    def aufraeumen_behalten(mid: str, d: dict = Depends(json_koerper)):
        aufraeumen.behalten(K(), mid, d.get("an", True))
        return {"ok": True}

    @app.post("/api/protokoll/zeigen")
    def protokoll_zeigen():
        pfad = zustand["bestand"].pfad("partatlas.log")
        if not os.path.exists(pfad):
            raise KatalogFehler("Es gibt noch kein Protokoll.")
        try:
            programme.im_ordner_zeigen(pfad)
        except (OSError, subprocess.SubprocessError) as e:
            raise KatalogFehler(f"Dateimanager ließ sich nicht öffnen: {e}")
        return {"ok": True, "pfad": pfad}

    @app.post("/api/ordner/im_ordner")
    def ordner_im_ordner(koerper: dict = Depends(json_koerper)):
        pfad = K()._ordner_pfad(koerper.get("id", ""))[2]
        try:
            programme.im_ordner_zeigen(pfad)
        except (OSError, subprocess.SubprocessError) as e:
            raise KatalogFehler(f"Dateimanager ließ sich nicht öffnen: {e}")
        return {"ok": True}

    @app.post("/api/modelle/{mid}/im_ordner")
    def im_ordner(mid: str, d: dict = Depends(json_koerper)):
        # Mit {"pfad": …}: genau diese Kopie (Aufräumen zeigt jede einzeln) — nur einer der Orte des Modells.
        m = K().modell(mid)
        datei = aufraeumen.pfad_von(K(), mid, d["pfad"]) if d.get("pfad") else \
            next((o["absolut"] for o in m["orte"] if o["absolut"] and os.path.exists(o["absolut"])), None)
        if not datei:
            raise KatalogFehler("Die Datei ist nicht da.")
        try:
            programme.im_ordner_zeigen(datei)
        except (OSError, subprocess.SubprocessError) as e:
            raise KatalogFehler(f"Dateimanager ließ sich nicht öffnen: {e}")
        return {"ok": True}

    @app.post("/api/modelle/{mid}/oeffnen")
    def modell_oeffnen(mid: str, daten: dict = Depends(json_koerper)):
        m = K().modell(mid)
        datei = next((o["absolut"] for o in m["orte"] if o["absolut"] and os.path.exists(o["absolut"])), None)
        if not datei:
            raise KatalogFehler("Die Datei ist nicht da.")
        if daten.get("system"):
            try:
                programme.mit_system(datei)
            except OSError as e:
                raise KatalogFehler(f"Mit dem System öffnen ging nicht: {e}")
            return {"ok": True}
        liste, std = _programme()
        pfad = daten.get("pfad") or std.get(m["format"])
        if pfad not in {p["pfad"] for p in liste}:
            raise KatalogFehler("Dieses Programm kennt partAtlas nicht.")
        try:
            programme.oeffnen(pfad, datei, zustand["bestand"].pfad("arbeit", "programmstart.log"))
        except (OSError, subprocess.SubprocessError) as e:
            raise KatalogFehler(f"{next(p['name'] for p in liste if p['pfad'] == pfad)} ließ sich nicht starten: {e}")
        return {"ok": True, "programm": next(p["name"] for p in liste if p["pfad"] == pfad)}

    # ---------------------------------------------------------------- Oberfläche

    @app.get("/")
    def start():
        return FileResponse(os.path.join(WEB, "index.html"), headers={"Cache-Control": "no-cache"})

    class Web(StaticFiles):
        """Skript und Stile prüft der Browser bei jedem Aufruf neu (ETag, ein 304 kostet nichts): sonst zeigt er nach einer
        Aktualisierung stundenlang die alte Oberfläche. Nur das mitgelieferte three.js ändert sich nie."""
        async def get_response(self, path, scope):
            antwort = await super().get_response(path, scope)
            antwort.headers["Cache-Control"] = "max-age=31536000, immutable" if path.startswith("vendor/") else "no-cache"
            return antwort

    app.mount("/web", Web(directory=WEB), name="web")
    return app
