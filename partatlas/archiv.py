"""
Archive entpacken — wie im 3MF Katalog: in einen Unterordner neben dem
Archiv, nichts wird überschrieben, Programme und Skripte kommen nie heraus.

Hier gilt eine Positivliste statt einer Sperrliste: ein Archiv aus dem
Netz kann alles enthalten, und „alles ausser .exe“ vergisst immer eine
Endung. Heraus kommen Modelle, G-Code, Bilder und Beschreibungen.

Mit der Standardbibliothek: zip und tar (gz, bz2, xz). 7z und rar
brauchen fremde Pakete — offen (KONZEPT §9).
"""
import os
import posixpath
import tarfile
import zipfile

from . import dateien

ARCHIVE = (".zip", ".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz")
ERLAUBT = {".3mf", ".stl", ".obj", ".step", ".stp", ".fcstd", ".gcode", ".bgcode",
           ".png", ".jpg", ".jpeg", ".webp", ".gif", ".txt", ".md", ".pdf"}
MAX_GESAMT = 2 * 1024**3
MAX_EINTRAEGE = 20_000


class ArchivFehler(Exception):
    pass


def ist_archiv(name):
    n = name.lower()
    return any(n.endswith(e) for e in ARCHIVE)


def stamm(name):
    n = os.path.basename(name)
    for e in sorted(ARCHIVE, key=len, reverse=True):
        if n.lower().endswith(e):
            return n[: -len(e)]
    return n


def _sicherer_pfad(name):
    """Relativer Pfad im Archiv → Teile, oder None, wenn er hinausführt."""
    name = name.replace("\\", "/")
    if name.startswith("/") or (len(name) > 1 and name[1] == ":"):
        return None
    teile = [t for t in posixpath.normpath(name).split("/") if t not in ("", ".")]
    if not teile or any(t == ".." for t in teile):
        return None
    return teile


def _eintraege(pfad):
    """(teile, groesse, lesen) je Datei; Links und Geräte werden übergangen."""
    if zipfile.is_zipfile(pfad):
        z = zipfile.ZipFile(pfad)
        for info in z.infolist():
            if info.is_dir():
                continue
            if info.flag_bits & 0x1:
                raise ArchivFehler("Das Archiv ist passwortgeschützt.")
            # Symlink in einem Zip: Unix-Modus im oberen Teil von external_attr.
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                continue
            yield info.filename, info.file_size, (lambda i=info: z.read(i))
        return
    try:
        t = tarfile.open(pfad)
    except tarfile.TarError as e:
        raise ArchivFehler(f"Kein lesbares Archiv: {e}") from e
    for m in t.getmembers():
        if not m.isfile():
            continue
        yield m.name, m.size, (lambda m=m: t.extractfile(m).read())


def entpacken(pfad, ziel=None):
    """Entpackt nach `ziel` (Vorgabe: Ordner mit dem Namen des Archivs daneben).
    Gibt (zielordner, entpackt, uebersprungen) zurück."""
    if ziel is None:
        ziel = dateien.freier_name(os.path.join(os.path.dirname(pfad), stamm(pfad)))
    liste = list(_eintraege(pfad))
    if len(liste) > MAX_EINTRAEGE:
        raise ArchivFehler(f"Zu viele Einträge ({len(liste)}).")
    if sum(g for _, g, _ in liste) > MAX_GESAMT:
        raise ArchivFehler("Entpackt grösser als 2 GB.")
    entpackt, uebersprungen = [], []
    for name, _, lesen in liste:
        teile = _sicherer_pfad(name)
        if teile is None or os.path.splitext(teile[-1])[1].lower() not in ERLAUBT \
                or any(t.startswith(".") or t == "__MACOSX" for t in teile):
            uebersprungen.append(name)
            continue
        zieldatei = dateien.freier_name(os.path.join(ziel, *teile))
        dateien.neu_anlegen(zieldatei, lesen())
        entpackt.append(zieldatei)
    return ziel, entpackt, uebersprungen
