"""
Drucke: ein einzelnes Mal, dass ein Modell auf dem Drucker lag (KONZEPT §4.6).

Ein Druck (`PRINT_JOB`) hängt an einem oder mehreren Modellen (Kante
`PRINTED_IN`) — mehrere, wenn eine Platte mehrere Bibliotheksmodelle trug.
Er trägt Datum, Dauer, Gewicht, Filament, Ergebnis, Notiz und Fotos.
„Gedruckt“ und der Zähler sind abgeleitet; damit die Kachelliste nicht bei
jedem Modell die Drucke nachschlagen muss, steht das Abgeleitete am Modell
(`drucke_n`, `gedruckt`, `ref_werte`) und wird bei jeder Änderung eines
Drucks nachgezogen.
"""
import hashlib
import os
import re
import shutil
import tempfile
import time

from . import dateien, slicer
from .bestand import AUSGEFUEHRT, BASIERT_AUF, DATEI, DRUCK, GCODE, GEDRUCKT_IN, GESLICED_AUS, MODELL, PROFIL, REFERENZ
from .katalog import KatalogFehler, jetzt, ref

DATEI_ARTEN = {".gcode": "gcode", ".3mf": "3mf"}       # .gcode.3mf (Bambu: geslicetes Projekt) ist eine 3MF
MAX_DATEI = 1 << 30

ERGEBNISSE = ("gut", "fehler", "abgebrochen")
ZAEHLT = ("gut", "fehler")      # ein Druck mit Fehlern hat stattgefunden; abgebrochen nicht
FELDER = ("datum", "dauer_s", "gewicht_g", "filament", "ergebnis", "notiz")


def _zahl(wert, name, hoechst):
    if wert in (None, ""):
        return None
    try:
        z = float(wert)
    except (TypeError, ValueError):
        raise KatalogFehler(f"{name}: keine Zahl.")
    if not 0 <= z <= hoechst:
        raise KatalogFehler(f"{name}: ausserhalb des Möglichen.")
    return z


def pruefen(felder, voll):
    """Eingaben prüfen und bereinigen. `voll`: ein neuer Druck bekommt Vorgaben."""
    neu = {}
    for k in felder:
        if k not in FELDER:
            raise KatalogFehler(f"Feld {k!r} gibt es am Druck nicht.")
    if "datum" in felder or voll:
        d = felder.get("datum") or (time.strftime("%Y-%m-%d") if voll else None)
        if d is not None and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
            raise KatalogFehler("Datum als JJJJ-MM-TT.")
        neu["datum"] = d
    if "dauer_s" in felder or voll:
        z = _zahl(felder.get("dauer_s"), "Dauer", 60 * 60 * 24 * 60)
        neu["dauer_s"] = int(z) if z is not None else None
    if "gewicht_g" in felder or voll:
        z = _zahl(felder.get("gewicht_g"), "Gewicht", 100000)
        neu["gewicht_g"] = round(z, 2) if z is not None else None
    if "filament" in felder or voll:
        f = felder.get("filament") or []
        if not isinstance(f, list) or len(f) > 8:
            raise KatalogFehler("Filament: höchstens acht Einträge.")
        sauber = []
        for e in f:
            if not isinstance(e, dict):
                raise KatalogFehler("Filament: Eintrag ungültig.")
            farbe = e.get("farbe") or None
            if farbe is not None and not re.fullmatch(r"#[0-9a-fA-F]{6}", farbe):
                raise KatalogFehler("Farbe als #rrggbb.")
            g = _zahl(e.get("g"), "Filament-Gewicht", 100000)
            sauber.append({"typ": str(e.get("typ") or "").strip()[:20] or None, "farbe": farbe,
                           "g": round(g, 2) if g is not None else None})
        neu["filament"] = sauber
    if "ergebnis" in felder or voll:
        e = felder.get("ergebnis") or "gut"
        if e not in ERGEBNISSE:
            raise KatalogFehler("Ergebnis: gut, fehler oder abgebrochen.")
        neu["ergebnis"] = e
    if "notiz" in felder or voll:
        n = (felder.get("notiz") or "").strip()
        if len(n) > 2000:
            raise KatalogFehler("Notiz länger als 2000 Zeichen.")
        neu["notiz"] = n or None
    return neu


