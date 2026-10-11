"""
Baugruppen: eine Stückliste, nicht nur eine Liste.

Eine Baugruppe (`ASSEMBLY`) enthält Positionen — Kanten `CONTAINS` zu
einem Modell, einer Unterbaugruppe oder einem Kaufteil, mit Menge und
Zähler „erledigt“ (gedruckt bzw. beschafft). Daraus folgt alles andere:
was fehlt noch, wie viel Filament welcher Farbe, welche Schrauben kaufen.

Mengen multiplizieren sich über die Ebenen: 4× Arm-Modul mit je 2 Haltern
sind 8 Halter. Der Zähler einer Position gilt über alle Exemplare, in
denen sie gebraucht wird (4 Module → „8 von 8 gedruckt“).

flatgraph ändert Kanten nicht an Ort und Stelle; eine Position ändern
heisst ihre Kante in einer Transaktion neu legen (wie in den Sammlungen).
"""
import contextlib
import csv
import io
import re
import threading

from . import standardteile
from .bestand import MATERIALIEN, MODELL  # noqa: F401 — MATERIALIEN für main
from .katalog import KatalogFehler, jetzt, ref
from .teilezugriff import Teilezugriff

BAUGRUPPE = "ASSEMBLY"
KAUFTEIL = "PURCHASED_PART"
EIGEN = "CUSTOM_COMPONENT"            # eigene Komponenten, siehe eigene.py
ENTHAELT = "CONTAINS"
# Projekt: die Klammer um einen Bau-Auftrag (KONZEPT §4.5a). Eigene Kante, damit der Kern (Löschvorschau, Suche, Aufräumen), der `CONTAINS`
# als „steckt in Baugruppe“ liest, unberührt bleibt. Dieselbe Positionslogik wie bei Baugruppen; ein Projekt steckt in nichts.
PROJEKT = "PROJECT"
BENOETIGT = "REQUIRES"
BEHAELTER = {BAUGRUPPE: ENTHAELT, PROJEKT: BENOETIGT}       # Art des Behälters -> Kante zu seinen Positionen

ARTEN = {MODELL: "modell", BAUGRUPPE: "baugruppe", KAUFTEIL: "kaufteil", EIGEN: "eigen"}
POSITIONSFELDER = ("menge", "erledigt", "material", "farbe", "notiz")
# Wo man ein Kaufteil bekommt: ein Verweis, die Artikelnummer beim Händler, ein Hinweis („mit Schraubensicherung“). Alles freiwillig.
BEZUGSFELDER = {"link": 500, "artikelnr": 60, "hinweis": 200}
VERLAUF_MAX = 100          # so viele Änderungen lassen sich zurücknehmen (nur im Speicher, bis zum Neustart)
FELDNAMEN = {"menge": "Menge", "erledigt": "Zähler", "material": "Material", "farbe": "Farbe", "notiz": "Notiz"}

# Gewicht ohne Slicer-Daten, geschätzt wie ein Slicer mit Standardwerten
# druckt: eine Hülle von 1,2 mm (2–3 Wände, Boden, Deckel) und 15 %
# Füllung innen. Massiv gerechnet käme ein 10-cm-Klotz auf das Drei- bis
# Vierfache. Es bleibt eine Schätzung, und die Oberfläche sagt das.
ROLLE_G = 1000
HUELLE_CM = 0.12
FUELLUNG = 0.15
DICHTE = {"PLA": 1.24, "PLA+": 1.24, "PETG": 1.27, "ABS": 1.04, "ASA": 1.07, "TPU": 1.21, "PA": 1.14, "PC": 1.20}

MENGE_IM_NAMEN = [re.compile(r"(?:^|[_\-\s])x(\d{1,3})(?:$|[_\-\s.])", re.I),
                  re.compile(r"(?:^|[_\-\s])(\d{1,3})x(?:$|[_\-\s.])", re.I)]


def menge_aus_namen(name):
    """`Arm_x4`, `4x_Arm` → 4 — so schreiben viele Designer die Stückzahl."""
    for muster in MENGE_IM_NAMEN:
        m = muster.search(name or "")
        if m and 0 < int(m.group(1)) <= 500:
            return int(m.group(1))
    return 1


