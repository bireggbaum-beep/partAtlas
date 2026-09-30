"""
Suche wie in pDMS: jedes Wort muss vorkommen, auch als Wortteil;
"Wortfolge" genau; -wort schliesst aus; feld:wert schränkt auf ein Feld
ein. Geordnet nach dem Feld, in dem ein Begriff steht.

Der Wortindex (Kopie aus pDMS) findet die Kandidaten; die Felder je
Modell liegen daneben im Arbeitsspeicher, klein genug für Phrasen,
Feldfilter und Bewertung. Nachgeführt wird über den Rückruf von
flatgraph: der merkt sich nur, WAS sich geändert hat (er läuft unter der
Sperre von flatgraph); eingelesen wird erst bei der nächsten Suche.
"""
import re
import threading

from .bestand import DATEI, HAT_TAG, IN_SAMMLUNG, MODELL
from .wortindex import Wortindex

# Aus baugruppen.py; hier wiederholt, weil baugruppen den Katalog braucht.
ENTHAELT = "CONTAINS"



def ref(sammlung, kennung):
    return f"{sammlung}/{kennung}"


_TRENNER = re.compile(r"[\W_]+", re.UNICODE)


def norm(text):
    """Vergleichsform mit derselben Trennung wie der Wortindex, aber in
    Reihenfolge — für Phrasen."""
    return " ".join(w for w in _TRENNER.split((text or "").lower()) if w)


# Wo ein Begriff steht, entscheidet die Reihenfolge: „Halter“ im Namen ist
# fast immer das gesuchte Modell, im Ordnernamen nur vielleicht.
FELDGEWICHT = {
    "name": 10.0,
    "tags": 6.0,
    "baugruppen": 4.0,
    "sammlungen": 4.0,
    "titel": 3.0,
    "designer": 3.0,
    "ordner": 3.0,
    "material": 2.0,
}
# Ganzes Wort wiegt doppelt: „arm“ meint eher „Arm“ als „Armatur“.
WORTBONUS = 2.0

# feld:wert — deutsch, wie es der Anwender tippt.
FILTER = {"tag": "tags", "ordner": "ordner", "baugruppe": "baugruppen", "sammlung": "sammlungen",
          "material": "material", "designer": "designer", "name": "name", "titel": "titel",
          "format": "format", "gedruckt": "gedruckt", "favorit": "favorit"}
# Diese vergleichen genau: „format:st“ soll nicht STL und STEP liefern.
GENAU = {"format", "gedruckt", "favorit"}
JA = {"ja": "ja", "j": "ja", "1": "ja", "true": "ja", "nein": "nein", "n": "nein", "0": "nein", "false": "nein"}

_FELDFILTER = re.compile(r'(-?)(\w+):(?:"([^"]*)"|(\S+))')
_PHRASE = re.compile(r'"([^"]*)"')


class Anfrage:
    __slots__ = ("pflicht", "verboten", "phrasen", "filter")

    def __init__(self, pflicht, verboten, phrasen, filter_):
        self.pflicht, self.verboten, self.phrasen, self.filter = pflicht, verboten, phrasen, filter_

    def __bool__(self):
        return bool(self.pflicht or self.verboten or self.phrasen or self.filter)


def zerlege(q):
    """Eingabe → Pflicht, Verbot, Phrasen, Feldfilter [(feld, wert, nicht)].

    Unbekanntes `x:y` bleibt ein gewöhnlicher Begriff — ein Doppelpunkt im
    Dateinamen soll nicht still zur leeren Trefferliste führen.
    """
    text, filter_ = q or "", []

    def feld(m):
        name = m.group(2).lower()
        if name not in FILTER:
            return m.group(0)
        wert = norm(m.group(3) if m.group(3) is not None else m.group(4))
        if FILTER[name] in ("gedruckt", "favorit"):
            wert = JA.get(wert, wert)
        if wert:
            filter_.append((FILTER[name], wert, m.group(1) == "-"))
        return " "

    text = _FELDFILTER.sub(feld, text)
    phrasen = [norm(p) for p in _PHRASE.findall(text) if norm(p)]
    text = _PHRASE.sub(" ", text)
    pflicht, verboten = [], []
    for roh in text.split():
        if roh.startswith("-") and len(roh) > 1:
            verboten += norm(roh[1:]).split()
        else:
            pflicht += norm(roh).split()
    return Anfrage(pflicht, verboten, phrasen, filter_)


def _ganzes_wort(begriff, text):
    return re.search(rf"(?<!\w){re.escape(begriff)}(?!\w)", text) is not None


