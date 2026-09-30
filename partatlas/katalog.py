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
import time

from . import archiv, dateien, formate, tags
from .suche import Suchindex
from .bestand import DATEI, HAT_DATEI, HAT_TAG, IN_SAMMLUNG, MODELL, SAMMLUNG, TAG, WURZEL


class KatalogFehler(Exception):
    """Ein Wunsch an den Katalog, der sich nicht erfüllen lässt (Meldung für den Anwender)."""


def jetzt():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def ref(sammlung, kennung):
    return f"{sammlung}/{kennung}"


class Katalog:
    def __init__(self, bestand):
        self.b = bestand
        self.db = bestand.db
        self.suche = Suchindex(self)

    # ------------------------------------------------------------ Wurzeln

    def wurzeln(self):
        return {k: dict(v) for k, v in self.db.list_nodes(WURZEL, readonly=True).items()}

    def wurzel_pfad(self, wid):
        w = self.db.get_node(ref(WURZEL, wid), readonly=True)
        return w["pfad"] if w else None

    def wurzel_hinzufuegen(self, pfad):
        pfad = os.path.abspath(os.path.expanduser(pfad))
        if not os.path.isdir(pfad):
            raise KatalogFehler(f"Kein Ordner: {pfad}")
        bestand = os.path.abspath(self.b.wurzel)
        if pfad == bestand or pfad.startswith(bestand + os.sep) or bestand.startswith(pfad + os.sep):
            # Der eigene Bestand (Papierkorb, Cache) darf nicht Teil einer
            # Sammlung sein und umgekehrt — sonst katalogisiert partAtlas
            # seine eigenen Arbeitsdateien.
            raise KatalogFehler("Der Ordner überschneidet sich mit dem Bestand von partAtlas.")
        for wid, w in self.wurzeln().items():
            vorhanden = w["pfad"]
            if pfad == vorhanden or pfad.startswith(vorhanden + os.sep) or vorhanden.startswith(pfad + os.sep):
                raise KatalogFehler(f"Überschneidet sich mit dem Wurzelordner {vorhanden}.")
        wid = self.db.next_id(WURZEL, "w_", 3)
        self.db.create_node(WURZEL, wid, {"pfad": pfad, "name": os.path.basename(pfad) or pfad,
                                          "angelegt": jetzt()})
        return wid

    def wurzel_entfernen(self, wid):
        """Nur der Eintrag geht; Dateien bleiben, ihre Orte unter dieser Wurzel
        verschwinden. Modelle ohne anderen Ort gelten danach als fehlend."""
        with self.db.transaction():
            for h, d in self._dateien().items():
                orte = [o for o in d.get("orte", []) if o["wurzel"] != wid]
                if len(orte) != len(d.get("orte", [])):
                    self.db.update_node(DATEI, h, {"orte": orte})
            self.db.soft_delete(WURZEL, wid)

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
        if self.db.get_node_raw(ref(DATEI, h)) is not None:
            return "papierkorb"
        return None

    def ort_setzen(self, h, wurzel, pfad, groesse, mtime):
        d = self.db.get_node(ref(DATEI, h))
        orte = [o for o in d.get("orte", []) if (o["wurzel"], o["pfad"]) != (wurzel, pfad)]
        orte.append({"wurzel": wurzel, "pfad": pfad, "groesse": groesse, "mtime": mtime})
        orte.sort(key=lambda o: (o["wurzel"], o["pfad"]))
        self.db.update_node(DATEI, h, {"orte": orte})

    def ort_entfernen(self, h, wurzel, pfad):
        d = self.db.get_node(ref(DATEI, h))
        if d is None:
            return
        orte = [o for o in d.get("orte", []) if (o["wurzel"], o["pfad"]) != (wurzel, pfad)]
        self.db.update_node(DATEI, h, {"orte": orte})

    def neue_datei(self, h, felder, orte, vorschau, fehler=None):
        """Datei, Modell und automatische Tags in einem Zug. Aufrufer hält die Transaktion."""
        name = os.path.splitext(os.path.basename(orte[0]["pfad"]))[0]
        self.db.create_node(DATEI, h, {**felder, "orte": orte, "vorschau": vorschau,
                                       "fehler": fehler, "eingelesen": jetzt()})
        mid = self.db.next_id(MODELL, "m_", 6)
        self.db.create_node(MODELL, mid, {
            "name": name, "favorit": False, "gedruckt": False, "quelle_url": None,
            "angelegt": jetzt(), "zuletzt_angesehen": None,
        })
        # cascade_delete: wer das Modell löscht, legt seine Datei mit in den
        # Papierkorb (VERTRAG §2.4) — und loeschfolgen() zeigt das vorher an.
        self.db.create_edge(ref(MODELL, mid), ref(DATEI, h), HAT_DATEI, cascade_delete=True)
        for t in tags.vorschlaege(name, felder):
            self._tag_verbinden(mid, t)
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
            self.db.update_node(DATEI, h, {"vorschau": status})

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
        materialien = sorted({f["typ"].upper() for p in platten for f in p.get("filamente", []) if f.get("typ")})
        material = next((f["typ"] for p in platten for f in p.get("filamente", []) if f.get("typ")), None)
        orte = d.get("orte", [])
        return {
            "id": mid, "name": m.get("name"), "format": d.get("format"),
            "masse": d.get("masse_mm"), "gewicht_g": round(gewicht, 2) if gewicht else None,
            "material": material, "materialien": materialien, "gedruckt": m.get("gedruckt", False),
            "favorit": m.get("favorit", False), "hash": h,
            "vorschau": d.get("vorschau"), "fehlt": not orte and not papierkorb,
            "duplikat": len(orte) > 1, "fehler": bool(d.get("fehler")),
            "ordner": [f'{o["wurzel"]}/{o["pfad"].rsplit("/", 1)[0] if "/" in o["pfad"] else ""}' for o in orte],
            "tags": self.tags_von(mid) if not papierkorb else [],
            "angelegt": m.get("angelegt"), "warteschlange": m.get("warteschlange"),
            # Kurzer Hash des eigenen Bilds: ändert sich mit dem Bild und macht
            # die Adresse im Browser-Cache eindeutig.
            "bild": (m.get("bild") or "")[-16:-4] or None,
            "groesse": sum(o.get("groesse") or 0 for o in orte[:1]) or None,
        }

    def _datei_im_papierkorb(self, mid):
        # Kanten eines gelöschten Knotens liefert get_connected nur mit include_deleted.
        teile = self.db.get_connected(ref(MODELL, mid), rel_type=HAT_DATEI, include_deleted=True)
        return teile[0].split("/", 1)[1] if teile else None

    def modelle(self, suche=None, tag=None, ordner=None, fmt=None, ansicht="alle", sammlung=None,
                tags=(), materialien=(), leiste=False):
        """Wie `_modelle`, dazu die Chips der Leiste: Tags und Materialien je
        mit ODER. Wer mehr gewählte Chips trifft, steht weiter oben; bei
        Gleichstand bleibt die Reihenfolge davor (Relevanz, Name …).

        Mit `leiste` kommt je Chip die Anzahl dazu — gezählt vor der
        Chip-Auswahl, damit man sieht, was ein weiterer Chip brächte."""
        basis = self._modelle(suche, tag, ordner, fmt, ansicht, sammlung)
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
        ordnen = lambda z: [{"name": k, "anzahl": v} for k, v in sorted(z.items(), key=lambda kv: (-kv[1], kv[0]))]
        return {"modelle": liste, "leiste": {"tags": ordnen(zaehl_t), "materialien": ordnen(zaehl_m)}}

    def _modelle(self, suche=None, tag=None, ordner=None, fmt=None, ansicht="alle", sammlung=None):
        """Kacheln für das Raster, gefiltert. Suche über den Wortindex (suche.py),
        Tag über die Nachbarschaft in flatgraph, der Rest über die Kacheln selbst."""
        if ansicht == "papierkorb":
            roh = self.db.list_nodes(MODELL, include_deleted=True, readonly=True)
            liste = [self._kurz(k, v, papierkorb=True) for k, v in roh.items()
                     if self.db.get_node(ref(MODELL, k), readonly=True) is None]
            return sorted(liste, key=lambda x: (x["name"] or "").lower())
        kandidaten = self.db.list_nodes(MODELL, readonly=True)
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
        liste = [self._kurz(k, v) for k, v in kandidaten.items()]
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
            liste = [x for x in liste if x["fehlt"]]
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
            "platten": d.get("platten") or [], "fehler_text": d.get("fehler"),
            "quelle_url": m.get("quelle_url"), "eingelesen": d.get("eingelesen"),
            "papierkorb_ablage": d.get("papierkorb", []),
            "sammlungen": [] if papierkorb else self.sammlungen_von(mid),
        }

    def modell_aendern(self, mid, werte):
        erlaubt = {"favorit": bool, "gedruckt": bool, "quelle_url": (str, type(None))}
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
        if neu.get("gedruckt"):
            # Wie im 3MF Katalog: gedruckt heisst erledigt, raus aus der Warteschlange.
            neu["warteschlange"] = None
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
        if os.path.lexists(ziel):
            raise KatalogFehler("Den Ordner gibt es schon.")
        os.makedirs(ziel)
        return f"{eltern_id.rstrip('/')}/{name}"

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

    # ------------------------------------------------------------ Eigenes Bild
    #
    # Ein hochgeladenes Bild ist Anwenderdaten, nicht abgeleitet: es gehört in
    # den Vault (gesichert), nicht in den Cache. Pillow liest und schreibt es
    # neu als PNG — so kommt nur ein Bild an, keine Metadaten, kein Anhängsel.

    MAX_BILD = 5 * 1024**2

    def bild_setzen(self, mid, daten):
        from PIL import Image, UnidentifiedImageError
        m = self.db.get_node(ref(MODELL, mid), readonly=True)
        if m is None:
            raise KatalogFehler(f"Modell {mid} gibt es nicht.")
        if len(daten) > self.MAX_BILD:
            raise KatalogFehler("Bild grösser als 5 MB.")
        try:
            bild = Image.open(io.BytesIO(daten))
            if bild.format not in ("PNG", "JPEG", "WEBP"):
                raise KatalogFehler("Nur PNG, JPG oder WebP.")
            bild.load()
        except (UnidentifiedImageError, OSError) as e:
            raise KatalogFehler("Kein lesbares Bild.") from e
        bild = bild.convert("RGBA")
        bild.thumbnail((1024, 1024))
        puffer = io.BytesIO()
        bild.save(puffer, "PNG", optimize=True)
        png = puffer.getvalue()
        titel = re.sub(r"[^\w.-]+", "_", m.get("name") or mid)[:60]
        rel = f"vault/bilder/{titel}__{hashlib.sha256(png).hexdigest()[:12]}.png"
        ziel = self.b.pfad(*rel.split("/"))
        if not os.path.exists(ziel):
            dateien.schreibe_atomar(ziel, png)
        self.db.update_node(MODELL, mid, {"bild": rel})

    def bild_entfernen(self, mid):
        # Die Datei bleibt im Vault — er wächst nur (KONZEPT §3.2).
        self.db.update_node(MODELL, mid, {"bild": None})

    def bild_pfad(self, mid):
        m = self.db.get_node(ref(MODELL, mid), readonly=True) or self.db.get_node_raw(ref(MODELL, mid))
        return self.b.pfad(*m["bild"].split("/")) if m and m.get("bild") else None

    # ------------------------------------------------------------ Hochladen und Archive

    def hochladen(self, ordner_id, name, daten):
        """Eine Datei aus dem Browser in einen Ordner legen, nie überschreiben.
        Ein Archiv wird gleich entpackt. Gibt die neuen Pfade zurück."""
        name = os.path.basename((name or "").replace("\\", "/"))
        if not name or name.startswith("."):
            raise KatalogFehler("Ungültiger Dateiname.")
        if formate.format_von(name) is None and not archiv.ist_archiv(name):
            raise KatalogFehler(f"„{name}“ ist weder Modell noch Archiv.")
        _, _, zielordner = self._ordner_pfad(ordner_id)
        ziel = dateien.freier_name(os.path.join(zielordner, name))
        dateien.neu_anlegen(ziel, daten)
        if archiv.ist_archiv(name):
            try:
                _, neu, _ = archiv.entpacken(ziel)
            finally:
                os.unlink(ziel)          # hochgeladen, um entpackt zu werden
            return neu
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

    def archiv_entpacken(self, archiv_id, original_loeschen=False):
        wid, wpfad, pfad = self._ordner_pfad(archiv_id)
        if not os.path.isfile(pfad) or not archiv.ist_archiv(pfad):
            raise KatalogFehler("Kein Archiv.")
        try:
            ziel, neu, weg = archiv.entpacken(pfad)
        except archiv.ArchivFehler as e:
            raise KatalogFehler(str(e)) from e
        if original_loeschen:
            # Nicht löschen, sondern in den Papierkorb von partAtlas.
            dateien.verschiebe(pfad, dateien.freier_name(self.b.pfad("papierkorb", os.path.basename(pfad))))
        return {"ordner": os.path.relpath(ziel, wpfad), "entpackt": len(neu), "uebersprungen": weg}

    # ------------------------------------------------------------ Mehrere auf einmal

    def stapel(self, aktion, modelle, wert=None):
        """Eine Aktion für viele Modelle; reine Graph-Änderungen in einer
        Transaktion, Dateiaktionen einzeln (jede für sich rückgängig)."""
        fehler = []
        if aktion in ("favorit", "gedruckt", "tag", "sammlung", "warteschlange", "aus_warteschlange"):
            with self.db.transaction():
                for mid in modelle:
                    if aktion in ("favorit", "gedruckt"):
                        self.modell_aendern(mid, {aktion: bool(wert)})
                    elif aktion == "tag":
                        self._tag_verbinden(mid, wert)
                    elif aktion == "warteschlange":
                        self.in_warteschlange(mid)
                    elif aktion == "aus_warteschlange":
                        self.aus_warteschlange(mid)
                if aktion == "sammlung":
                    self._sammlung_pruefen(wert)
                    self._hinzufuegen(wert, modelle)
        elif aktion in ("loeschen", "verschieben"):
            for mid in modelle:
                try:
                    self.loeschen(mid) if aktion == "loeschen" else self.verschieben(mid, wert)
                except (KatalogFehler, OSError) as e:
                    fehler.append({"id": mid, "fehler": str(e)})
        else:
            raise KatalogFehler(f"Unbekannte Aktion {aktion!r}.")
        return {"fehler": fehler}

    def loeschvorschau_viele(self, modelle):
        ergebnis = {"knoten": [], "kanten": {}, "dateien": []}
        for mid in modelle:
            v = self.loeschvorschau(mid)
            ergebnis["knoten"] += v["knoten"]
            ergebnis["dateien"] += v["dateien"]
            for k, n in v["kanten"].items():
                ergebnis["kanten"][k] = ergebnis["kanten"].get(k, 0) + n
        return ergebnis

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
        """Was mit dem Modell verschwindet — ohne etwas zu ändern (VERTRAG §2.4)."""
        folgen = self.db.loeschfolgen(ref(MODELL, mid))
        h = self.datei_von(mid)
        d = self.db.get_node(ref(DATEI, h), readonly=True) if h else None
        kanten = {}
        for kid in folgen["kanten"]:
            e = self.db.get_edge(kid)
            if e:
                kanten[e["type"]] = kanten.get(e["type"], 0) + 1
        return {
            "knoten": folgen["knoten"],
            "kanten": kanten,
            "dateien": [self.absoluter_pfad(o) for o in (d or {}).get("orte", [])],
        }

    def loeschen(self, mid):
        """Dateien in den Papierkorb von partAtlas, Modell samt Datei-Knoten in
        den Papierkorb von flatgraph. Erst die Dateien: scheitert eine,
        werden die schon verschobenen zurückgelegt und nichts ist passiert."""
        h = self.datei_von(mid)
        d = self.db.get_node(ref(DATEI, h)) if h else None
        ablage, erledigt = [], []
        try:
            for o in (d or {}).get("orte", []):
                quelle = self.absoluter_pfad(o)
                if not quelle or not os.path.exists(quelle):
                    continue
                ziel = dateien.freier_name(self.b.pfad("papierkorb", f"{h[:12]}__{os.path.basename(quelle)}"))
                dateien.verschiebe(quelle, ziel)
                erledigt.append((ziel, quelle))
                ablage.append({"wurzel": o["wurzel"], "pfad": o["pfad"],
                               "ablage": os.path.relpath(ziel, self.b.wurzel)})
        except OSError:
            self._zurueck(erledigt)
            raise
        with self.db.transaction():
            if d is not None:
                self.db.update_node(DATEI, h, {"orte": [], "papierkorb": ablage,
                                               "geloescht": jetzt()})
            self.db.soft_delete(MODELL, mid)

    def wiederherstellen(self, mid):
        if self.db.get_node(ref(MODELL, mid), readonly=True) is not None:
            return
        h = self._datei_im_papierkorb(mid)
        d = self.db.get_node_raw(ref(DATEI, h)) if h else None
        orte, erledigt = [], []
        try:
            for a in (d or {}).get("papierkorb", []):
                quelle = self.b.pfad(a["ablage"])
                wpfad = self.wurzel_pfad(a["wurzel"])
                if wpfad is None or not os.path.exists(quelle):
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
        with self.db.transaction():
            self.db.restore_node(MODELL, mid)
            if h is not None:
                self.db.update_node(DATEI, h, {"orte": orte, "papierkorb": [], "geloescht": None})

    def papierkorb_leeren(self):
        """Endgültig: Dateien im Papierkorb löschen, dann der Müllsammler."""
        weg = []
        for mid in [x["id"] for x in self.modelle(ansicht="papierkorb")]:
            h = self._datei_im_papierkorb(mid)
            d = self.db.get_node_raw(ref(DATEI, h)) if h else None
            for a in (d or {}).get("papierkorb", []):
                try:
                    os.unlink(self.b.pfad(a["ablage"]))
                except FileNotFoundError:
                    pass
            if h:
                weg.append(h)
        self.db.run_garbage_collection()
        for h in weg:
            try:
                os.unlink(self.b.vorschau_pfad(h))
            except FileNotFoundError:
                pass
        return len(weg)
