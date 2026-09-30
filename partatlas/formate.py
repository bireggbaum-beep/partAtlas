"""
Modelldateien lesen: STL, OBJ, 3MF, STEP.

Jeder Leser liefert dasselbe Ergebnis (`Analyse`), damit Scan und
Vorschau nichts über Formate wissen müssen. Ein Leser wirft bei einer
kaputten Datei `FormatFehler`; der Scan überspringt die Datei dann und
merkt sich den Grund (Konzept NFR-04: eine defekte Datei hält den Katalog
nicht an).

Läuft in Arbeitsprozessen des Scans (`scan.py`), deshalb ohne Zugriff auf
den Bestand und ohne globale Zustände.
"""
import hashlib
import io
import os
import posixpath
import re
import struct
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

import numpy as np

FORMATE = {".3mf": "3mf", ".stl": "stl", ".obj": "obj", ".step": "step", ".stp": "step"}

# Obergrenzen gegen Zip-Bomben und absurde Dateien. Ein echtes 3MF mit
# vielen Platten kommt auf einige 100 MB entpackt; mehr als 2 GB ist kein
# Modell mehr, sondern ein Angriff oder ein Fehler.
MAX_ENTPACKT = 2 * 1024**3
MAX_VORSCHAU = 20 * 1024**2


class FormatFehler(Exception):
    """Die Datei lässt sich nicht als Modell lesen."""


@dataclass
class Analyse:
    format: str
    masse_mm: list | None = None          # [x, y, z]
    volumen_cm3: float | None = None
    dreiecke: int | None = None
    objekte: int | None = None
    titel: str | None = None
    designer: str | None = None
    platten: list = field(default_factory=list)   # [{nr, gewicht_g, zeit_s, filamente:[...]}]
    vorschau_png: bytes | None = None
    netz: np.ndarray | None = None        # (n, 3, 3) float32 — nur für die Vorschau

    def als_felder(self):
        """Was in den Graphen gehört: alles ausser Bild und Netz."""
        return {
            "format": self.format, "masse_mm": self.masse_mm,
            "volumen_cm3": self.volumen_cm3, "dreiecke": self.dreiecke,
            "objekte": self.objekte, "titel": self.titel,
            "designer": self.designer, "platten": self.platten,
        }


def format_von(pfad):
    return FORMATE.get(os.path.splitext(pfad)[1].lower())


def datei_hash(pfad, block=1 << 20):
    h = hashlib.sha256()
    with open(pfad, "rb") as f:
        while chunk := f.read(block):
            h.update(chunk)
    return h.hexdigest()


def analysiere(pfad, mit_netz=False):
    fmt = format_von(pfad)
    if fmt is None:
        raise FormatFehler(f"kein Modellformat: {pfad}")
    try:
        a = {"stl": _stl, "obj": _obj, "3mf": _3mf, "step": _step}[fmt](pfad)
    except FormatFehler:
        raise
    except (OSError, ValueError, KeyError, IndexError, struct.error,
            zipfile.BadZipFile, ET.ParseError) as e:
        raise FormatFehler(f"{type(e).__name__}: {e}") from e
    if a.netz is not None:
        _geometrie_ausfuellen(a)
        if not mit_netz:
            a.netz = None
    return a


def _geometrie_ausfuellen(a):
    netz = a.netz
    a.dreiecke = int(len(netz))
    if len(netz) == 0:
        return
    punkte = netz.reshape(-1, 3)
    mini, maxi = punkte.min(axis=0), punkte.max(axis=0)
    a.masse_mm = [round(float(v), 2) for v in (maxi - mini)]
    # Vorzeichenbehaftetes Tetraedervolumen: bei geschlossenem Netz das
    # Volumen, bei offenem ein Näherungswert. Wie im 3MF Katalog.
    n = netz.astype(np.float64)
    vol = np.einsum("ij,ij->i", n[:, 0], np.cross(n[:, 1], n[:, 2])).sum() / 6.0
    a.volumen_cm3 = round(abs(float(vol)) / 1000.0, 3)


# ---------------------------------------------------------------- STL

