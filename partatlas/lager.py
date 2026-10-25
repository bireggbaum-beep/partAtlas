"""
Filamentlager: die Spulen, die der Anwender hat (nach dem 3MF Katalog Manager, dort „Material Manager“).

Eine Spule (`MATERIAL_SPOOL`) trägt Material, Hersteller, Farbe, Durchmesser, Start- und Restgewicht, Preis, Lagerort und Notiz.
Das Restgewicht stimmt, soweit der Anwender es pflegt; abgezogen wird erst, wenn ein Druck die Spule nennt (drucke.py).
Eine Spule ist kein Modell: sie lässt sich löschen (Anwender 25.10.2026), mit Rückgängig — der Knoten geht in den Papierkorb des Graphen und kommt zurück.
Ein Bild an der Spule liegt wie die Fotos im Vault. `reicht` beantwortet „Reicht das Filament?“ für den Bedarf eines geslicten Projekts.
"""
import re

from .bestand import SPULE
from .katalog import KatalogFehler, jetzt, ref

FELDER = ("material", "hersteller", "farbname", "farbe", "ort", "durchmesser", "start_g", "rest_g", "preis", "notiz")
MAX_ANZAHL = 20
VORGABE_START_G = 1000.0


def _text(wert, name, laenge, pflicht=False):
    t = (wert or "").strip() if isinstance(wert, str) or wert is None else str(wert).strip()
    if pflicht and not t:
        raise KatalogFehler(f"{name}: bitte ausfüllen.")
    if len(t) > laenge:
        raise KatalogFehler(f"{name}: höchstens {laenge} Zeichen.")
    return t


def _zahl(wert, name, klein, gross, einheit=""):
    try:
        z = float(str(wert).replace(",", "."))
    except (TypeError, ValueError):
        raise KatalogFehler(f"{name}: keine Zahl.")
    if not klein <= z <= gross:
        raise KatalogFehler(f"{name}: zwischen {klein:g} und {gross:g}{einheit}.")
    return z


def pruefen(felder):
    """Eingaben prüfen und bereinigen; nur die genannten Felder, ohne Vorgaben (die setzt `anlegen`)."""
    neu = {}
    for k in felder:
        if k not in FELDER:
            raise KatalogFehler(f"Feld {k!r} gibt es an der Spule nicht.")
    if "material" in felder:
        neu["material"] = _text(felder["material"], "Material", 30, pflicht=True)
    for k, name, n in (("hersteller", "Hersteller", 60), ("farbname", "Farbname", 40), ("ort", "Lagerort", 60), ("notiz", "Notiz", 500)):
        if k in felder:
            neu[k] = _text(felder[k], name, n)
    if "farbe" in felder:
        f = _text(felder["farbe"], "Farbe", 7)
        if f and not re.fullmatch(r"#[0-9a-fA-F]{6}", f):
            raise KatalogFehler("Farbe: ein Farbwert wie #1a1a1a.")
        neu["farbe"] = f.lower()
    if "durchmesser" in felder:
        neu["durchmesser"] = _zahl(felder["durchmesser"], "Durchmesser", 1.0, 3.5, " mm")
    if "start_g" in felder:
        neu["start_g"] = _zahl(felder["start_g"], "Gewicht der vollen Spule", 1, 20000, " g")
    if "rest_g" in felder:
        neu["rest_g"] = round(_zahl(felder["rest_g"], "Rest", 0, 20000, " g"), 1)
    if "preis" in felder:
        neu["preis"] = None if felder["preis"] in (None, "") else round(_zahl(felder["preis"], "Preis", 0, 10000), 2)
    return neu