class Baugruppen:
    def __init__(self, katalog):
        # Der Kern kommt nur über Teilezugriff herein (Sidecar, siehe dort); `db` für die eigenen Knoten.
        self.teile = Teilezugriff(katalog)
        self.db = katalog.db
        # Rückgängig/Wiederholen: eine Liste für alle Baugruppen (wie das Dokument eines Editors). Jeder Eintrag hält den Zustand der
        # betroffenen Baugruppen und Kaufteile vor und nach der Änderung; zurück heisst: den Zustand vorher wieder einsetzen.
        self._verlauf_sperre = threading.RLock()
        self._zurueck, self._vor = [], []
        self._standardteile_anlegen()

    def _standardteile_anlegen(self):
        vorhanden = self.db.list_nodes(KAUFTEIL, include_deleted=True, readonly=True)
        neu = {k: v for k, v in standardteile.katalog().items() if k not in vorhanden}
        if neu:
            with self.db.transaction():
                for k, v in neu.items():
                    self.db.create_node(KAUFTEIL, k, v)

    # ------------------------------------------------------------ Behälter: Baugruppe oder Projekt

    @staticmethod
    def _col(bid):
        """Kennungen von Projekten beginnen mit `p_`, die von Baugruppen mit `b_`."""
        return PROJEKT if bid.startswith("p_") else BAUGRUPPE

    def _b(self, bid):
        return ref(self._col(bid), bid)

    def _rel(self, bid):
        return BEHAELTER[self._col(bid)]

    # ------------------------------------------------------------ Rückgängig

    def _zustand(self, r):
        """Was an einem Knoten änderbar ist: bei einer Baugruppe Name, Beschreibung und Positionen (mit allen ihren Feldern und der
        Reihenfolge), bei einem Kaufteil die Bezugsangaben. None, wenn es den Knoten nicht mehr gibt."""
        col, _, kid = r.partition("/")
        if col in BEHAELTER:
            n = self.db.get_node_full(r)
            if n is None:
                return None
            return {"name": n["name"], "beschreibung": n.get("beschreibung", ""), **({"status": n.get("status", "")} if col == PROJEKT else {}),
                    "kanten": [(ziel, {k: v for k, v in kante.items() if k in (*POSITIONSFELDER, "position")})
                               for _, ziel, kante in self._positionen(kid)]}
        n = self.db.get_node(r, readonly=True)
        return None if n is None else {k: n.get(k) or "" for k in BEZUGSFELDER}

    def _herstellen(self, r, z):
        col, _, kid = r.partition("/")
        if z is None or self._zustand(r) is None:
            return                              # inzwischen gelöscht: nichts wiederherzustellen
        if col not in BEHAELTER:
            return self.db.update_node(KAUFTEIL, kid, z)
        self.db.update_node(col, kid, {k: v for k, v in z.items() if k != "kanten"})
        for eid, _, _ in self._positionen(kid):
            self.db.delete_edge(eid)
        for ziel, meta in z["kanten"]:
            if self.teile.existiert(ziel):      # ein Ziel, das es nicht mehr gibt, bleibt weg
                self.db.create_edge(ref(col, kid), ziel, BEHAELTER[col], meta=dict(meta))

    def _unterbaugruppen(self, bid, gesehen=None):
        gesehen = gesehen if gesehen is not None else set()
        gesehen.add(bid)
        for _, r, _ in self._positionen(bid):
            col, _, kid = r.partition("/")
            if col == BAUGRUPPE and kid not in gesehen:
                self._unterbaugruppen(kid, gesehen)
        return gesehen

    @contextlib.contextmanager
    def _protokolliert(self, text, knoten):
        """Merkt sich, was `knoten` (Verweise) vor und nach dem Block waren. Ändert sich nichts oder scheitert der Block, kommt kein
        Eintrag in die Liste."""
        vorher = {r: self._zustand(r) for r in knoten}
        yield
        nachher = {r: self._zustand(r) for r in knoten}
        if nachher == vorher:
            return
        with self._verlauf_sperre:
            self._zurueck.append({"text": text, "vorher": vorher, "nachher": nachher})
            del self._zurueck[:-VERLAUF_MAX]
            self._vor.clear()                   # nach einer neuen Änderung gibt es nichts mehr zu wiederholen

    def _verlauf_schritt(self, von, nach, zustand_key, leer):
        with self._verlauf_sperre:
            if not von:
                raise KatalogFehler(leer)
            eintrag = von[-1]
            with self.db.transaction():
                for r, z in eintrag[zustand_key].items():
                    self._herstellen(r, z)
            nach.append(von.pop())
            return eintrag["text"]

    def rueckgaengig(self):
        return self._verlauf_schritt(self._zurueck, self._vor, "vorher", "Nichts zum Rückgängigmachen.")

    def wiederholen(self):
        return self._verlauf_schritt(self._vor, self._zurueck, "nachher", "Nichts zu wiederholen.")

    def verlauf(self):
        with self._verlauf_sperre:
            return {"zurueck": self._zurueck[-1]["text"] if self._zurueck else None, "vor": self._vor[-1]["text"] if self._vor else None,
                    "schritte": len(self._zurueck)}

    # ------------------------------------------------------------ Kaufteile

    def kaufteile(self, suche=None, kategorie=None):
        liste = []
        woerter = [w.lower() for w in (suche or "").split() if w]
        for k, v in self.db.list_nodes(KAUFTEIL, readonly=True).items():
            if kategorie and v.get("kategorie") != kategorie:
                continue
            text = f"{v.get('name', '')} {v.get('norm', '')} {v.get('gewinde', '')}".lower().replace("×", "x")
            if all(w.replace("×", "x") in text for w in woerter):
                liste.append({"id": k, **v})

        def schluessel(t):
            # M3×8 vor M3×10: Zahlen im Namen als Zahlen sortieren.
            return [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", t["name"].lower())]
        return sorted(liste, key=lambda t: (standardteile.KATEGORIEN.index(t["kategorie"])
                                            if t.get("kategorie") in standardteile.KATEGORIEN else 99, schluessel(t)))

    def kaufteil_anlegen(self, name, kategorie="Eigene", einheit="Stück"):
        name = (name or "").strip()
        if not name or len(name) > 120:
            raise KatalogFehler("Name leer oder zu lang.")
        kid = self.db.next_id(KAUFTEIL, "eigen-", 4)
        self.db.create_node(KAUFTEIL, kid, {"name": name, "kategorie": kategorie or "Eigene",
                                            "einheit": einheit or "Stück", "standard": False})
        return kid

    def kaufteil_aendern(self, kid, werte):
        """Bezugsquelle, Artikelnummer und Hinweis eines Kaufteils (auch der mitgelieferten Normteile). Der Link steht später als Verweis
        in der Oberfläche: nur http und https, sonst liesse sich dort Skript einschleusen."""
        if self.db.get_node(f"{KAUFTEIL}/{kid}", readonly=True) is None:
            raise KatalogFehler("Dieses Kaufteil gibt es nicht.")
        neu = {}
        for k, v in werte.items():
            if k not in BEZUGSFELDER:
                raise KatalogFehler(f"Feld {k!r} gibt es an einem Kaufteil nicht.")
            v = str(v or "").strip()
            if len(v) > BEZUGSFELDER[k]:
                raise KatalogFehler(f"{k} ist zu lang (höchstens {BEZUGSFELDER[k]} Zeichen).")
            if k == "link" and v and not re.fullmatch(r"https?://[^\s<>\"']+", v, re.I):
                raise KatalogFehler("Der Link muss mit http:// oder https:// beginnen.")
            neu[k] = v
        if neu:
            with self._protokolliert("Bezugsquelle ändern", [f"{KAUFTEIL}/{kid}"]):
                self.db.update_node(KAUFTEIL, kid, neu)

    # ------------------------------------------------------------ Baugruppen

    def _pruefen(self, bid):
        b = self.db.get_node(self._b(bid), readonly=True)
        if b is None:
            raise KatalogFehler(f"{'Projekt' if self._col(bid) == PROJEKT else 'Baugruppe'} {bid} gibt es nicht.")
        return b

    def anlegen(self, name, positionen=()):
        return self._anlegen(BAUGRUPPE, name, positionen)

    def projekt_anlegen(self, name, positionen=()):
        return self._anlegen(PROJEKT, name, positionen)

    def _anlegen(self, col, name, positionen):
        name = (name or "").strip()
        if not name or len(name) > 120:
            raise KatalogFehler("Name leer oder zu lang.")
        with self.db.transaction():
            bid = self.db.next_id(col, "p_" if col == PROJEKT else "b_", 4)
            self.db.create_node(col, bid, {"name": name, "beschreibung": "", **({"status": "Entwurf"} if col == PROJEKT else {}), "angelegt": jetzt()})
            for r, menge in positionen:
                self._hinzufuegen(bid, r, menge)
        return bid

    def aus_modellen(self, name, modelle):
        """Menge aus dem Dateinamen vorschlagen (`Arm_x4`) — der Anwender
        korrigiert, statt alles einzutippen."""
        positionen = []
        for mid in modelle:
            modellname = self.teile.modell_name(mid)
            if modellname is not None:
                positionen.append((ref(MODELL, mid), menge_aus_namen(modellname)))
        return self.anlegen(name, positionen)

    def aendern(self, bid, werte):
        b = self._pruefen(bid)
        neu = {}
        if "name" in werte:
            name = (werte["name"] or "").strip()
            if not name:
                raise KatalogFehler("Name leer.")
            neu["name"] = name[:120]
        if "beschreibung" in werte:
            neu["beschreibung"] = str(werte["beschreibung"] or "")[:4000]
        if "status" in werte:
            # Frei gewählt und ohne Wirkung (Entwurf, In Arbeit, Fertig …) — kein Freigabeverfahren; nur Projekte haben ihn.
            if self._col(bid) != PROJEKT:
                raise KatalogFehler("Nur ein Projekt hat einen Status.")
            neu["status"] = str(werte["status"] or "").strip()[:40]
        if neu:
            text = " und ".join(n for n, k in (("Name", "name"), ("Beschreibung", "beschreibung"), ("Status", "status")) if k in neu) + " ändern"
            with self._protokolliert(f"{text} ({b['name']})", [self._b(bid)]):
                self.db.update_node(self._col(bid), bid, neu)

    def loeschen(self, bid):
        """Die Baugruppe geht; Modelle und Kaufteile bleiben."""
        self._pruefen(bid)
        self.db.soft_delete(self._col(bid), bid)

    # ------------------------------------------------------------ Positionen

    def _positionen(self, bid):
        """[(kanten_id, ziel_ref, kante)] in Reihenfolge, nur lebende Ziele."""
        liste = [(eid, e["target"], e) for eid, e in
                 self.db.get_connected_edges(self._b(bid), direction="out", rel_type=self._rel(bid))
                 if self.db.get_node(e["target"], readonly=True) is not None]
        return sorted(liste, key=lambda p: (p[2].get("position", 0), p[1]))

    def _enthaelt(self, von_bid, gesucht_bid, gesehen=None):
        gesehen = gesehen or set()
        if von_bid == gesucht_bid:
            return True
        gesehen.add(von_bid)
        for _, r, _ in self._positionen(von_bid):
            col, _, kid = r.partition("/")
            if col == BAUGRUPPE and kid not in gesehen and self._enthaelt(kid, gesucht_bid, gesehen):
                return True
        return False

    def _hinzufuegen(self, bid, ziel, menge=1):
        col, _, kid = ziel.partition("/")
        if col not in ARTEN or not self.teile.existiert(ziel):
            raise KatalogFehler(f"{ziel} lässt sich nicht hinzufügen.")
        if col == BAUGRUPPE and self._enthaelt(kid, bid):
            raise KatalogFehler("Eine Baugruppe kann sich nicht selbst enthalten.")
        menge = max(1, min(int(menge or 1), 10_000))
        vorhanden = next((p for p in self._positionen(bid) if p[1] == ziel), None)
        if vorhanden:
            # Nochmal dazu heisst: eins mehr — so fühlt sich Ziehen richtig an.
            return self._neu_legen(bid, vorhanden, {"menge": vorhanden[2].get("menge", 1) + menge})
        pos = max((p[2].get("position", 0) for p in self._positionen(bid)), default=-1) + 1
        self.db.create_edge(self._b(bid), ziel, self._rel(bid),
                            meta={"menge": menge, "erledigt": 0, "position": pos})

    def _neu_legen(self, bid, position, aenderung):
        eid, ziel, kante = position
        meta = {k: kante[k] for k in (*POSITIONSFELDER, "position") if k in kante}
        meta.update(aenderung)
        self.db.delete_edge(eid)
        self.db.create_edge(self._b(bid), ziel, self._rel(bid), meta=meta)

    def hinzufuegen(self, bid, ziel, menge=1):
        b = self._pruefen(bid)
        with self._protokolliert(f"Teil hinzufügen ({b['name']})", [self._b(bid)]), self.db.transaction():
            self._hinzufuegen(bid, ziel, menge)

    def position_aendern(self, bid, ziel, werte):
        b = self._pruefen(bid)
        p = next((p for p in self._positionen(bid) if p[1] == ziel), None)
        if p is None:
            raise KatalogFehler("Diese Position gibt es nicht.")
        aenderung = {}
        for k, v in werte.items():
            if k not in POSITIONSFELDER:
                raise KatalogFehler(f"Feld {k!r} gibt es an einer Position nicht.")
            if k in ("menge", "erledigt"):
                try:
                    v = int(v)
                except (TypeError, ValueError):
                    raise KatalogFehler(f"{k} muss eine Zahl sein.")
                v = max(1 if k == "menge" else 0, min(v, 100_000))
            elif k == "farbe":
                # Die Farbe landet als CSS in der Oberfläche: nur #RRGGBB.
                v = str(v or "").strip() or None
                if v and not re.fullmatch(r"#[0-9a-fA-F]{6}", v):
                    raise KatalogFehler("Farbe als #RRGGBB angeben.")
            elif k == "material":
                # Die Position nennt den Material-Knoten beim Namen; es gibt ihn danach.
                v = self.teile.material_knoten(v) if str(v or "").strip() else None
            else:
                v = str(v or "").strip()[:200] or None
            aenderung[k] = v
        text = " und ".join(FELDNAMEN[k] for k in aenderung) + " ändern"
        with self._protokolliert(f"{text} ({b['name']})", [self._b(bid)]), self.db.transaction():
            self._neu_legen(bid, p, aenderung)

    def material_fuer_offene(self, bid, material, farbe=None):
        """Material (und Farbe) für alle Druckteile ohne Angabe, über alle
        Ebenen — so weit, wie die Filament-Übersicht zählt. Ein Klick statt
        zwanzig."""
        b = self._pruefen(bid)
        with self._protokolliert(f"Material für alle offenen Teile setzen ({b['name']})",
                                 [self._b(x) for x in self._unterbaugruppen(bid)]), self.db.transaction():
            self._material_setzen(bid, self.teile.material_knoten(material), farbe, set())

    def _material_setzen(self, bid, material, farbe, gesehen):
        if bid in gesehen:
            return
        gesehen.add(bid)
        for p in self._positionen(bid):
            col, _, kid = p[1].partition("/")
            if col == BAUGRUPPE:
                self._material_setzen(kid, material, farbe, gesehen)
                continue
            if col != MODELL or p[2].get("material") or not self._modell_daten(kid)[1]["material_angenommen"]:
                continue
            aenderung = {"material": material}
            if farbe and not p[2].get("farbe"):
                aenderung["farbe"] = farbe
            self._neu_legen(bid, p, aenderung)

    def position_entfernen(self, bid, ziel):
        b = self._pruefen(bid)
        with self._protokolliert(f"Position entfernen ({b['name']})", [self._b(bid)]):
            for eid, r, _ in self._positionen(bid):
                if r == ziel:
                    self.db.delete_edge(eid)

    def ordnen(self, bid, ziele):
        b = self._pruefen(bid)
        alt = self._positionen(bid)
        reihe = [r for r in dict.fromkeys(ziele) if any(p[1] == r for p in alt)] + \
                [p[1] for p in alt if p[1] not in ziele]
        with self._protokolliert(f"Reihenfolge ändern ({b['name']})", [self._b(bid)]), self.db.transaction():
            for p in alt:
                self._neu_legen(bid, p, {"position": reihe.index(p[1])})

    # ------------------------------------------------------------ Auswerten

    def standard(self):
        """Was gilt, wo nichts angegeben ist — aus den Einstellungen (wie in
        pDMS). Wer nur PLA+ druckt, soll nicht jedes Teil anfassen müssen."""
        e = self.teile.einstellungen()
        return {"material": (e.get("standard_material") or "PLA").upper(),
                "farbe": e.get("standard_farbe") or None,
                "rolle_g": int(e.get("rolle_g") or ROLLE_G)}

    def _modell_daten(self, mid, material=None, farbe=None, standard=None):
        kurz, d = self.teile.modell(mid)
        platten = d.get("platten") or []
        fil = next((f for p in platten for f in p.get("filamente", [])), {})
        gewicht, geschaetzt = kurz["gewicht_g"], False
        # Reihenfolge: an der Position gesetzt, aus dem Slicer, sonst der
        # Standard aus den Einstellungen — dann als „angenommen“ markiert.
        standard = standard or self.standard()
        stoff = (material or kurz["material"] or "").upper() or None
        stoff_angenommen = stoff is None
        stoff = stoff or standard["material"]
        if gewicht is None and d.get("volumen_cm3"):
            volumen = d["volumen_cm3"]
            if d.get("flaeche_cm2"):
                huelle = min(volumen, d["flaeche_cm2"] * HUELLE_CM)
                volumen = huelle + FUELLUNG * (volumen - huelle)
            gewicht = volumen * DICHTE.get(stoff or "PLA", 1.24)   # gerundet wird erst die Summe
            geschaetzt = True
        zeit = sum(p.get("zeit_s") or 0 for p in platten) or None
        farbe = farbe or fil.get("farbe")
        farbe_angenommen = farbe is None
        return kurz, {"gewicht_g": gewicht, "geschaetzt": geschaetzt, "zeit_s": zeit,
                      "material": stoff, "material_angenommen": stoff_angenommen,
                      "farbe": farbe or standard["farbe"], "farbe_angenommen": farbe_angenommen}

    def _aufloesen(self, bid, faktor=1, pfad=()):
        """Blätter der Stückliste mit Gesamtmenge: (art, id, kante, bedarf)."""
        if bid in pfad:
            return
        for _, r, kante in self._positionen(bid):
            col, _, kid = r.partition("/")
            bedarf = kante.get("menge", 1) * faktor
            if col == BAUGRUPPE:
                yield from self._aufloesen(kid, bedarf, (*pfad, bid))
            else:
                yield ARTEN[col], kid, kante, bedarf

    def fortschritt(self, bid):
        """Stück, getrennt nach Druck- und Kaufteilen — zusammengezählt hiess
        „3 von 45“, und niemand wusste, was die 45 sind."""
        f = {"bedarf": 0, "erledigt": 0, "druck_bedarf": 0, "druck_erledigt": 0, "kauf_bedarf": 0, "kauf_erledigt": 0,
             "eigen_bedarf": 0, "eigen_erledigt": 0}
        for art, _, kante, b in self._aufloesen(bid):
            fertig = min(kante.get("erledigt", 0), b)
            teil = {"modell": "druck", "eigen": "eigen"}.get(art, "kauf")
            f[f"{teil}_bedarf"] += b
            f[f"{teil}_erledigt"] += fertig
            f["bedarf"] += b
            f["erledigt"] += fertig
        return f

    def liste(self):
        ergebnis = []
        for bid, b in self.db.list_nodes(BAUGRUPPE, readonly=True).items():
            f = self.fortschritt(bid)
            ergebnis.append({"id": bid, "name": b["name"], **f, "positionen": len(self._positionen(bid)),
                             "verwendet_in": len(self.verwendet_in(ref(BAUGRUPPE, bid)))})
        return sorted(ergebnis, key=lambda x: x["name"].lower())

    def projekte(self):
        ergebnis = [{"id": pid, "name": p["name"], "status": p.get("status", ""), **self.fortschritt(pid), "positionen": len(self._positionen(pid))}
                    for pid, p in self.db.list_nodes(PROJEKT, readonly=True).items()]
        return sorted(ergebnis, key=lambda x: x["name"].lower())

    def verbaut_in(self, ziel):
        """Wo steckt dieses Teil — über alle Ebenen bis zur obersten Baugruppe. Je Verwendung ein Weg von oben nach unten
        („Drohne › Arm-Modul“) mit der Menge je Ebene und der Gesamtmenge. Gegenstück zu `verwendet_in`, das nur die Eltern nennt."""
        wege = []

        def eltern_kanten(knoten):      # in Baugruppen (CONTAINS) und in Projekten (REQUIRES)
            return [e for rel in BEHAELTER.values() for _, e in self.db.get_connected_edges(knoten, direction="in", rel_type=rel)]

        def hoch(knoten, weg, faktor, gesehen):
            eltern = [(e["source"], e.get("menge", 1)) for e in eltern_kanten(knoten)]
            for quelle, menge in sorted(eltern):
                if quelle in gesehen:
                    continue
                b = self.db.get_node(quelle, readonly=True)
                if b is None:
                    continue
                schritt = {"id": quelle.split("/", 1)[1], "name": b["name"], "menge": menge}
                neu = [schritt] + weg
                if eltern_kanten(quelle):
                    hoch(quelle, neu, faktor * menge, gesehen | {quelle})
                else:
                    wege.append({"weg": neu, "gesamt": faktor * menge})
        hoch(ziel, [], 1, {ziel})
        return sorted(wege, key=lambda w: (w["weg"][0]["name"].lower(), [x["name"].lower() for x in w["weg"]]))

    def exemplare(self, bid, pfad=()):
        """Wie oft wird diese Baugruppe insgesamt gebraucht? Oben 1; als
        Unterbaugruppe die Mengen der Eltern, multipliziert bis nach oben.
        Die Zähler ihrer Positionen gelten über alle diese Exemplare."""
        eltern = [(e["source"].split("/", 1)[1], e.get("menge", 1))
                  for _, e in self.db.get_connected_edges(ref(BAUGRUPPE, bid), direction="in", rel_type=ENTHAELT)
                  if self.db.get_node(e["source"], readonly=True) is not None]
        if not eltern or bid in pfad:
            return 1
        return sum(menge * self.exemplare(eid, (*pfad, bid)) for eid, menge in eltern)

    def verwendet_in(self, ziel):
        """Welche Baugruppen enthalten dieses Teil — die eingehenden Kanten."""
        ergebnis = []
        for eid, e in self.db.get_connected_edges(ziel, direction="in", rel_type=ENTHAELT):
            b = self.db.get_node(e["source"], readonly=True)
            if b is not None:
                ergebnis.append({"id": e["source"].split("/", 1)[1], "name": b["name"], "menge": e.get("menge", 1)})
        return sorted(ergebnis, key=lambda x: x["name"].lower())

    def detail(self, bid):
        b = self._pruefen(bid)
        exemplare = self.exemplare(bid)
        positionen = []
        for _, r, kante in self._positionen(bid):
            col, _, kid = r.partition("/")
            art = ARTEN[col]
            eintrag = {"ref": r, "art": art, "id": kid, **{k: kante.get(k) for k in POSITIONSFELDER}}
            eintrag["menge"] = kante.get("menge", 1)
            eintrag["erledigt"] = kante.get("erledigt", 0)
            eintrag["bedarf"] = eintrag["menge"] * exemplare
            if art == "modell":
                kurz, daten = self._modell_daten(kid, kante.get("material"), kante.get("farbe"))
                eintrag.update(name=kurz["name"], format=kurz["format"], hash=kurz["hash"], vorschau=kurz["vorschau"],
                               bild=kurz["bild"], fehlt=kurz["fehlt"], entwurf=kurz["entwurf"], masse=kurz["masse"],
                               **{f"je_{k}": v for k, v in daten.items()})
                eintrag["material"] = daten["material"]
                eintrag["farbe"] = daten["farbe"]
                eintrag["material_angenommen"] = daten["material_angenommen"]
                eintrag["farbe_angenommen"] = daten["farbe_angenommen"]
            elif art == "kaufteil":
                t = self.db.get_node(r, readonly=True)
                eintrag.update(name=t["name"], kategorie=t.get("kategorie"), einheit=t.get("einheit", "Stück"),
                               link=t.get("link") or "", artikelnr=t.get("artikelnr") or "", hinweis=t.get("hinweis") or "")
            elif art == "eigen":
                e = self.db.get_node(r, readonly=True)
                eintrag.update(name=e["name"], eigen_art=e.get("art") or "", eigen_masse=e.get("masse") or "",
                               eigen_notiz=e.get("notiz") or "", eigen_bild=(e.get("bild") or {}).get("k"),
                               eigen_datei=(e.get("datei") or {}).get("name"))
            else:
                u = self.db.get_node(r, readonly=True)
                f = self.fortschritt(kid)
                eintrag.update(name=u["name"], unter_bedarf=f["bedarf"], unter_erledigt=f["erledigt"],
                               unter_positionen=len(self._positionen(kid)))
            positionen.append(eintrag)
        return {"id": bid, "art": "projekt" if self._col(bid) == PROJEKT else "baugruppe", "name": b["name"], "status": b.get("status", ""),
                "beschreibung": self.db.get_node_full(self._b(bid)).get("beschreibung", ""), "exemplare": exemplare,
                "positionen": positionen, "fortschritt": self.fortschritt(bid),
                "summen": self.summen(bid), "verwendet_in": self.verwendet_in(self._b(bid)),
                "materialien": self.teile.materialien(), "verlauf": self.verlauf()}

    def summen(self, bid):
        """Was die ganze Baugruppe braucht, über alle Ebenen: Gewicht, Zeit,
        Filament je Material und Farbe, Einkaufsliste der Kaufteile."""
        standard = self.standard()
        zeiten = {}
        gewicht = rest_gewicht = zeit = rest_zeit = 0.0
        geschaetzt = False
        ohne_daten = 0
        filament, kauf = {}, {}
        druckteile = kaufteile = 0
        eigene = {}
        ohne_zeit = 0
        for art, kid, kante, bedarf in self._aufloesen(bid):
            offen = max(0, bedarf - kante.get("erledigt", 0))
            if art == "modell":
                druckteile += bedarf
                kurz, d = self._modell_daten(kid, kante.get("material"), kante.get("farbe"), standard)
                z = zeiten.setdefault(kid, {"id": kid, "name": kurz["name"], "stueck": 0, "offen": 0,
                                            "je_s": d["zeit_s"], "farbe": d["farbe"]})
                z["stueck"] += bedarf
                z["offen"] += offen
                if d["gewicht_g"] is None:
                    ohne_daten += 1
                    continue
                geschaetzt |= d["geschaetzt"]
                gewicht += d["gewicht_g"] * bedarf
                rest_gewicht += d["gewicht_g"] * offen
                ohne_zeit += 0 if d["zeit_s"] else 1
                zeit += (d["zeit_s"] or 0) * bedarf
                rest_zeit += (d["zeit_s"] or 0) * offen
                schluessel = (d["material"], d["farbe"])
                eintrag = filament.setdefault(schluessel, {"material": schluessel[0], "farbe": schluessel[1],
                                                          "gesamt_g": 0.0, "offen_g": 0.0, "angenommen_g": 0.0})
                eintrag["gesamt_g"] += d["gewicht_g"] * bedarf
                eintrag["offen_g"] += d["gewicht_g"] * offen
                if d["material_angenommen"]:
                    eintrag["angenommen_g"] += d["gewicht_g"] * bedarf
            elif art == "eigen":      # zählt weder zu Filament noch zum Einkauf
                e = self.db.get_node(f"{EIGEN}/{kid}", readonly=True)
                x = eigene.setdefault(kid, {"id": kid, "name": e["name"], "art": e.get("art") or "", "bedarf": 0,
                                            "bild": (e.get("bild") or {}).get("k")})
                x["bedarf"] += bedarf
            else:
                kaufteile += bedarf
                t = self.db.get_node(f"{KAUFTEIL}/{kid}", readonly=True)
                e = kauf.setdefault(kid, {"id": kid, "name": t["name"], "einheit": t.get("einheit", "Stück"),
                                          "kategorie": t.get("kategorie"), "bedarf": 0, "offen": 0,
                                          "link": t.get("link") or "", "artikelnr": t.get("artikelnr") or "", "hinweis": t.get("hinweis") or ""})
                e["bedarf"] += bedarf
                e["offen"] += offen
        runden = lambda x: round(x, 1)
        # Je Material zusammengefasst, mit seinen Farben: „124 g TPU in
        # Schwarz und Rot“ — das ist die Frage vor dem Drucken, nicht die
        # Gesamtsumme. Rollen zu 1 kg, der üblichen Grösse.
        materialien = {}
        for v in filament.values():
            m = materialien.setdefault(v["material"], {"material": v["material"], "gesamt_g": 0.0, "offen_g": 0.0,
                                                       "angenommen_g": 0.0, "farben": []})
            m["gesamt_g"] += v["gesamt_g"]
            m["offen_g"] += v["offen_g"]
            m["angenommen_g"] += v["angenommen_g"]
            m["farben"].append({"farbe": v["farbe"], "gesamt_g": runden(v["gesamt_g"]), "offen_g": runden(v["offen_g"])})
        materialien = sorted(({**m, "gesamt_g": runden(m["gesamt_g"]), "offen_g": runden(m["offen_g"]),
                               "angenommen_g": runden(m["angenommen_g"]),
                               "rollen": round(m["gesamt_g"] / standard["rolle_g"], 2),
                               "farben": sorted(m["farben"], key=lambda f: -f["gesamt_g"])}
                              for m in materialien.values()),
                             key=lambda m: (m["material"] is None, -m["gesamt_g"]))
        return {
            "druckteile": druckteile, "kaufteile": kaufteile,
            "gewicht_g": runden(gewicht), "offen_gewicht_g": runden(rest_gewicht), "gewicht_geschaetzt": geschaetzt,
            "zeit_s": int(zeit), "offen_zeit_s": int(rest_zeit), "ohne_daten": ohne_daten, "ohne_zeit": ohne_zeit,
            "filament": sorted(({**v, "gesamt_g": runden(v["gesamt_g"]), "offen_g": runden(v["offen_g"])}
                                for v in filament.values()), key=lambda x: -x["gesamt_g"]),
            "einkauf": sorted(kauf.values(), key=lambda x: (x["kategorie"] or "", x["name"])),
            "eigene": sorted(eigene.values(), key=lambda x: x["name"].lower()),
            "materialien": materialien,
            "rolle_g": standard["rolle_g"], "standard": standard,
            # Druckzeit je Teil, längste zuerst — „was frisst die Zeit?“
            "zeiten": sorted(({**z, "gesamt_s": (z["je_s"] or 0) * z["stueck"], "offen_s": (z["je_s"] or 0) * z["offen"]}
                              for z in zeiten.values()), key=lambda z: (z["je_s"] is None, -((z["je_s"] or 0) * z["stueck"]))),
        }

    def fehlende_in_warteschlange(self, bid):
        n = 0
        for art, kid, kante, bedarf in self._aufloesen(bid):
            if art == "modell" and kante.get("erledigt", 0) < bedarf:
                self.teile.in_warteschlange(kid)
                n += 1
        return n

    def export(self, bid, art="csv"):
        d = self.detail(bid)
        zeilen = [("Art", "Menge", "Einheit", "Erledigt", "Name", "Material", "Farbe", "Notiz", "Bezugsquelle", "Artikelnr")]
        bezug = {e["id"]: e for e in d["summen"]["einkauf"]}
        for p in d["positionen"]:
            notiz = p.get("notiz") or ""
            if p["art"] == "eigen":      # Art, Maße und Notiz des Teils stehen mit in der Zeile
                notiz = ", ".join(x for x in (p.get("eigen_art"), p.get("eigen_masse"), p.get("eigen_notiz"), notiz) if x)
            zeilen.append(({"modell": "Druckteil", "kaufteil": "Kaufteil", "baugruppe": "Baugruppe", "eigen": "Eigene Komponente"}[p["art"]],
                           p["menge"], p.get("einheit") or "Stück", p["erledigt"], p["name"],
                           p.get("material") or "", p.get("farbe") or "", notiz,
                           bezug.get(p["id"], {}).get("link", "") if p["art"] == "kaufteil" else "",
                           bezug.get(p["id"], {}).get("artikelnr", "") if p["art"] == "kaufteil" else ""))
        if art == "csv":
            puffer = io.StringIO()
            csv.writer(puffer, delimiter=";").writerows(zeilen)
            return puffer.getvalue()
        md = [f"# {d['name']}", "", d["beschreibung"] or "", "",
              "| " + " | ".join(zeilen[0]) + " |", "|" + "---|" * len(zeilen[0])]
        md += ["| " + " | ".join(str(x).replace("|", "/") for x in z) + " |" for z in zeilen[1:]]
        s = d["summen"]
        if s["einkauf"]:
            md += ["", "## Einkaufsliste (alle Ebenen)", ""] + [f"- {e['bedarf']} {e['einheit']} {e['name']}" + (f" — {e['link']}" if e["link"] else "") + (f" ({e['artikelnr']})" if e["artikelnr"] else "")
                                                                  + (f" · {e['hinweis']}" if e["hinweis"] else "") for e in s["einkauf"]]
        if s["eigene"]:
            md += ["", "## Eigene Komponenten (alle Ebenen)", ""] + [
                f"- {e['bedarf']}× {e['name']}" + (f" ({e['art']})" if e["art"] else "") for e in s["eigene"]]
        if s["filament"]:
            md += ["", "## Filament", ""] + [f"- {m['material']}: {m['gesamt_g']} g (" + ", ".join(
                f"{x['farbe'] or 'Farbe offen'} {x['gesamt_g']} g" for x in m["farben"]) + ")" for m in s["materialien"]]
        return "\n".join(md) + "\n"

    def aus_sammlung(self, sid):
        s = self.db.get_node(f"COLLECTION/{sid}", readonly=True)
        if s is None:
            raise KatalogFehler("Sammlung gibt es nicht.")
        return self.aus_modellen(s["name"], [x["id"] for x in self.teile.modelle(sammlung=sid)])

    def aus_ordner(self, ordner_id):
        # Entwürfe nicht: der Ordner eines Projekts hält oft viele Konstruktionsstände, die Stückliste braucht den einen.
        alle = self.teile.modelle(ordner=ordner_id)
        modelle = [m for m in alle if not m["entwurf"]]
        if not modelle:
            raise KatalogFehler("Im Ordner liegen nur Entwürfe." if alle else "Im Ordner liegen keine Modelle.")
        name = ordner_id.rstrip("/").split("/")[-1] if "/" in ordner_id else (self.teile.ordner_name(ordner_id) or ordner_id)
        return self.aus_modellen(name, [m["id"] for m in modelle])

    def vorschlaege(self, mindestens=3):
        """Ordner mit mehreren Modellen, die noch keine Baugruppe sind — zum
        Anlegen mit einem Klick. Heute nur aus Ordnern (Schritt 2: mehr)."""
        namen = {b["name"].lower() for b in self.liste()}
        # Die Namen aus den Kacheln (zwischengespeichert), nicht je Modell aus der Datenbank: das waren bei 8 600 Modellen 3,3–3,9 s je
        # Aufruf, solange eingelesen wurde (jeder Zugriff wartete auf die Schreibsperre).
        je_ordner = {}                      # Ordner -> Namen der Modelle darin
        for m in self.teile.modelle():
            if m["entwurf"]:
                continue
            for o in m["ordner"]:
                if "/" in o and o.split("/", 1)[1]:
                    je_ordner.setdefault(o, []).append(m["name"])
        vorschlag = [{"ordner": o, "name": o.rstrip("/").split("/")[-1], "anzahl": len(n),
                      "mengen_im_namen": sum(1 for x in n if menge_aus_namen(x) > 1)}
                     for o, n in je_ordner.items() if len(n) >= mindestens]
        vorschlag = [v for v in vorschlag if v["name"].lower() not in namen]
        return sorted(vorschlag, key=lambda v: (-v["mengen_im_namen"], -v["anzahl"]))[:12]
