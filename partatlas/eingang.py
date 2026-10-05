"""
Die Eingangsliste: Dateien, die der Anwender gerade hineingelegt hat (Hochladen, Entpacken) und die der Dienst im Hintergrund
einlesen soll.

Wer eine Datei ablegt, trägt sie hier ein — mehr nicht, keine Wartezeit, kein Anstossen eines Laufs durch den Browser. Die Liste
steht im Bestand (`arbeit/eingang.json`, atomar geschrieben) und übersteht Abbruch, geschlossenen Tab und Neustart. Die Platte
bleibt die Wahrheit: was in der Liste fehlt (Datei von aussen hineingelegt, Liste verloren), findet das vollständige Einlesen
trotzdem. Deshalb darf eine unlesbare oder beschädigte Liste still leer anfangen.

Ein Eintrag ist (Wurzel, relativer Pfad) — derselbe Schlüssel wie ein Ort im Katalog.
"""
import json
import logging
import threading

from .dateien import schreibe_atomar

log = logging.getLogger("partatlas.eingang")

FORM = 1


class Eingang:
    def __init__(self, bestand):
        self._bestand = bestand
        self._pfad = bestand.pfad("arbeit", "eingang.json")
        self._sperre = threading.Lock()
        self._liste = self._lesen()          # in Reihenfolge des Eintreffens; Schlüssel (wurzel, pfad) kommt einmal vor

    def _lesen(self):
        try:
            with open(self._pfad, encoding="utf-8") as f:
                roh = json.load(f)
            liste, gesehen = [], set()
            for e in roh["eintraege"]:
                s = (str(e["wurzel"]), str(e["pfad"]))
                if s not in gesehen:
                    gesehen.add(s)
                    liste.append(s)
            return liste
        except FileNotFoundError:
            return []
        except (OSError, ValueError, KeyError, TypeError) as e:
            log.warning("Eingangsliste nicht lesbar, sie fängt leer an (das Einlesen der Ordner findet die Dateien): %s", e)
            return []

    def _schreiben(self):
        daten = {"form": FORM, "eintraege": [{"wurzel": w, "pfad": p} for w, p in self._liste]}
        if not self._liste:
            self._bestand.entfernen(self._pfad)       # der einzige Löschweg von partAtlas; die Liste liegt im Bestand
            return
        schreibe_atomar(self._pfad, json.dumps(daten, ensure_ascii=False).encode("utf-8"))

    def eintragen(self, eintraege):
        """[(Wurzel, Pfad)] anhängen; was schon drinsteht, nicht doppelt. Gibt die Zahl der neuen Einträge zurück.
        Fehlt der Platz zum Schreiben, schlägt es fehl, und die Liste im Speicher bleibt, wie sie war: der Aufrufer
        darf nicht glauben, die Datei sei vorgemerkt."""
        with self._sperre:
            vorhanden = set(self._liste)
            neu = []
            for e in eintraege:
                if e not in vorhanden:
                    vorhanden.add(e)
                    neu.append(e)
            if not neu:
                return 0
            alt = self._liste
            self._liste = alt + neu
            try:
                self._schreiben()
            except OSError:
                self._liste = alt
                raise
            return len(neu)

    def liste(self):
        with self._sperre:
            return list(self._liste)

    def erledigt(self, eintraege):
        """Einträge streichen, die der Dienst fertig bearbeitet hat. Was inzwischen neu dazukam, bleibt."""
        weg = set(eintraege)
        with self._sperre:
            rest = [e for e in self._liste if e not in weg]
            if len(rest) == len(self._liste):
                return
            self._liste = rest
            try:
                self._schreiben()
            except OSError as e:
                # Bleibt die Datei länger stehen als die Liste im Speicher, liest der nächste Start die Einträge nur noch einmal:
                # bekannte Dateien werden dann an Ort, Grösse und Zeit erkannt und übersprungen.
                log.warning("Eingangsliste nicht geschrieben: %s", e)

    def __len__(self):
        with self._sperre:
            return len(self._liste)