class Lager:
    def __init__(self, katalog):
        self.k = katalog
        self.db = katalog.db

    def liste(self):
        """Alle Spulen, nach Material und Farbe sortiert."""
        aus = [{"id": sid, **d} for sid, d in self.db.list_nodes(SPULE, readonly=True).items()]
        aus.sort(key=lambda s: (s.get("material", ""), s.get("farbname", ""), s["id"]))
        return aus

    def _spule(self, sid):
        d = self.db.get_node(ref(SPULE, sid), readonly=True)
        if d is None:
            raise KatalogFehler("Diese Spule gibt es nicht.")
        return d

    def anlegen(self, felder, anzahl=1):
        """Legt `anzahl` gleiche Spulen an (jede mit eigenem Rest). Ohne Restgewicht ist die Spule voll."""
        try:
            anzahl = int(anzahl)
        except (TypeError, ValueError):
            raise KatalogFehler("Anzahl: keine Zahl.")
        if not 1 <= anzahl <= MAX_ANZAHL:
            raise KatalogFehler(f"Anzahl: zwischen 1 und {MAX_ANZAHL}.")
        felder = felder or {}
        if "material" not in felder:
            raise KatalogFehler("Material: bitte ausfüllen.")
        daten = pruefen(felder)
        daten.setdefault("durchmesser", 1.75)
        daten.setdefault("start_g", VORGABE_START_G)
        daten.setdefault("rest_g", daten["start_g"])
        for k in ("hersteller", "farbname", "farbe", "ort", "notiz"):
            daten.setdefault(k, "")
        daten.setdefault("preis", None)
        if daten["rest_g"] > daten["start_g"]:
            raise KatalogFehler("Der Rest kann nicht grösser sein als die volle Spule.")
        ids = []
        with self.db.transaction():
            for _ in range(anzahl):
                sid = self.db.next_id(SPULE, "sp_", 5)
                self.db.create_node(SPULE, sid, {**daten, "angelegt": jetzt()})
                ids.append(sid)
        return ids

    def aendern(self, sid, felder):
        alt = self._spule(sid)
        neu = pruefen(felder)
        start, rest = neu.get("start_g", alt.get("start_g")), neu.get("rest_g", alt.get("rest_g"))
        if rest is not None and start is not None and rest > start:
            raise KatalogFehler("Der Rest kann nicht grösser sein als die volle Spule.")
        if neu:
            with self.db.transaction():
                self.db.update_node(SPULE, sid, neu)

    def nachkaufen(self, sid, anzahl, felder=None):
        """Eine Spule nachgekauft, die es schon gibt: `anzahl` neue, volle Spulen mit Material, Hersteller, Farbe und Durchmesser der Vorlage;
        Menge, Preis und Lagerort lassen sich dabei anpassen (3MF Katalog: „Nachkaufen“). Die Vorlage bleibt, wie sie ist."""
        vorlage = self._spule(sid)
        eigen = pruefen({k: v for k, v in (felder or {}).items() if k in ("start_g", "preis", "ort")})
        daten = {k: vorlage.get(k) for k in ("material", "hersteller", "farbname", "farbe", "durchmesser", "start_g", "preis", "ort", "notiz")}
        daten.update(eigen)
        daten["rest_g"] = daten["start_g"]
        ids = self.anlegen({k: v for k, v in daten.items() if v is not None}, anzahl)
        if vorlage.get("bild"):
            with self.db.transaction():
                for i in ids:
                    self.db.update_node(SPULE, i, {"bild": vorlage["bild"]})
        return ids

    def loeschen(self, sid):
        self._spule(sid)
        with self.db.transaction():
            self.db.soft_delete(SPULE, sid)

    def wiederherstellen(self, sid):
        """Das Rückgängig nach dem Löschen."""
        if self.db.get_node_raw(ref(SPULE, sid)) is None:
            raise KatalogFehler("Diese Spule gibt es nicht mehr.")
        with self.db.transaction():
            self.db.restore_node(SPULE, sid)

    # ------------------------------------------------------------ Bild

    def bild_setzen(self, sid, daten):
        """Ein Foto der Spule (PNG, JPG, WebP bis 5 MB); es ersetzt das bisherige, das im Vault bleibt (Nachkaufen teilt es sich)."""
        self._spule(sid)
        if len(daten) > MAX_BILD:
            raise KatalogFehler("Bild grösser als 5 MB.")
        k, rel = self.k.bild_ablegen(self.k.png_aus(daten), f"spule_{sid}")
        with self.db.transaction():
            self.db.update_node(SPULE, sid, {"bild": {"k": k, "datei": rel}})
        return k

    def bild_entfernen(self, sid):
        self._spule(sid)
        with self.db.transaction():
            self.db.update_node(SPULE, sid, {"bild": None})

    def bild_pfad(self, sid):
        d = self.db.get_node(ref(SPULE, sid), readonly=True) or self.db.get_node_raw(ref(SPULE, sid)) or {}
        b = d.get("bild")
        return self.k.b.pfad(*b["datei"].split("/")) if b else None

    # ------------------------------------------------------------ Abbuchen

    @staticmethod
    def euro_je_g(s):
        return s["preis"] / s["start_g"] if s.get("preis") and s.get("start_g") else None

    def abbuchen(self, sid, g):
        """Zieht `g` Gramm vom Rest ab, nie unter 0 (der Aufrufer hält die Transaktion). Gibt zurück, was wirklich abgezogen wurde und was es kostete."""
        s = self._spule(sid)
        g = _zahl(g, "Verbrauch", 0.01, 20000, " g")
        abgezogen = round(min(g, s["rest_g"]), 2)
        self.db.update_node(SPULE, sid, {"rest_g": round(s["rest_g"] - abgezogen, 2)})
        je_g = self.euro_je_g(s)
        name = " ".join(x for x in (s.get("hersteller"), s.get("farbname")) if x) or s["material"]
        return {"spule": sid, "name": f"{s['material']} · {name}" if name != s["material"] else s["material"], "g": abgezogen,
                "kosten": round(abgezogen * je_g, 2) if je_g else None}

    def vorschlag(self, typ, farbe, g):
        """Die Spule, von der ein Druck mit diesem Filament am ehesten abgezogen wird (dieselbe Zuteilung wie bei „Reicht das Filament?“)."""
        f = self.reicht([{"typ": typ, "farbe": farbe, "g": g}])["filamente"][0]
        return f["spulen"][0]["id"] if f["spulen"] else None

    # ------------------------------------------------------------ Reicht das Filament?

    @staticmethod
    def bedarf_aus_platten(platten):
        """[{typ, farbe, g}] aus den Platten eines geslicten 3MF, gleiche Filamente zusammengezählt; leer, wenn die Datei keine Mengen kennt."""
        summe = {}
        for p in platten or []:
            for f in p.get("filamente") or []:
                if not f.get("g"):
                    continue
                k = ((f.get("typ") or "").strip(), (f.get("farbe") or "").lower()[:7])
                summe[k] = summe.get(k, 0) + f["g"]
        return [{"typ": t, "farbe": c, "g": round(g, 2)} for (t, c), g in summe.items()]

    def reicht(self, bedarf, frei=None):
        """Für jedes Filament des Projekts (`[{typ, farbe, g}]`, über alle Platten zusammengezählt): welche Spule reicht?

        Gleiches Material und ähnliche Farbe (3MF Katalog). Ergebnis je Filament: `reicht` (eine Spule hat genug), `wechsel` (nur mit einer zweiten
        Spule), `reicht_nicht` (mit `fehlt_g`), `unklar` (keine passende Spule oder kein Bedarf bekannt). `frei` {Spule: Rest}: was schon für
        andere vorgesehen ist, ist abgezogen — so zählt eine Spule nicht doppelt, auch nicht über mehrere Modelle der Warteschlange hinweg."""
        spulen = self.liste()
        if frei is None:
            frei = {s["id"]: s["rest_g"] for s in spulen}
        info = {s["id"]: s for s in spulen}
        aus = []
        for f in sorted(bedarf, key=lambda f: -(f.get("g") or 0)):
            g = f.get("g")
            eintrag = {"typ": f.get("typ"), "farbe": f.get("farbe"), "bedarf_g": g, "spulen": [], "fehlt_g": 0}
            if not g or not f.get("typ"):
                aus.append({**eintrag, "status": "unklar", "grund": "Bedarf nicht bekannt"})
                continue
            pass_ = sorted((s for s in spulen if _gleiches_material(s["material"], f["typ"]) and frei.get(s["id"], 0) > 0),
                           key=lambda s: (_farbabstand(s.get("farbe"), f.get("farbe")), -frei[s["id"]]))
            pass_ = [s for s in pass_ if _farbabstand(s.get("farbe"), f.get("farbe")) <= FARB_GRENZE]
            if not pass_:
                aus.append({**eintrag, "status": "unklar", "grund": "Keine passende Spule"})
                continue
            ganz = next((s for s in pass_ if frei[s["id"]] >= g), None)
            if ganz:
                frei[ganz["id"]] -= g
                aus.append({**eintrag, "status": "reicht", "spulen": [_kurz(info[ganz["id"]], g)]})
                continue
            noetig, genommen = g, []
            for s in pass_:
                nimm = min(frei[s["id"]], noetig)
                genommen.append(_kurz(info[s["id"]], nimm))
                frei[s["id"]] -= nimm
                noetig -= nimm
                if noetig <= 0:
                    break
            aus.append({**eintrag, "status": "wechsel" if noetig <= 0 else "reicht_nicht", "spulen": genommen, "fehlt_g": round(max(noetig, 0), 2)})
        schlimmst = max((a["status"] for a in aus), key=ENGE.index, default="unklar")
        # Materialkosten: nur, wo eine Spule mit Preis zugeteilt ist; fehlt bei einem Filament der Preis, ist die Summe unvollständig.
        preise = [(sp["nimmt_g"], sp["euro_je_g"]) for a in aus for sp in a["spulen"]]
        kosten = round(sum(g * e for g, e in preise if e), 2) if any(e for _, e in preise) else None
        return {"filamente": aus, "status": schlimmst if aus else "unklar", "kosten": kosten,
                "kosten_vollstaendig": bool(preise) and all(e for _, e in preise) and all(a["status"] in ("reicht", "wechsel") for a in aus)}


