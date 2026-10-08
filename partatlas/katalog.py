"""
Der Katalog im Graphen: Wurzelordner, Modelle, Dateien, Tags.

Alles, was den Graphen liest oder schreibt, steht hier — der Scan liefert
nur zu, die Oberfläche fragt nur ab. KONZEPT §3 und §6.

Eine Datei (`PART_GEOMETRY`) hat ihren SHA-256 als Kennung und eine Liste
von Orten `{"wurzel", "pfad"}` (Pfad relativ zur Wurzel). Liegt dieselbe
Datei an zwei Stellen, ist das EIN Knoten mit zwei Orten — ein Duplikat.
Ohne Ort fehlt sie. Beides wird abgeleitet, nicht gespeichert.
"""
import hashlib
import io
import os
import re
import threading
import time

from . import archiv, dateien, formate, sicherung, tags
from .suche import Suchindex
from .bestand import (BRAUCHT, DATEI, HAT_DATEI, VORSCHAU_ARTEN, HAT_TAG, IN_SAMMLUNG, MATERIAL, MATERIALIEN, MODELL, SAMMLUNG,
                      TAG, VORGESEHEN, WURZEL)


class KatalogFehler(Exception):
    """Ein Wunsch an den Katalog, der sich nicht erfüllen lässt (Meldung für den Anwender)."""


def jetzt():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def ref(sammlung, kennung):
    return f"{sammlung}/{kennung}"


LOESCHEN_GRUPPE = 200