def bewerten(felder, begriffe):
    """Je Begriff zählt der BESTE Fundort, summiert über die Begriffe.
    (pDMS `bewerten` kehrt nach dem ersten Begriff zurück — hier nicht.)"""
    punkte = 0.0
    for begriff in begriffe:
        bestes = 0.0
        for feld, gewicht in FELDGEWICHT.items():
            text = felder.get(feld, "")
            if begriff in text:
                bestes = max(bestes, gewicht * (WORTBONUS if _ganzes_wort(begriff, text) else 1.0))
        punkte += bestes
    return punkte


class Suchindex:
    def __init__(self, katalog):
        self.k = katalog
        self.db = katalog.db
        self.index = Wortindex()
        self.felder = {}                  # mid → {feld: Vergleichsform}
        self._offen = set()               # Refs, die sich seit dem letzten Nachführen geändert haben
        self._sperre = threading.Lock()
        self._gebaut = False
        katalog.b.hoeren(self._gemeldet)

    def _gemeldet(self, meldung):
        # Unter der Sperre von flatgraph: nur merken.
        refs = [meldung.get(x) for x in ("quelle", "ziel")] if meldung.get("kantenart") else [meldung.get("ref")]
        with self._sperre:
            self._offen.update(r for r in refs if r)

    def _felder_von(self, mid):
        m = self.db.get_node(ref(MODELL, mid), readonly=True)
        if m is None:
            return None
        h = self.k.datei_von(mid)
        d = (self.db.get_node(ref(DATEI, h), readonly=True) if h else None) or {}
        namen = lambda refs: " ".join(norm((self.db.get_node(r, readonly=True) or {}).get("name", "")) for r in refs)
        material = {f.get("typ") for p in d.get("platten") or [] for f in p.get("filamente", []) if f.get("typ")}
        return {
            "name": norm(m.get("name")),
            "tags": " ".join(norm(r.split("/", 1)[1]) for r in
                             self.db.get_connected(ref(MODELL, mid), rel_type=HAT_TAG)),
            "sammlungen": namen(self.db.get_connected(ref(MODELL, mid), rel_type=IN_SAMMLUNG)),
            "baugruppen": namen(self.db.get_connected(ref(MODELL, mid), direction="in", rel_type=ENTHAELT)),
            "titel": norm(d.get("titel")),
            "designer": norm(d.get("designer")),
            "ordner": " ".join(norm(o["pfad"].rsplit("/", 1)[0]) for o in d.get("orte", []) if "/" in o["pfad"]),
            "material": norm(" ".join(sorted(material))),
            "format": d.get("format") or "",
            "gedruckt": "ja" if m.get("gedruckt") else "nein",
            "favorit": "ja" if m.get("favorit") else "nein",
        }

    def _eintragen(self, mid):
        f = self._felder_von(mid)
        if f is None:
            self.felder.pop(mid, None)
            self.index.entfernen(mid)
            return
        self.felder[mid] = f
        self.index.eintragen(mid, {k: v for k, v in f.items() if k in FELDGEWICHT})

    def _betroffene(self, r):
        """Welche Modelle hängen an dieser Änderung? Ein Tag, eine Sammlung,
        eine Baugruppe oder eine Datei betrifft alle Modelle daran."""
        art, _, schluessel = r.partition("/")
        if art == MODELL:
            return {schluessel}
        return {x.split("/", 1)[1] for x in self.db.get_connected(r, direction="both", include_deleted=True)
                if x.startswith(MODELL + "/")}

    def nachfuehren(self):
        with self._sperre:
            offen, self._offen = self._offen, set()
        if not self._gebaut:
            for mid in self.db.list_nodes(MODELL, readonly=True):
                self._eintragen(mid)
            self._gebaut = True
            return
        mids = set()
        for r in offen:
            mids |= self._betroffene(r)
        for mid in mids:
            self._eintragen(mid)

    def suchen(self, q):
        """Treffer als {mid: punkte}, oder None bei leerer Anfrage."""
        a = zerlege(q)
        if not a:
            return None
        self.nachfuehren()
        begriffe = a.pflicht + [w for p in a.phrasen for w in p.split()]
        kandidaten = self.index.kandidaten(begriffe)
        if kandidaten is None:
            kandidaten = set(self.felder)
        for v in a.verboten:
            kandidaten -= self.index.knoten_mit(v)
        treffer = {}
        for mid in kandidaten:
            f = self.felder.get(mid)
            if f is None:
                continue
            gesamt = " | ".join(f[k] for k in FELDGEWICHT)
            if any(p not in gesamt for p in a.phrasen):
                continue
            passt = True
            for feld, wert, nicht in a.filter:
                if feld in GENAU:
                    drin = f.get(feld) == wert
                elif feld == "tags":
                    # Ein Tag ist ein Name, kein Text: tag:arm meint #arm, nicht #armatur.
                    drin = wert in f["tags"].split()
                else:
                    drin = wert in f.get(feld, "")
                if drin == nicht:
                    passt = False
                    break
            if passt:
                treffer[mid] = bewerten(f, a.phrasen + a.pflicht)
        return treffer
