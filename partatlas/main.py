"""
Der Server: ein Prozess, ein Bestand, Oberfläche im Browser (KONZEPT §2).

    python -m partatlas            http://127.0.0.1:8765

Ohne Passwort lauscht er nur auf 127.0.0.1 — lieber unbrauchbar als offen
(wie pDMS). Zugriff aus dem Heimnetz kommt mit dem Passwort (offen).
"""
import asyncio
import logging
import os
import re
import subprocess
import sys
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

import numpy as np

from . import dateidialog, durchsuchen, formate, programme
from .baugruppen import Baugruppen
from .bestand import Bestand
from .katalog import Katalog, KatalogFehler
from .live import Verteiler
from .scan import Scanner
from .stueckliste import PDF_STANDARD, Stueckliste
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
        zustand.update(bestand=b, katalog=k, scanner=s, baugruppen=Baugruppen(k))
        if scan_beim_start and k.wurzeln():
            s.starten()
        yield
        s.warten(30)
        b.schliessen()

    app = FastAPI(title="partAtlas", version=VERSION, lifespan=leben)
    app.state.zustand = zustand

    def K():
        return zustand["katalog"]

    def B():
        return zustand["baugruppen"]

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

    @app.delete("/api/wurzeln/{wid}")
    def wurzel_weg(wid: str):
        K().wurzel_entfernen(wid)
        return {"ok": True}

    @app.post("/api/scan")
    def scan():
        return {"gestartet": zustand["scanner"].starten()}

    # ---------------------------------------------------------------- Modelle

    @app.get("/api/modelle")
    def modelle(q: str = "", tag: str = "", ordner: str = "", format: str = "", ansicht: str = "alle",
                sammlung: str = "", tags: str = "", material: str = "", leiste: bool = False):
        # tags und material als Komma-Liste: die Chips der Leiste, je mit ODER.
        liste = lambda s: [x for x in s.split(",") if x]
        return K().modelle(suche=q or None, tag=tag or None, ordner=ordner or None,
                           fmt=format or None, ansicht=ansicht, sammlung=sammlung or None,
                           tags=liste(tags), materialien=liste(material), leiste=leiste)

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
            "warteschlange": sum(m["warteschlange"] is not None for m in alle),
            "neu": len(k.modelle(ansicht="neu")),
        }

    @app.get("/api/modelle/{mid}")
    def modell(mid: str):
        k = K()
        daten = k.modell(mid)
        daten["baugruppen"] = B().verwendet_in(f"MODEL_ASSET/{mid}")
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

    @app.get("/api/materialien")
    def materialien():
        return K().materialien()

    @app.post("/api/modelle/{mid}/material")
    async def material_neu(mid: str, request: Request):
        daten = await request.json()
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
    async def loeschen(mid: str, request: Request):
        # Ohne Körper: nur das Modell. Mit {"tags": [...], "sammlungen": [...]}:
        # was nur an ihm hing, auf Wunsch mit.
        d = await request.json() if await request.body() else {}
        fehler = K().loeschen_mit([mid], d.get("tags") or (), d.get("sammlungen") or ())
        if fehler:
            raise KatalogFehler(fehler[0]["fehler"])
        return {"ok": True}

    @app.post("/api/modelle/{mid}/wiederherstellen")
    def wiederherstellen(mid: str):
        K().wiederherstellen(mid)
        return {"ok": True}

    @app.post("/api/papierkorb/leeren")
    def papierkorb_leeren():
        return {"geloescht": K().papierkorb_leeren()}

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
    def sammlungen():
        return K().sammlungen()

    @app.post("/api/sammlungen")
    async def sammlung_neu(request: Request):
        d = await request.json()
        return {"id": K().sammlung_anlegen(d.get("name", ""), d.get("modelle", []))}

    @app.patch("/api/sammlungen/{sid}")
    async def sammlung_umbenennen(sid: str, request: Request):
        K().sammlung_umbenennen(sid, (await request.json()).get("name", ""))
        return {"ok": True}

    @app.delete("/api/sammlungen/{sid}")
    def sammlung_loeschen(sid: str):
        K().sammlung_loeschen(sid)
        return {"ok": True}

    @app.post("/api/sammlungen/{sid}/modelle")
    async def sammlung_dazu(sid: str, request: Request):
        K().zur_sammlung(sid, (await request.json()).get("modelle", []))
        return {"ok": True}

    @app.delete("/api/sammlungen/{sid}/modelle/{mid}")
    def sammlung_weg(sid: str, mid: str):
        K().aus_sammlung(sid, mid)
        return {"ok": True}

    @app.put("/api/sammlungen/{sid}/reihenfolge")
    async def sammlung_ordnen(sid: str, request: Request):
        K().sammlung_ordnen(sid, (await request.json()).get("modelle", []))
        return {"ok": True}

    # ---------------------------------------------------------------- Warteschlange

    @app.get("/api/warteschlange")
    def warteschlange():
        return K().warteschlange()

    @app.post("/api/warteschlange")
    async def warteschlange_dazu(request: Request):
        for mid in (await request.json()).get("modelle", []):
            K().in_warteschlange(mid)
        return {"ok": True}

    @app.delete("/api/warteschlange/{mid}")
    def warteschlange_weg(mid: str):
        K().aus_warteschlange(mid)
        return {"ok": True}

    @app.put("/api/warteschlange")
    async def warteschlange_ordnen(request: Request):
        K().warteschlange_ordnen((await request.json()).get("modelle", []))
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
    async def verzeichnis_neu(request: Request):
        d = await request.json()
        return {"id": K().ordner_anlegen(d.get("eltern", ""), d.get("name", ""))}

    @app.post("/api/modelle/{mid}/verschieben")
    async def verschieben(mid: str, request: Request):
        K().verschieben(mid, (await request.json()).get("ordner", ""))
        return {"ok": True}

    @app.post("/api/hochladen")
    async def hochladen(request: Request, ordner: str, name: str):
        neu = K().hochladen(ordner, name, await request.body())
        zustand["scanner"].starten()
        return {"dateien": len(neu)}

    @app.get("/api/archive")
    def archive():
        return K().archive()

    @app.post("/api/archive/entpacken")
    async def archiv_entpacken(request: Request):
        d = await request.json()
        ergebnis = K().archiv_entpacken(d.get("id", ""), bool(d.get("original_loeschen")))
        zustand["scanner"].starten()
        return ergebnis

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
    async def bild_dazu(mid: str, request: Request):
        return {"k": K().bild_hinzufuegen(mid, await request.body())}

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
    async def druck_neu(request: Request):
        d = await request.json()
        return {"id": K().drucke.anlegen(d.get("modelle"), d.get("felder"))}

    @app.patch("/api/drucke/{did}")
    async def druck_aendern(did: str, request: Request):
        K().drucke.aendern(did, await request.json())
        return {"ok": True}

    @app.delete("/api/drucke/{did}")
    def druck_weg(did: str):
        K().drucke.loeschen(did)
        return {"ok": True}

    @app.post("/api/drucke/{did}/referenz")
    async def druck_referenz(did: str, request: Request):
        d = await request.json()
        K().drucke.referenz(did, d.get("modell"), bool(d.get("an", True)))
        return {"ok": True}

    @app.post("/api/drucke/{did}/bilder")
    async def druck_bild_dazu(did: str, request: Request):
        return {"k": K().drucke.bild_hinzufuegen(did, await request.body())}

    @app.get("/api/drucke/{did}/bilder/{k}")
    def druck_bild(did: str, k: str):
        return _bild_antwort(K().drucke.bild_pfad(did, k))

    @app.delete("/api/drucke/{did}/bilder/{k}")
    def druck_bild_weg(did: str, k: str):
        K().drucke.bild_entfernen(did, k)
        return {"ok": True}

    @app.post("/api/stapel")
    async def stapel(request: Request):
        d = await request.json()
        return K().stapel(d.get("aktion", ""), d.get("modelle", []), d.get("wert"))

    @app.post("/api/stapel/loeschvorschau")
    async def stapel_loeschvorschau(request: Request):
        return K().loeschvorschau_viele((await request.json()).get("modelle", []))

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
        return {"auto_tags": True, **e, "gilt": B().standard(), "materialien": K().materialien(),
                "pdf": {**PDF_STANDARD, **(e.get("pdf") or {})}, "programm": prog}

    @app.put("/api/einstellungen")
    async def einstellungen_setzen(request: Request):
        d = await request.json()
        werte = {}
        if "standard_material" in d:
            with zustand["bestand"].db.transaction():
                werte["standard_material"] = K().material_knoten(d["standard_material"] or "PLA")
        if "standard_farbe" in d:
            f = d["standard_farbe"] or None
            if f and not re.fullmatch(r"#[0-9a-fA-F]{6}", f):
                raise KatalogFehler("Farbe als #RRGGBB angeben.")
            werte["standard_farbe"] = f
        if "auto_tags" in d:
            werte["auto_tags"] = bool(d["auto_tags"])
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
    def baugruppen():
        return B().liste()

    @app.get("/api/baugruppen/vorschlaege")
    def baugruppen_vorschlaege():
        return B().vorschlaege()

    @app.post("/api/baugruppen")
    async def baugruppe_neu(request: Request):
        d = await request.json()
        if d.get("aus_sammlung"):
            return {"id": B().aus_sammlung(d["aus_sammlung"])}
        if d.get("aus_ordner"):
            return {"id": B().aus_ordner(d["aus_ordner"])}
        return {"id": B().aus_modellen(d.get("name", ""), d.get("modelle", []))}

    @app.get("/api/baugruppen/{bid}")
    def baugruppe(bid: str):
        return B().detail(bid)

    @app.patch("/api/baugruppen/{bid}")
    async def baugruppe_aendern(bid: str, request: Request):
        B().aendern(bid, await request.json())
        return {"ok": True}

    @app.delete("/api/baugruppen/{bid}")
    def baugruppe_loeschen(bid: str):
        B().loeschen(bid)
        return {"ok": True}

    @app.post("/api/baugruppen/{bid}/positionen")
    async def position_neu(bid: str, request: Request):
        d = await request.json()
        for ziel in d.get("refs") or [d.get("ref", "")]:
            B().hinzufuegen(bid, ziel, d.get("menge", 1))
        return {"ok": True}

    @app.patch("/api/baugruppen/{bid}/positionen")
    async def position_aendern(bid: str, request: Request):
        d = await request.json()
        ziel = d.pop("ref", "")
        B().position_aendern(bid, ziel, d)
        return {"ok": True}

    @app.delete("/api/baugruppen/{bid}/positionen")
    def position_weg(bid: str, ref: str):
        B().position_entfernen(bid, ref)
        return {"ok": True}

    @app.put("/api/baugruppen/{bid}/reihenfolge")
    async def positionen_ordnen(bid: str, request: Request):
        B().ordnen(bid, (await request.json()).get("refs", []))
        return {"ok": True}

    @app.post("/api/baugruppen/{bid}/material")
    async def baugruppe_material(bid: str, request: Request):
        d = await request.json()
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
    async def kaufteil_neu(request: Request):
        d = await request.json()
        return {"id": B().kaufteil_anlegen(d.get("name", ""), d.get("kategorie") or "Eigene", d.get("einheit") or "Stück")}

    @app.get("/api/tags")
    def tags():
        return K().tags()

    @app.get("/api/ordner")
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
    async def programm_waehlen(request: Request):
        """Öffnet den Dateidialog des Rechners; gespeichert wird erst mit „Speichern“."""
        art = (await request.json()).get("art")
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

    @app.post("/api/modelle/{mid}/im_ordner")
    def im_ordner(mid: str):
        m = K().modell(mid)
        datei = next((o["absolut"] for o in m["orte"] if o["absolut"] and os.path.exists(o["absolut"])), None)
        if not datei:
            raise KatalogFehler("Die Datei ist nicht da.")
        try:
            programme.im_ordner_zeigen(datei)
        except (OSError, subprocess.SubprocessError) as e:
            raise KatalogFehler(f"Dateimanager ließ sich nicht öffnen: {e}")
        return {"ok": True}

    @app.post("/api/modelle/{mid}/oeffnen")
    async def modell_oeffnen(mid: str, request: Request):
        daten = await request.json()
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
