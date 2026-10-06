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


class Verteiler:
    def __init__(self):
        self._schlangen = set()
        self._sperre = threading.Lock()
        self._schleife = None

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

    def graph(self, meldung):
        self.senden("graph", {k: meldung.get(k) for k in ("ereignis", "ref", "sammlung", "kantenart", "quelle", "ziel")})

    async def strom(self):
        q = asyncio.Queue()
        with self._sperre:
            self._schlangen.add(q)
        try:
            yield "retry: 2000\n\n"
            while True:
                try:
                    text = await asyncio.wait_for(q.get(), timeout=20)
                    yield f"data: {text}\n\n"
                except asyncio.TimeoutError:
                    yield ": wach\n\n"
        finally:
            with self._sperre:
                self._schlangen.discard(q)
