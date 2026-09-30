"""
Ein Wortindex: welche Knoten enthalten welches Wort.

UNVERÄNDERTE KOPIE von pDMS `pdms/services/wortindex.py` (Stand
30.09.2026). Das Modul kennt keine Dokumente und keine Modelle, nur Knoten
und Text — deshalb passt es hier ohne Änderung. Zwei Anwender sind der
Beleg für den Umzug nach flatgraph; bis dahin wird hier nichts geändert,
sonst laufen die Kopien auseinander.

Teilwörter: ein Begriff, der nicht wörtlich im Vokabular steht, wird
gegen die WÖRTER geprüft statt gegen die Texte. Der Index liegt im
Arbeitsspeicher; der Neustart ist die Entwertung.
"""
import re

# Dieselbe Trennung wie in `suche.py::norm`: Unterstriche zählen
# wie Leerzeichen. Stünde hier eine andere Regel, fände der Index andere
# Treffer als die Suche davor — und zwar lautlos.
#
# `[\W_]` und nicht `[^\w]`: der Unterstrich gehört in Python zu `\w` und
# wäre damit Teil des Wortes geblieben. "Verification_Plan_001" wäre EIN
# Wort gewesen, und wer "Plan" sucht, fände es nur noch über die
# Teilwortsuche — also langsamer und mit anderer Bewertung.
_TRENNER = re.compile(r"[\W_]+", re.UNICODE)


def zerlegen(text: str) -> set[str]:
    """Text in seine Wörter, schon in Vergleichsform.

    Ein `set`, keine Liste: für die Frage „welche Knoten enthalten das
    Wort" zählt nicht, wie oft es vorkommt. Die Häufigkeit ist Sache der
    Bewertung, und die gehört dem Anwender.
    """
    if not text:
        return set()
    return {w for w in _TRENNER.split(text.lower()) if w}


class Wortindex:
    """Wort → Knoten. Vollständig im Arbeitsspeicher."""

    __slots__ = ("_posting", "_woerter_je_knoten")

    def __init__(self):
        # {wort: {knoten_id, …}}
        self._posting: dict[str, set[str]] = {}
        # {knoten_id: {wort, …}} — die Rückrichtung, ohne die ein Knoten
        # nicht zu entfernen wäre, ohne ALLE Postinglisten durchzugehen.
        # Sie kostet Speicher, spart aber genau den Volldurchgang, dessen
        # Abschaffung der Zweck des Index ist.
        self._woerter_je_knoten: dict[str, set[str]] = {}

    # ------------------------------------------------------------------
    # Schreiben
    # ------------------------------------------------------------------

    def eintragen(self, knoten_id: str, felder: dict[str, str]) -> None:
        """Einen Knoten aufnehmen oder ersetzen.

        Ersetzen und nicht ergänzen: `entfernen` läuft zuerst. Ohne das
        blieben die Wörter einer früheren Fassung stehen, und der Index
        fände einen Knoten unter einem Wort, das längst nicht mehr darin
        vorkommt — ein Fehler, der niemandem auffällt, weil die Suche ja
        Treffer liefert.
        """
        self.entfernen(knoten_id)
        woerter: set[str] = set()
        for text in (felder or {}).values():
            woerter |= zerlegen(text)
        if not woerter:
            return
        self._woerter_je_knoten[knoten_id] = woerter
        for wort in woerter:
            self._posting.setdefault(wort, set()).add(knoten_id)

    def entfernen(self, knoten_id: str) -> None:
        """Einen Knoten aus dem Index nehmen. Unbekannte Id ist kein Fehler."""
        woerter = self._woerter_je_knoten.pop(knoten_id, None)
        if not woerter:
            return
        for wort in woerter:
            treffer = self._posting.get(wort)
            if treffer is None:
                continue
            treffer.discard(knoten_id)
            # Leere Postinglisten werden weggeräumt, sonst wächst das
            # Vokabular mit jedem gelöschten Knoten weiter — und über das
            # Vokabular läuft die Teilwortsuche.
            if not treffer:
                del self._posting[wort]

    def leeren(self) -> None:
        self._posting.clear()
        self._woerter_je_knoten.clear()

    # ------------------------------------------------------------------
    # Lesen
    # ------------------------------------------------------------------

    def knoten_mit(self, begriff: str) -> set[str]:
        """Alle Knoten, in denen `begriff` als Wort ODER Wortteil vorkommt.

        Der genaue Treffer ist ein Nachschlagen. Nur wenn zusätzlich
        Wortteile in Frage kommen, wird das Vokabular durchgegangen — und
        das ist der Fall, sobald jemand etwas sucht, das nicht zufällig ein
        ganzes Wort ist.
        """
        begriff = (begriff or "").lower().strip()
        if not begriff:
            return set()
        treffer = set(self._posting.get(begriff, ()))
        for wort, ids in self._posting.items():
            if wort != begriff and begriff in wort:
                treffer |= ids
        return treffer

    def knoten_mit_ganzem_wort(self, begriff: str) -> set[str]:
        """Nur die Knoten, in denen der Begriff als EIGENES Wort steht.

        Der Unterschied zu `knoten_mit` ist der Bonus, den eine Bewertung
        daraus machen kann: wer „Plan" sucht, meint eher ein Dokument, in
        dem das Wort dasteht, als eines, in dem es in
        „Planungsabteilung" steckt. Getroffen wird beides — nur die
        Reihenfolge unterscheidet sich, und deshalb ist es ein Bonus und
        kein Filter.

        Das ist ein reines Nachschlagen: das Vokabular muss dafür nicht
        durchgegangen werden.
        """
        return set(self._posting.get((begriff or "").lower().strip(), ()))

    def kandidaten(self, begriffe) -> set[str] | None:
        """Knoten, die JEDEN der Begriffe enthalten.

        `None` heisst „keine Einschränkung" — bei leerer Eingabe soll der
        Aufrufer seinen ganzen Bestand behalten und nicht das leere
        Ergebnis, das ein `set()` bedeuten würde. Die Unterscheidung steht
        hier und nicht beim Aufrufer, weil sie sonst an jeder Aufrufstelle
        neu getroffen (und einmal falsch getroffen) würde.

        Der Schnitt läuft über die kleinste Menge zuerst: ein seltenes Wort
        engt stärker ein als ein häufiges, und danach sind die weiteren
        Schnitte billig.
        """
        gesucht = [b for b in (begriffe or []) if (b or "").strip()]
        if not gesucht:
            return None
        mengen = [self.knoten_mit(b) for b in gesucht]
        mengen.sort(key=len)
        treffer = mengen[0]
        for weitere in mengen[1:]:
            treffer &= weitere
            if not treffer:
                break
        return treffer

    # ------------------------------------------------------------------
    # Auskunft über sich selbst
    # ------------------------------------------------------------------

    @property
    def knoten(self) -> int:
        return len(self._woerter_je_knoten)

    @property
    def woerter(self) -> int:
        return len(self._posting)