MAX_BILD = 5 * 1024 * 1024
FARB_GRENZE = 110          # Abstand zweier Farben (RGB, 0 bis 441), bis zu dem eine Spule als „ähnliche Farbe“ gilt
ENGE = ["reicht", "wechsel", "unklar", "reicht_nicht"]      # vom Besten zum Schlimmsten; der Gesamtstatus ist der schlimmste


def _gleiches_material(a, b):
    norm = lambda t: re.sub(r"[^a-z0-9+]", "", (t or "").lower())
    return norm(a) == norm(b)


def _rgb(h):
    if not isinstance(h, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?", h):
        return None
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def _farbabstand(a, b):
    """0 für gleiche Farben, 441 für Schwarz gegen Weiss; fehlt eine Farbe, gilt sie als passend (Abstand 60), damit sie nicht ausschliesst."""
    x, y = _rgb(a), _rgb(b)
    if x is None or y is None:
        return 60
    return sum((p - q) ** 2 for p, q in zip(x, y)) ** 0.5


def _kurz(s, g):
    return {"id": s["id"], "material": s["material"], "hersteller": s.get("hersteller", ""), "farbname": s.get("farbname", ""), "farbe": s.get("farbe", ""),
            "ort": s.get("ort", ""), "rest_g": s["rest_g"], "nimmt_g": round(g, 2), "euro_je_g": Lager.euro_je_g(s)}
