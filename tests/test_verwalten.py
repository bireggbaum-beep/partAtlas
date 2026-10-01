"""Verschieben, Ordner, Quelle, eigenes Bild, Hochladen, Archive, mehrere
Modelle auf einmal — alles, was in die Ordner des Anwenders schreibt, und
deshalb auch mit Eingaben, die hinaus wollen."""
import io
import os
import stat
import tarfile
import tempfile
import zipfile

import muster
from muster import check
from fastapi.testclient import TestClient
from PIL import Image
from partatlas.main import erstelle_app


def warten(c):
    c.app.state.zustand["scanner"].warten(120)


def ids(c, **filter):
    return {m["name"]: m["id"] for m in c.get("/api/modelle", params=filter).json()}


def stl_bytes(x=7):
    # Jede Datei eigene Masse: gleiche Bytes wären ein Duplikat desselben Modells.
    p = os.path.join(tempfile.mkdtemp(), "x.stl")
    muster.stl_binaer(p, x, 8, 9)
    return open(p, "rb").read()


if __name__ == "__main__":
    tmp = tempfile.mkdtemp()
    samm = os.path.join(tmp, "3D-Druck")
    for o in ("Deko", "Technik", "Leer"):
        os.makedirs(os.path.join(samm, o))
    muster.stl_binaer(os.path.join(samm, "Deko", "Vase.stl"), 10, 10, 30)
    muster.stl_binaer(os.path.join(samm, "Deko", "Stern.stl"), 20, 20, 3)
    muster.stl_binaer(os.path.join(samm, "Technik", "Stern.stl"), 21, 20, 3)
    muster.obj(os.path.join(samm, "Technik", "Welle.obj"))
    muster.dreimf(os.path.join(samm, "Technik", "Doppel.3mf"))
    muster.dreimf(os.path.join(samm, "Deko", "Doppel.3mf"))

    with TestClient(erstelle_app(os.path.join(tmp, "bestand"), prozesse=2)) as c:
        w = c.post("/api/wurzeln", json={"pfad": samm}).json()["id"]
        warten(c)
        m = ids(c)

        # -- Verzeichnisse und Verschieben
        vz = [v["id"] for v in c.get("/api/verzeichnisse").json()]
        check("Verzeichnisse als Ziele, auch leere", f"{w}/Leer" in vz and w in vz)
        r = c.post(f"/api/modelle/{m['Vase']}/verschieben", json={"ordner": f"{w}/Leer"})
        check("Verschieben: Datei liegt danach im Zielordner, Katalog kennt den neuen Ort",
              r.status_code == 200 and os.path.exists(os.path.join(samm, "Leer", "Vase.stl"))
              and not os.path.exists(os.path.join(samm, "Deko", "Vase.stl"))
              and c.get(f"/api/modelle/{m['Vase']}").json()["orte"][0]["pfad"] == "Leer/Vase.stl")
        deko_stern = next(x for x in c.get("/api/modelle", params={"ordner": f"{w}/Deko"}).json() if x["name"] == "Stern")
        r = c.post(f"/api/modelle/{deko_stern['id']}/verschieben", json={"ordner": f"{w}/Technik"})
        check("Verschieben auf eine gleichnamige Datei: abgelehnt, beide unverändert",
              r.status_code == 400 and os.path.getsize(os.path.join(samm, "Technik", "Stern.stl")) == 684
              and os.path.exists(os.path.join(samm, "Deko", "Stern.stl")))
        r = c.post(f"/api/modelle/{m['Doppel']}/verschieben", json={"ordner": f"{w}/Leer"})
        check("Ein Duplikat (zwei Orte) wird nicht verschoben", r.status_code == 400 and "mehrfach" in r.json()["fehler"])
        r = c.post(f"/api/modelle/{m['Welle']}/verschieben", json={"ordner": f"{w}/../.."})
        check("Ziel ausserhalb der Wurzel über ../ wird abgelehnt",
              r.status_code == 400 and os.path.exists(os.path.join(samm, "Technik", "Welle.obj")))
        r = c.post("/api/verzeichnisse", json={"eltern": f"{w}/Technik", "name": "Drohne"})
        check("Neuen Unterordner anlegen", r.status_code == 200 and os.path.isdir(os.path.join(samm, "Technik", "Drohne")))
        check("Ordnername mit Schrägstrich abgelehnt",
              c.post("/api/verzeichnisse", json={"eltern": w, "name": "a/../../b"}).status_code == 400)

        # -- Quelle
        r = c.patch(f"/api/modelle/{m['Welle']}", json={"quelle_url": "https://www.printables.com/model/123"})
        check("Quelle als https-Adresse", r.json()["quelle_url"] == "https://www.printables.com/model/123")
        check("javascript: als Quelle abgelehnt (würde in der Oberfläche ausgeführt)",
              c.patch(f"/api/modelle/{m['Welle']}", json={"quelle_url": "javascript:alert(1)"}).status_code == 400)
        c.patch(f"/api/modelle/{m['Welle']}", json={"quelle_url": ""})
        check("Leere Quelle entfernt sie", c.get(f"/api/modelle/{m['Welle']}").json()["quelle_url"] is None)

        # -- Eigenes Bild
        puffer = io.BytesIO()
        Image.new("RGB", (2000, 1000), (200, 50, 50)).save(puffer, "JPEG")
        r = c.post(f"/api/modelle/{m['Welle']}/bild", content=puffer.getvalue())
        kachel = next(x for x in c.get("/api/modelle").json() if x["id"] == m["Welle"])
        bild = c.get(f"/api/modelle/{m['Welle']}/bild")
        gross = Image.open(io.BytesIO(bild.content))
        check("Eigenes Bild: als PNG neu geschrieben, höchstens 1024 px, Kachel kennt es",
              r.status_code == 200 and kachel["bild"] and gross.format == "PNG" and max(gross.size) == 1024)
        check("… liegt im Vault (gesichert), nicht im Cache",
              any(n.endswith(".png") for n in os.listdir(os.path.join(tmp, "bestand", "vault", "bilder"))))
        check("Kein Bild (Text) wird abgelehnt",
              c.post(f"/api/modelle/{m['Welle']}/bild", content=b"<svg onload=alert(1)>").status_code == 400)
        check("Über 5 MB wird abgelehnt",
              c.post(f"/api/modelle/{m['Welle']}/bild", content=b"\0" * (5 * 1024**2 + 1)).status_code == 400)
        db = c.app.state.zustand["bestand"].db
        mref = f"MODEL_ASSET/{m['Welle']}"
        iid = db.get_connected(mref, rel_type="HAS_IMAGE")[0]
        datei = db.get_node(iid, readonly=True)["datei"]
        check("Eigenes Bild ist ein Knoten mit `datei` im Vault, per Kante am Modell",
              datei.startswith("vault/bilder/") and os.path.exists(os.path.join(tmp, "bestand", datei)) and kachel["bild"] == iid.split("/")[1])
        puffer2 = io.BytesIO()
        Image.new("RGB", (300, 300), (20, 200, 50)).save(puffer2, "PNG")
        c.post(f"/api/modelle/{m['Welle']}/bild", content=puffer2.getvalue())
        check("Neues Bild ersetzt das alte: ein Bild am Modell, das alte im Papierkorb, seine Datei bleibt",
              len(db.get_connected(mref, rel_type="HAS_IMAGE")) == 1 and db.get_connected(mref, rel_type="HAS_IMAGE")[0] != iid
              and db.get_node(iid, readonly=True) is None and os.path.exists(os.path.join(tmp, "bestand", datei)))
        v = c.get(f"/api/modelle/{m['Welle']}/loeschen").json()
        check("Löschvorschau nennt das Bild", any(k.startswith("MODEL_IMAGE/") for k in v["knoten"]))
        c.post(f"/api/modelle/{m['Welle']}/loeschen")
        check("Mit dem Modell im Papierkorb, sein Bild noch erreichbar (das ersetzte nicht)",
              c.get(f"/api/modelle/{m['Welle']}/bild").status_code == 200
              and Image.open(io.BytesIO(c.get(f"/api/modelle/{m['Welle']}/bild").content)).size == (300, 300))
        c.post(f"/api/modelle/{m['Welle']}/wiederherstellen")
        check("Wiederhergestellt: das Bild ist wieder dran",
              next(x for x in c.get("/api/modelle").json() if x["id"] == m["Welle"])["bild"] is not None)
        # Bestand von vorher: `bild` als Textfeld am Modell
        db.update_node("MODEL_ASSET", m["Welle"], {"bild": datei})
        c.delete(f"/api/modelle/{m['Welle']}/bild")
        check("Bild entfernen: Kachel hat keins mehr, die Datei bleibt im Vault",
              next(x for x in c.get("/api/modelle").json() if x["id"] == m["Welle"])["bild"] is None
              and not db.get_connected(mref, rel_type="HAS_IMAGE") and os.path.exists(os.path.join(tmp, "bestand", datei)))
        db.update_node("MODEL_ASSET", m["Welle"], {"bild": datei})
        from partatlas.katalog import Katalog
        Katalog(c.app.state.zustand["bestand"])
        check("Bestand von vorher: das Feld `bild` wird zum Knoten, das Feld ist leer",
              len(db.get_connected(mref, rel_type="HAS_IMAGE")) == 1 and not db.get_node(mref, readonly=True).get("bild"))

        # -- Hochladen
        r = c.post("/api/hochladen", params={"ordner": f"{w}/Deko", "name": "Stern.stl"}, content=stl_bytes())
        warten(c)
        check("Hochladen auf einen belegten Namen: neue Datei „Stern (2).stl“, nichts überschrieben",
              r.status_code == 200 and os.path.exists(os.path.join(samm, "Deko", "Stern (2).stl"))
              and os.path.getsize(os.path.join(samm, "Deko", "Stern.stl")) == 684)
        check("… und nach dem Scan im Katalog", "Stern (2)" in ids(c))
        r = c.post("/api/hochladen", params={"ordner": w, "name": "../../ausbruch.stl"}, content=stl_bytes(11))
        check("Dateiname mit ../ landet trotzdem nur im Zielordner",
              os.path.exists(os.path.join(samm, "ausbruch.stl")) and not os.path.exists(os.path.join(tmp, "ausbruch.stl")))
        check("Anderes als Modell oder Archiv wird nicht angenommen",
              c.post("/api/hochladen", params={"ordner": w, "name": "boese.sh"}, content=b"rm -rf ~").status_code == 400)
        warten(c)

        # -- Archive
        zp = os.path.join(samm, "Paket.zip")
        with zipfile.ZipFile(zp, "w") as z:
            z.writestr("Paket/Teil A.stl", stl_bytes(12))
            z.writestr("Paket/bild.png", muster.PNG_1PX)
            z.writestr("Paket/setup.exe", b"MZ")
            z.writestr("../../ausserhalb.stl", stl_bytes(13))
            z.writestr("__MACOSX/._Teil A.stl", b"x")
            info = zipfile.ZipInfo("Paket/verweis.stl")
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(info, "/etc/passwd")
        tp = os.path.join(samm, "Technik", "Satz.tar.gz")
        with tarfile.open(tp, "w:gz") as t:
            daten = stl_bytes(14)
            ti = tarfile.TarInfo("Satz/Teil B.stl")
            ti.size = len(daten)
            t.addfile(ti, io.BytesIO(daten))
            link = tarfile.TarInfo("Satz/link.stl")
            link.type = tarfile.SYMTYPE
            link.linkname = "/etc/passwd"
            t.addfile(link)
        liste = {a["name"]: a["id"] for a in c.get("/api/archive").json()}
        check("Archive unter den Wurzeln gefunden", set(liste) == {"Paket.zip", "Satz.tar.gz"})
        r = c.post("/api/archive/entpacken", json={"id": liste["Paket.zip"], "original_loeschen": True}).json()
        ziel = os.path.join(samm, "Paket")
        entpackt = sorted(os.path.relpath(os.path.join(d, f), ziel) for d, _, fs in os.walk(ziel) for f in fs)
        check("Zip: Modell und Bild heraus, in einen Ordner neben dem Archiv", entpackt == ["Paket/Teil A.stl", "Paket/bild.png"])
        check("Zip: .exe, ../-Pfad, __MACOSX und Symlink bleiben drin",
              r["entpackt"] == 2 and not os.path.exists(os.path.join(tmp, "ausserhalb.stl"))
              and not os.path.exists(os.path.join(os.path.dirname(tmp), "ausserhalb.stl")))
        check("Original auf Wunsch in den Papierkorb von partAtlas, nicht gelöscht",
              not os.path.exists(zp) and os.path.exists(os.path.join(tmp, "bestand", "papierkorb", "Paket.zip")))
        c.post("/api/archive/entpacken", json={"id": liste["Satz.tar.gz"]})
        check("tar.gz: Datei heraus, Symlink nicht, Original bleibt",
              os.listdir(os.path.join(samm, "Technik", "Satz", "Satz")) == ["Teil B.stl"] and os.path.exists(tp))
        c.post("/api/archive/entpacken", json={"id": liste["Satz.tar.gz"]})
        check("Zweites Entpacken: neuer Ordner „Satz (2)“, nichts überschrieben",
              os.path.isdir(os.path.join(samm, "Technik", "Satz (2)")))
        warten(c)
        check("Entpacktes ist nach dem Scan im Katalog", {"Teil A", "Teil B"} <= set(ids(c)))

        # -- Mehrere auf einmal
        m = ids(c)
        drei = [m["Welle"], m["Teil A"], m["Stern (2)"]]
        c.post("/api/stapel", json={"aktion": "favorit", "modelle": drei, "wert": True})
        c.post("/api/stapel", json={"aktion": "tag", "modelle": drei, "wert": "#Projekt X"})
        sid = c.post("/api/sammlungen", json={"name": "Auswahl"}).json()["id"]
        c.post("/api/stapel", json={"aktion": "sammlung", "modelle": drei, "wert": sid})
        c.post("/api/stapel", json={"aktion": "warteschlange", "modelle": drei})
        check("Stapel: Favorit, Tag, Sammlung, Warteschlange für drei Modelle",
              sorted(x["name"] for x in c.get("/api/modelle", params={"ansicht": "favoriten"}).json()) == ["Stern (2)", "Teil A", "Welle"]
              and len(c.get("/api/modelle", params={"tag": "projekt x"}).json()) == 3
              and len(c.get("/api/modelle", params={"sammlung": sid}).json()) == 3
              and len(c.get("/api/warteschlange").json()) == 3)
        v = c.post("/api/stapel/loeschvorschau", json={"modelle": drei[:2]}).json()
        check("Löschvorschau für mehrere: Dateien und Verknüpfungen zusammengezählt",
              len(v["dateien"]) == 2 and v["kanten"].get("HAS_TAG", 0) >= 2 and v["kanten"].get("IN_COLLECTION") == 2)
        r = c.post("/api/stapel", json={"aktion": "loeschen", "modelle": drei[:2]}).json()
        check("Stapel löschen: beide im Papierkorb", r["fehler"] == [] and c.get("/api/zaehler").json()["papierkorb"] == 2)
        r = c.post("/api/stapel", json={"aktion": "verschieben", "modelle": [m["Stern (2)"], m["Doppel"]], "wert": f"{w}/Leer"}).json()
        check("Stapel verschieben: was geht, geht; das Duplikat meldet seinen Grund",
              os.path.exists(os.path.join(samm, "Leer", "Stern (2).stl"))
              and [f["id"] for f in r["fehler"]] == [m["Doppel"]])
        check("Unbekannte Aktion abgelehnt", c.post("/api/stapel", json={"aktion": "formatieren", "modelle": drei}).status_code == 400)
    muster.ende()