class Katalog:
    def __init__(self, bestand):
        self.b = bestand
        self.db = bestand.db
        # Zwischenspeicher der Kacheln — siehe _kurz_alle. `_kurz_offen`: Verweise aus den Änderungsmeldungen, deren Kacheln veraltet sind.
        self._kurz_zwischen = None
        self._kurz_offen = set()
        self._kurz_alles_neu = 0             # zählt „alles neu“: ein Bau, der davor begann, wird nicht gespeichert
        self._kurz_sperre = threading.Lock()
        self._kurz_bau = threading.Lock()    # immer nur ein Nachbau: zwei gleichzeitig verlören die Änderungen des einen
        bestand.hoeren(self._kurz_veraltet)
        self.suche = Suchindex(self)
        self._material_nachziehen()
        self._vault_nachziehen()
        from .drucke import Drucke
        self.drucke = Drucke(self)

    # ------------------------------------------------------------ Wurzeln

    def wurzeln(self):
        return {k: dict(v) for k, v in self.db.list_nodes(WURZEL, readonly=True).items()}

    def wurzel_pfad(self, wid):
        w = self.db.get_node(ref(WURZEL, wid), readonly=True)
        return w["pfad"] if w else None

    def _wurzel_pruefen(self, pfad, ausser=None):
        pfad = os.path.abspath(os.path.expanduser(pfad))
        if not os.path.isdir(pfad):
            raise KatalogFehler(f"Kein Ordner: {pfad}")
        # Ein ganzes Laufwerk oder die Systemordner einzulesen wäre ein Versehen: es dauerte ewig und füllte den Katalog mit Fremdem.
        if os.path.dirname(pfad) == pfad or pfad in ("/proc", "/sys", "/dev", "/run", "/etc", "/usr", "/var", "/boot"):
            raise KatalogFehler("Das ist ein System- oder Laufwerksordner. Wähle den Ordner, in dem deine 3D-Modelle liegen.")
        bestand = os.path.abspath(self.b.wurzel)
        if pfad == bestand or pfad.startswith(bestand + os.sep) or bestand.startswith(pfad + os.sep):
            # Der eigene Bestand (Papierkorb, Cache) darf nicht Teil einer
            # Sammlung sein und umgekehrt — sonst katalogisiert partAtlas
            # seine eigenen Arbeitsdateien.
            raise KatalogFehler("Der Ordner überschneidet sich mit dem Bestand von partAtlas.")
        for wid, w in self.wurzeln().items():
            vorhanden = w["pfad"]
            if wid != ausser and (pfad == vorhanden or pfad.startswith(vorhanden + os.sep) or vorhanden.startswith(pfad + os.sep)):
                raise KatalogFehler(f"Überschneidet sich mit dem Wurzelordner {vorhanden}.")
        return pfad

    def wurzel_hinzufuegen(self, pfad):
        pfad = self._wurzel_pruefen(pfad)
        wid = self.db.next_id(WURZEL, "w_", 3)
        self.db.create_node(WURZEL, wid, {"pfad": pfad, "name": os.path.basename(pfad) or pfad,
                                          "angelegt": jetzt()})
        return wid

    def _sichern_vor(self, was):
        """Vor einer Massenaktion immer eine Sicherung der Datenbank. Scheitert sie (Platte voll), unterbleibt die Aktion: lieber nichts
        tun als etwas, das sich nicht zurückholen lässt."""
        try:
            sicherung.sichern(self.b, f"vor-{was}", immer=True)
        except OSError as e:
            raise KatalogFehler(f"Vorher liess sich keine Sicherung anlegen ({e}); die Aktion unterbleibt.") from e

    def wurzel_entfernen(self, wid):
        """Nur der Eintrag geht; Dateien bleiben, ihre Orte unter dieser Wurzel
        verschwinden. Modelle ohne anderen Ort gelten danach als fehlend — samt Tags, Drucken und Verknüpfungen, die am Inhalt hängen.
        Der Eintrag selbst bleibt im Papierkorb (`entfernte_wurzeln`) und lässt sich zurückholen.
        Liegt keine Datei mehr darunter, ändert sich nur dieser Eintrag: dann keine Sicherung (sie kopiert die ganze Datenbank samt
        Papierkorb — beim Anwender 4 s für einen leeren Ordner)."""
        if any(o["wurzel"] == wid for d in self._dateien().values() for o in d.get("orte", [])):
            self._sichern_vor("ordner-entfernen")
        with self.db.transaction():
            n = 0
            for h, d in self._dateien().items():
                orte = [o for o in d.get("orte", []) if o["wurzel"] != wid]
                if len(orte) != len(d.get("orte", [])):
                    n += 1
                    self._orte_setzen(h, d, orte)
            self.db.update_node(WURZEL, wid, {"entfernt": jetzt(), "modelle_n": n})
            self.db.soft_delete(WURZEL, wid)

    def entfernte_wurzeln(self):
        """Die entfernten Ordner, jüngste zuerst — ohne die, die der Anwender inzwischen unter anderer Nummer wieder hinzugefügt hat."""
        live = {w["pfad"] for w in self.wurzeln().values()}
        liste = []
        for wid, d in self.db.list_nodes(WURZEL, include_deleted=True, readonly=True).items():
            if wid in self.wurzeln() or d.get("pfad") in live:
                continue
            liste.append({"id": wid, "name": d.get("name"), "pfad": d.get("pfad"), "modelle": d.get("modelle_n"),
                          "entfernt": d.get("entfernt"), "vorhanden": os.path.isdir(d.get("pfad") or "")})
        return sorted(liste, key=lambda x: x["entfernt"] or "", reverse=True)

    def wurzel_wiederherstellen(self, wid):
        """Einen entfernten Ordner zurückholen. Die Orte der Modelle kommen beim nächsten Scan über den Inhalt zurück."""
        roh = self.db.get_node_raw(ref(WURZEL, wid))
        if roh is None or self.db.get_node(ref(WURZEL, wid), readonly=True) is not None:
            raise KatalogFehler("Diesen entfernten Ordner gibt es nicht.")
        self._wurzel_pruefen(roh["pfad"], ausser=wid)
        with self.db.transaction():
            self.db.restore_node(WURZEL, wid)

    # ------------------------------------------------------------ Dateien und Orte

    def _dateien(self):
        return self.db.list_nodes(DATEI, readonly=True)

    def ort_index(self):
        """{(wurzel, pfad): (hash, groesse, mtime)} für den Scan."""
        index = {}
        for h, d in self._dateien().items():
            for o in d.get("orte", []):
                index[(o["wurzel"], o["pfad"])] = (h, o.get("groesse"), o.get("mtime"))
        return index

    def datei_status(self, h):
        """"lebt", "papierkorb" oder None (unbekannt)."""
        if self.db.get_node(ref(DATEI, h), readonly=True) is not None:
            return "lebt"
        roh = self.db.get_node_raw(ref(DATEI, h))
        if roh is not None:
            # Durch Überschreiben abgelöst: kommt sie wieder, ist sie neu.
            return None if roh.get("ersetzt_durch") else "papierkorb"
        return None

    def aus_papierkorb_zurueck(self, h, wurzel, pfad, st):
        """Die Datei `h` liegt wieder im Ordner, ihr Modell im Papierkorb: das Modell kommt mit allem zurück (Tags, Drucke, Baugruppen) und
        bekommt den neuen Ort. Die Kopie im Papierkorb ist dieselbe Datei und wird überflüssig. Hatte das Modell mehrere Orte, kommen
        die übrigen wie bei „Wiederherstellen“ an ihren Platz zurück — es geht nichts verloren."""
        d = self.db.get_node_raw(ref(DATEI, h))
        teile = self.db.get_connected(ref(DATEI, h), direction="in", rel_type=HAT_DATEI, include_deleted=True)
        mid = teile[0].split("/", 1)[1] if teile else None
        ablage = (d or {}).get("papierkorb", [])
        # Nur für Modelle, deren Dateien eine frühere Fassung in den Papierkorb von partAtlas verschoben hat. Seit 0.30 bleibt die Datei
        # beim Löschen im Ordner; dort ist sie kein „Zurücklegen“, sondern der Normalfall, und das Modell bleibt im Papierkorb.
        if d is None or mid is None or not ablage or any("ablage" not in a for a in ablage):
            return False
        if len(ablage) > 1:
            self.wiederherstellen(mid)
            with self.db.transaction():
                self.ort_setzen(h, wurzel, pfad, st.st_size, st.st_mtime)
            return True
        ort = {"wurzel": wurzel, "pfad": pfad, "groesse": st.st_size, "mtime": st.st_mtime}
        with self.db.transaction():
            self.db.restore_node(MODELL, mid)
            self.db.update_node(DATEI, h, {"orte": [ort], "papierkorb": [], "geloescht": None})
        for a in ablage:
            # Dieselbe Datei (gleicher Hash) liegt wieder im Ordner: die Kopie im Papierkorb von partAtlas ist überzählig.
            self.b.entfernen(self.b.pfad(a["ablage"]))
        return True

    def ignorierte_orte(self):
        """{(wurzel, pfad): (hash, groesse, mtime)} der Dateien, deren Modell im Papierkorb liegt, die Datei aber im Ordner geblieben ist:
        der Scan überspringt sie, ohne sie bei jedem Lauf neu zu lesen."""
        orte = {}
        for h, d in self.db.list_nodes(DATEI, include_deleted=True, readonly=True).items():
            if d.get("ersetzt_durch"):
                continue
            for o in d.get("papierkorb") or []:
                if "ablage" not in o:
                    orte[(o["wurzel"], o["pfad"])] = (h, o.get("groesse"), o.get("mtime"))
        return orte

    def ort_setzen(self, h, wurzel, pfad, groesse, mtime):
        d = self.db.get_node(ref(DATEI, h))
        orte = [o for o in d.get("orte", []) if (o["wurzel"], o["pfad"]) != (wurzel, pfad)]
        orte.append({"wurzel": wurzel, "pfad": pfad, "groesse": groesse, "mtime": mtime})
        orte.sort(key=lambda o: (o["wurzel"], o["pfad"]))
        self._orte_setzen(h, d, orte)

    def ort_entfernen(self, h, wurzel, pfad):
        d = self.db.get_node(ref(DATEI, h))
        if d is None:
            return
        orte = [o for o in d.get("orte", []) if (o["wurzel"], o["pfad"]) != (wurzel, pfad)]
        self._orte_setzen(h, d, orte)

    def _orte_setzen(self, h, d, orte):
        """Verschwindet der letzte Ort, bleibt er als `zuletzt_ort` stehen — für „Lag zuletzt in“ und als Grösse, an der „Suchen …“ die
        Datei vorab erkennt. Kommt sie zurück, gilt „ohne Datei behalten“ nicht mehr: verschwindet sie wieder, ist das wieder eine Warnung."""
        werte = {"orte": orte}
        if not orte and d.get("orte"):
            werte["zuletzt_ort"] = d["orte"][0]
        if orte and d.get("ohne_datei"):
            werte["ohne_datei"] = None
        self.db.update_node(DATEI, h, werte)

    def neue_datei(self, h, felder, orte, vorschau, fehler=None, vorgaenger=None):
        """Datei, Modell und automatische Tags in einem Zug. Aufrufer hält die Transaktion.

        Mit `vorgaenger`: am selben Ort lag vorher diese Datei, jetzt liegt
        dort neuer Inhalt. Die Datei führt, der Container folgt (KONZEPT
        §3.1): ist die alte an keinem anderen Ort mehr, bekommt ihr Modell
        den neuen Inhalt — Tags, Bilder, Baugruppen bleiben."""
        name = os.path.splitext(os.path.basename(orte[0]["pfad"]))[0]
        daten = {**felder, "orte": orte, "vorschau": vorschau, "fehler": fehler, "eingelesen": jetzt(),
                 "vorschau_extrahiert": self.b.vorschau_rel(h, "extrahiert") if vorschau == "eingebettet" else None,
                 "ersetzt_durch": None}
        if self.db.get_node_raw(ref(DATEI, h)) is not None:
            # Eine früher abgelöste Fassung ist zurück: als eigene Datei.
            self.db.restore_node(DATEI, h)
            self.db.update_node(DATEI, h, daten)
        else:
            self.db.create_node(DATEI, h, daten)
        mid = self._nachfolger_von(vorgaenger, h) if vorgaenger else None
        if mid:
            return mid
        mid = self.db.next_id(MODELL, "m_", 6)
        self.db.create_node(MODELL, mid, {
            "name": name, "favorit": False, "gedruckt": False, "drucke_n": 0, "quelle_url": None,
            "angelegt": jetzt(), "zuletzt_angesehen": None,
        })
        # cascade_delete: wer das Modell löscht, legt seine Datei mit in den
        # Papierkorb (VERTRAG §2.4) — und loeschfolgen() zeigt das vorher an.
        self.db.create_edge(ref(MODELL, mid), ref(DATEI, h), HAT_DATEI, cascade_delete=True)
        if self.b.einstellungen().get("auto_tags", True):
            for t in tags.vorschlaege(name, felder):
                self._tag_verbinden(mid, t)
        self._datei_materialien(h, felder)
        return mid

    def _nachfolger_von(self, alt, h):
        """Hängt die neue Datei `h` an das Modell der alten, wenn die alte
        nirgends mehr liegt. Sonst None — dann ist sie eine abgezweigte Kopie."""
        d = self.db.get_node(ref(DATEI, alt), readonly=True)
        mid = self.modell_von(alt) if d is not None and not d.get("orte") else None
        if mid is None or self.db.get_node(ref(MODELL, mid), readonly=True) is None:
            return None
        for kid, _ in self.db.verwendungen(ref(MODELL, mid), direction="out").get(HAT_DATEI, []):
            self.db.delete_edge(kid)
        self.db.update_node(DATEI, alt, {"ersetzt_durch": h})
        self.db.soft_delete(DATEI, alt)
        self.db.create_edge(ref(MODELL, mid), ref(DATEI, h), HAT_DATEI, cascade_delete=True)
        self._datei_materialien(h, self.db.get_node(ref(DATEI, h), readonly=True))
        for art in VORSCHAU_ARTEN:
            self.b.entfernen(self.b.vorschau_pfad(alt, art))      # abgeleitet von einem Inhalt, den es nicht mehr gibt
        self._netz_weg(alt)
        return mid

    def namen_angleichen(self):
        """Name = Dateiname: hat eine Datei genau einen Ort und passt der Name
        des Modells nicht mehr dazu, wurde sie ausserhalb umbenannt — der
        Name folgt. Bei Duplikaten bleibt er, dort gibt es keinen einen Namen."""
        for h, d in self._dateien().items():
            orte = d.get("orte", [])
            if len(orte) != 1:
                continue
            stamm = os.path.splitext(orte[0]["pfad"].rsplit("/", 1)[-1])[0]
            mid = self.modell_von(h)
            m = self.db.get_node(ref(MODELL, mid), readonly=True) if mid else None
            if m is not None and m.get("name") != stamm:
                self.db.update_node(MODELL, mid, {"name": stamm})

    def vorschau_setzen(self, h, status):
        if self.db.get_node(ref(DATEI, h), readonly=True) is not None:
            self.db.update_node(DATEI, h, {"vorschau": status,
                                           **({"vorschau_berechnet": self.b.vorschau_rel(h, "berechnet")} if status == "gerendert" else {})})

    def vorschauen(self, d):
        """Die Vorschaubilder einer Datei: [(art, Pfad im Vault)], aus der Datei zuerst."""
        arten = VORSCHAU_ARTEN
        if (d or {}).get("format") in formate.OHNE_NETZ:
            # CAD-Datei: das Bild aus der Datei ist ein kleines Thumbnail; das berechnete aus dem Netz ist schärfer.
            arten = tuple(reversed(arten))
        return [(art, d[f"vorschau_{art}"]) for art in arten if (d or {}).get(f"vorschau_{art}")]

    def vorschau_datei(self, h):
        """Bestes Vorschaubild als Pfad: aus der Datei vor berechnet."""
        d = (self.db.get_node(ref(DATEI, h), readonly=True) or self.db.get_node_raw(ref(DATEI, h))) if h else None
        v = self.vorschauen(d)
        return self.b.pfad(*v[0][1].split("/")) if v else None

    def ausstehende_cad(self):
        """STEP-Dateien, die noch ein Netz von FreeCAD brauchen. Auch ältere Einträge ohne das Feld `cad`: sie wurden vor
        dieser Fassung aufgenommen. `fehler` ist der Lesefehler der Datei selbst, nicht der der Umwandlung."""
        return [(h, d) for h, d in self._dateien().items()
                if d.get("format") in ("step", "fcstd") and d.get("cad") in (None, "ausstehend") and d.get("orte") and not d.get("fehler")
                and not d.get("auslesen")]

    def cad_ergebnis(self, h, felder, vorschau, fehler=None):
        """Netz und Vorschau aus FreeCAD sind da. Der Aufrufer hält die Transaktion."""
        if self.db.get_node(ref(DATEI, h), readonly=True) is None:
            return
        if vorschau == "fehler":
            return self.cad_fehler(h, fehler or "Vorschau nicht möglich")
        self.db.update_node(DATEI, h, {**felder, "cad": "ok", "cad_fehler": None, "vorschau": vorschau,
                                       **({"vorschau_berechnet": self.b.vorschau_rel(h, "berechnet")} if vorschau == "gerendert" else {})})

    def cad_erneut(self):
        """Gescheiterte CAD-Umwandlungen wieder auf „ausstehend“ — etwa nach einer Reparatur oder wenn FreeCAD gefehlt hat."""
        n = 0
        with self.db.transaction():
            for h, d in self._dateien().items():
                if d.get("cad") == "fehler":
                    self.db.update_node(DATEI, h, {"cad": "ausstehend", "cad_fehler": None})
                    n += 1
        return n

    def cad_fehler(self, h, text):
        if self.db.get_node(ref(DATEI, h), readonly=True) is not None:
            self.db.update_node(DATEI, h, {"cad": "fehler", "cad_fehler": text})

    def _netz_weg(self, h):
        self.b.entfernen(self.b.netz_pfad(h))

    def auszulesen(self):
        """Dateien, deren Inhalt noch nicht ausgelesen ist (Einlesen legt sie sofort an, KONZEPT §3.4) — die erste Arbeit des Workers.
        Die schnellen Formate zuerst, STEP zuletzt; innerhalb eines Formats die kleinen zuerst, damit früh viele Kacheln fertig werden."""
        reihe = {"stl": 0, "obj": 0, "3mf": 0, "fcstd": 1, "step": 2}
        offen = [(h, d) for h, d in self._dateien().items() if d.get("auslesen") == "ausstehend" and d.get("orte")]
        return sorted(offen, key=lambda x: (reihe.get(x[1].get("format"), 1), (x[1]["orte"][0].get("groesse") or 0)))

    def ausgelesen(self, h, felder, vorschau, fehler=None):
        """Was der Worker aus der Datei gelesen hat, nachtragen: Werte, Vorschau-Status, Materialien, Tags aus den Werten (mehrteilig,
        miniatur …). Der Aufrufer hält die Transaktion."""
        d = self.db.get_node(ref(DATEI, h), readonly=True)
        if d is None:
            return
        self.db.update_node(DATEI, h, {**felder, "auslesen": None, "vorschau": vorschau, "fehler": fehler,
                                       "vorschau_extrahiert": self.b.vorschau_rel(h, "extrahiert") if vorschau == "eingebettet" else None})
        self._datei_materialien(h, felder)
        mid = self.modell_von(h)
        m = self.db.get_node(ref(MODELL, mid), readonly=True) if mid else None
        if m is not None and self.b.einstellungen().get("auto_tags", True):
            for t in tags.vorschlaege(m.get("name") or "", felder):
                self._tag_verbinden(mid, t)

    def ausstehende_vorschauen(self):
        return [(h, d) for h, d in self._dateien().items() if d.get("vorschau") == "ausstehend"]

    def absoluter_pfad(self, ort):
        w = self.wurzel_pfad(ort["wurzel"])
        return os.path.join(w, *ort["pfad"].split("/")) if w else None

    # ------------------------------------------------------------ Modelle

    def datei_von(self, mid):
        teile = self.db.get_connected(ref(MODELL, mid), rel_type=HAT_DATEI)
        return teile[0].split("/", 1)[1] if teile else None

    def modell_von(self, h):
        m = self.db.get_connected(ref(DATEI, h), direction="in", rel_type=HAT_DATEI)
        return m[0].split("/", 1)[1] if m else None

    def tags_von(self, mid):
        return sorted(r.split("/", 1)[1] for r in self.db.get_connected(ref(MODELL, mid), rel_type=HAT_TAG))

    def _kurz(self, mid, m, papierkorb=False):
        """Was eine Kachel braucht — klein halten, das Raster lädt es für alle."""
        h = self.datei_von(mid) if not papierkorb else self._datei_im_papierkorb(mid)
        d = (self.db.get_node(ref(DATEI, h), readonly=True) or self.db.get_node_raw(ref(DATEI, h))) if h else {}
        d = d or {}
        platten = d.get("platten") or []
        gewicht = sum(p.get("gewicht_g") or 0 for p in platten) or None
        # Der Referenzdruck („so war es gut“) geht vor der Schätzung aus der Datei (KONZEPT §4.6).
        rw = m.get("ref_werte") or {}
        gewicht_herkunft = "druck" if rw.get("gewicht_g") else ("datei" if gewicht else None)
        gewicht = rw.get("gewicht_g") or gewicht
        mat = self.materialien_von(mid, h) if not papierkorb else {"vorgesehen": [], "aus_datei": []}
        materialien = sorted(set(mat["vorgesehen"]) | set(mat["aus_datei"]))
        # Vorgesehen geht vor: der Anwender weiss, womit er drucken will.
        material = next(iter(mat["vorgesehen"] + mat["aus_datei"]), None)
        orte = d.get("orte", [])
        return {
            "id": mid, "name": m.get("name"), "format": d.get("format"),
            "masse": d.get("masse_mm"), "gewicht_g": round(gewicht, 2) if gewicht else None, "gewicht_herkunft": gewicht_herkunft,
            "material": material, "materialien": materialien, "gedruckt": m.get("gedruckt", False),
            "drucke_n": m.get("drucke_n", 0),
            "favorit": m.get("favorit", False), "entwurf": bool(m.get("entwurf")), "hash": h,
            "vorschau": d.get("vorschau"), "cad": d.get("cad"), "fehlt": not orte and not papierkorb,
            # Der Anwender hat gesagt: die Datei ist absichtlich weg. Dann kein Problem mehr, nur ein ruhiges Zeichen.
            "ohne_datei": bool(d.get("ohne_datei")) and not orte and not papierkorb,
            "duplikat": len(orte) > 1, "fehler": bool(d.get("fehler")),
            "ordner": [f'{o["wurzel"]}/{o["pfad"].rsplit("/", 1)[0] if "/" in o["pfad"] else ""}' for o in orte],
            "tags": self.tags_von(mid) if not papierkorb else [],
            "angelegt": m.get("angelegt"), "warteschlange": m.get("warteschlange"),
            # Kurzer Hash des eigenen Bilds: ändert sich mit dem Bild und macht
            # die Adresse im Browser-Cache eindeutig.
            # Kennung des Titelbilds (das erste der Liste) — ändert sich mit
            # dem Bild und macht die Adresse im Browser-Cache eindeutig.
            "bild": None if m.get("vorschau_art") else (m.get("bilder") or [{}])[0].get("k"),
            "vorschau_art": m.get("vorschau_art"),
            "groesse": sum(o.get("groesse") or 0 for o in orte[:1]) or None,
        }

    def _datei_im_papierkorb(self, mid):
        # Kanten eines gelöschten Knotens liefert get_connected nur mit include_deleted.
        teile = self.db.get_connected(ref(MODELL, mid), rel_type=HAT_DATEI, include_deleted=True)
        return teile[0].split("/", 1)[1] if teile else None

    def modelle(self, suche=None, tag=None, ordner=None, fmt=None, ansicht="alle", sammlung=None,
                tags=(), materialien=(), leiste=False, alle=None):
        """Wie `_modelle`, dazu die Chips der Leiste: Tags und Materialien je
        mit ODER. Wer mehr gewählte Chips trifft, steht weiter oben; bei
        Gleichstand bleibt die Reihenfolge davor (Relevanz, Name …).

        Mit `leiste` kommt je Chip die Anzahl dazu — gezählt vor der
        Chip-Auswahl, damit man sieht, was ein weiterer Chip brächte."""
        basis = self._modelle(suche, tag, ordner, fmt, ansicht, sammlung, alle)
        tags, materialien = set(tags), {m.upper() for m in materialien}
        liste = basis
        if tags or materialien:
            def treffer(x):
                return len(tags.intersection(x.get("tags") or ())) + len(materialien.intersection(x.get("materialien") or ()))
            liste = sorted((x for x in basis if treffer(x)), key=lambda x: -treffer(x))
        if not leiste:
            return liste
        zaehl_t, zaehl_m = {}, {}
        for x in basis:
            for t in x.get("tags") or ():
                zaehl_t[t] = zaehl_t.get(t, 0) + 1
            for m in x.get("materialien") or ():
                zaehl_m[m] = zaehl_m.get(m, 0) + 1
        # Formate: gezählt in der Ansicht, wie sie dasteht (Ordner, Suche, Chips), nur ohne den Format-Filter selbst — sonst zeigte jeder
        # andere Format-Chip 0. Vorher kamen die Zahlen aus dem ganzen Katalog (/api/zaehler) und passten zu keiner Ansicht.
        ohne_fmt = liste if not fmt else self._modelle(suche, tag, ordner, None, ansicht, sammlung, alle)
        if fmt and (tags or materialien):
            ohne_fmt = [x for x in ohne_fmt if treffer(x)]
        zaehl_f = {}
        for x in ohne_fmt:
            zaehl_f[x["format"]] = zaehl_f.get(x["format"], 0) + 1
        ordnen = lambda z: [{"name": k, "anzahl": v} for k, v in sorted(z.items(), key=lambda kv: (-kv[1], kv[0]))]
        return {"modelle": liste, "leiste": {"tags": ordnen(zaehl_t), "materialien": ordnen(zaehl_m),
                                            "formate": {k: v for k, v in zaehl_f.items() if k}}}

    def aenderungen(self, refs, **filter):
        """Für das Nachreichen während des Einlesens: die Modelle hinter diesen Graph-Verweisen (Modell, Datei, Kante), je mit der Antwort,
        ob sie in die Ansicht mit `filter` gehören. Baut nur ihre Kacheln — die ganze Liste kostete bei 9 000 Modellen Sekunden, und der
        Zwischenspeicher aller Kacheln ist während des Einlesens nach jeder Änderung veraltet."""
        mids = set()
        for r in refs:
            sammlung, _, schluessel = r.partition("/")
            if sammlung == MODELL:
                mids.add(schluessel)
            elif sammlung == DATEI:
                mid = self.modell_von(schluessel)
                if mid:
                    mids.add(mid)
        kacheln = {}
        for mid in mids:
            m = self.db.get_node(ref(MODELL, mid), readonly=True)
            if m is not None:
                kacheln[mid] = self._kurz(mid, m)
        treffer = self.modelle(**filter, alle=kacheln) if kacheln else []
        drin = {x["id"] for x in treffer}
        return {"modelle": treffer, "weg": sorted(mids - drin)}

    def _kurz_veraltet(self, meldung):
        """Merkt sich, welche Kacheln eine Änderung betrifft. Läuft unter der Sperre von flatgraph (VERTRAG §2.7): nur merken, nichts lesen."""
        sammlung = (meldung.get("ref") or "").split("/", 1)[0]
        with self._kurz_sperre:
            if meldung.get("ereignis") in ("create_edge", "delete_edge"):
                # Tags, Material, die Datei eines Modells: Kanten zwischen ihnen. Beide Enden, falls sie Modell oder Datei sind.
                for r in (meldung.get("quelle"), meldung.get("ziel")):
                    if r and r.split("/", 1)[0] in (MODELL, DATEI):
                        self._kurz_offen.add(r)
            elif sammlung in (MODELL, DATEI):
                self._kurz_offen.add(meldung["ref"])
            elif sammlung in (TAG, MATERIAL) and meldung.get("ereignis") != "create_node":
                self._kurz_alles_neu += 1
                self._kurz_zwischen = None          # ein Tag oder Material geändert: kann viele Kacheln betreffen, selten — alles neu

    def _kurz_alle(self):
        """Die Kacheln aller Modelle, zwischengespeichert. Neu gebaut werden nur die, deren Modell, Datei, Tags oder Material sich seit
        dem letzten Mal geändert haben (`_kurz_veraltet`). Vorher galt der Zwischenspeicher nur, solange nichts geschrieben wurde: während
        des Einlesens baute damit jeder Klick alle Kacheln neu — bei 3000 Modellen 1,4–4 s je Filter-Klick (Messung 7.10.2026), bei 9 000
        auf einem älteren Rechner entsprechend mehr."""
        # Unter EINER Sperre von flatgraph (eine Transaktion ohne Schreiben, VERTRAG §3.1): sonst wartet jeder der fünf Lesezugriffe
        # je Kachel einzeln auf die laufende Schreib-Transaktion des Einlesens — gemessen 1,3 ms statt 0,03 ms je Kachel.
        with self._kurz_sperre:
            if self._kurz_zwischen is not None and not self._kurz_offen:
                return self._kurz_zwischen          # nichts geändert: ohne die Sperre von flatgraph (die hält gerade vielleicht ein Schreiber)
        # Reihenfolge immer: zuerst die Sperre von flatgraph, dann `_kurz_bau` — Abfragen unter `am_stueck` (main.py) halten die erste
        # schon; umgekehrt genommen warteten zwei Anfragen für immer aufeinander.
        with self.db.transaction(), self._kurz_bau:
            return self._kurz_nachbauen()

    def _kurz_nachbauen(self):
        with self._kurz_sperre:
            zwischen, offen, stand = self._kurz_zwischen, self._kurz_offen, self._kurz_alles_neu
            self._kurz_offen = set()
        if zwischen is None:
            erg = {k: self._kurz(k, v) for k, v in self.db.list_nodes(MODELL, readonly=True).items()}
        elif not offen:
            return zwischen
        else:
            mids = set()
            for r in offen:
                sammlung, _, schluessel = r.partition("/")
                if sammlung == MODELL:
                    mids.add(schluessel)
                elif (mid := self.modell_von(schluessel)):
                    mids.add(mid)
            erg = dict(zwischen)        # neu, nicht ändern: eine andere Anfrage liest den alten gerade
            for mid in mids:
                m = self.db.get_node(ref(MODELL, mid), readonly=True)
                if m is None:
                    erg.pop(mid, None)
                else:
                    erg[mid] = self._kurz(mid, m)
        with self._kurz_sperre:
            # Kam inzwischen „alles neu“ (Tag geändert), gilt das; Änderungen während des Bauens stehen schon im neuen `_kurz_offen`.
            if self._kurz_alles_neu == stand:
                self._kurz_zwischen = erg
        return erg

    def _modelle(self, suche=None, tag=None, ordner=None, fmt=None, ansicht="alle", sammlung=None, alle=None):
        """Kacheln für das Raster, gefiltert. Suche über den Wortindex (suche.py),
        Tag über die Nachbarschaft in flatgraph, der Rest über die Kacheln selbst."""
        if ansicht == "papierkorb":
            roh = self.db.list_nodes(MODELL, include_deleted=True, readonly=True)
            liste = [self._kurz(k, v, papierkorb=True) for k, v in roh.items()
                     if self.db.get_node(ref(MODELL, k), readonly=True) is None]
            return sorted(liste, key=lambda x: (x["name"] or "").lower())
        # `alle`: nur diese Kacheln prüfen statt aller (aenderungen).
        alle = self._kurz_alle() if alle is None else alle
        kandidaten = alle
        punkte = self.suche.suchen(suche) if suche else None
        if punkte is not None:
            kandidaten = {k: v for k, v in kandidaten.items() if k in punkte}
        if tag:
            mit_tag = {r.split("/", 1)[1] for r in
                       self.db.get_connected(ref(TAG, tag), direction="in", rel_type=HAT_TAG)}
            kandidaten = {k: v for k, v in kandidaten.items() if k in mit_tag}
        reihe = None
        if sammlung:
            reihe = self._sammlung_reihe(sammlung)
            kandidaten = {k: v for k, v in kandidaten.items() if k in reihe}
        liste = [dict(alle[k]) for k in kandidaten]       # flache Kopien: wer die Liste ändert, ändert nicht den Zwischenspeicher
        if fmt:
            liste = [x for x in liste if x["format"] == fmt]
        if ordner:
            liste = [x for x in liste if any(o == ordner or o.startswith(ordner.rstrip("/") + "/")
                                             for o in x["ordner"])]
        if ansicht == "favoriten":
            liste = [x for x in liste if x["favorit"]]
        elif ansicht == "duplikate":
            liste = [x for x in liste if x["duplikat"]]
        elif ansicht == "fehlt":
            liste = [x for x in liste if x["fehlt"] and not x["ohne_datei"]]
        elif ansicht == "unlesbar":
            liste = [x for x in liste if x["fehler"]]
        elif ansicht == "warteschlange":
            return sorted((x for x in liste if x["warteschlange"] is not None), key=lambda x: x["warteschlange"])
        if reihe is not None:
            return sorted(liste, key=lambda x: reihe[x["id"]])
        if ansicht == "neu":
            liste = sorted(liste, key=lambda x: x["angelegt"] or "", reverse=True)[:100]
            return liste
        if punkte is not None:
            # Mit Suche zuerst die Relevanz; die Oberfläche sortiert nur um, wenn man es verlangt.
            return sorted(liste, key=lambda x: (-punkte[x["id"]], (x["name"] or "").lower()))
        return sorted(liste, key=lambda x: (x["name"] or "").lower())

    def modell(self, mid):
        m = self.db.get_node(ref(MODELL, mid))
        papierkorb = False
        if m is None:
            m = self.db.get_node_raw(ref(MODELL, mid))
            if m is None:
                raise KatalogFehler(f"Modell {mid} gibt es nicht.")
            papierkorb = True
        kurz = self._kurz(mid, m, papierkorb)
        h = kurz["hash"]
        d = (self.db.get_node(ref(DATEI, h)) or self.db.get_node_raw(ref(DATEI, h)) or {}) if h else {}
        wurzeln = self.wurzeln()
        orte = [{**o, "absolut": self.absoluter_pfad(o),
                 "wurzel_name": wurzeln.get(o["wurzel"], {}).get("name")} for o in d.get("orte", [])]
        return {
            **kurz, "papierkorb": papierkorb, "orte": orte,
            "volumen_cm3": d.get("volumen_cm3"), "dreiecke": d.get("dreiecke"),
            "objekte": d.get("objekte"), "titel": d.get("titel"), "designer": d.get("designer"),
            "platten": d.get("platten") or [], "fehler_text": d.get("fehler"), "cad_fehler": d.get("cad_fehler"),
            "quelle_url": m.get("quelle_url"), "eingelesen": d.get("eingelesen"),
            "papierkorb_ablage": d.get("papierkorb", []),
            "zuletzt": self._zuletzt_absolut(d.get("zuletzt_ort")) if kurz["fehlt"] else None,
            "sammlungen": [] if papierkorb else self.sammlungen_von(mid),
            "material_herkunft": self.materialien_von(mid, kurz["hash"]) if not papierkorb else None,
            "ansichten": self.ansichten(mid, m, d),
            "ref_werte": m.get("ref_werte"),
            "drucke": [] if papierkorb else self.drucke.liste(mid),
        }

    def modell_aendern(self, mid, werte):
        # entwurf: ein Konstruktionsstand, der nicht gebraucht wird — ausblendbar, nicht in neuen Baugruppen. Kein Versionsbaum,
        # nur ein Etikett, das der Anwender setzt (03.10.2026: Versionsverwaltung war zu viel).
        erlaubt = {"favorit": bool, "gedruckt": bool, "entwurf": bool, "quelle_url": (str, type(None))}
        neu = {}
        for k, v in werte.items():
            if k not in erlaubt or not isinstance(v, erlaubt[k]):
                raise KatalogFehler(f"Feld {k!r} lässt sich so nicht ändern.")
            neu[k] = v
        if "quelle_url" in neu:
            # Nur http(s): die Oberfläche macht daraus einen Link, und ein
            # „javascript:“ wäre dort ausführbarer Code.
            url = (neu["quelle_url"] or "").strip()
            if url and (not re.match(r"https?://[^\s]+$", url, re.I) or len(url) > 2000):
                raise KatalogFehler("Quelle muss eine http(s)-Adresse sein.")
            neu["quelle_url"] = url or None
        if "gedruckt" in neu:
            # „Gedruckt“ ist abgeleitet: es gibt es, wenn es einen Druck gibt (KONZEPT §4.6).
            # Der Haken legt einen leeren Druck an; zurücknehmen geht nur, solange
            # kein Druck Angaben trägt.
            gesetzt = neu.pop("gedruckt")
            self.drucke.markieren(mid, gesetzt)
            if gesetzt:
                neu["warteschlange"] = None   # wie im 3MF Katalog: erledigt heisst raus aus der Warteschlange
        if neu:
            self.db.update_node(MODELL, mid, neu)

    def angesehen(self, mid):
        if self.db.get_node(ref(MODELL, mid), readonly=True) is not None:
            self.db.update_node(MODELL, mid, {"zuletzt_angesehen": jetzt()})

    def umbenennen(self, mid, name):
        """Wie im 3MF Katalog: der Name ist der Dateiname, die Endung bleibt.
        Jeder Ort wird umbenannt; nichts wird überschrieben."""
        name = (name or "").strip()
        if not name or any(c in name for c in '/\\\0') or name in (".", ".."):
            raise KatalogFehler("Ungültiger Name.")
        h = self.datei_von(mid)
        d = self.db.get_node(ref(DATEI, h))
        erledigt, neue_orte = [], []
        try:
            for o in d.get("orte", []):
                alt = self.absoluter_pfad(o)
                ext = os.path.splitext(alt)[1]
                ziel = os.path.join(os.path.dirname(alt), name + ext)
                if ziel != alt:
                    dateien.verschiebe(alt, ziel)
                    erledigt.append((ziel, alt))
                rel = o["pfad"].rsplit("/", 1)[0] + "/" if "/" in o["pfad"] else ""
                st = os.stat(ziel)
                neue_orte.append({**o, "pfad": rel + name + ext, "groesse": st.st_size,
                                  "mtime": st.st_mtime})
        except dateien.ZielBelegt as e:
            self._zurueck(erledigt)
            raise KatalogFehler(f"Dort liegt schon eine Datei: {e}") from e
        except OSError:
            self._zurueck(erledigt)
            raise
        with self.db.transaction():
            self.db.update_node(DATEI, h, {"orte": neue_orte})
            self.db.update_node(MODELL, mid, {"name": name})

    # ------------------------------------------------------------ Verschieben
    #
    # Wie im 3MF Katalog: der Ordner in der App ist das Verzeichnis auf der
    # Platte. Verschieben heisst die Datei verschieben — ohne zu
    # überschreiben (dateien.verschiebe).

    def _ordner_pfad(self, ordner_id):
        wid, _, rel = ordner_id.partition("/")
        wpfad = self.wurzel_pfad(wid)
        if wpfad is None:
            raise KatalogFehler("Unbekannter Wurzelordner.")
        ziel = os.path.realpath(os.path.join(wpfad, *[t for t in rel.split("/") if t]))
        if ziel != os.path.realpath(wpfad) and not ziel.startswith(os.path.realpath(wpfad) + os.sep):
            raise KatalogFehler("Ziel liegt ausserhalb des Wurzelordners.")
        return wid, wpfad, ziel

    def verzeichnisse(self):
        """Alle Verzeichnisse unter den Wurzeln, auch leere — Ziele zum Verschieben."""
        liste = []
        for wid, w in self.wurzeln().items():
            liste.append({"id": wid, "name": w["name"], "pfad": ""})
            for ordner, unter, _ in os.walk(w["pfad"]):
                unter[:] = sorted(u for u in unter if not u.startswith("."))
                for u in unter:
                    rel = os.path.relpath(os.path.join(ordner, u), w["pfad"]).replace(os.sep, "/")
                    liste.append({"id": f"{wid}/{rel}", "name": w["name"], "pfad": rel})
        return liste

    def ordner_anlegen(self, eltern_id, name):
        name = (name or "").strip()
        if not name or any(c in name for c in '/\\\0') or name.startswith("."):
            raise KatalogFehler("Ungültiger Ordnername.")
        wid, _, eltern = self._ordner_pfad(eltern_id)
        ziel = os.path.join(eltern, name)
        if os.path.isdir(ziel) and not os.path.islink(ziel):
            # Den Ordner gibt es schon — oft als Rest, weil der Baum nur Ordner mit Modellen zeigt: ein gelöschtes Modell lässt sein
            # leeres Verzeichnis zurück, und von aussen sieht der Anwender nichts davon. Wer ihn „neu“ anlegt, will ihn benutzen.
            return f"{eltern_id.rstrip('/')}/{name}"
        if os.path.lexists(ziel):
            raise KatalogFehler("Dort liegt schon eine Datei mit diesem Namen.")
        os.makedirs(ziel)
        return f"{eltern_id.rstrip('/')}/{name}"

    def ordner_inhalt(self, ordner_id):
        """Was in einem Ordner liegt, damit der Anwender vor dem Löschen sieht, was passiert: Modelle, die ganz darin liegen
        (sie gehen in den Papierkorb), Modelle mit einer Kopie ausserhalb (bleiben, sonst ginge die andere Kopie mit) und
        alle übrigen Dateien (Bilder, PDFs, Texte aus einem entpackten Archiv — partAtlas rührt sie nie an)."""
        wid, wpfad, pfad = self._ordner_pfad(ordner_id)
        wreal = os.path.realpath(wpfad)
        rel = os.path.relpath(pfad, wreal).replace(os.sep, "/")
        if not os.path.isdir(pfad):
            raise KatalogFehler("Den Ordner gibt es nicht (mehr).")
        modelle, mehrfach, bekannt = [], [], set()
        for h, d in self._dateien().items():
            orte = d.get("orte", [])
            innen = [o for o in orte if o["wurzel"] == wid and (rel == "." or o["pfad"].startswith(rel + "/"))]
            if not innen:
                continue
            mid = self.modell_von(h)
            if mid is None:
                continue
            bekannt.update(o["pfad"] for o in innen)
            if len(innen) == len(orte):
                modelle.append(mid)
            else:
                mehrfach.append(mid)
        andere = []
        for ordner, _, namen in os.walk(pfad):
            for n in namen:
                p = os.path.relpath(os.path.join(ordner, n), wreal).replace(os.sep, "/")
                if p not in bekannt:
                    andere.append(p if rel == "." else p[len(rel) + 1:])
        return {"id": ordner_id, "name": os.path.basename(pfad), "pfad": pfad, "wurzel": rel == ".", "modelle": modelle,
                "mehrfach": mehrfach, "andere": sorted(andere)}

    def ordner_loeschen(self, ordner_id, tags=(), sammlungen=()):
        """Alle Modelle des Ordners aus dem Katalog nehmen (Papierkorb). Der Ordner und alles darin bleibt auf der Platte, auch die
        leeren Verzeichnisse: partAtlas löscht in den Ordnern des Anwenders nichts. Ein Wurzelordner geht hier nicht: er wird nur
        aus partAtlas entfernt."""
        i = self.ordner_inhalt(ordner_id)
        if i["wurzel"]:
            raise KatalogFehler("Ein Wurzelordner wird nicht gelöscht, nur aus partAtlas entfernt.")
        if i["modelle"]:
            self._sichern_vor("ordner-aus-katalog")
        fehler = self.loeschen_mit(i["modelle"], tags, sammlungen) if i["modelle"] else []
        return {"fehler": fehler, "modelle": len(i["modelle"]) - len(fehler), "pfad": i["pfad"],
                "mehrfach": len(i["mehrfach"]), "andere": len(i["andere"])}

    def verschieben(self, mid, ordner_id):
        h = self.datei_von(mid)
        d = self.db.get_node(ref(DATEI, h)) if h else None
        orte = (d or {}).get("orte", [])
        if len(orte) != 1:
            raise KatalogFehler("Das Modell liegt mehrfach oder fehlt — erst die Duplikate auflösen."
                                if orte else "Die Datei ist nicht da.")
        wid, wpfad, zielordner = self._ordner_pfad(ordner_id)
        alt = self.absoluter_pfad(orte[0])
        ziel = os.path.join(zielordner, os.path.basename(alt))
        if os.path.realpath(ziel) == os.path.realpath(alt):
            return
        try:
            dateien.verschiebe(alt, ziel)
        except dateien.ZielBelegt as e:
            raise KatalogFehler(f"Im Zielordner liegt schon „{os.path.basename(alt)}“.") from e
        st = os.stat(ziel)
        self.db.update_node(DATEI, h, {"orte": [{"wurzel": wid, "pfad": os.path.relpath(ziel, wpfad).replace(os.sep, "/"),
                                                 "groesse": st.st_size, "mtime": st.st_mtime}]})

    # ------------------------------------------------------------ Bilder des Anwenders
    #
    # Ein Modell kann mehrere Bilder haben (Foto vom Druck, Ansicht von
    # hinten …). Sie hängen am Modell wie ein PDF am Dokument in pDMS: eine
    # Liste `bilder` mit Verweisen in den Vault, kein Knoten je Bild. Das
    # erste ist das Titelbild. Pillow liest und schreibt jedes neu als PNG —
    # so kommt nur ein Bild an, keine Metadaten, kein Anhängsel.

    MAX_BILD = 15 * 1024**2

    def _bilder(self, mid, papierkorb=False):
        m = self.db.get_node(ref(MODELL, mid), readonly=True)
        if m is None and papierkorb:
            m = self.db.get_node_raw(ref(MODELL, mid))
        if m is None:
            raise KatalogFehler(f"Modell {mid} gibt es nicht.")
        return m, list(m.get("bilder") or [])

    def png_aus(self, daten):
        """Rohe Bildbytes → PNG-Bytes: lesbar, höchstens 1600 px, gedreht, ohne Metadaten."""
        from PIL import Image, ImageOps, UnidentifiedImageError
        if len(daten) > self.MAX_BILD:
            raise KatalogFehler("Bild grösser als 15 MB.")
        try:
            bild = Image.open(io.BytesIO(daten))
            if bild.format not in ("PNG", "JPEG", "WEBP"):
                raise KatalogFehler("Nur PNG, JPG oder WebP.")
            bild.load()
        except (UnidentifiedImageError, OSError) as e:
            raise KatalogFehler("Kein lesbares Bild.") from e
        # Handyfotos liegen sonst quer: die Drehung steht nur in den Exif-Daten,
        # und die fallen beim Neuschreiben weg.
        bild = ImageOps.exif_transpose(bild).convert("RGBA")
        bild.thumbnail((1600, 1600))
        puffer = io.BytesIO()
        bild.save(puffer, "PNG", optimize=True)
        return puffer.getvalue()

    def bild_ablegen(self, png, name):
        """PNG in den Vault legen; gibt (Kennung, Pfad im Vault) zurück."""
        k = hashlib.sha256(png).hexdigest()[:12]
        titel = re.sub(r"[^\w.-]+", "_", name or "bild")[:60]
        rel = f"vault/bilder/{titel}__{k}.png"
        ziel = self.b.pfad(*rel.split("/"))
        if not os.path.exists(ziel):
            dateien.schreibe_atomar(ziel, png)
        return k, rel

    def bild_hinzufuegen(self, mid, daten):
        m, bilder = self._bilder(mid)
        k, rel = self.bild_ablegen(self.png_aus(daten), m.get("name") or mid)
        if any(b["k"] == k for b in bilder):
            return k
        self.db.update_node(MODELL, mid, {"bilder": bilder + [{"k": k, "datei": rel, "angelegt": jetzt()}]})
        return k

    def bild_entfernen(self, mid, k):
        """Aus der Liste; die Datei geht nach vault_archive — wie in pDMS
        verschwindet nichts, was der Anwender selbst hineingetan hat."""
        _, bilder = self._bilder(mid)
        weg = [b for b in bilder if b["k"] == k]
        if not weg:
            raise KatalogFehler("Dieses Bild gibt es nicht.")
        self.db.update_node(MODELL, mid, {"bilder": [b for b in bilder if b["k"] != k]})
        self._archivieren(weg[0]["datei"])

    def bild_als_titel(self, mid, k):
        _, bilder = self._bilder(mid)
        if not any(b["k"] == k for b in bilder):
            raise KatalogFehler("Dieses Bild gibt es nicht.")
        self.db.update_node(MODELL, mid, {"bilder": sorted(bilder, key=lambda b: b["k"] != k), "vorschau_art": None})

    def vorschau_als_titel(self, mid, art):
        """Das Bild aus der Datei oder die berechnete Vorschau soll auf der
        Kachel stehen, auch wenn eigene Bilder da sind — sonst bliebe ein
        schlechtes eigenes Bild nur durch Löschen zu überstimmen."""
        m, _ = self._bilder(mid)
        h = self.datei_von(mid)
        d = self.db.get_node(ref(DATEI, h), readonly=True) if h else None
        if art not in [a for a, _ in self.vorschauen(d)]:
            raise KatalogFehler("Dieses Bild gibt es nicht.")
        self.db.update_node(MODELL, mid, {"vorschau_art": art})

    def bild_pfad(self, mid, k=None):
        """Pfad eines Bilds, ohne `k` das Titelbild. Auch im Papierkorb."""
        try:
            _, bilder = self._bilder(mid, papierkorb=True)
        except KatalogFehler:
            return None
        b = next((b for b in bilder if k is None or b["k"] == k), None)
        return self.b.pfad(*b["datei"].split("/")) if b else None

    def _archivieren(self, rel):
        quelle = self.b.pfad(*rel.split("/"))
        if os.path.exists(quelle):
            ziel = dateien.freier_name(self.b.pfad("vault_archive", os.path.basename(rel)))
            os.makedirs(os.path.dirname(ziel), exist_ok=True)
            dateien.verschiebe(quelle, ziel)

    def ansichten(self, mid, m, d):
        """Was die Galerie im Inspektor durchblättert, in dieser Reihenfolge:
        die Bilder des Anwenders, dann was in der Datei steckt, dann was
        partAtlas berechnet hat. Die 3D-Ansicht fügt die Oberfläche ein."""
        art_titel = m.get("vorschau_art")
        eigene = [{"art": "eigen", "k": b["k"], "url": f"/api/modelle/{mid}/bilder/{b['k']}",
                   "titel": "Vorschaubild" if i == 0 and not art_titel else "Eigenes Bild",
                   "ist_vorschaubild": i == 0 and not art_titel} for i, b in enumerate(m.get("bilder") or [])]
        h = self.datei_von(mid) or self._datei_im_papierkorb(mid)
        titel = {"extrahiert": "Aus der Datei", "berechnet": "Vorschau"}
        vorschauen = [a for a, _ in self.vorschauen(d)]
        # Ohne Wahl und ohne eigenes Bild zeigt die Kachel das beste der Datei.
        gewaehlt = art_titel or (vorschauen[0] if vorschauen and not eigene else None)
        return eigene + [{"art": art, "url": f"/api/vorschau/{h}.{art}.png", "titel": titel[art],
                          "ist_vorschaubild": art == gewaehlt} for art in vorschauen]

    # ------------------------------------------------------------ Hochladen und Archive

    def hochladen(self, ordner_id, name, daten, unterordner=""):
        """Eine Datei aus dem Browser in einen Ordner legen, nie überschreiben.
        Ein Archiv wird gleich entpackt. Gibt die neuen Pfade zurück.

        `unterordner`: wo die Datei in einem hineingezogenen Ordner lag (`Projekt/Teile`) — die Struktur bleibt. Angelegt wird nur
        Neues; ein schon vorhandener Unterordner wird mitbenutzt, eine Datei darin nie überschrieben."""
        name = os.path.basename((name or "").replace("\\", "/"))
        if not name or name.startswith("."):
            raise KatalogFehler("Ungültiger Dateiname.")
        if formate.format_von(name) is None and not archiv.ist_archiv(name):
            raise KatalogFehler(f"„{name}“ ist weder Modell noch Archiv.")
        _, wpfad, zielordner = self._ordner_pfad(ordner_id)
        teile = [t for t in (unterordner or "").replace("\\", "/").split("/") if t]
        if any(t in (".", "..") or t.startswith(".") for t in teile):
            raise KatalogFehler("Ungültiger Unterordner.")
        if teile:
            zielordner = os.path.join(zielordner, *teile)
            echt, wurzel = os.path.realpath(zielordner), os.path.realpath(wpfad)
            if not echt.startswith(wurzel + os.sep):
                raise KatalogFehler("Ziel liegt ausserhalb des Wurzelordners.")
            os.makedirs(zielordner, exist_ok=True)
        if archiv.ist_archiv(name):
            # Das Archiv selbst landet nur im Bestand (arbeit/), entpackt wird in einen neuen Unterordner des Ziels: so muss partAtlas
            # im Ordner des Anwenders nichts wieder wegräumen.
            arbeit = dateien.freier_name(self.b.pfad("arbeit", "hochladen", name))
            dateien.neu_anlegen(arbeit, daten)
            try:
                _, neu, _ = archiv.entpacken(arbeit, ziel=dateien.freier_name(os.path.join(zielordner, archiv.stamm(name))))
            finally:
                self.b.entfernen(arbeit)
            return neu
        ziel = dateien.freier_name(os.path.join(zielordner, name))
        dateien.neu_anlegen(ziel, daten)
        return [ziel]

    def archive(self):
        """Archive unter den Wurzeln — der 3MF Katalog entpackt auf Rückfrage."""
        liste = []
        for wid, w in self.wurzeln().items():
            for ordner, unter, namen in os.walk(w["pfad"]):
                unter[:] = sorted(u for u in unter if not u.startswith("."))
                for n in sorted(namen):
                    if archiv.ist_archiv(n) and not n.startswith("."):
                        p = os.path.join(ordner, n)
                        liste.append({"id": f"{wid}/{os.path.relpath(p, w['pfad']).replace(os.sep, '/')}",
                                      "name": n, "groesse": os.path.getsize(p)})
        return liste

    def archiv_entpacken(self, archiv_id):
        wid, wpfad, pfad = self._ordner_pfad(archiv_id)
        if not os.path.isfile(pfad) or not archiv.ist_archiv(pfad):
            raise KatalogFehler("Kein Archiv.")
        try:
            ziel, neu, weg = archiv.entpacken(pfad)
        except archiv.ArchivFehler as e:
            raise KatalogFehler(str(e)) from e
        return {"ordner": os.path.relpath(ziel, wpfad), "entpackt": len(neu), "uebersprungen": weg}

    # ------------------------------------------------------------ Mehrere auf einmal

    def stapel(self, aktion, modelle, wert=None, melden=None):
        """Eine Aktion für viele Modelle; reine Graph-Änderungen in einer
        Transaktion, Dateiaktionen einzeln (jede für sich rückgängig)."""
        fehler = []
        if aktion in ("favorit", "gedruckt", "entwurf", "tag", "material", "sammlung", "warteschlange", "aus_warteschlange", "behalten"):
            with self.db.transaction():
                for mid in modelle:
                    if aktion in ("favorit", "gedruckt", "entwurf"):
                        self.modell_aendern(mid, {aktion: bool(wert)})
                    elif aktion == "tag":
                        self._tag_verbinden(mid, wert)
                    elif aktion == "material":
                        self.material_vorsehen(mid, wert)
                    elif aktion == "warteschlange":
                        self.in_warteschlange(mid)
                    elif aktion == "aus_warteschlange":
                        self.aus_warteschlange(mid)
                    elif aktion == "behalten":
                        from . import aufraeumen
                        aufraeumen.behalten(self, mid, True)
                if aktion == "sammlung":
                    self._sammlung_pruefen(wert)
                    self._hinzufuegen(wert, modelle)
        elif aktion == "loeschen":
            wert = wert if isinstance(wert, dict) else {}
            fehler = self.loeschen_mit(modelle, wert.get("tags") or (), wert.get("sammlungen") or (), melden=melden)
        elif aktion == "wiederherstellen":
            # In Gruppen je eine Transaktion wie beim Löschen; vorher je Modell eine Anfrage samt fsync. Sicher gebündelt: ein Modell, das
            # scheitert, hat noch nichts geschrieben (wiederherstellen legt zuerst Dateien zurück und nimmt sie bei einem Fehler selbst zurück).
            fehler = self._gruppenweise(modelle, self.wiederherstellen, melden)
        elif aktion == "verschieben":
            for mid in modelle:
                try:
                    self.verschieben(mid, wert)
                except (KatalogFehler, OSError) as e:
                    fehler.append({"id": mid, "fehler": str(e)})
        else:
            raise KatalogFehler(f"Unbekannte Aktion {aktion!r}.")
        return {"fehler": fehler}

    def _gruppenweise(self, modelle, aufruf, melden=None):
        """`aufruf(mid)` für viele Modelle, je LOESCHEN_GRUPPE eine Transaktion. Einzeln kostete jedes Modell seinen fsync: „alle 8 600
        löschen“ dauerte unter Windows Minuten, und jede andere Anfrage wartete dazwischen (Protokoll des Anwenders: /api/modelle 51 s).
        Nach jeder Gruppe kurz loslassen: die Sperre von flatgraph ist nicht fair — wer sie eben freigab, bekommt sie meist gleich wieder,
        und Zähler und Tags warteten trotz Gruppen 14 s. Ein Modell, das scheitert, wird gemeldet; die anderen gehen weiter.
        `melden(fertig, gesamt)` am Anfang und nach jeder Gruppe — für die Anzeige unten links."""
        fehler = []
        if melden:
            melden(0, len(modelle))
        for i in range(0, len(modelle), LOESCHEN_GRUPPE):
            if i:
                time.sleep(0.02)
            with self.db.transaction():
                for mid in modelle[i:i + LOESCHEN_GRUPPE]:
                    try:
                        aufruf(mid)
                    except (KatalogFehler, OSError) as e:
                        fehler.append({"id": mid, "fehler": str(e)})
            if melden:
                melden(min(i + LOESCHEN_GRUPPE, len(modelle)), len(modelle))
        return fehler

    @staticmethod
    def _zurueck(erledigt):
        for ziel, alt in reversed(erledigt):
            try:
                dateien.verschiebe(ziel, alt)
            except OSError:
                pass

    # ------------------------------------------------------------ Sammlungen
    #
    # Mitgliedschaft ist eine Kante Modell → Sammlung mit `position` als
    # Kantenfeld; ein Modell kann in vielen Sammlungen sein. flatgraph
    # ändert Kanten nicht an Ort und Stelle, also heisst Umsortieren: die
    # Kanten der Sammlung in einer Transaktion neu legen.

    def sammlungen(self):
        liste = []
        for sid, s in self.db.list_nodes(SAMMLUNG, readonly=True).items():
            n = len(self.db.get_connected(ref(SAMMLUNG, sid), direction="in", rel_type=IN_SAMMLUNG))
            liste.append({"id": sid, "name": s["name"], "anzahl": n, "angelegt": s.get("angelegt")})
        return sorted(liste, key=lambda x: x["name"].lower())

    def _sammlung_pruefen(self, sid):
        if self.db.get_node(ref(SAMMLUNG, sid), readonly=True) is None:
            raise KatalogFehler(f"Sammlung {sid} gibt es nicht.")

    def _sammlung_kanten(self, sid):
        """[(kanten_id, modell_id, position)] in Reihenfolge."""
        kanten = [(eid, e["source"].split("/", 1)[1], e.get("position", 0))
                  for eid, e in self.db.get_connected_edges(ref(SAMMLUNG, sid), direction="in", rel_type=IN_SAMMLUNG)
                  if self.db.get_node(e["source"], readonly=True) is not None]
        return sorted(kanten, key=lambda k: (k[2], k[1]))

    def _sammlung_reihe(self, sid):
        return {mid: i for i, (_, mid, _) in enumerate(self._sammlung_kanten(sid))}

    def sammlungen_von(self, mid):
        namen = []
        for r in self.db.get_connected(ref(MODELL, mid), rel_type=IN_SAMMLUNG):
            s = self.db.get_node(r, readonly=True)
            if s is not None:
                namen.append({"id": r.split("/", 1)[1], "name": s["name"]})
        return sorted(namen, key=lambda x: x["name"].lower())

    @staticmethod
    def _name_pruefen(name):
        name = (name or "").strip()
        if not name or len(name) > 120:
            raise KatalogFehler("Name leer oder zu lang.")
        return name

    def sammlung_anlegen(self, name, modelle=()):
        name = self._name_pruefen(name)
        with self.db.transaction():
            sid = self.db.next_id(SAMMLUNG, "s_", 4)
            self.db.create_node(SAMMLUNG, sid, {"name": name, "angelegt": jetzt()})
            self._hinzufuegen(sid, modelle)
        return sid

    def sammlung_umbenennen(self, sid, name):
        self._sammlung_pruefen(sid)
        self.db.update_node(SAMMLUNG, sid, {"name": self._name_pruefen(name)})

    def sammlung_loeschen(self, sid):
        """Die Sammlung geht, die Modelle bleiben — nur ihre Kanten verlieren das Ziel."""
        self._sammlung_pruefen(sid)
        self.db.soft_delete(SAMMLUNG, sid)

    def _hinzufuegen(self, sid, modelle):
        vorhanden = self._sammlung_kanten(sid)
        drin = {mid for _, mid, _ in vorhanden}
        pos = max((p for _, _, p in vorhanden), default=-1) + 1
        for mid in modelle:
            if mid in drin or self.db.get_node(ref(MODELL, mid), readonly=True) is None:
                continue
            self.db.create_edge(ref(MODELL, mid), ref(SAMMLUNG, sid), IN_SAMMLUNG, meta={"position": pos})
            drin.add(mid)
            pos += 1

    def zur_sammlung(self, sid, modelle):
        self._sammlung_pruefen(sid)
        with self.db.transaction():
            self._hinzufuegen(sid, modelle)

    def aus_sammlung(self, sid, mid):
        for eid, m, _ in self._sammlung_kanten(sid):
            if m == mid:
                self.db.delete_edge(eid)

    def sammlung_ordnen(self, sid, modelle):
        """Neue Reihenfolge; wer fehlt, kommt in alter Reihenfolge ans Ende."""
        self._sammlung_pruefen(sid)
        alt = self._sammlung_kanten(sid)
        drin = [mid for _, mid, _ in alt]
        neu = [m for m in dict.fromkeys(modelle) if m in drin] + [m for m in drin if m not in modelle]
        with self.db.transaction():
            for eid, _, _ in alt:
                self.db.delete_edge(eid)
            for pos, mid in enumerate(neu):
                self.db.create_edge(ref(MODELL, mid), ref(SAMMLUNG, sid), IN_SAMMLUNG, meta={"position": pos})

    # ------------------------------------------------------------ Warteschlange
    #
    # Ein Feld am Modell wie im 3MF Katalog (`queue_position`), bis die
    # Flotte in Phase 4 eine eigene Sammlung braucht (KONZEPT §6.1).

    def warteschlange(self):
        return self.modelle(ansicht="warteschlange")

    def in_warteschlange(self, mid):
        m = self.db.get_node(ref(MODELL, mid), readonly=True)
        if m is None:
            raise KatalogFehler(f"Modell {mid} gibt es nicht.")
        if m.get("warteschlange") is not None:
            return
        letzte = max((x["warteschlange"] for x in self.warteschlange()), default=-1)
        self.db.update_node(MODELL, mid, {"warteschlange": letzte + 1})

    def aus_warteschlange(self, mid):
        self.db.update_node(MODELL, mid, {"warteschlange": None})

    def warteschlange_ordnen(self, modelle):
        drin = [x["id"] for x in self.warteschlange()]
        neu = [m for m in dict.fromkeys(modelle) if m in drin] + [m for m in drin if m not in modelle]
        with self.db.transaction():
            for pos, mid in enumerate(neu):
                self.db.update_node(MODELL, mid, {"warteschlange": pos})

    # ------------------------------------------------------------ Tags

    # ------------------------------------------------------------ Material

    def material_knoten(self, name):
        """Name → Kennung des Material-Knotens; legt ihn an, wenn es ihn nicht gibt."""
        mat = str(name or "").strip().upper().replace("/", "-")[:20]
        if not mat:
            raise KatalogFehler("Kein Material angegeben.")
        if self.db.get_node(ref(MATERIAL, mat), readonly=True) is None:
            if self.db.get_node_raw(ref(MATERIAL, mat)) is not None:
                self.db.restore_node(MATERIAL, mat)
            else:
                self.db.create_node(MATERIAL, mat, {"name": mat})
        return mat

    def _datei_materialien(self, h, felder):
        for f in {f["typ"] for p in felder.get("platten") or [] for f in p.get("filamente", []) if f.get("typ")}:
            mat = self.material_knoten(f)
            if ref(MATERIAL, mat) not in self.db.get_connected(ref(DATEI, h), rel_type=BRAUCHT):
                self.db.create_edge(ref(DATEI, h), ref(MATERIAL, mat), BRAUCHT)

    def _material_nachziehen(self):
        """Grundbestand anlegen und Dateien aus der Zeit vor den Material-
        Knoten verbinden. Schreibt nur, wenn etwas fehlt."""
        fehlt = [m for m in MATERIALIEN if self.db.get_node(ref(MATERIAL, m), readonly=True) is None]
        dateien = {h: d for h, d in self.db.list_nodes(DATEI, readonly=True).items()
                   if any(f.get("typ") for p in d.get("platten") or [] for f in p.get("filamente", []))
                   and not self.db.get_connected(ref(DATEI, h), rel_type=BRAUCHT)}
        if not fehlt and not dateien:
            return
        with self.db.transaction():
            for m in fehlt:
                self.material_knoten(m)
            for h, d in dateien.items():
                self._datei_materialien(h, d)

    def _vault_nachziehen(self):
        """Bestände von vorher in die heutige Form bringen. Schreibt nur, wenn
        etwas fehlt. Erst die Dateien, dann die Knoten: bricht es dazwischen
        ab, holt der nächste Start den Rest nach.

        - Vorschau ohne Art im Namen: `cache/vorschau/<h>.png` (bis 0.10)
          oder `vault/vorschau/<h>.png` (0.11) → `<h>.<art>.png`, Feld dazu.
        - Eigenes Bild als Feld `bild` (bis 0.10) oder als Knoten
          MODEL_IMAGE (0.11) → Liste `bilder` am Modell.
        """
        alt_cache = self.b.pfad("cache", "vorschau")
        art_von = {"eingebettet": "extrahiert", "gerendert": "berechnet"}
        dateien_alt = {h: art_von[d["vorschau"]]
                       for h, d in self.db.list_nodes(DATEI, include_deleted=True, readonly=True).items()
                       if d.get("vorschau") in art_von and not d.get(f"vorschau_{art_von[d['vorschau']]}")}
        for h, art in dateien_alt.items():
            ziel = self.b.vorschau_pfad(h, art)
            for quelle in (self.b.pfad("vault", "vorschau", f"{h}.png"), os.path.join(alt_cache, f"{h}.png")):
                if not os.path.exists(ziel) and os.path.exists(quelle):
                    os.replace(quelle, ziel)
        modelle = self.db.list_nodes(MODELL, include_deleted=True, readonly=True)
        feld_bild = {mid: m["bild"] for mid, m in modelle.items() if m.get("bild")}
        knoten_bild = {}
        for mid in modelle:
            for kid, ziel in self.db.verwendungen(ref(MODELL, mid), direction="out").get("HAS_IMAGE", []):
                knoten_bild.setdefault(mid, []).append((kid, ziel))
        if dateien_alt or feld_bild or knoten_bild:
            with self.db.transaction():
                for h, art in dateien_alt.items():
                    if os.path.exists(self.b.vorschau_pfad(h, art)):
                        self.db.update_node(DATEI, h, {f"vorschau_{art}": self.b.vorschau_rel(h, art), "datei": None})
                for mid in set(feld_bild) | set(knoten_bild):
                    bilder = list(modelle[mid].get("bilder") or [])
                    pfade = [feld_bild[mid]] if mid in feld_bild else []
                    for _, ziel in knoten_bild.get(mid, []):
                        b = self.db.get_node_raw(ziel) or {}
                        # Ein in 0.11 ersetztes Bild lag schon im Papierkorb: nicht mehr dabei.
                        if b.get("datei") and (not b.get("_deletion_flag") or b.get("_geloescht_durch") == ref(MODELL, mid)):
                            pfade.append(b["datei"])
                        # soft_delete nimmt die Kante mit; ein schon gelöschter Knoten hat keine sichtbare mehr.
                        if not b.get("_deletion_flag"):
                            self.db.soft_delete(*ziel.split("/", 1))
                    for rel in pfade:
                        pfad = self.b.pfad(*rel.split("/"))
                        if os.path.exists(pfad):
                            with open(pfad, "rb") as f:
                                k = hashlib.sha256(f.read()).hexdigest()[:12]
                            if not any(x["k"] == k for x in bilder):
                                bilder.append({"k": k, "datei": rel, "angelegt": jetzt()})
                    self.db.update_node(MODELL, mid, {"bilder": bilder, "bild": None})
        for ordner in (alt_cache, os.path.dirname(alt_cache)):
            try:
                os.rmdir(ordner)
            except OSError:
                pass

    def materialien_von(self, mid, h=None):
        h = h if h is not None else self.datei_von(mid)
        name = lambda r: r.split("/", 1)[1]
        return {"vorgesehen": sorted(name(r) for r in self.db.get_connected(ref(MODELL, mid), rel_type=VORGESEHEN)),
                "aus_datei": sorted(name(r) for r in self.db.get_connected(ref(DATEI, h), rel_type=BRAUCHT)) if h else []}

    def material_vorsehen(self, mid, name):
        if self.db.get_node(ref(MODELL, mid), readonly=True) is None:
            raise KatalogFehler(f"Modell {mid} gibt es nicht.")
        mat = self.material_knoten(name)
        if ref(MATERIAL, mat) not in self.db.get_connected(ref(MODELL, mid), rel_type=VORGESEHEN):
            self.db.create_edge(ref(MODELL, mid), ref(MATERIAL, mat), VORGESEHEN)
        return mat

    def material_loesen(self, mid, name):
        for kid, andere in self.db.verwendungen(ref(MODELL, mid), direction="out").get(VORGESEHEN, []):
            if andere == ref(MATERIAL, str(name).upper()):
                self.db.delete_edge(kid)

    def materialien(self):
        """Alle Material-Knoten, der Grundbestand zuerst."""
        alle = [k for k in self.db.list_nodes(MATERIAL, readonly=True)]
        return [m for m in MATERIALIEN if m in alle] + sorted(m for m in alle if m not in MATERIALIEN)

    def _tag_verbinden(self, mid, name):
        name = tags.normalisiere(name)
        if not name:
            raise KatalogFehler("Leerer Tag.")
        if self.db.get_node(ref(TAG, name), readonly=True) is None:
            if self.db.get_node_raw(ref(TAG, name)) is not None:
                self.db.restore_node(TAG, name)
            else:
                self.db.create_node(TAG, name, {"name": name})
        if ref(TAG, name) not in self.db.get_connected(ref(MODELL, mid), rel_type=HAT_TAG):
            self.db.create_edge(ref(MODELL, mid), ref(TAG, name), HAT_TAG)
        return name

    def tag_setzen(self, mid, name):
        with self.db.transaction():
            return self._tag_verbinden(mid, name)

    def tag_loesen(self, mid, name):
        for kid, andere in self.db.verwendungen(ref(MODELL, mid), direction="out").get(HAT_TAG, []):
            if andere == ref(TAG, name):
                self.db.delete_edge(kid)

    def tags(self):
        """[{name, anzahl}] — Anzahl über die Nachbarschaft, nicht gezählt über Modelle."""
        liste = []
        for name in self.db.list_nodes(TAG, readonly=True):
            n = len(self.db.get_connected(ref(TAG, name), direction="in", rel_type=HAT_TAG))
            if n:
                liste.append({"name": name, "anzahl": n})
        return sorted(liste, key=lambda t: (-t["anzahl"], t["name"]))

    # ------------------------------------------------------------ Ordner (abgeleitet)

    def ordnerbaum(self):
        """Je Wurzel ein Baum aus den Pfaden der Dateien — KONZEPT §3.1."""
        baeume = {wid: {"id": wid, "name": w["name"], "pfad": w["pfad"], "anzahl": 0, "kinder": {}}
                  for wid, w in self.wurzeln().items()}
        for d in self._dateien().values():
            for o in d.get("orte", []):
                knoten = baeume.get(o["wurzel"])
                if knoten is None:
                    continue
                knoten["anzahl"] += 1
                teile = o["pfad"].split("/")[:-1]
                weg = o["wurzel"]
                for t in teile:
                    weg += "/" + t
                    knoten = knoten["kinder"].setdefault(t, {"id": weg, "name": t, "anzahl": 0, "kinder": {}})
                    knoten["anzahl"] += 1

        def liste(k):
            return {**k, "kinder": [liste(c) for c in sorted(k["kinder"].values(), key=lambda c: c["name"].lower())]}
        return [liste(b) for b in sorted(baeume.values(), key=lambda b: b["name"].lower())]

    # ------------------------------------------------------------ Löschen

    def loeschvorschau(self, mid):
        return self.loeschvorschau_viele([mid])

    def loeschvorschau_viele(self, modelle):
        """Was am Modell hängt, damit man informiert entscheidet — ohne etwas
        zu ändern. Alles ist ein Schritt in der Nachbarschaft (flatgraph):
        Tags, Sammlungen und Baugruppen je mit der Frage, ob noch andere
        Modelle daran hängen. `loeschfolgen` (VERTRAG §2.4) sagt, was der
        Papierkorb mitnimmt."""
        from .baugruppen import ENTHAELT
        weg = set(modelle)
        knoten, kanten, pfade, bilder, schlange = [], {}, [], 0, 0
        tags, sammlungen, baugruppen = {}, {}, {}
        for mid in modelle:
            m = self.db.get_node(ref(MODELL, mid), readonly=True)
            if m is None:
                continue
            folgen = self.db.loeschfolgen(ref(MODELL, mid))
            knoten += folgen["knoten"]
            for kid in folgen["kanten"]:
                e = self.db.get_edge(kid)
                if e:
                    kanten[e["type"]] = kanten.get(e["type"], 0) + 1
            h = self.datei_von(mid)
            d = self.db.get_node(ref(DATEI, h), readonly=True) if h else None
            pfade += [self.absoluter_pfad(o) for o in (d or {}).get("orte", [])]
            bilder += len(m.get("bilder") or [])
            schlange += m.get("warteschlange") is not None
            for r in self.db.get_connected(ref(MODELL, mid), rel_type=HAT_TAG):
                tags.setdefault(r.split("/", 1)[1], set()).add(mid)
            for r in self.db.get_connected(ref(MODELL, mid), rel_type=IN_SAMMLUNG):
                sammlungen.setdefault(r, set()).add(mid)
            for _, e in self.db.get_connected_edges(ref(MODELL, mid), direction="in", rel_type=ENTHAELT):
                if self.db.get_node(e["source"], readonly=True) is not None:
                    b = baugruppen.setdefault(e["source"], {"menge": 0, "teile": []})
                    b["menge"] += e.get("menge", 1)
                    b["teile"].append(m.get("name"))

        def andere(r, richtung, art):
            return sum(1 for x in self.db.get_connected(r, direction=richtung, rel_type=art)
                       if x.startswith(MODELL + "/") and x.split("/", 1)[1] not in weg)
        return {
            "knoten": knoten, "kanten": kanten, "dateien": pfade, "bilder": bilder, "warteschlange": schlange,
            # sonst = wie viele ANDERE Modelle noch daran hängen; 0 heisst: nur hier.
            "tags": sorted(({"name": t, "betroffen": len(v), "sonst": andere(ref(TAG, t), "in", HAT_TAG)}
                            for t, v in tags.items()), key=lambda x: (x["sonst"], x["name"])),
            "sammlungen": sorted(({"id": r.split("/", 1)[1], "name": self.db.get_node(r, readonly=True)["name"],
                                   "betroffen": len(v), "sonst": andere(r, "in", IN_SAMMLUNG)}
                                  for r, v in sammlungen.items() if self.db.get_node(r, readonly=True)),
                                 key=lambda x: x["name"].lower()),
            "baugruppen": sorted(({"id": r.split("/", 1)[1], "name": self.db.get_node(r, readonly=True)["name"], **v}
                                  for r, v in baugruppen.items()), key=lambda x: x["name"].lower()),
        }

    def _mitloeschen_pruefen(self, modelle, tags=(), sammlungen=()):
        """Nach dem Löschen der Modelle: Tags und Sammlungen, die nur an ihnen
        hingen, auf Wunsch mit in den Papierkorb. Was noch an einem anderen
        Modell hängt, bleibt — das prüft der Server, nicht die Oberfläche."""
        v = self.loeschvorschau_viele(modelle)
        nur_hier_t = {t["name"] for t in v["tags"] if t["sonst"] == 0}
        nur_hier_s = {x["id"] for x in v["sammlungen"] if x["sonst"] == 0}
        falsch = [t for t in tags if t not in nur_hier_t] + [x for x in sammlungen if x not in nur_hier_s]
        if falsch:
            raise KatalogFehler(f"Hängt noch an anderen Modellen: {', '.join(falsch)}")
        return set(tags), set(sammlungen)

    def loeschen_mit(self, modelle, tags=(), sammlungen=(), melden=None):
        """Modelle löschen und danach, was nur an ihnen hing. Geprüft wird
        vorher; gelöscht wird erst, wenn alles passt."""
        tags, sammlungen = self._mitloeschen_pruefen(modelle, tags, sammlungen)
        if len(modelle) > 1 or tags or sammlungen:
            self._sichern_vor("entfernen")      # ein einzelnes Modell holt der Papierkorb zurück; mehrere und Mitgelöschtes die Sicherung
        # Nur Graph-Änderungen, die Dateien bleiben (siehe loeschen).
        fehler = self._gruppenweise(modelle, self.loeschen, melden)
        if tags or sammlungen:
            with self.db.transaction():
                for t in tags:
                    self.db.soft_delete(TAG, t)
                for sid in sammlungen:
                    self.db.soft_delete(SAMMLUNG, sid)
        return fehler

    def loeschen(self, mid):
        """Das Modell aus dem Katalog nehmen: Modell samt Datei-Knoten in den Papierkorb von flatgraph. **Die Dateien auf der Platte
        bleiben, wo sie sind** — partAtlas löscht und verschiebt dabei nichts. Gemerkt wird, wo sie lagen (samt Grösse und Zeit), damit
        der Scan sie weiter kennt und nicht bei jedem Lauf neu liest, und damit „Wiederherstellen“ sie wiederfindet."""
        h = self.datei_von(mid)
        d = self.db.get_node(ref(DATEI, h)) if h else None
        gemerkt = [{"wurzel": o["wurzel"], "pfad": o["pfad"], "groesse": o.get("groesse"), "mtime": o.get("mtime")}
                   for o in (d or {}).get("orte", [])]
        with self.db.transaction():
            if d is not None:
                self.db.update_node(DATEI, h, {"orte": [], "papierkorb": gemerkt, "geloescht": jetzt()})
            self.db.soft_delete(MODELL, mid)

    def wiederherstellen(self, mid):
        if self.db.get_node(ref(MODELL, mid), readonly=True) is not None:
            return
        h = self._datei_im_papierkorb(mid)
        d = self.db.get_node_raw(ref(DATEI, h)) if h else None
        for a in (d or {}).get("papierkorb", []):
            if self.wurzel_pfad(a["wurzel"]) is None:
                # Der Ordner ist entfernt: ohne ihn hat das Modell keinen Ort, und eine Datei aus einer früheren Fassung bliebe im Papierkorb von
                # partAtlas liegen. Erst den Ordner zurückholen, dann geht beides.
                w = self.db.get_node_raw(ref(WURZEL, a["wurzel"])) or {}
                raise KatalogFehler(f"Der Ordner {w.get('pfad') or a['wurzel']} ist nicht mehr eingetragen. Hole ihn zuerst unter "
                                    f"Bereinigen › Papierkorb mit „Wieder hinzufügen“ zurück; dann lässt sich das Modell wiederherstellen.")
        orte, erledigt = [], []
        try:
            for a in (d or {}).get("papierkorb", []):
                wpfad = self.wurzel_pfad(a["wurzel"])
                if "ablage" not in a:
                    # Seit 0.30 bleibt die Datei beim Löschen, wo sie ist: ist sie noch da, ist das Modell damit wieder im Katalog;
                    # hat der Anwender sie inzwischen selbst entfernt, gilt es als „Datei fehlt“.
                    pfad = os.path.join(wpfad, *a["pfad"].split("/"))
                    if os.path.isfile(pfad):
                        st = os.stat(pfad)
                        orte.append({"wurzel": a["wurzel"], "pfad": a["pfad"], "groesse": st.st_size, "mtime": st.st_mtime})
                    continue
                # Frühere Fassungen haben die Datei in den Papierkorb von partAtlas verschoben: zurücklegen.
                quelle = self.b.pfad(a["ablage"])
                if not os.path.exists(quelle):
                    continue
                ziel = dateien.freier_name(os.path.join(wpfad, *a["pfad"].split("/")))
                dateien.verschiebe(quelle, ziel)
                erledigt.append((ziel, quelle))
                st = os.stat(ziel)
                orte.append({"wurzel": a["wurzel"], "pfad": os.path.relpath(ziel, wpfad).replace(os.sep, "/"),
                             "groesse": st.st_size, "mtime": st.st_mtime})
        except OSError:
            self._zurueck(erledigt)
            raise
        z = (d or {}).get("zuletzt_ort")
        if not orte and z and self.wurzel_pfad(z["wurzel"]):
            # Gelöscht, während die Datei schon fehlte (etwa nach „Ordner entfernen“): ohne gemerkten Ort. Liegt sie wieder, wo sie zuletzt
            # lag, und ist gleich gross, gilt dieser Ort — sonst käme das Modell auf „Datei fehlt“, bis ein Einlesen es findet.
            pfad = os.path.join(self.wurzel_pfad(z["wurzel"]), *z["pfad"].split("/"))
            if os.path.isfile(pfad) and os.path.getsize(pfad) == z.get("groesse"):
                st = os.stat(pfad)
                orte.append({"wurzel": z["wurzel"], "pfad": z["pfad"], "groesse": st.st_size, "mtime": st.st_mtime})
        with self.db.transaction():
            self.db.restore_node(MODELL, mid)
            if h is not None:
                self.db.update_node(DATEI, h, {"orte": orte, "papierkorb": [], "geloescht": None})

    # ------------------------------------------------------------ Endgültig entfernen

    def _im_papierkorb(self, mid):
        roh = self.db.get_node_raw(ref(MODELL, mid))
        if roh is None or self.db.get_node(ref(MODELL, mid), readonly=True) is not None:
            raise KatalogFehler("Dieses Modell liegt nicht im Papierkorb.")
        return roh

    def endgueltig_vorschau(self, mid):
        """Was ein endgültiges Entfernen bedeutet, ohne etwas zu ändern: vor allem, ob die Datei noch im Ordner liegt — dann kommt sie
        beim nächsten Einlesen als neues Modell zurück, denn partAtlas löscht sie nicht."""
        roh = self._im_papierkorb(mid)
        h = self._datei_im_papierkorb(mid)
        d = (self.db.get_node_raw(ref(DATEI, h)) if h else None) or {}
        im_ordner = []
        for a in d.get("papierkorb") or []:
            wpfad = self.wurzel_pfad(a["wurzel"])
            pfad = os.path.join(wpfad, *a["pfad"].split("/")) if wpfad and "ablage" not in a else None
            if pfad and os.path.isfile(pfad):
                im_ordner.append(pfad)
        return {"name": roh.get("name"), "im_ordner": im_ordner, "bilder": len(roh.get("bilder") or [])}

    def endgueltig_entfernen(self, mid):
        """Ein Modell aus dem Papierkorb endgültig aus dem Katalog nehmen — nur dieses, mit genau dem, was mit ihm in den Papierkorb kam
        (seine Datei im Katalog). Nie „alles leeren“: der Müllsammler von flatgraph räumte auch entfernte Ordner, Baugruppen und Drucke
        ab. Vorher immer eine Sicherung. Keine Datei des Anwenders geht verloren: die Datei im Ordner bleibt, eigene Bilder und Dateien
        aus dem alten Papierkorb von partAtlas kommen nach vault_archive/; nur Abgeleitetes (Vorschauen, Netz) wird gelöscht."""
        roh = self._im_papierkorb(mid)
        h = self._datei_im_papierkorb(mid)
        d = (self.db.get_node_raw(ref(DATEI, h)) if h else None) or {}
        self._sichern_vor("endgueltig-entfernen")
        self.db.purge(MODELL, mid)
        for b in roh.get("bilder") or []:
            self._archivieren(b["datei"])
        for a in d.get("papierkorb") or []:
            if "ablage" in a:
                self._archivieren(a["ablage"])
        if h and self.db.get_node_raw(ref(DATEI, h)) is None:
            for art in VORSCHAU_ARTEN:
                self.b.entfernen(self.b.vorschau_pfad(h, art))
            self._netz_weg(h)

    # ------------------------------------------------------------ Datei fehlt

    def _zuletzt_absolut(self, ort):
        """Wo die Datei zuletzt lag, auch wenn ihr Ordner inzwischen entfernt ist."""
        if not ort:
            return None
        w = self.db.get_node_raw(ref(WURZEL, ort["wurzel"])) or {}
        return os.path.join(w["pfad"], *ort["pfad"].split("/")) if w.get("pfad") else ort["pfad"]

    def ohne_datei(self, mid, an=True):
        """„Ohne Datei behalten“: das Modell bleibt mit allem im Katalog und zählt nicht mehr als Problem. Nur für ein Modell, dessen Datei
        fehlt; kommt sie zurück, verschwindet die Markierung von selbst (`_orte_setzen`)."""
        h = self.datei_von(mid)
        d = self.db.get_node(ref(DATEI, h)) if h else None
        if d is None or d.get("orte"):
            raise KatalogFehler("Die Datei dieses Modells ist da.")
        self.db.update_node(DATEI, h, {"ohne_datei": jetzt() if an else None})

    def fehlende_suchen(self, pfad, grenze=60_000):
        """Liegen fehlende Dateien in diesem Ordner? Erkannt wird nur gleicher Inhalt (Hash) — eine geänderte Fassung nicht, das wäre
        geraten. Kennt partAtlas die Grösse jeder fehlenden Datei, wird nur gehasht, was gleich gross ist. Ändert nichts; verbunden wird
        über den Scan, wenn der Ordner zum Katalog gehört oder hinzugefügt wird."""
        pfad = os.path.abspath(os.path.expanduser(pfad))
        if not os.path.isdir(pfad):
            raise KatalogFehler(f"Kein Ordner: {pfad}")
        fehlend, groessen = {}, set()
        for h, d in self._dateien().items():
            if not d.get("orte"):
                mid = self.modell_von(h)
                if mid and self.db.get_node(ref(MODELL, mid), readonly=True) is not None:
                    fehlend[h] = mid
                    groessen.add((d.get("zuletzt_ort") or {}).get("groesse"))
        alle_groessen_bekannt = None not in groessen
        treffer, gesehen = {}, 0
        for ordner, unter, namen in os.walk(pfad):
            unter[:] = [u for u in unter if not u.startswith((".", "$"))]
            for n in namen:
                gesehen += 1
                voll = os.path.join(ordner, n)
                if not fehlend or os.path.splitext(n)[1].lower() not in formate.FORMATE:
                    continue
                try:
                    if alle_groessen_bekannt and os.path.getsize(voll) not in groessen:
                        continue
                    h = formate.datei_hash(voll)
                except OSError:
                    continue
                if h in fehlend and h not in treffer:
                    treffer[h] = voll
            if gesehen > grenze:
                break
        wurzel = next((wid for wid, w in self.wurzeln().items()
                       if pfad == w["pfad"] or pfad.startswith(w["pfad"] + os.sep)), None)
        return {"pfad": pfad, "wurzel": wurzel, "vollstaendig": gesehen <= grenze,
                "treffer": sorted(({"id": fehlend[h], "name": (self.db.get_node(ref(MODELL, fehlend[h]), readonly=True) or {}).get("name"),
                                    "pfad": p} for h, p in treffer.items()), key=lambda x: (x["name"] or "").lower())}
