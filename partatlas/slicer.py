"""Slicer-Einstellungen lesen: aus 3MF-Projekten und aus G-Code (KONZEPT §4.1).

Bambu Studio, OrcaSlicer und seine Abkömmlinge (Anycubic Slicer Next) legen in jedes Projekt `Metadata/project_settings.config` — ein
JSON mit der ganzen Konfiguration (Druck, Filament, Drucker; mehrere hundert Werte). In den G-Code schreiben sie dieselbe Konfiguration
als Kommentarblock (`; CONFIG_BLOCK_START` … `; CONFIG_BLOCK_END`, je Zeile `; schlüssel = wert`). PrusaSlicer: `Metadata/Slic3r_PE.config`
im 3MF bzw. `; prusaslicer_config = begin` … `end` am Ende des G-Codes. *Ob Bambu Studio die volle Konfiguration in jeden G-Code schreibt,
ist ungeprüft (KONZEPT §9); die Tests nutzen nachgebaute Dateien, keine echten.*

Nichts davon kommt beim Einlesen in den Graphen: einige hundert Werte je Datei wären bei 9 000 Dateien hunderte MB. Gelesen wird, wenn
jemand den Reiter öffnet (die Datei liegt auf demselben Rechner). Nur ein Druck mit G-Code bewahrt seine Konfiguration als
`PRINT_PROFILE` (drucke.py) — dort gehört sie zum Ergebnis.
"""
import hashlib
import json
import re
import xml.etree.ElementTree as ET
import zipfile

# Kein Teil der Einstellungen, die den Druck bestimmen: Namen, Herkunft, Fassungen, Pfade. Zwei Drucke mit sonst gleichen Werten sollen
# denselben PRINT_PROFILE haben, auch wenn das Profil anders heisst. *Die Liste ist eine Schätzung aus dem Aufbau der Dateien, nicht an
# vielen echten Projekten geprüft.*
NICHT_IM_HASH = re.compile(r"(^|_)(settings_id|inherits|compatible_printers.*|compatible_prints.*|from|version|name|is_custom_defined|"
                           r"different_settings_to_system|post_process|thumbnails.*|upward_compatible_machine|filament_ids|"
                           r"print_compatible_printers|setting_id|default_.*_profile|host_type|print_host.*|printhost_.*)$")

# Was ein Maker zuerst wissen will, gruppiert und in Worten. Je Eintrag mehrere Schlüssel: Orca/Bambu zuerst, dann PrusaSlicer.
WICHTIG = [
    ("Drucker", [
        ("Drucker", ("printer_model", "printer_settings_id")),
        ("Düse", ("nozzle_diameter",), "mm"),
        ("Druckbett", ("curr_bed_type",)),
        ("Profil", ("print_settings_id",)),
        ("Filament", ("filament_settings_id",)),
    ]),
    ("Qualität", [
        ("Schichthöhe", ("layer_height",), "mm"),
        ("Erste Schicht", ("initial_layer_print_height", "first_layer_height"), "mm"),
        ("Wände", ("wall_loops", "perimeters")),
        ("Oben / unten", (("top_shell_layers", "bottom_shell_layers"), ("top_solid_layers", "bottom_solid_layers")), "Schichten"),
        ("Naht", ("seam_position",)),
        ("Bügeln", ("ironing_type", "ironing")),
    ]),
    ("Füllung", [
        ("Dichte", ("sparse_infill_density", "fill_density")),
        ("Muster", ("sparse_infill_pattern", "fill_pattern")),
    ]),
    ("Stützen und Haftung", [
        ("Stützen", ("enable_support", "support_material")),
        ("Art", ("support_type", "support_material_style")),
        ("Überhang ab", ("support_threshold_angle", "support_material_threshold"), "°"),
        ("Brim", ("brim_type", "brim_width")),
    ]),
    ("Temperaturen", [
        ("Düse", ("nozzle_temperature", "temperature"), "°C"),
        ("Düse, erste Schicht", ("nozzle_temperature_initial_layer", "first_layer_temperature"), "°C"),
        ("Bett", ("hot_plate_temp", "textured_plate_temp", "bed_temperature"), "°C"),
        ("Kammer", ("chamber_temperatures", "chamber_temperature"), "°C"),
    ]),
    ("Geschwindigkeit und Kühlung", [
        ("Aussenwand", ("outer_wall_speed", "external_perimeter_speed"), "mm/s"),
        ("Innenwand", ("inner_wall_speed", "perimeter_speed"), "mm/s"),
        ("Füllung", ("sparse_infill_speed", "infill_speed"), "mm/s"),
        ("Lüfter", ("fan_max_speed", "max_fan_speed"), "%"),
    ]),
]