def _stl(pfad):
    groesse = os.path.getsize(pfad)
    with open(pfad, "rb") as f:
        kopf = f.read(84)
    if len(kopf) >= 84:
        n = struct.unpack("<I", kopf[80:84])[0]
        # Binär erkennt man an der Länge, nicht am Wort „solid“: viele
        # Exporter schreiben „solid“ auch in den Binärkopf.
        if 84 + 50 * n == groesse:
            daten = np.fromfile(pfad, dtype=np.dtype([
                ("normale", "<f4", 3), ("ecken", "<f4", (3, 3)), ("attr", "<u2")]),
                count=n, offset=84)
            return Analyse("stl", netz=np.ascontiguousarray(daten["ecken"]), objekte=1)
    with open(pfad, "rb") as f:
        text = f.read().decode("latin-1")
    if not text.lstrip().lower().startswith("solid"):
        raise FormatFehler("weder binäres noch ASCII-STL")
    zahlen = re.findall(r"vertex\s+(\S+)\s+(\S+)\s+(\S+)", text)
    if len(zahlen) % 3:
        raise FormatFehler("ASCII-STL: Eckenzahl nicht durch 3 teilbar")
    netz = np.array(zahlen, dtype=np.float32).reshape(-1, 3, 3)
    return Analyse("stl", netz=netz, objekte=max(1, text.lower().count("endsolid")))


# ---------------------------------------------------------------- OBJ

def _obj(pfad):
    ecken, flaechen, objekte = [], [], 0
    with open(pfad, "r", encoding="utf-8", errors="replace") as f:
        for zeile in f:
            if zeile.startswith("v "):
                t = zeile.split()
                ecken.append((float(t[1]), float(t[2]), float(t[3])))
            elif zeile.startswith("f "):
                idx = []
                for teil in zeile.split()[1:]:
                    i = int(teil.split("/")[0])
                    idx.append(i - 1 if i > 0 else len(ecken) + i)
                # Vielecke als Fächer zerlegen.
                for k in range(1, len(idx) - 1):
                    flaechen.append((idx[0], idx[k], idx[k + 1]))
            elif zeile.startswith(("o ", "g ")):
                objekte += 1
    if not flaechen:
        raise FormatFehler("OBJ ohne Flächen")
    v = np.array(ecken, dtype=np.float32)
    return Analyse("obj", netz=v[np.array(flaechen)], objekte=max(1, objekte))


# ---------------------------------------------------------------- STEP

def _step(pfad):
    # Ohne Open CASCADE keine Geometrie. Der Katalog nimmt die Datei trotzdem
    # auf; Titel aus dem Kopf, wenn vorhanden (Konzept §9: offen).
    with open(pfad, "rb") as f:
        kopf = f.read(4096).decode("latin-1")
    if "ISO-10303-21" not in kopf:
        raise FormatFehler("kein STEP (ISO-10303-21 fehlt)")
    m = re.search(r"FILE_NAME\s*\(\s*'([^']*)'", kopf)
    return Analyse("step", titel=(m.group(1) or None) if m else None)


# ---------------------------------------------------------------- 3MF

NS_CORE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
NS_PROD = "http://schemas.microsoft.com/3dmanufacturing/production/2015/06"
REL_MODELL = "http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"
REL_VORSCHAU = "http://schemas.openxmlformats.org/package/2006/relationships/metadata/thumbnail"
# Bambu Studio und OrcaSlicer legen das Plattenbild unter plate_1.png ab;
# der 3MF Katalog kennt nur die ersten beiden und zeigt dann nichts.
VORSCHAU_ERSATZ = ["Metadata/thumbnail.png", "3D/Thumbnails/thumbnail.png",
                   "Metadata/plate_1.png", "Metadata/top_1.png"]


class _Zip:
    """Zip-Zugriff mit Budget gegen Zip-Bomben."""

    def __init__(self, pfad):
        self.z = zipfile.ZipFile(pfad)
        self.namen = {n.lstrip("/"): n for n in self.z.namelist()}
        self.verbraucht = 0

    def lies(self, name, grenze=MAX_ENTPACKT):
        echt = self.namen.get(name.lstrip("/"))
        if echt is None:
            return None
        info = self.z.getinfo(echt)
        if info.file_size > grenze or self.verbraucht + info.file_size > MAX_ENTPACKT:
            raise FormatFehler(f"{name}: entpackt zu gross ({info.file_size} Bytes)")
        daten = self.z.read(echt)
        self.verbraucht += len(daten)
        return daten


def _matrix(text):
    if not text:
        return None
    w = [float(x) for x in text.split()]
    if len(w) != 12:
        raise FormatFehler(f"Transformation mit {len(w)} statt 12 Werten")
    m = np.eye(4)
    m[:3, :3] = np.array(w[:9]).reshape(3, 3)
    m[3, :3] = w[9:]
    return m


def _anwenden(netz, m):
    if m is None:
        return netz
    p = netz.reshape(-1, 3).astype(np.float64) @ m[:3, :3] + m[3, :3]
    return p.astype(np.float32).reshape(-1, 3, 3)


