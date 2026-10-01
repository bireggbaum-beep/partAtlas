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

        # -- Bilder des Anwenders: Liste am Modell, Dateien im Vault
        def jpeg(farbe, gross=(2000, 1000)):
            p = io.BytesIO()
            Image.new("RGB", gross, farbe).save(p, "JPEG")
            return p.getvalue()

        db = c.app.state.zustand["bestand"].db
        mref = f"MODEL_ASSET/{m['Welle']}"
        k1 = c.post(f"/api/modelle/{m['Welle']}/bilder", content=jpeg((200, 50, 50))).json()["k"]
        k2 = c.post(f"/api/modelle/{m['Welle']}/bilder", content=jpeg((20, 200, 50), (300, 300))).json()["k"]
        kachel = next(x for x in c.get("/api/modelle").json() if x["id"] == m["Welle"])
        gross = Image.open(io.BytesIO(c.get(f"/api/modelle/{m['Welle']}/bilder/{k1}").content))
        bilder = db.get_node(mref, readonly=True)["bilder"]
        check("Zwei eigene Bilder als Liste am Modell (kein Knoten je Bild), Dateien im Vault",
              [b["k"] for b in bilder] == [k1, k2] and all(os.path.exists(os.path.join(tmp, "bestand", b["datei"])) for b in bilder)
              and all(b["datei"].startswith("vault/bilder/") for b in bilder) and "MODEL_IMAGE" not in db.list_collections())
        check("Als PNG neu geschrieben, höchstens 1600 px; die Kachel zeigt das erste als Titelbild",
              gross.format == "PNG" and max(gross.size) == 1600 and kachel["bild"] == k1)
        ans = c.get(f"/api/modelle/{m['Welle']}").json()["ansichten"]
        check("Galerie: eigene Bilder zuerst (das erste heisst Vorschaubild), dann die berechnete Vorschau",
              [(a["art"], a.get("k"), a["titel"]) for a in ans]
              == [("eigen", k1, "Vorschaubild"), ("eigen", k2, "Eigenes Bild"), ("berechnet", None, "Vorschau")]
              and c.get(ans[2]["url"]).status_code == 200)
        c.post(f"/api/modelle/{m['Welle']}/bilder/{k2}/titel")
        check("Als Titelbild: rückt nach vorn, die Kachel folgt",
              [b["k"] for b in db.get_node(mref, readonly=True)["bilder"]] == [k2, k1]
              and next(x for x in c.get("/api/modelle").json() if x["id"] == m["Welle"])["bild"] == k2)
        r = c.post(f"/api/modelle/{m['Welle']}/vorschau/berechnet/titel")
        kachel = next(x for x in c.get("/api/modelle").json() if x["id"] == m["Welle"])
        ans = c.get(f"/api/modelle/{m['Welle']}").json()["ansichten"]
        check("Original als Vorschaubild: die Kachel zeigt es statt des eigenen Bilds, die Galerie markiert es",
              r.status_code == 200 and kachel["bild"] is None and kachel["vorschau_art"] == "berechnet"
              and [a["ist_vorschaubild"] for a in ans] == [False, False, True])
        check("Unbekannte Art als Vorschaubild abgelehnt",
              c.post(f"/api/modelle/{m['Welle']}/vorschau/gibtsnicht/titel").status_code >= 400)
        c.post(f"/api/modelle/{m['Welle']}/bilder/{k2}/titel")
        check("Ein eigenes Bild als Vorschaubild nimmt die Wahl des Originals zurück",
              next(x for x in c.get("/api/modelle").json() if x["id"] == m["Welle"])["bild"] == k2)
        check("Dasselbe Bild zweimal wird nicht doppelt",
              c.post(f"/api/modelle/{m['Welle']}/bilder", content=jpeg((20, 200, 50), (300, 300))).json()["k"] == k2
              and len(db.get_node(mref, readonly=True)["bilder"]) == 2)
        check("Kein Bild (Text) wird abgelehnt",
              c.post(f"/api/modelle/{m['Welle']}/bilder", content=b"<svg onload=alert(1)>").status_code == 400)
        check("Über 15 MB wird abgelehnt",
              c.post(f"/api/modelle/{m['Welle']}/bilder", content=b"\0" * (15 * 1024**2 + 1)).status_code == 400)
        hoch = io.BytesIO()
        foto = Image.new("RGB", (40, 20), (1, 2, 3))
        exif = foto.getexif()
        exif[0x0112] = 6   # Handy hochkant: Drehung nur in den Exif-Daten
        foto.save(hoch, "JPEG", exif=exif)
        k3 = c.post(f"/api/modelle/{m['Welle']}/bilder", content=hoch.getvalue()).json()["k"]
        check("Handyfoto mit Drehung in den Exif-Daten steht aufrecht",
              Image.open(io.BytesIO(c.get(f"/api/modelle/{m['Welle']}/bilder/{k3}").content)).size == (20, 40))
        datei3 = next(b["datei"] for b in db.get_node(mref, readonly=True)["bilder"] if b["k"] == k3)
        c.delete(f"/api/modelle/{m['Welle']}/bilder/{k3}")
        archiv = os.path.join(tmp, "bestand", "vault_archive")
        check("Bild entfernen: aus der Liste, die Datei geht ins Archiv, nicht ins Nichts",
              [b["k"] for b in db.get_node(mref, readonly=True)["bilder"]] == [k2, k1]
              and not os.path.exists(os.path.join(tmp, "bestand", datei3))
              and os.path.basename(datei3) in os.listdir(archiv))
        v = c.get(f"/api/modelle/{m['Welle']}/loeschen").json()
        check("Löschvorschau nennt die Bilder", v["bilder"] == 2)
        c.post(f"/api/modelle/{m['Welle']}/loeschen")
        check("Mit dem Modell im Papierkorb: Titelbild noch erreichbar",
              Image.open(io.BytesIO(c.get(f"/api/modelle/{m['Welle']}/bild").content)).size == (300, 300))
        c.post(f"/api/modelle/{m['Welle']}/wiederherstellen")
        check("Wiederhergestellt: beide Bilder wieder da",
              [a.get("k") for a in c.get(f"/api/modelle/{m['Welle']}").json()["ansichten"] if a["art"] == "eigen"] == [k2, k1])

        # -- Bestand von vorher: Feld `bild` (bis 0.10) und Knoten MODEL_IMAGE (0.11)
        from partatlas.katalog import Katalog
        alt1 = db.get_node(mref, readonly=True)["bilder"][1]["datei"]
        alt2 = db.get_node(mref, readonly=True)["bilder"][0]["datei"]
        with db.transaction():
            db.update_node("MODEL_ASSET", m["Welle"], {"bilder": None, "bild": alt1})
            db.create_node("MODEL_IMAGE", "i_000001", {"datei": alt2})
            db.create_edge(mref, "MODEL_IMAGE/i_000001", "HAS_IMAGE", cascade_delete=True)
        Katalog(c.app.state.zustand["bestand"])
        n = db.get_node(mref, readonly=True)
        check("Bestand von vorher: Feld und Bildknoten werden zur Liste, Kante weg, Feld leer",
              [b["datei"] for b in n["bilder"]] == [alt1, alt2] and not n.get("bild")
              and not db.verwendungen(mref, direction="out").get("HAS_IMAGE") and db.get_node("MODEL_IMAGE/i_000001") is None)

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
        c.post("/api/stapel", json={"aktion": "tag", "modelle": drei[:2], "wert": "nur-zwei"})
        s2 = c.post("/api/sammlungen", json={"name": "Nur zwei", "modelle": drei[:2]}).json()["id"]
        bid = c.post("/api/baugruppen", json={"name": "Rahmen", "modelle": [drei[0]]}).json()["id"]
        v = c.post("/api/stapel/loeschvorschau", json={"modelle": drei[:2]}).json()
        tag = {t["name"]: t for t in v["tags"]}
        sml = {x["name"]: x for x in v["sammlungen"]}
        check("Löschvorschau für mehrere: Dateien, Warteschlange und Baugruppe aus der Nachbarschaft",
              len(v["dateien"]) == 2 and v["warteschlange"] == 2
              and [(b["name"], b["menge"]) for b in v["baugruppen"]] == [("Rahmen", 1)])
        check("… je Tag und Sammlung, ob sonst noch ein Modell daran hängt",
              tag["projekt x"]["sonst"] == 1 and tag["nur-zwei"]["sonst"] == 0 and tag["nur-zwei"]["betroffen"] == 2
              and sml["Auswahl"]["sonst"] == 1 and sml["Nur zwei"]["sonst"] == 0)
        r = c.post("/api/stapel", json={"aktion": "loeschen", "modelle": drei[:2], "wert": {"tags": ["projekt x"]}})
        check("Ein Tag, der noch an einem anderen Modell hängt, wird nicht mitgelöscht — und dann gar nichts",
              r.status_code == 400 and c.get("/api/zaehler").json()["papierkorb"] == 0)
        r = c.post("/api/stapel", json={"aktion": "loeschen", "modelle": drei[:2],
                                        "wert": {"tags": ["nur-zwei"], "sammlungen": [s2]}}).json()
        check("Stapel löschen: beide im Papierkorb, der Tag und die leere Sammlung auf Wunsch mit, der Rest bleibt",
              r["fehler"] == [] and c.get("/api/zaehler").json()["papierkorb"] == 2
              and "nur-zwei" not in {t["name"] for t in c.get("/api/tags").json()}
              and "projekt x" in {t["name"] for t in c.get("/api/tags").json()}
              and [x["name"] for x in c.get("/api/sammlungen").json()] == ["Auswahl"])
        r = c.post("/api/stapel", json={"aktion": "verschieben", "modelle": [m["Stern (2)"], m["Doppel"]], "wert": f"{w}/Leer"}).json()
        check("Stapel verschieben: was geht, geht; das Duplikat meldet seinen Grund",
              os.path.exists(os.path.join(samm, "Leer", "Stern (2).stl"))
              and [f["id"] for f in r["fehler"]] == [m["Doppel"]])
        check("Unbekannte Aktion abgelehnt", c.post("/api/stapel", json={"aktion": "formatieren", "modelle": drei}).status_code == 400)
    muster.ende()