JA_NEIN = {"enable_support", "support_material", "ironing", "enable_prime_tower", "wipe_tower"}
BETTARTEN = {"Cool Plate": "cool_plate_temp", "Engineering Plate": "eng_plate_temp", "High Temp Plate": "hot_plate_temp",
             "Textured PEI Plate": "textured_plate_temp", "Smooth PEI Plate": "hot_plate_temp"}


class SlicerFehler(Exception):
    pass


def _wert(v):
    """Listen mit einem Wert (je Filament, je Extruder) als dieser Wert; gleiche Werte nur einmal."""
    if isinstance(v, list):
        eindeutig = list(dict.fromkeys(str(x) for x in v))
        return eindeutig[0] if len(eindeutig) == 1 else ", ".join(eindeutig)
    return "" if v is None else str(v)


def _ini(text):
    werte = {}
    for zeile in text.splitlines():
        zeile = zeile.strip().lstrip(";").strip()
        if " = " in zeile:
            k, _, v = zeile.partition(" = ")
            werte[k.strip()] = v.strip()
    return werte


def aus_3mf(pfad):
    """{slicer, werte} aus einem 3MF-Projekt oder None, wenn es keine Einstellungen trägt (reine Geometrie)."""
    try:
        with zipfile.ZipFile(pfad) as z:
            namen = {n.lstrip("/"): n for n in z.namelist()}
            slicer = None
            modell = namen.get("3D/3dmodel.model")
            if modell and z.getinfo(modell).file_size < 64 << 20:
                # Nur die Metadaten am Anfang: das Hauptmodell kann gross sein, der Kopf ist es nicht.
                kopf = z.open(modell).read(64 << 10).decode("utf-8", "replace")
                m = re.search(r'name="Application"[^>]*>([^<]+)<', kopf)
                slicer = m.group(1).strip() if m else None
            if "Metadata/project_settings.config" in namen:
                roh = z.read(namen["Metadata/project_settings.config"])
                if len(roh) > 16 << 20:
                    raise SlicerFehler("Einstellungen zu gross")
                werte = json.loads(roh)
                if not isinstance(werte, dict):
                    raise SlicerFehler("Einstellungen haben eine unbekannte Form")
                return {"slicer": slicer or "OrcaSlicer/Bambu Studio", "werte": werte, "objekte": _objekte(z, namen)}
            if "Metadata/Slic3r_PE.config" in namen:
                return {"slicer": slicer or "PrusaSlicer", "werte": _ini(z.read(namen["Metadata/Slic3r_PE.config"]).decode("utf-8", "replace")),
                        "objekte": []}
    except (zipfile.BadZipFile, ValueError, OSError, KeyError) as e:
        raise SlicerFehler(f"Datei nicht lesbar: {e}") from e
    return None


def _objekte(z, namen):
    """Abweichende Einstellungen einzelner Objekte (Metadata/model_settings.config): [{name, werte}] — etwa mehr Wände für ein Teil."""
    n = namen.get("Metadata/model_settings.config")
    if not n:
        return []
    try:
        wurzel = ET.fromstring(z.read(n))
    except ET.ParseError:
        return []
    erg = []
    for o in wurzel.iter("object"):
        werte = {m.get("key"): m.get("value") for m in o.findall("metadata") if m.get("key")}
        name = werte.pop("name", None) or o.get("id")
        werte = {k: v for k, v in werte.items() if k not in ("extruder",)}
        if werte:
            erg.append({"name": name, "werte": werte})
    return erg