def ist_leer(d):
    """Ein Druck ohne jede Angabe — das, was der Haken „gedruckt“ anlegt."""
    return not (d.get("dauer_s") or d.get("gewicht_g") or d.get("filament") or d.get("notiz") or d.get("bilder"))


class Drucke:
    def __init__(self, katalog):
        self.k = katalog
        self.db = katalog.db
        self._alte_haken_umziehen()
        self._gcode_nachziehen()

    # ------------------------------------------------------------ Lesen

    def _modelle_von(self, did):
        return [r.split("/", 1)[1] for r in self.db.get_connected(ref(DRUCK, did), direction="in", rel_type=GEDRUCKT_IN)]

    def _druck(self, did):
        d = self.db.get_node(ref(DRUCK, did), readonly=True)
        if d is None:
            raise KatalogFehler("Diesen Druck gibt es nicht.")
        return d

    def _ids_von(self, mid):
        return [r.split("/", 1)[1] for r in self.db.get_connected(ref(MODELL, mid), rel_type=GEDRUCKT_IN)]

    def _referenz_von(self, mid):
        r = self.db.get_connected(ref(MODELL, mid), rel_type=REFERENZ)
        return r[0].split("/", 1)[1] if r else None

    def liste(self, mid):
        """Die Drucke eines Modells, neueste zuerst; der Referenzdruck steht vorn."""
        referenz = self._referenz_von(mid)
        aus = []
        for did in self._ids_von(mid):
            d = self.db.get_node(ref(DRUCK, did), readonly=True)
            if d is None:
                continue
            gefaehrten = [x for x in self._modelle_von(did) if x != mid]
            aus.append({
                "id": did, **{f: d.get(f) for f in FELDER}, "filament": d.get("filament") or [],
                "bilder": [{"k": b["k"], "url": f"/api/drucke/{did}/bilder/{b['k']}"} for b in d.get("bilder") or []],
                "zusammen_mit": [{"id": x, "name": (self.db.get_node(ref(MODELL, x), readonly=True) or {}).get("name")}
                                 for x in gefaehrten],
                "referenz": did == referenz, "leer": ist_leer(d), "angelegt": d.get("angelegt"), "abbuchung": d.get("abbuchung"),
                "datei": self.datei_von(did),
            })
        aus.sort(key=lambda x: (x["datum"] or "", x["angelegt"] or ""), reverse=True)
        aus.sort(key=lambda x: not x["referenz"])
        return aus

    # ------------------------------------------------------------ Schreiben

    def nachziehen(self, mids):
        """Zähler, Haken und Referenzwerte am Modell neu aus den Drucken ableiten."""
        for mid in mids:
            m = self.db.get_node(ref(MODELL, mid), readonly=True)
            if m is None:
                continue
            drucke = [self.db.get_node(ref(DRUCK, i), readonly=True) for i in self._ids_von(mid)]
            drucke = [d for d in drucke if d]
            referenz = self._referenz_von(mid)
            rd = self.db.get_node(ref(DRUCK, referenz), readonly=True) if referenz else None
            ref_werte = ({"druck": referenz, "gewicht_g": rd.get("gewicht_g"), "dauer_s": rd.get("dauer_s"),
                          "filament": rd.get("filament") or []} if rd else None)
            neu = {"drucke_n": sum(1 for d in drucke if d.get("ergebnis") in ZAEHLT),
                   "gedruckt": any(d.get("ergebnis") == "gut" for d in drucke), "ref_werte": ref_werte,
                   # Wie viele Drucke einen G-Code oder ein Projekt tragen: die Kachel zeigt „G-Code“, ohne bei jedem Modell nachzuschlagen.
                   "gcode_n": sum(1 for i in self._ids_von(mid) if self.db.get_connected(ref(DRUCK, i), rel_type=AUSGEFUEHRT))}
            if any(m.get(k) != v for k, v in neu.items()):
                self.db.update_node(MODELL, mid, neu)

    def anlegen(self, modelle, felder=None):
        modelle = list(dict.fromkeys(modelle or []))
        if not modelle:
            raise KatalogFehler("Ein Druck braucht mindestens ein Modell.")
        for mid in modelle:
            if self.db.get_node(ref(MODELL, mid), readonly=True) is None:
                raise KatalogFehler(f"Modell {mid} gibt es nicht.")
        felder = dict(felder or {})
        abbuchung = felder.pop("abbuchung", None)       # nur beim Anlegen: Verbrauch von einer Spule abziehen (lager.py)
        if abbuchung is not None and not isinstance(abbuchung, dict):
            raise KatalogFehler("Abbuchung: Eintrag ungültig.")
        daten = pruefen(felder, voll=True)
        with self.db.transaction():
            did = self.db.next_id(DRUCK, "d_", 6)
            if abbuchung:
                daten["abbuchung"] = self.k.lager.abbuchen(abbuchung.get("spule"), abbuchung.get("g"))
            self.db.create_node(DRUCK, did, {**daten, "bilder": [], "herkunft": "hand", "angelegt": jetzt()})
            for mid in modelle:
                self.db.create_edge(ref(MODELL, mid), ref(DRUCK, did), GEDRUCKT_IN)
            self.nachziehen(modelle)
        return did

    def aendern(self, did, felder):
        self._druck(did)
        neu = pruefen(felder, voll=False)
        with self.db.transaction():
            if neu:
                self.db.update_node(DRUCK, did, neu)
            self.nachziehen(self._modelle_von(did))

    def loeschen(self, did):
        self._druck(did)
        modelle = self._modelle_von(did)
        # Die Fotos bleiben im Vault: der Druck liegt im Papierkorb und kommt mit ihnen zurück (papierkorb.py). Bis 0.55 gingen sie
        # gleich nach vault_archive/ — ein zurückgeholter Druck hätte keine Fotos mehr gehabt.
        with self.db.transaction():
            self.db.soft_delete(DRUCK, did)
            self.nachziehen(modelle)

    def referenz(self, did, mid, an=True):
        self._druck(did)
        if mid not in self._modelle_von(did):
            raise KatalogFehler("Dieser Druck gehört nicht zu diesem Modell.")
        with self.db.transaction():
            for kante, _ in self.db.verwendungen(ref(MODELL, mid), direction="out").get(REFERENZ, []):
                self.db.delete_edge(kante)
            if an:
                self.db.create_edge(ref(MODELL, mid), ref(DRUCK, did), REFERENZ)
            self.nachziehen([mid])

    def markieren(self, mid, gesetzt):
        """Der Haken „gedruckt“: setzen legt einen leeren Druck an, zurücknehmen
        entfernt leere Drucke — und weigert sich, wenn einer Angaben trägt."""
        m = self.db.get_node(ref(MODELL, mid), readonly=True)
        if m is None:
            raise KatalogFehler(f"Modell {mid} gibt es nicht.")
        if gesetzt:
            if not m.get("gedruckt"):
                self.anlegen([mid], {})
            return
        ids = self._ids_von(mid)
        mit = [i for i in ids if not ist_leer(self.db.get_node(ref(DRUCK, i), readonly=True) or {})]
        if mit:
            raise KatalogFehler(f"Dieses Modell hat {len(mit)} Druck{'e' if len(mit) > 1 else ''} mit Angaben — "
                                "entferne sie im Reiter „Drucke“.")
        with self.db.transaction():
            for i in ids:
                self.db.soft_delete(DRUCK, i)
            self.nachziehen([mid])

    # ------------------------------------------------------------ Fotos

    def bild_hinzufuegen(self, did, daten):
        d = self._druck(did)
        k, rel = self.k.bild_ablegen(self.k.png_aus(daten), f"druck_{did}")
        bilder = list(d.get("bilder") or [])
        if not any(b["k"] == k for b in bilder):
            self.db.update_node(DRUCK, did, {"bilder": bilder + [{"k": k, "datei": rel, "angelegt": jetzt()}]})
            self.nachziehen(self._modelle_von(did))
        return k

    def bild_entfernen(self, did, k):
        d = self._druck(did)
        weg = [b for b in d.get("bilder") or [] if b["k"] == k]
        if not weg:
            raise KatalogFehler("Dieses Bild gibt es nicht.")
        self.db.update_node(DRUCK, did, {"bilder": [b for b in d["bilder"] if b["k"] != k]})
        self.k._archivieren(weg[0]["datei"])

    def bild_pfad(self, did, k):
        d = self.db.get_node(ref(DRUCK, did), readonly=True) or self.db.get_node_raw(ref(DRUCK, did)) or {}
        b = next((b for b in d.get("bilder") or [] if b["k"] == k), None)
        return self.k.b.pfad(*b["datei"].split("/")) if b else None

    # ------------------------------------------------------------ Datei zum Druck (Stufe b, KONZEPT §4.6)

    def datei_anhaengen(self, did, name, daten):
        """G-Code oder Slicer-Projekt an einen Druck: die Datei kommt unverändert in den Vault (`vault/gcode/<Titel>__<Hash>.<ext>`,
        ohne App lesbar), ihre Einstellungen werden ein PRINT_PROFILE (gleiche Einstellungen, gleicher Knoten), und die Datei des
        Modells kommt als Quelle mit in den Vault — wer neu slicen will, braucht sie auch nach dem Aufräumen des Ordners (§3.2).
        Felder des Drucks, die leer sind, füllt der Kopf des G-Codes (Gewicht, Dauer). Gibt eine kurze Bilanz zurück."""
        self._druck(did)
        endung = ".3mf" if name.lower().endswith(".3mf") else os.path.splitext(name.lower())[1]
        art = DATEI_ARTEN.get(endung)
        if art is None:
            raise KatalogFehler("Nur G-Code (.gcode) oder ein Slicer-Projekt (.3mf).")
        if not daten:
            raise KatalogFehler("Die Datei ist leer.")
        if len(daten) > MAX_DATEI:
            raise KatalogFehler("Datei grösser als 1 GB.")
        h = hashlib.sha256(daten).hexdigest()
        titel = re.sub(r"[^\w.-]+", "_", os.path.basename(name)[:-len(endung)] or "druck")[:60]
        rel = f"vault/gcode/{titel}__{h[:12]}{endung}"
        ziel = self.k.b.pfad(*rel.split("/"))
        bestehend = self.db.get_node(ref(GCODE, h), readonly=True)
        if bestehend is not None:
            rel, ziel = bestehend["datei"], self.k.b.pfad(*bestehend["datei"].split("/"))
        # Lesen aus einer Arbeitsdatei: der Vault bekommt nur, was sich lesen liess.
        os.makedirs(self.k.b.pfad("arbeit"), exist_ok=True)
        with tempfile.NamedTemporaryFile(suffix=endung, dir=self.k.b.pfad("arbeit"), delete=False) as f:
            f.write(daten)
            arbeit = f.name
        try:
            gelesen = slicer.aus_gcode(arbeit) if art == "gcode" else (slicer.aus_3mf(arbeit) or {"werte": {}, "slicer": None})
            if art == "3mf":
                gelesen["kopf"] = _kopf_aus_3mf(arbeit)
        except (slicer.SlicerFehler, OSError) as e:
            raise KatalogFehler(f"Die Datei liess sich nicht lesen: {e}") from e
        finally:
            self.k.b.entfernen(arbeit)
        if not os.path.exists(ziel):
            dateien.schreibe_atomar(ziel, daten)
        werte, kopf = gelesen.get("werte") or {}, gelesen.get("kopf") or {}
        ph = slicer.profil_hash(werte) if werte else None
        modelle = self._modelle_von(did)
        with self.db.transaction():
            if bestehend is None:
                self.db.create_node(GCODE, h, {"datei": rel, "name": os.path.basename(name)[:200], "art": art, "groesse": len(daten),
                                               "slicer": gelesen.get("slicer"), "kopf": kopf, "angelegt": jetzt()})
            if ph:
                if self.db.get_node(ref(PROFIL, ph), readonly=True) is None:
                    if self.db.get_node_raw(ref(PROFIL, ph)) is not None:
                        self.db.restore_node(PROFIL, ph)
                    else:
                        self.db.create_node(PROFIL, ph, {"werte": werte, "slicer": gelesen.get("slicer"), "angelegt": jetzt()})
                if ref(PROFIL, ph) not in self.db.get_connected(ref(GCODE, h), rel_type=BASIERT_AUF):
                    self.db.create_edge(ref(GCODE, h), ref(PROFIL, ph), BASIERT_AUF)
            for kid, _ in self.db.get_connected_edges(ref(DRUCK, did), rel_type=AUSGEFUEHRT):
                self.db.delete_edge(kid)
            self.db.create_edge(ref(DRUCK, did), ref(GCODE, h), AUSGEFUEHRT)
            for mid in modelle:
                self._quelle_sichern(h, mid)
            d = self._druck(did)
            neu = {"herkunft": "datei"}
            if d.get("gewicht_g") is None and kopf.get("gewicht_g") is not None:
                neu["gewicht_g"] = round(float(kopf["gewicht_g"]), 2)
            if d.get("dauer_s") is None and kopf.get("dauer_s"):
                neu["dauer_s"] = int(kopf["dauer_s"])
            self.db.update_node(DRUCK, did, neu)
            self.nachziehen(modelle)
        gleich = self._drucke_mit_profil(ph) if ph else []
        return {"gcode": h, "profil": ph, "werte": len(werte), "slicer": gelesen.get("slicer"),
                "gleiche_einstellungen": len(gleich), "gewicht_g": neu.get("gewicht_g"), "dauer_s": neu.get("dauer_s")}

    def _quelle_sichern(self, gh, mid):
        """Die Modelldatei, aus der gesliced wurde, als Kopie in den Vault (einmal je Inhalt) und die Kante SLICED_FROM."""
        h = self.k.datei_von(mid)
        d = self.db.get_node(ref(DATEI, h), readonly=True) if h else None
        if d is None:
            return
        if not d.get("quelle_vault"):
            pfad = next((p for o in d.get("orte", []) if (p := self.k.absoluter_pfad(o)) and os.path.exists(p)), None)
            if pfad is None:
                return
            name = os.path.basename(pfad)
            stamm, endung = os.path.splitext(name)
            sauber = re.sub(r"[^\w.-]+", "_", stamm)[:60]
            rel = f"vault/quellen/{sauber}__{h[:12]}{endung.lower()}"
            ziel = self.k.b.pfad(*rel.split("/"))
            if not os.path.exists(ziel):
                os.makedirs(os.path.dirname(ziel), exist_ok=True)
                arbeit = ziel + ".arbeit"
                shutil.copyfile(pfad, arbeit)
                with open(arbeit, "rb") as f:
                    os.fsync(f.fileno())
                os.replace(arbeit, ziel)
            self.db.update_node(DATEI, h, {"quelle_vault": rel})
        if ref(DATEI, h) not in self.db.get_connected(ref(GCODE, gh), rel_type=GESLICED_AUS):
            self.db.create_edge(ref(GCODE, gh), ref(DATEI, h), GESLICED_AUS)

    def _drucke_mit_profil(self, ph):
        """Alle lebenden Drucke, deren Datei genau diese Einstellungen hat — ein Schritt durch den Graphen (Profil ← G-Code ← Druck)."""
        drucke = set()
        for g in self.db.get_connected(ref(PROFIL, ph), direction="in", rel_type=BASIERT_AUF):
            drucke |= set(self.db.get_connected(g, direction="in", rel_type=AUSGEFUEHRT))
        return sorted(drucke)

    def datei_von(self, did):
        """{gcode, name, art, slicer, profil, datei (Pfad im Vault), gleiche} oder None."""
        g = self.db.get_connected(ref(DRUCK, did), rel_type=AUSGEFUEHRT)
        if not g:
            return None
        gh = g[0].split("/", 1)[1]
        n = self.db.get_node(g[0], readonly=True) or {}
        p = self.db.get_connected(g[0], rel_type=BASIERT_AUF)
        ph = p[0].split("/", 1)[1] if p else None
        return {"gcode": gh, "name": n.get("name"), "art": n.get("art"), "slicer": n.get("slicer"), "groesse": n.get("groesse"),
                "profil": ph, "datei": n.get("datei"), "gleiche": len(self._drucke_mit_profil(ph)) if ph else 0}

    def datei_loesen(self, did):
        """Nur die Verbindung geht; die Datei bleibt im Vault (er wächst nur, §3.2) — hängt man sie wieder an, ist sie gleich da."""
        self._druck(did)
        with self.db.transaction():
            for kid, _ in self.db.get_connected_edges(ref(DRUCK, did), rel_type=AUSGEFUEHRT):
                self.db.delete_edge(kid)
        with self.db.transaction():                    # erst nach dem Lösen: sonst zählt nachziehen die Kante noch mit
            self.nachziehen(self._modelle_von(did))

    def einstellungen(self, did):
        """{slicer, wichtig, alle} der Datei am Druck."""
        info = self.datei_von(did)
        if not info or not info["profil"]:
            raise KatalogFehler("Dieser Druck hat keine Datei mit Einstellungen.")
        werte = (self.db.get_node(ref(PROFIL, info["profil"]), readonly=True) or {}).get("werte") or {}
        return {"slicer": info["slicer"], "datei": info["name"], "wichtig": slicer.wichtigste(werte), "alle": slicer.alle(werte)}

    def vergleich(self, a, b):
        """Was sich zwischen den Einstellungen zweier Drucke unterscheidet (KONZEPT §4.1: „Düse 215 → 225 °C“)."""
        werte = []
        for did in (a, b):
            info = self.datei_von(did)
            if not info or not info["profil"]:
                raise KatalogFehler("Beide Drucke brauchen eine Datei mit Einstellungen.")
            werte.append((self.db.get_node(ref(PROFIL, info["profil"]), readonly=True) or {}).get("werte") or {})
        namen = {z["schluessel"]: f"{g['gruppe']} › {z['name']}" for w in werte for g in slicer.wichtigste(w) for z in g["zeilen"]}
        diff = slicer.unterschiede(*werte)
        for x in diff:
            x["name"] = namen.get(x["schluessel"])
        diff.sort(key=lambda x: (x["name"] is None, x["name"] or x["schluessel"]))
        return {"gleich": not diff, "unterschiede": diff}

    # ------------------------------------------------------------ Umzug

    def _gcode_nachziehen(self):
        """Bestände vor 1.0.5: Modelle mit Drucken bekommen `gcode_n`. Schreibt nur, wenn so ein Modell da ist."""
        alt = [mid for mid, m in self.db.list_nodes(MODELL, readonly=True).items() if m.get("drucke_n") and m.get("gcode_n") is None]
        if alt:
            with self.db.transaction():
                self.nachziehen(alt)

    def _alte_haken_umziehen(self):
        """Bestände vor 0.19: der Haken „gedruckt“ war ein Feld. Jeder wird zu
        einem leeren Druck ohne Datum; die Modelle bekommen `drucke_n`. Schreibt
        nur, wenn so ein Modell da ist."""
        alt = [mid for mid, m in self.db.list_nodes(MODELL, readonly=True).items()
               if m.get("gedruckt") and m.get("drucke_n") is None]
        if not alt:
            return
        with self.db.transaction():
            for mid in alt:
                did = self.db.next_id(DRUCK, "d_", 6)
                self.db.create_node(DRUCK, did, {"datum": None, "dauer_s": None, "gewicht_g": None, "filament": [],
                                                 "ergebnis": "gut", "notiz": None, "bilder": [],
                                                 "herkunft": "hand", "angelegt": jetzt()})
                self.db.create_edge(ref(MODELL, mid), ref(DRUCK, did), GEDRUCKT_IN)
            self.nachziehen(alt)


def _kopf_aus_3mf(pfad):
    """Gewicht und Dauer aus einem geslicten Projekt (.gcode.3mf: Metadata/slice_info.config), sonst leer."""
    from . import formate
    try:
        platten = formate._platten(formate._Zip(pfad))
    except (formate.FormatFehler, OSError, ValueError):
        return {}
    g = sum(p.get("gewicht_g") or 0 for p in platten)
    z = sum(p.get("zeit_s") or 0 for p in platten)
    return {k: v for k, v in (("gewicht_g", g or None), ("dauer_s", int(z) if z else None)) if v}