def _modell_lesen(xml):
    """{objektid: (netz | None, [(pfad|None, objektid, matrix)])}, build-items, metadaten"""
    wurzel = ET.fromstring(xml)
    objekte, items, meta = {}, [], {}
    for m in wurzel.iter(f"{{{NS_CORE}}}metadata"):
        meta[m.get("name", "")] = (m.text or "").strip()
    for obj in wurzel.iter(f"{{{NS_CORE}}}object"):
        oid = obj.get("id")
        netz = None
        mesh = obj.find(f"{{{NS_CORE}}}mesh")
        if mesh is not None:
            v = np.array([(float(e.get("x")), float(e.get("y")), float(e.get("z")))
                          for e in mesh.iter(f"{{{NS_CORE}}}vertex")], dtype=np.float32)
            t = np.array([(int(e.get("v1")), int(e.get("v2")), int(e.get("v3")))
                          for e in mesh.iter(f"{{{NS_CORE}}}triangle")], dtype=np.int64)
            netz = v[t] if len(t) else np.zeros((0, 3, 3), np.float32)
        teile = [(c.get(f"{{{NS_PROD}}}path"), c.get("objectid"), _matrix(c.get("transform")))
                 for c in obj.iter(f"{{{NS_CORE}}}component")]
        objekte[oid] = (netz, teile)
    build = wurzel.find(f"{{{NS_CORE}}}build")
    if build is not None:
        items = [(i.get(f"{{{NS_PROD}}}path"), i.get("objectid"), _matrix(i.get("transform")))
                 for i in build.iter(f"{{{NS_CORE}}}item")]
    return objekte, items, meta


def _3mf(pfad):
    z = _Zip(pfad)
    modellpfad, vorschaupfad = "3D/3dmodel.model", None
    rels = z.lies("_rels/.rels", 1 << 20)
    if rels:
        for r in ET.fromstring(rels):
            typ, ziel = r.get("Type"), (r.get("Target") or "").lstrip("/")
            if typ == REL_MODELL:
                modellpfad = ziel
            elif typ == REL_VORSCHAU:
                vorschaupfad = ziel
    haupt = z.lies(modellpfad)
    if haupt is None:
        raise FormatFehler(f"3MF ohne Modell ({modellpfad})")

    dateien = {modellpfad: _modell_lesen(haupt)}

    def objekt(datei, oid, tiefe=0):
        if tiefe > 16:
            raise FormatFehler("Komponenten zu tief verschachtelt")
        if datei not in dateien:
            xml = z.lies(datei)
            if xml is None:
                raise FormatFehler(f"Komponente verweist auf fehlende Datei {datei}")
            dateien[datei] = _modell_lesen(xml)
        netz, teile = dateien[datei][0].get(oid, (None, []))
        stuecke = [] if netz is None else [netz]
        for p, sub, m in teile:
            ziel = (p or datei).lstrip("/")
            stuecke.append(_anwenden(objekt(ziel, sub, tiefe + 1), m))
        return np.concatenate(stuecke) if stuecke else np.zeros((0, 3, 3), np.float32)

    _, items, meta = dateien[modellpfad]
    stuecke = [_anwenden(objekt((p or modellpfad).lstrip("/"), oid), m) for p, oid, m in items]
    netz = np.concatenate(stuecke) if stuecke else np.zeros((0, 3, 3), np.float32)

    vorschau = None
    for kandidat in ([vorschaupfad] if vorschaupfad else []) + VORSCHAU_ERSATZ:
        vorschau = z.lies(kandidat, MAX_VORSCHAU)
        if vorschau:
            break

    a = Analyse("3mf", netz=netz, objekte=len(items) or None,
                titel=meta.get("Title") or None, designer=meta.get("Designer") or None,
                vorschau_png=vorschau)
    a.platten = _platten(z)
    return a


def _platten(z):
    """Filament je Platte aus Metadata/slice_info.config (Orca, Bambu)."""
    xml = z.lies("Metadata/slice_info.config", 16 << 20)
    if not xml:
        return []
    platten = []
    for plate in ET.fromstring(xml).iter("plate"):
        werte = {m.get("key"): m.get("value") for m in plate.findall("metadata")}
        filamente = [{
            "typ": f.get("type"), "farbe": f.get("color"),
            "g": _zahl(f.get("used_g")), "m": _zahl(f.get("used_m")),
        } for f in plate.findall("filament")]
        platten.append({
            "nr": int(werte.get("index") or len(platten) + 1),
            "gewicht_g": _zahl(werte.get("weight")),
            "zeit_s": _zahl(werte.get("prediction")),
            "filamente": filamente,
        })
    return platten


def _zahl(text):
    try:
        return round(float(text), 2)
    except (TypeError, ValueError):
        return None
