"""
Schreibwege auf Dateien — die einzigen in partAtlas.

Harte Regel aus flatgraph und pDMS: jede Datei über eine Arbeitsdatei
daneben, `fsync`, `os.replace`; nichts wird an Ort und Stelle verändert.
In den Ordnern des Anwenders gilt zusätzlich: **nie etwas überschreiben**
(KONZEPT §3.1). Wer eine Datei verschiebt, darf am Ziel nichts vorfinden.
"""
import os
import shutil


class ZielBelegt(FileExistsError):
    """Am Ziel liegt schon eine Datei; partAtlas überschreibt nichts."""


def _verzeichnis_sichern(pfad):
    # Unter Windows lässt sich ein Verzeichnis nicht öffnen; dort bleibt es
    # beim fsync der Datei (wie flatgraph, VERTRAG §2.2).
    try:
        fd = os.open(pfad, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def schreibe_atomar(ziel, daten):
    """Ganze Datei ersetzen: Arbeitsdatei daneben, fsync, os.replace."""
    ordner = os.path.dirname(os.path.abspath(ziel))
    os.makedirs(ordner, exist_ok=True)
    arbeit = os.path.join(ordner, f".{os.path.basename(ziel)}.{os.getpid()}.arbeit")
    try:
        with open(arbeit, "wb") as f:
            f.write(daten)
            f.flush()
            os.fsync(f.fileno())
        os.replace(arbeit, ziel)
    except BaseException:
        try:
            os.unlink(arbeit)
        except FileNotFoundError:
            pass
        raise
    _verzeichnis_sichern(ordner)


def verschiebe(quelle, ziel):
    """Datei verschieben, ohne je etwas zu überschreiben.

    Auf demselben Dateisystem ist das ein `link` + `unlink`: `link` scheitert,
    wenn das Ziel existiert — anders als `rename`, das unter Linux still
    überschreibt. Über Dateisystemgrenzen: kopieren, fsync, erst dann die
    Quelle entfernen. Ein Absturz dazwischen hinterlässt schlimmstenfalls
    zwei Kopien, nie keine.
    """
    if os.path.lexists(ziel):
        raise ZielBelegt(ziel)
    os.makedirs(os.path.dirname(os.path.abspath(ziel)), exist_ok=True)
    try:
        os.link(quelle, ziel)
    except FileExistsError:
        raise ZielBelegt(ziel)
    except OSError:
        # Andere Platte oder ein Dateisystem ohne harte Links (FAT, manche
        # Freigaben): kopieren.
        _kopiere_ohne_ueberschreiben(quelle, ziel)
    else:
        _verzeichnis_sichern(os.path.dirname(os.path.abspath(ziel)))
    os.unlink(quelle)
    _verzeichnis_sichern(os.path.dirname(os.path.abspath(quelle)))


def _kopiere_ohne_ueberschreiben(quelle, ziel):
    ordner = os.path.dirname(os.path.abspath(ziel))
    arbeit = os.path.join(ordner, f".{os.path.basename(ziel)}.{os.getpid()}.arbeit")
    with open(quelle, "rb") as q, open(arbeit, "wb") as z:
        shutil.copyfileobj(q, z, 1 << 20)
        z.flush()
        os.fsync(z.fileno())
    shutil.copystat(quelle, arbeit)
    try:
        os.link(arbeit, ziel)          # scheitert, wenn inzwischen jemand dort ist
    except OSError as e:
        if os.path.lexists(ziel):
            os.unlink(arbeit)
            raise ZielBelegt(ziel) from e
        # Kein link möglich (FAT): exklusiv anlegen geht nicht atomar mit
        # Inhalt; letzte Prüfung, dann umbenennen.
        os.replace(arbeit, ziel)
    else:
        os.unlink(arbeit)
    _verzeichnis_sichern(ordner)


def freier_name(ziel):
    """`name.ext`, sonst `name (2).ext`, `name (3).ext` … — wie ein Dateimanager."""
    if not os.path.lexists(ziel):
        return ziel
    stamm, ext = os.path.splitext(ziel)
    n = 2
    while os.path.lexists(f"{stamm} ({n}){ext}"):
        n += 1
    return f"{stamm} ({n}){ext}"
