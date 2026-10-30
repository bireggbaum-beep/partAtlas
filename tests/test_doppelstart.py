"""Abschusstest 5 (OFFEN.md, 30.10.2026): partAtlas zweimal auf demselben Bestand gestartet (flatgraph VERTRAG §3.2: ein Bestand gehört einem Prozess).
Echte Prozesse (`python -m partatlas`): der zweite darf dem ersten nichts antun, der erste arbeitet weiter, nach dem harten Ende des ersten
(kill -9, die Sperre fällt mit dem Prozess) öffnet ein neuer Start den Bestand mit allen Daten.
Gehört zu „vor einer Fassung“, nicht in jeden Lauf."""
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

import muster
from muster import check


def freier_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def holen(port, pfad, daten=None, warten=0.0):
    """(Status, JSON) oder (None, None), wenn niemand antwortet."""
    req = urllib.request.Request(f"http://127.0.0.1:{port}{pfad}", method="POST" if daten is not None else "GET",
                                 data=json.dumps(daten).encode() if daten is not None else None, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"null")
        except ValueError:
            return e.code, None
    except OSError:
        return None, None


def starten(bestand, port):
    env = {**os.environ, "PARTATLAS_BESTAND": bestand, "PARTATLAS_PORT": str(port), "PYTHONPATH": os.pathsep.join(x for x in (os.environ.get("PYTHONPATH"), muster.sys.path[0]) if x)}
    return subprocess.Popen([sys.executable, "-m", "partatlas"], env=env, cwd=muster.sys.path[0], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def bereit(port, grenze=40):
    ende = time.time() + grenze
    while time.time() < ende:
        if holen(port, "/api/stand")[0] == 200:
            return True
        time.sleep(0.3)
    return False


if __name__ == "__main__":
    muster.zeitgrenze(180)
    tmp = tempfile.mkdtemp()
    sammlung = os.path.join(tmp, "3D-Druck")
    os.makedirs(sammlung)
    bestand = os.path.join(tmp, "bestand")
    for i, n in enumerate(["Halter", "Deckel", "Clip"]):
        muster.stl_binaer(os.path.join(sammlung, n + ".stl"), 10 + i, 20, 30)
    p1, p2, p3 = freier_port(), freier_port(), freier_port()
    a = starten(bestand, p1)
    try:
        check("Der erste Start öffnet den Bestand", bereit(p1))
        holen(p1, "/api/wurzeln", {"pfad": sammlung})
        for _ in range(100):
            if len(holen(p1, "/api/modelle")[1] or []) == 3:
                break
            time.sleep(0.3)
        modelle = holen(p1, "/api/modelle")[1] or []
        check("Ausgangslage: drei Modelle eingelesen", len(modelle) == 3)
        mid = modelle[0]["id"]
        holen(p1, f"/api/modelle/{mid}/tags", {"tag": "vorher"})

        # -- zweiter Start auf demselben Bestand, anderer Port: kommt nicht an die Daten
        b = starten(bestand, p2)
        time.sleep(6)
        st, antwort = holen(p2, "/api/modelle")
        check("Zweiter Start (anderer Port) liefert keine Daten des Bestands", st != 200)
        check("… und sagt, woran es liegt (Bestand von anderem Prozess geöffnet)", "anderen Prozess" in json.dumps(antwort or {}, ensure_ascii=False))
        st, _ = holen(p1, f"/api/modelle/{mid}/tags", {"tag": "nachher"})
        tags = (holen(p1, f"/api/modelle/{mid}")[1] or {}).get("tags") or []
        check("Der erste arbeitet währenddessen weiter und schreibt", st == 200 and {"vorher", "nachher"} <= set(tags))
        b.kill(); b.wait()
        check("Der erste läuft nach dem Ende des zweiten weiter", holen(p1, "/api/stand")[0] == 200)

        # -- zweiter Start auf demselben Port: bricht ab, ohne den ersten zu stören
        c = starten(bestand, p1)
        try:
            c.wait(timeout=30)
            beendet = True
        except subprocess.TimeoutExpired:
            c.kill(); c.wait(); beendet = False
        check("Zweiter Start auf demselben Port beendet sich von selbst", beendet)
        check("… und der erste antwortet weiter", holen(p1, "/api/stand")[0] == 200)

        # -- hartes Ende des ersten: die Sperre fällt mit dem Prozess, ein neuer Start hat alles
        a.send_signal(signal.SIGKILL); a.wait()
        d = starten(bestand, p3)
        try:
            check("Nach kill -9 öffnet ein neuer Start den Bestand (keine hängengebliebene Sperre)", bereit(p3))
            modelle = holen(p3, "/api/modelle")[1] or []
            tags = (holen(p3, f"/api/modelle/{mid}")[1] or {}).get("tags") or []
            check("… mit allen Modellen und beiden Tags", len(modelle) == 3 and {"vorher", "nachher"} <= set(tags))
        finally:
            d.kill(); d.wait()
    finally:
        for p in (a,):
            if p.poll() is None:
                p.kill(); p.wait()
    muster.ende()
