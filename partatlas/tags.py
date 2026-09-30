"""
Automatische Tags beim Einlesen — dieselben Regeln wie im 3MF Katalog
(`src-tauri/src/tagging.rs`), damit der Anwender dieselben Chips sieht:
bis zu vier Wörter aus dem Dateinamen, dazu Geometrie und Material.
"""
import re
import unicodedata

MIN_LAENGE = 3
MAX_AUS_NAME = 4
MINIATUR_MM = 30.0
GROSS_MM = 200.0
STOPPWOERTER = {
    "kopie", "copy", "neu", "new", "final", "fertig", "export", "test", "scan", "model", "modell",
    "copia", "nuevo", "nueva", "modelo", "prueba", "copie", "nouveau", "nouvelle", "modèle", "essai",
    "untitled", "sans", "titre", "stl", "3mf", "obj", "step", "stp",
}


def normalisiere(name):
    name = unicodedata.normalize("NFC", (name or "").strip().lstrip("#").lower())
    return re.sub(r"\s+", " ", name)[:60]


def _aus_name(name):
    tokens = [t.lower() for t in re.split(r"[^\w]+|_", name) if t]
    gut = [t for t in tokens
           if len(t) >= MIN_LAENGE and not t.isdigit()
           and not re.fullmatch(r"v\d+", t) and t not in STOPPWOERTER]
    ergebnis = []
    for t in gut:
        if t not in ergebnis:
            ergebnis.append(t)
    return ergebnis[:MAX_AUS_NAME]


def vorschlaege(name, felder):
    tags = _aus_name(name)
    if (felder.get("objekte") or 1) > 1:
        tags.append("mehrteilig")
    masse = felder.get("masse_mm")
    if masse:
        groesste = max(masse)
        if groesste <= MINIATUR_MM:
            tags.append("miniatur")
        elif groesste >= GROSS_MM:
            tags.append("grossformat")
    filamente = [f for p in felder.get("platten") or [] for f in p.get("filamente", [])]
    for f in filamente:
        if f.get("typ"):
            tags.append(f["typ"].lower())
    if len({(f.get("farbe") or "").lower() for f in filamente}) > 1:
        tags.append("mehrfarbig")
    return list(dict.fromkeys(normalisiere(t) for t in tags if normalisiere(t)))
