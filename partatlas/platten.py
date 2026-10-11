"""
Druckplatten: wie ein Projekt auf Platten verteilt wird.

Eine Platte (`PRINT_PLATE`) gehört zu genau einem Projekt (`HAS_PLATE`) und hält Modelle mit Mengen (`PRINTS`): acht Halter dürfen auf zwei
Platten zu je vier liegen. „Verteilt“ heisst: Summe der Mengen auf allen Platten des Projekts ≥ Bedarf aus der Stückliste des Projekts —
über alle Baugruppen darunter. Ein Teil darf auch mehr als nötig auf Platten liegen (Reserve); die Rechnung zählt dann nur den Bedarf
und meldet den Überschuss, statt Daten stillschweigend zu ändern (KONZEPT §4.5a).

Sidecar wie die Baugruppen: Modelle nur über ihre Kennung, den Kern nur über `Teilezugriff`.
"""
from .baugruppen import PROJEKT
from .bestand import MODELL
from .katalog import KatalogFehler, jetzt, ref

PLATTE = "PRINT_PLATE"
HAT_PLATTE = "HAS_PLATE"
DRUCKT = "PRINTS"
MENGE_MAX = 10_000


class Platten:
    def __init__(self, baugruppen):
        self.bg = baugruppen
        self.db = baugruppen.db
        self.teile = baugruppen.teile
        baugruppen._behandler[PLATTE] = (self._zustand, self._herstellen)
        baugruppen._loesch_haken.append(self._projekt_geloescht)

    # ------------------------------------------------------------ Hilfen

    def _pruefen(self, plid):
        p = self.db.get_node(ref(PLATTE, plid), readonly=True)
        if p is None:
            raise KatalogFehler(f"Druckplatte {plid} gibt es nicht.")
        return p

    def _projekt_von(self, plid):
        for _, e in self.db.get_connected_edges(ref(PLATTE, plid), direction="in", rel_type=HAT_PLATTE):
            return e["source"].split("/", 1)[1]
        raise KatalogFehler(f"Druckplatte {plid} gehört zu keinem Projekt.")

    def _plattenkennungen(self, pid):
        """Kennungen der lebenden Platten eines Projekts, in der Reihenfolge ihrer Anlage."""
        ids = [e["target"].split("/", 1)[1] for _, e in
               self.db.get_connected_edges(ref(PROJEKT, pid), direction="out", rel_type=HAT_PLATTE)
               if self.db.get_node(e["target"], readonly=True) is not None]
        return sorted(ids)

    def _posten(self, plid):
        """[(kanten_id, ziel_ref, kante)] — nur Modelle, die es noch gibt."""
        liste = [(eid, e["target"], e) for eid, e in self.db.get_connected_edges(ref(PLATTE, plid), direction="out", rel_type=DRUCKT)
                 if self.teile.existiert(e["target"])]
        return sorted(liste, key=lambda p: (p[2].get("position", 0), p[1]))

    def _modell_ref(self, ziel):
        col, _, mid = (ziel or "").partition("/")
        if col != MODELL or not self.teile.existiert(ziel):
            raise KatalogFehler("Auf eine Druckplatte kommen nur Modelle.")
        return mid

    def _menge(self, menge):
        try:
            menge = int(menge)
        except (TypeError, ValueError):
            raise KatalogFehler("Die Menge muss eine Zahl sein.")
        return max(0, min(menge, MENGE_MAX))

    def _setzen(self, plid, ziel, menge):
        """Menge eines Modells auf der Platte setzen; 0 nimmt es herunter. Kanten ändert flatgraph nicht an Ort und Stelle: neu legen."""
        alt = next((p for p in self._posten(plid) if p[1] == ziel), None)
        position = alt[2].get("position") if alt else max((p[2].get("position", 0) for p in self._posten(plid)), default=-1) + 1
        if alt:
            self.db.delete_edge(alt[0])
        if menge > 0:
            self.db.create_edge(ref(PLATTE, plid), ziel, DRUCKT, meta={"menge": menge, "position": position})

    def _menge_auf(self, plid, ziel):
        return next((p[2].get("menge", 0) for p in self._posten(plid) if p[1] == ziel), 0)

    # ------------------------------------------------------------ Anlegen, Ändern, Löschen

    def anlegen(self, pid, name=None, material=None):
        self.bg._pruefen(pid)
        if self.bg._col(pid) != PROJEKT:
            raise KatalogFehler("Druckplatten gehören zu einem Projekt.")
        name = (name or "").strip() or f"Platte {len(self._plattenkennungen(pid)) + 1}"
        if len(name) > 60:
            raise KatalogFehler("Name zu lang.")
        stoff = self.teile.material_knoten(material) if str(material or "").strip() else None
        with self.db.transaction():
            plid = self.db.next_id(PLATTE, "pl_", 4)
            self.db.create_node(PLATTE, plid, {"name": name, "material": stoff, "angelegt": jetzt()})
            self.db.create_edge(ref(PROJEKT, pid), ref(PLATTE, plid), HAT_PLATTE)
        return plid

    def aendern(self, plid, werte, kontext=None):
        p = self._pruefen(plid)
        neu = {}
        if "name" in werte:
            name = (werte["name"] or "").strip()
            if not name or len(name) > 60:
                raise KatalogFehler("Name leer oder zu lang.")
            neu["name"] = name
        if "material" in werte:
            neu["material"] = self.teile.material_knoten(werte["material"]) if str(werte["material"] or "").strip() else None
        if neu:
            with self.bg._protokolliert(f"Platte ändern ({p['name']})", [ref(PLATTE, plid)], kontext or self._projekt_von(plid)):
                self.db.update_node(PLATTE, plid, neu)

    def loeschen(self, plid):
        """Die Platte geht; Modelle bleiben, ihre Teile gelten danach wieder als nicht verteilt."""
        self._pruefen(plid)
        self.db.soft_delete(PLATTE, plid)

    def _projekt_geloescht(self, pid):
        if self.bg._col(pid) == PROJEKT:
            for plid in self._plattenkennungen(pid):
                self.db.soft_delete(PLATTE, plid)

    # ------------------------------------------------------------ Verteilen

    def posten_setzen(self, plid, ziel, menge, kontext=None):
        p = self._pruefen(plid)
        self._modell_ref(ziel)
        menge = self._menge(menge)
        with self.bg._protokolliert(f"Menge auf {p['name']} ändern", [ref(PLATTE, plid)], kontext or self._projekt_von(plid)), self.db.transaction():
            self._setzen(plid, ziel, menge)

    def rest_auflegen(self, plid, ziel, kontext=None):
        """Was von diesem Teil im Projekt noch auf keiner Platte liegt, kommt auf diese."""
        p = self._pruefen(plid)
        self._modell_ref(ziel)
        pid = self._projekt_von(plid)
        rest = self.verteilung(pid)["offen"].get(ziel.split("/", 1)[1], 0)
        if rest <= 0:
            raise KatalogFehler("Davon ist schon alles verteilt.")
        with self.bg._protokolliert(f"Teile auf {p['name']} legen", [ref(PLATTE, plid)], kontext or pid), self.db.transaction():
            self._setzen(plid, ziel, self._menge_auf(plid, ziel) + rest)

    def verteilen(self, pid, ziel, von, nach, kontext=None):
        """Eine Zeile von Platte `von` auf Platte `nach` verschieben; `von` leer heisst „noch nicht verteilt“ (es kommt, was fehlt),
        `nach` leer heisst „zurück nach nicht verteilt“. Ein Schritt im Verlauf."""
        self.bg._pruefen(pid)
        mid = self._modell_ref(ziel)
        von, nach = von or "", nach or ""
        if von == nach:
            return
        for plid in (von, nach):
            if plid and self._projekt_von(plid) != pid:
                raise KatalogFehler("Diese Druckplatte gehört zu einem anderen Projekt.")
        if von and not self._menge_auf(von, ziel):
            raise KatalogFehler("Dieses Teil liegt nicht auf der Platte.")
        menge = self._menge_auf(von, ziel) if von else self.verteilung(pid)["offen"].get(mid, 0)
        if menge <= 0:
            raise KatalogFehler("Davon ist schon alles verteilt.")
        namen = [self._pruefen(x)["name"] for x in (von, nach) if x]
        with self.bg._protokolliert(f"Teile verschieben ({' → '.join(namen) or 'nicht verteilt'})",
                                    [ref(PLATTE, x) for x in (von, nach) if x], kontext or pid), self.db.transaction():
            if von:
                self._setzen(von, ziel, 0)
            if nach:
                self._setzen(nach, ziel, self._menge_auf(nach, ziel) + menge)

    def verteilung(self, pid):
        """Bedarf (aus der Stückliste des Projekts), verteilt, offen und Überschuss je Modell; `ges`/`ver` als Summen in Stück."""
        bedarf, verteilt = {}, {}
        for art, kid, _, b in self.bg._aufloesen(pid):
            if art == "modell":
                bedarf[kid] = bedarf.get(kid, 0) + b
        for plid in self._plattenkennungen(pid):
            for _, ziel, kante in self._posten(plid):
                mid = ziel.split("/", 1)[1]
                verteilt[mid] = verteilt.get(mid, 0) + kante.get("menge", 0)
        offen = {m: b - verteilt.get(m, 0) for m, b in bedarf.items() if b > verteilt.get(m, 0)}
        zu_viel = {m: v - bedarf.get(m, 0) for m, v in verteilt.items() if v > bedarf.get(m, 0)}
        return {"bedarf": bedarf, "verteilt": verteilt, "offen": offen, "zu_viel": zu_viel,
                "ges": sum(bedarf.values()), "ver": sum(min(b, verteilt.get(m, 0)) for m, b in bedarf.items())}

    def liste(self, pid):
        """Die Platten des Projekts mit ihren Teilen und was sie brauchen (Gewicht, Zeit — wie die Stückliste: Slicer-Wert, sonst Schätzung)."""
        self.bg._pruefen(pid)
        standard = self.bg.standard()
        platten = []
        for plid in self._plattenkennungen(pid):
            node = self.db.get_node(ref(PLATTE, plid), readonly=True)
            posten, gewicht, zeit, geschaetzt, ohne_daten = [], 0.0, 0.0, False, 0
            for _, ziel, kante in self._posten(plid):
                mid, menge = ziel.split("/", 1)[1], kante.get("menge", 0)
                kurz, d = self.bg._modell_daten(mid, node.get("material"), None, standard)
                posten.append({"ref": ziel, "id": mid, "name": kurz["name"], "menge": menge, "bild": kurz["bild"], "hash": kurz["hash"],
                               "format": kurz["format"], "je_gewicht_g": d["gewicht_g"], "je_zeit_s": d["zeit_s"]})
                if d["gewicht_g"] is None:
                    ohne_daten += 1
                    continue
                geschaetzt |= d["geschaetzt"]
                gewicht += d["gewicht_g"] * menge
                zeit += (d["zeit_s"] or 0) * menge
            platten.append({"id": plid, "name": node["name"], "material": node.get("material"), "posten": posten,
                            "stueck": sum(p["menge"] for p in posten), "gewicht_g": round(gewicht, 1), "gewicht_geschaetzt": geschaetzt,
                            "zeit_s": int(zeit), "ohne_daten": ohne_daten})
        return {"platten": platten, "verteilung": self.verteilung(pid)}

    # ------------------------------------------------------------ Rückgängig

    def _zustand(self, plid):
        n = self.db.get_node_full(ref(PLATTE, plid))
        if n is None:
            return None
        return {"name": n["name"], "material": n.get("material"),
                "posten": [(ziel, {"menge": k.get("menge", 0), "position": k.get("position", 0)}) for _, ziel, k in self._posten(plid)]}

    def _herstellen(self, plid, z):
        self.db.update_node(PLATTE, plid, {"name": z["name"], "material": z["material"]})
        for eid, _, _ in self._posten(plid):
            self.db.delete_edge(eid)
        for ziel, meta in z["posten"]:
            if self.teile.existiert(ziel):
                self.db.create_edge(ref(PLATTE, plid), ziel, DRUCKT, meta=dict(meta))
