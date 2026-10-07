"""
Live-Oberfläche: Meldungen von flatgraph (`bei_aenderung`, VERTRAG §2.7)
und vom Scan per Server-Sent Events an jeden offenen Browser.

Der Rückruf von flatgraph läuft unter dessen Sperre. Hier wird deshalb
nur in Warteschlangen gelegt, nie gewartet.
"""
import asyncio
import json
import threading
import time


STAPEL_S = 0.3


class Verteiler:
    def __init__(self):
        self._schlangen = set()
        self._sperre = threading.Lock()
        self._schleife = None
        self._stapel = {}               # Graph-Meldungen seit dem letzten Senden, je (Ereignis, Verweis) einmal
        self._stapel_geplant = False

    def binden(self, schleife):
        self._schleife = schleife

    def antwortzeit(self, frist=5.0):
        """Wie lange die Ereignisschleife des Servers braucht, um eine Kleinigkeit zu erledigen (ms), oder None, wenn sie in `frist` Sekunden
        nicht antwortet — dann steckt der Server fest (etwas blockiert die Schleife). Für das Protokoll."""
        if self._schleife is None:
            return None
        t0 = time.monotonic()
        try:
            asyncio.run_coroutine_threadsafe(asyncio.sleep(0), self._schleife).result(frist)
        except Exception:
            return None
        return round((time.monotonic() - t0) * 1000)

    def senden(self, art, daten):
        if self._schleife is None:
            return
        text = json.dumps({"art": art, **daten}, ensure_ascii=False, default=str)
        with self._sperre:
            schlangen = list(self._schlangen)
        for q in schlangen:
            self._schleife.call_soon_threadsafe(self._einreihen, q, text)

    @staticmethod
    def _einreihen(q, text):
        # Ein Browser, der nicht abholt, soll den Server nicht füllen: wer
        # 1000 Meldungen zurückliegt, bekommt nur noch „neu laden“.
        if q.qsize() > 1000:
            while not q.empty():
                q.get_nowait()
            text = json.dumps({"art": "neu_laden"})
        q.put_nowait(text)

    def beenden(self):
        """Jede offene Live-Verbindung endet. Beim Beenden des Servers: sonst wartet uvicorn, bis sie von selbst endet — das tut sie nie,
        solange ein Tab offen ist. Darf aus dem Signal-Handler gerufen werden."""
        if self._schleife is None:
            return
        with self._sperre:
            schlangen = list(self._schlangen)
        for q in schlangen:
            self._schleife.call_soon_threadsafe(q.put_nowait, None)

    def graph(self, meldung):
        """Sammelt Änderungen am Graphen und schickt sie höchstens alle STAPEL_S als eine Meldung. Einzeln waren es beim Einlesen tausende
        je Sekunde: der Browser kam nicht nach, die Schlange lief über, und jedes Überlaufen hiess „alles neu laden“ — bei 8 600 Modellen
        etwa jede Sekunde die ganze Liste samt Baugruppen-Vorschlägen (Protokoll des Anwenders, 7.10.2026). Läuft unter der Sperre von
        flatgraph: nur merken."""
        if self._schleife is None:
            return
        eintrag = {k: meldung.get(k) for k in ("ereignis", "ref", "sammlung", "kantenart", "quelle", "ziel")}
        with self._sperre:
            self._stapel[(eintrag["ereignis"], eintrag["ref"])] = eintrag
            if self._stapel_geplant:
                return
            self._stapel_geplant = True
        self._schleife.call_soon_threadsafe(self._schleife.call_later, STAPEL_S, self._stapel_senden)

    def _stapel_senden(self):
        with self._sperre:
            stapel, self._stapel, self._stapel_geplant = list(self._stapel.values()), {}, False
        if stapel:
            self.senden("graph", {"stapel": stapel})

    async def strom(self, anfang=None):
        """`anfang`: liefert die Meldungen, die ein Browser beim (Wieder-)Verbinden zuerst bekommt — den ganzen Stand, nicht nur, was sich
        danach ändert. Sonst blieb eine Anzeige, deren Endmeldung in eine Verbindungslücke fiel, für immer bei „läuft“ stehen."""
        q = asyncio.Queue()
        with self._sperre:
            self._schlangen.add(q)
        try:
            yield "retry: 2000\n\n"
            for art, daten in (anfang() if anfang else []):
                yield f"data: {json.dumps({'art': art, **daten}, ensure_ascii=False, default=str)}\n\n"
            while True:
                try:
                    text = await asyncio.wait_for(q.get(), timeout=20)
                    if text is None:          # beenden()
                        return
                    yield f"data: {text}\n\n"
                except asyncio.TimeoutError:
                    yield ": wach\n\n"
        finally:
            with self._sperre:
                self._schlangen.discard(q)
