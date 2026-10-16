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
        if os.path.lexists(ziel):
            os.unlink(arbeit)
            raise ZielBelegt(ziel)
        os.replace(arbeit, ziel)
    else:
        os.unlink(arbeit)
    _verzeichnis_sichern(ordner)


def neu_anlegen(ziel, daten):
    """Neue Datei mit Inhalt; scheitert, wenn am Ziel schon etwas liegt.
    Arbeitsdatei, fsync, dann `link` — der scheitert statt zu überschreiben."""
    ordner = os.path.dirname(os.path.abspath(ziel))
    os.makedirs(ordner, exist_ok=True)
    arbeit = os.path.join(ordner, f".{os.path.basename(ziel)}.{os.getpid()}.arbeit")
    try:
        with open(arbeit, "wb") as f:
            f.write(daten)
            f.flush()
            os.fsync(f.fileno())
        try:
            os.link(arbeit, ziel)
        except FileExistsError as e:
            raise ZielBelegt(ziel) from e
        except OSError:
            # Dateisystem ohne harte Links: letzte Prüfung, dann umbenennen.
            if os.path.lexists(ziel):
                raise ZielBelegt(ziel)
            os.replace(arbeit, ziel)
    finally:
        try:
            os.unlink(arbeit)
        except FileNotFoundError:
            pass
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


# Die Regeln von Windows gelten überall: so bleiben die Ordner zwischen Windows und Linux tragbar, und ein Name, den der Explorer
# ablehnt, lehnt auch partAtlas ab — mit demselben Sinn im Satz.
_VERBOTEN = set('\\/:*?"<>|')
_RESERVIERT = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


def ordnername_pruefen(name, art="Ordnername"):
    """Der bereinigte Name (Leerzeichen aussen weg, wie im Explorer) oder ValueError mit einem Satz für den Anwender. `art`: „Ordnername“
    oder „Dateiname“ (ohne Endung), für den Satz."""
    name = (name or "").strip()
    if not name:
        raise ValueError("Der Name darf nicht leer sein.")
    if any(c in _VERBOTEN or ord(c) < 32 for c in name):
        raise ValueError(f'Ein {art} darf keines dieser Zeichen enthalten: \\ / : * ? " < > |')
    if name.startswith("."):
        raise ValueError(f"Ein Name mit einem Punkt vorn wäre {'ein versteckter Ordner' if art == 'Ordnername' else 'eine versteckte Datei'} "
                         f"— partAtlas zeigt solche nicht.")
    if name.endswith("."):
        raise ValueError(f"Ein {art} darf nicht mit einem Punkt enden.")
    if name.split(".")[0].strip().upper() in _RESERVIERT:
        raise ValueError(f"„{name}“ ist unter Windows als Name reserviert.")
    if len(name) > 255:
        raise ValueError("Der Name ist zu lang (höchstens 255 Zeichen).")
    return name


def ordner_umbenennen(quelle, ziel):
    """Ein Verzeichnis in einem Schritt umbenennen oder verschieben (dasselbe Dateisystem), ohne je etwas zu ersetzen.

    `os.rename` ersetzt unter Linux ein leeres Zielverzeichnis still; darum reserviert `mkdir` das Ziel erst (scheitert, wenn es
    da ist) und `rename` ersetzt dann nur diesen eigenen, leeren Platzhalter. Unter Windows scheitert `rename` an einem vorhandenen
    Ziel von selbst. Nur andere Schreibung (`halter` → `Halter`) auf einem Dateisystem, das sie nicht unterscheidet: über einen
    Zwischennamen daneben."""
    if os.path.lexists(ziel) and os.path.samefile(quelle, ziel):
        zwischen = os.path.join(os.path.dirname(quelle), f".{os.path.basename(ziel)}.partatlas-umbenennen")
        os.rename(quelle, zwischen)
        try:
            os.rename(zwischen, ziel)
        except OSError:
            os.rename(zwischen, quelle)
            raise
    elif os.name == "nt":
        os.rename(quelle, ziel)
    else:
        try:
            os.mkdir(ziel)
        except FileExistsError:
            raise ZielBelegt(ziel)
        try:
            os.rename(quelle, ziel)
        except OSError:
            os.rmdir(ziel)
            raise
    _verzeichnis_sichern(os.path.dirname(os.path.abspath(ziel)))
    _verzeichnis_sichern(os.path.dirname(os.path.abspath(quelle)))
