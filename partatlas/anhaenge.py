"""Anhänge an Modellen und Baugruppen: Montageanleitung, Konstruktionszeichnung (PDF, CorelDRAW, SVG, DXF …), Datenblatt.

Entschieden 12.10.2026 (Anwender): eine **Kopie im Bestand** — sie gehört fest zum Modell, kommt ins Backup und bleibt, auch wenn der
Ordner aufgeräumt wird. Wie die eigenen Bilder (KONZEPT §3.2): eine Liste `anhaenge` am Knoten, kein Knoten je Datei; die Datei liegt
unverändert in `vault/anhaenge/<Titel>__<Hash>.<endung>` (ohne App lesbar), und was der Anwender hineingetan hat, verschwindet nie —
entfernt geht es nach `vault_archive/`.

Öffnen startet eine **Kopie** in `arbeit/geoeffnet/`: ein Programm, das beim Speichern die Datei an Ort und Stelle ändert, darf den Vault
nicht verändern (er wird nie überschrieben, §3.2). Geänderte Fassungen hängt man neu an.
"""
import filecmp
import hashlib
import os
import re
import shutil

from . import dateien
from .bestand import MODELL
from .katalog import KatalogFehler, jetzt, ref

BAUGRUPPE = "ASSEMBLY"          # wie baugruppen.BAUGRUPPE; hier ohne den Import, der sonst im Kreis liefe
ZIELE = {"modell": MODELL, "baugruppe": BAUGRUPPE}
MAX_ANHANG = 500 << 20
# Im Browser ansehen statt herunterladen: nur, was der Browser selbst sicher darstellt. Alles andere (auch SVG und HTML, die Skript
# enthalten können) kommt als Download.
ANZEIGEN = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
            ".gif": "image/gif", ".txt": "text/plain; charset=utf-8", ".md": "text/plain; charset=utf-8"}


class Anhaenge:
    def __init__(self, katalog):
        self.k = katalog
        self.db = katalog.db

    def _knoten(self, art, kennung):
        sammlung = ZIELE.get(art)
        if sammlung is None:
            raise KatalogFehler(f"Anhänge gibt es an {art} nicht.")
        n = self.db.get_node(ref(sammlung, kennung), readonly=True)
        if n is None:
            raise KatalogFehler("Das gibt es nicht (mehr).")
        return sammlung, n

    def liste(self, art, kennung):
        _, n = self._knoten(art, kennung)
        return [{**a, "url": f"/api/anhaenge/{art}/{kennung}/{a['k']}", "anzeigen": os.path.splitext(a["name"])[1].lower() in ANZEIGEN}
                for a in n.get("anhaenge") or []]

    def hinzufuegen(self, art, kennung, name, daten):
        sammlung, n = self._knoten(art, kennung)
        name = os.path.basename((name or "").replace("\\", "/")).strip()[:200] or "anhang"
        if not daten:
            raise KatalogFehler("Die Datei ist leer.")
        if len(daten) > MAX_ANHANG:
            raise KatalogFehler("Anhang grösser als 500 MB.")
        k = hashlib.sha256(daten).hexdigest()[:12]
        liste = list(n.get("anhaenge") or [])
        if any(a["k"] == k for a in liste):
            return k                                    # derselbe Inhalt hängt schon da
        stamm, endung = os.path.splitext(name)
        titel = re.sub(r"[^\w.-]+", "_", stamm)[:60] or "anhang"
        rel = f"vault/anhaenge/{titel}__{k}{endung.lower()[:12]}"
        ziel = self.k.b.pfad(*rel.split("/"))
        if not os.path.exists(ziel):
            dateien.schreibe_atomar(ziel, daten)
        liste.append({"k": k, "name": name, "datei": rel, "groesse": len(daten), "angelegt": jetzt()})
        self.db.update_node(sammlung, kennung, {"anhaenge": liste})
        return k

    def _eintrag(self, art, kennung, k):
        sammlung, n = self._knoten(art, kennung)
        a = next((a for a in n.get("anhaenge") or [] if a["k"] == k), None)
        if a is None:
            raise KatalogFehler("Diesen Anhang gibt es nicht.")
        return sammlung, n, a

    def pfad(self, art, kennung, k):
        _, _, a = self._eintrag(art, kennung, k)
        return self.k.b.pfad(*a["datei"].split("/")), a["name"]

    def entfernen(self, art, kennung, k):
        """Aus der Liste; die Datei geht nach vault_archive/ — nie weg, wie bei den eigenen Bildern."""
        sammlung, n, a = self._eintrag(art, kennung, k)
        self.db.update_node(sammlung, kennung, {"anhaenge": [x for x in n["anhaenge"] if x["k"] != k]})
        if not any(a["datei"] == x["datei"] for nn in self._alle_mit_anhaengen() for x in nn):
            self.k._archivieren(a["datei"])

    def _alle_mit_anhaengen(self):
        """Listen aller Knoten mit Anhängen — derselbe Inhalt kann an zwei Knoten hängen und liegt dann nur einmal im Vault."""
        for sammlung in ZIELE.values():
            for n in self.db.list_nodes(sammlung, include_deleted=True, readonly=True).values():
                if n.get("anhaenge"):
                    yield n["anhaenge"]

    def umbenennen(self, art, kennung, k, name):
        sammlung, n, _ = self._eintrag(art, kennung, k)
        name = os.path.basename((name or "").replace("\\", "/")).strip()[:200]
        if not name:
            raise KatalogFehler("Name leer.")
        self.db.update_node(sammlung, kennung, {"anhaenge": [{**x, "name": name} if x["k"] == k else x for x in n["anhaenge"]]})

    def kopie_zum_oeffnen(self, art, kennung, k):
        """Eine Kopie in arbeit/geoeffnet/ — das Programm darf sie ändern, den Vault nicht. Gibt den Pfad zurück."""
        quelle, name = self.pfad(art, kennung, k)
        ordner = self.k.b.pfad("arbeit", "geoeffnet")
        os.makedirs(ordner, exist_ok=True)
        # Dieselbe, unveränderte Kopie wieder nehmen: nach zehnmal Anklicken lagen sonst zehn gleiche Dateien da (Tester, 13.10.2026). Eine,
        # die das Programm inzwischen geändert hat, bleibt unberührt — die Kopie daneben ist dann eine neue.
        ziel = os.path.join(ordner, name)
        stamm, endung = os.path.splitext(ziel)
        n = 1
        while os.path.lexists(ziel):
            if os.path.isfile(ziel) and filecmp.cmp(quelle, ziel, shallow=False):
                return ziel
            n += 1
            ziel = f"{stamm} ({n}){endung}"
        shutil.copyfile(quelle, ziel)
        return ziel


def notiz_pruefen(text, grenze=50000):
    text = str(text or "")
    if len(text) > grenze:
        raise KatalogFehler(f"Notiz länger als {grenze} Zeichen.")
    return text