def aus_gcode(pfad, grenze=4 << 20):
    """{slicer, werte, kopf} aus einem G-Code: der Konfigurationsblock (Orca/Bambu: CONFIG_BLOCK, Prusa: prusaslicer_config) und die
    Kopfzeilen (Druckzeit, Gewicht). Gelesen werden nur Anfang und Ende (je `grenze`): dort stehen die Blöcke, dazwischen Bahnen."""
    with open(pfad, "rb") as f:
        anfang = f.read(grenze)
        f.seek(0, 2)
        groesse = f.tell()
        ende = b""
        if groesse > grenze:
            f.seek(max(grenze, groesse - grenze))
            ende = f.read()
    text = (anfang + b"\n" + ende).decode("utf-8", "replace")
    werte = {}
    for start, stop in (("; CONFIG_BLOCK_START", "; CONFIG_BLOCK_END"), ("; prusaslicer_config = begin", "; prusaslicer_config = end")):
        i = text.find(start)
        j = text.find(stop, i + 1)
        if i >= 0 and j > i:
            werte = _ini(text[i + len(start):j])
            break
    if not werte:
        # PrusaSlicer ohne Block: die Einstellungen als Kommentare am Ende, „; key = value“.
        werte = {k: v for k, v in _ini(ende.decode("utf-8", "replace")).items() if re.fullmatch(r"[a-z0-9_]+", k)}
    slicer = None
    m = re.search(r"^; generated by (\S+(?: \S+)?)", text, re.M | re.I) or re.search(r"^; (BambuStudio|OrcaSlicer|PrusaSlicer)\S*", text, re.M)
    if m:
        slicer = m.group(1)
    kopf = {}
    for muster, schluessel in ((r"; total filament weight \[g\] : ([\d.]+)", "gewicht_g"),
                               (r"; filament used \[g\] = ([\d.]+)", "gewicht_g"),
                               (r"; model printing time: ([^;\n]+?)(?:;|$)", "zeit"),
                               (r"; estimated printing time \(normal mode\) = (.+)", "zeit"),
                               (r"; total estimated time: (.+)", "zeit"),
                               (r"^;TIME:(\d+)", "sekunden")):         # Cura (und was darauf aufbaut): die Druckzeit in Sekunden im Kopf
        m = re.search(muster, text, re.M)
        if m and schluessel not in kopf:
            kopf[schluessel] = m.group(1).strip()
    if "zeit" in kopf:
        kopf["dauer_s"] = dauer_s(kopf.pop("zeit"))
    if "sekunden" in kopf:
        kopf.setdefault("dauer_s", int(kopf["sekunden"]) or None)
        del kopf["sekunden"]
    if kopf.get("dauer_s") is None:
        kopf.pop("dauer_s", None)
    if "gewicht_g" in kopf:
        kopf["gewicht_g"] = float(kopf["gewicht_g"])
    return {"slicer": slicer, "werte": werte, "kopf": kopf}


def dauer_s(text):
    """„1d 2h 3m 4s“ / „2h 3m“ → Sekunden."""
    teile = {einheit: zahl for zahl, einheit in re.findall(r"(\d+)\s*([dhms])", text)}
    s = sum(int(teile.get(e, 0)) * f for e, f in (("d", 86400), ("h", 3600), ("m", 60), ("s", 1)))
    return s or None


def profil_hash(werte):
    """Gleiche Einstellungen, gleicher Hash (KONZEPT §4.1): sortiert, ohne Namen und Herkunft (NICHT_IM_HASH)."""
    rein = {k: werte[k] for k in sorted(werte) if not NICHT_IM_HASH.search(k)}
    return hashlib.sha256(json.dumps(rein, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def wichtigste(werte):
    """[{gruppe, zeilen: [{name, wert, schluessel}]}] — nur Zeilen, für die die Datei etwas hat."""
    erg = []
    for gruppe, zeilen in WICHTIG:
        aus = []
        for eintrag in zeilen:
            name, schluessel = eintrag[0], eintrag[1]
            einheit = eintrag[2] if len(eintrag) > 2 else ""
            wert, welche = None, None
            for k in schluessel:
                if isinstance(k, tuple):            # zwei Werte als einer: „4 / 3“
                    if all(x in werte for x in k):
                        wert, welche = " / ".join(_wert(werte[x]) for x in k), k[0]
                        break
                elif k in werte and _wert(werte[k]) != "":
                    wert, welche = _wert(werte[k]), k
                    break
            if name == "Bett" and werte.get("curr_bed_type") in BETTARTEN and BETTARTEN[werte["curr_bed_type"]] in werte:
                welche = BETTARTEN[werte["curr_bed_type"]]
                wert = _wert(werte[welche])
            if wert is None:
                continue
            if welche in JA_NEIN:
                wert = {"0": "aus", "1": "an", "false": "aus", "true": "an"}.get(wert.lower(), wert)
            if einheit and wert and not wert.endswith("%") and einheit not in wert:
                wert = f"{wert} {einheit}"
            aus.append({"name": name, "wert": wert, "schluessel": welche})
        if aus:
            erg.append({"gruppe": gruppe, "zeilen": aus})
    return erg


def unterschiede(a, b):
    """Was sich zwischen zwei Konfigurationen unterscheidet: [{schluessel, a, b}] — ohne Namen und Herkunft, sortiert."""
    erg = []
    for k in sorted(set(a) | set(b)):
        if NICHT_IM_HASH.search(k):
            continue
        va, vb = _wert(a.get(k)), _wert(b.get(k))
        if va != vb:
            erg.append({"schluessel": k, "a": va, "b": vb})
    return erg


def alle(werte):
    """Alle Werte als [{schluessel, wert}], sortiert — für die durchsuchbare Liste."""
    return [{"schluessel": k, "wert": _wert(v)} for k, v in sorted(werte.items())]
