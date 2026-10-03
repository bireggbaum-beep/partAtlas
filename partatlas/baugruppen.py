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
import csv
import io
import re

from . import standardteile
from .bestand import MATERIALIEN, MODELL  # noqa: F401 — MATERIALIEN für main
from .katalog import KatalogFehler, jetzt, ref

BAUGRUPPE = "ASSEMBLY"
KAUFTEIL = "PURCHASED_PART"
EIGEN = "CUSTOM_COMPONENT"            # EIGENE: eigene Komponenten, siehe eigene.py
ENTHAELT = "CONTAINS"

ARTEN = {MODELL: "modell", BAUGRUPPE: "baugruppe", KAUFTEIL: "kaufteil", EIGEN: "eigen"}
POSITIONSFELDER = ("menge", "erledigt", "material", "farbe", "notiz")

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
        self.k = katalog
        self.db = katalog.db
        self._standardteile_anlegen()

    def _standardteile_anlegen(self):
        vorhanden = self.db.list_nodes(KAUFTEIL, include_deleted=True, readonly=True)
        neu = {k: v for k, v in standardteile.katalog().items() if k not in vorhanden}
        if neu:
            with self.db.transaction():
                for k, v in neu.items():
                    self.db.create_node(KAUFTEIL, k, v)

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

    # ------------------------------------------------------------ Baugruppen

    def _pruefen(self, bid):
        b = self.db.get_node(ref(BAUGRUPPE, bid), readonly=True)
        if b is None:
            raise KatalogFehler(f"Baugruppe {bid} gibt es nicht.")
        return b

    def anlegen(self, name, positionen=()):
        name = (name or "").strip()
        if not name or len(name) > 120:
            raise KatalogFehler("Name leer oder zu lang.")
        with self.db.transaction():
            bid = self.db.next_id(BAUGRUPPE, "b_", 4)
            self.db.create_node(BAUGRUPPE, bid, {"name": name, "beschreibung": "", "angelegt": jetzt()})
            for r, menge in positionen:
                self._hinzufuegen(bid, r, menge)
        return bid

    def aus_modellen(self, name, modelle):
        """Menge aus dem Dateinamen vorschlagen (`Arm_x4`) — der Anwender
        korrigiert, statt alles einzutippen."""
        positionen = []
        for mid in modelle:
            m = self.db.get_node(ref(MODELL, mid), readonly=True)
            if m is not None:
                positionen.append((ref(MODELL, mid), menge_aus_namen(m.get("name"))))
        return self.anlegen(name, positionen)

    def aendern(self, bid, werte):
        self._pruefen(bid)
        neu = {}
        if "name" in werte:
            name = (werte["name"] or "").strip()
            if not name:
                raise KatalogFehler("Name leer.")
            neu["name"] = name[:120]
        if "beschreibung" in werte:
            neu["beschreibung"] = str(werte["beschreibung"] or "")[:4000]
        if neu:
            self.db.update_node(BAUGRUPPE, bid, neu)

    def loeschen(self, bid):
        """Die Baugruppe geht; Modelle und Kaufteile bleiben."""
        self._pruefen(bid)
        self.db.soft_delete(BAUGRUPPE, bid)

    # ------------------------------------------------------------ Positionen

    def _positionen(self, bid):
        """[(kanten_id, ziel_ref, kante)] in Reihenfolge, nur lebende Ziele."""
        liste = [(eid, e["target"], e) for eid, e in
                 self.db.get_connected_edges(ref(BAUGRUPPE, bid), direction="out", rel_type=ENTHAELT)
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
        if col not in ARTEN or self.db.get_node(ziel, readonly=True) is None:
            raise KatalogFehler(f"{ziel} lässt sich nicht hinzufügen.")
        if col == BAUGRUPPE and self._enthaelt(kid, bid):
            raise KatalogFehler("Eine Baugruppe kann sich nicht selbst enthalten.")
        menge = max(1, min(int(menge or 1), 10_000))
        vorhanden = next((p for p in self._positionen(bid) if p[1] == ziel), None)
        if vorhanden:
            # Nochmal dazu heisst: eins mehr — so fühlt sich Ziehen richtig an.
            return self._neu_legen(bid, vorhanden, {"menge": vorhanden[2].get("menge", 1) + menge})
        pos = max((p[2].get("position", 0) for p in self._positionen(bid)), default=-1) + 1
        self.db.create_edge(ref(BAUGRUPPE, bid), ziel, ENTHAELT,
                            meta={"menge": menge, "erledigt": 0, "position": pos})

    def _neu_legen(self, bid, position, aenderung):
        eid, ziel, kante = position
        meta = {k: kante[k] for k in (*POSITIONSFELDER, "position") if k in kante}
        meta.update(aenderung)
        self.db.delete_edge(eid)
        self.db.create_edge(ref(BAUGRUPPE, bid), ziel, ENTHAELT, meta=meta)

    def hinzufuegen(self, bid, ziel, menge=1):
        self._pruefen(bid)
        with self.db.transaction():
            self._hinzufuegen(bid, ziel, menge)

    def position_aendern(self, bid, ziel, werte):
        self._pruefen(bid)
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
                v = self.k.material_knoten(v) if str(v or "").strip() else None
            else:
                v = str(v or "").strip()[:200] or None
            aenderung[k] = v
        with self.db.transaction():
            self._neu_legen(bid, p, aenderung)

    def material_fuer_offene(self, bid, material, farbe=None):
        """Material (und Farbe) für alle Druckteile ohne Angabe, über alle
        Ebenen — so weit, wie die Filament-Übersicht zählt. Ein Klick statt
        zwanzig."""
        with self.db.transaction():
            self._material_setzen(bid, self.k.material_knoten(material), farbe, set())

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
        for eid, r, _ in self._positionen(bid):
            if r == ziel:
                self.db.delete_edge(eid)

    def ordnen(self, bid, ziele):
        alt = self._positionen(bid)
        reihe = [r for r in dict.fromkeys(ziele) if any(p[1] == r for p in alt)] + \
                [p[1] for p in alt if p[1] not in ziele]
        with self.db.transaction():
            for p in alt:
                self._neu_legen(bid, p, {"position": reihe.index(p[1])})

    # ------------------------------------------------------------ Auswerten

    def standard(self):
        """Was gilt, wo nichts angegeben ist — aus den Einstellungen (wie in
        pDMS). Wer nur PLA+ druckt, soll nicht jedes Teil anfassen müssen."""
        e = self.k.b.einstellungen()
        return {"material": (e.get("standard_material") or "PLA").upper(),
                "farbe": e.get("standard_farbe") or None,
                "rolle_g": int(e.get("rolle_g") or ROLLE_G)}

    def _modell_daten(self, mid, material=None, farbe=None, standard=None):
        m = self.db.get_node(ref(MODELL, mid), readonly=True)
        kurz = self.k._kurz(mid, m)
        h = kurz["hash"]
        d = self.db.get_node(f"PART_GEOMETRY/{h}", readonly=True) if h else None
        d = d or {}
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
            teil = {"modell": "druck", "eigen": "eigen"}.get(art, "kauf")      # EIGENE
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
                eintrag.update(name=t["name"], kategorie=t.get("kategorie"), einheit=t.get("einheit", "Stück"))
            elif art == "eigen":      # EIGENE
                e = self.db.get_node(r, readonly=True)
                eintrag.update(name=e["name"], eigen_art=e.get("art") or "", eigen_masse=e.get("masse") or "",
                               eigen_notiz=e.get("notiz") or "", eigen_bild=(e.get("bild") or {}).get("k"))
            else:
                u = self.db.get_node(r, readonly=True)
                f = self.fortschritt(kid)
                eintrag.update(name=u["name"], unter_bedarf=f["bedarf"], unter_erledigt=f["erledigt"],
                               unter_positionen=len(self._positionen(kid)))
            positionen.append(eintrag)
        return {"id": bid, "name": b["name"], "beschreibung": self.db.get_node_full(ref(BAUGRUPPE, bid)).get("beschreibung", ""), "exemplare": exemplare,
                "positionen": positionen, "fortschritt": self.fortschritt(bid),
                "summen": self.summen(bid), "verwendet_in": self.verwendet_in(ref(BAUGRUPPE, bid)),
                "materialien": self.k.materialien()}

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
        eigene = {}      # EIGENE
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
            elif art == "eigen":      # EIGENE: zählt weder zu Filament noch zum Einkauf
                e = self.db.get_node(f"{EIGEN}/{kid}", readonly=True)
                x = eigene.setdefault(kid, {"id": kid, "name": e["name"], "art": e.get("art") or "", "bedarf": 0,
                                            "bild": (e.get("bild") or {}).get("k")})
                x["bedarf"] += bedarf
            else:
                kaufteile += bedarf
                t = self.db.get_node(f"{KAUFTEIL}/{kid}", readonly=True)
                e = kauf.setdefault(kid, {"id": kid, "name": t["name"], "einheit": t.get("einheit", "Stück"),
                                          "kategorie": t.get("kategorie"), "bedarf": 0, "offen": 0})
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
            "eigene": sorted(eigene.values(), key=lambda x: x["name"].lower()),      # EIGENE
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
                self.k.in_warteschlange(kid)
                n += 1
        return n

    def export(self, bid, art="csv"):
        d = self.detail(bid)
        zeilen = [("Art", "Menge", "Einheit", "Erledigt", "Name", "Material", "Farbe", "Notiz")]
        for p in d["positionen"]:
            notiz = p.get("notiz") or ""
            if p["art"] == "eigen":      # EIGENE: Art, Maße und Notiz des Teils stehen mit in der Zeile
                notiz = ", ".join(x for x in (p.get("eigen_art"), p.get("eigen_masse"), p.get("eigen_notiz"), notiz) if x)
            zeilen.append(({"modell": "Druckteil", "kaufteil": "Kaufteil", "baugruppe": "Baugruppe", "eigen": "Eigene Komponente"}[p["art"]],
                           p["menge"], p.get("einheit") or "Stück", p["erledigt"], p["name"],
                           p.get("material") or "", p.get("farbe") or "", notiz))
        if art == "csv":
            puffer = io.StringIO()
            csv.writer(puffer, delimiter=";").writerows(zeilen)
            return puffer.getvalue()
        md = [f"# {d['name']}", "", d["beschreibung"] or "", "",
              "| " + " | ".join(zeilen[0]) + " |", "|" + "---|" * len(zeilen[0])]
        md += ["| " + " | ".join(str(x).replace("|", "/") for x in z) + " |" for z in zeilen[1:]]
        s = d["summen"]
        if s["einkauf"]:
            md += ["", "## Einkaufsliste (alle Ebenen)", ""] + [f"- {e['bedarf']} {e['einheit']} {e['name']}" for e in s["einkauf"]]
        if s["eigene"]:      # EIGENE
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
        return self.aus_modellen(s["name"], [x["id"] for x in self.k.modelle(sammlung=sid)])

    def aus_ordner(self, ordner_id):
        # Entwürfe nicht: der Ordner eines Projekts hält oft viele Konstruktionsstände, die Stückliste braucht den einen.
        alle = self.k.modelle(ordner=ordner_id)
        modelle = [m for m in alle if not m["entwurf"]]
        if not modelle:
            raise KatalogFehler("Im Ordner liegen nur Entwürfe." if alle else "Im Ordner liegen keine Modelle.")
        name = ordner_id.rstrip("/").split("/")[-1] if "/" in ordner_id else (self.k.wurzeln().get(ordner_id, {}).get("name") or ordner_id)
        return self.aus_modellen(name, [m["id"] for m in modelle])

    def vorschlaege(self, mindestens=3):
        """Ordner mit mehreren Modellen, die noch keine Baugruppe sind — zum
        Anlegen mit einem Klick. Heute nur aus Ordnern (Schritt 2: mehr)."""
        namen = {b["name"].lower() for b in self.liste()}
        zaehler = {}
        for m in self.k.modelle():
            if m["entwurf"]:
                continue
            for o in m["ordner"]:
                if "/" in o and o.split("/", 1)[1]:
                    zaehler.setdefault(o, []).append(m["id"])
        vorschlag = [{"ordner": o, "name": o.rstrip("/").split("/")[-1], "anzahl": len(ids),
                      "mengen_im_namen": sum(1 for mid in ids if menge_aus_namen(
                          (self.db.get_node(ref(MODELL, mid), readonly=True) or {}).get("name")) > 1)}
                     for o, ids in zaehler.items() if len(ids) >= mindestens]
        vorschlag = [v for v in vorschlag if v["name"].lower() not in namen]
        return sorted(vorschlag, key=lambda v: (-v["mengen_im_namen"], -v["anzahl"]))[:12]
