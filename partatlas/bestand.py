"""
Der Bestand von partAtlas: Ort, Aufteilung, flatgraph-Instanz.

    <bestand>/datenbank/   flatgraph                        gesichert
    <bestand>/vault/       Anhänge der Knoten                gesichert
      vorschau/<hash>.extrahiert.png  Bild aus der Datei (3MF)  ─┐ gehören zur Datei
      vorschau/<hash>.berechnet.png   von partAtlas gerendert   ─┘ (PART_GEOMETRY)
      bilder/<Name>__<k>.png          Bilder des Anwenders, Liste am Modell
    <bestand>/vault_text/  lange Texte (ab LANGTEXT_AB Zeichen)  gesichert
    <bestand>/papierkorb/  gelöschte Modelldateien           bis zum Leeren
    <bestand>/arbeit/      Arbeitsdateien, nie /tmp

KONZEPT §3.2. Ein Prozess besitzt den Bestand: flatgraph lässt eine zweite
Instanz nicht zu (`BestandBelegt`), und das ist hier gewollt.
"""
import json
import os
import threading

import flatgraph

# Sammlungen und Kantenarten — KONZEPT §6. Namen folgen der Namensregel von
# flatgraph (VERTRAG §7).
WURZEL = "ROOT_FOLDER"
MODELL = "MODEL_ASSET"
DATEI = "PART_GEOMETRY"
TAG = "TAG_ITEM"
HAT_DATEI = "HAS_PART"
HAT_TAG = "HAS_TAG"
SAMMLUNG = "COLLECTION"
IN_SAMMLUNG = "IN_COLLECTION"
# Texte ab so vielen Zeichen liegen als Datei in vault_text/ und werden erst
# gelesen, wenn man sie braucht (get_node_full) — nicht mit jedem Knoten im RAM.
LANGTEXT_AB = 1000
VORSCHAU_ARTEN = ("extrahiert", "berechnet")
# Material ist ein Knoten, nicht Text: Modell ─[vorgesehen]→ Material vom
# Anwender, Datei ─[braucht]→ Material aus den Slicer-Daten (später auch
# der G-Code, KONZEPT §6). Ein Chip „PETG“ ist dann die Nachbarschaft.
MATERIAL = "MATERIAL_MASTER"
VORGESEHEN = "INTENDED_MATERIAL"
BRAUCHT = "REQUIRES_MATERIAL"
# Grundbestand; weitere legt der Anwender an.
MATERIALIEN = ["PLA", "PLA+", "PETG", "ABS", "ASA", "TPU", "PA", "PC", "PLA-CF", "PETG-CF", "PVA", "HIPS"]


def standard_ort():
    basis = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(basis, "partatlas")


class Bestand:
    def __init__(self, wurzel=None, bei_aenderung=None):
        self.wurzel = os.path.abspath(wurzel or os.environ.get("PARTATLAS_BESTAND") or standard_ort())
        for teil in ("vault/vorschau", "vault/bilder", "papierkorb", "arbeit"):
            os.makedirs(os.path.join(self.wurzel, teil), exist_ok=True)
        self._hoerer = []
        self._hoerer_sperre = threading.Lock()
        if bei_aenderung:
            self._hoerer.append(bei_aenderung)
        self.db = flatgraph.FlatGraphDB(self.wurzel, bei_aenderung=self._melden,
                                        longtext_threshold=LANGTEXT_AB)
        self._einstellungen_pfad = os.path.join(self.wurzel, "einstellungen.json")

    # Der Rückruf läuft unter der Sperre von flatgraph (VERTRAG §2.7): nur
    # weiterreichen, nichts Langsames.
    def _melden(self, meldung):
        with self._hoerer_sperre:
            hoerer = list(self._hoerer)
        for h in hoerer:
            h(meldung)

    def hoeren(self, f):
        with self._hoerer_sperre:
            self._hoerer.append(f)

    def schliessen(self):
        self.db.close()

    def pfad(self, *teile):
        return os.path.join(self.wurzel, *teile)

    def vorschau_pfad(self, datei_hash, art):
        return self.pfad(*self.vorschau_rel(datei_hash, art).split("/"))

    @staticmethod
    def vorschau_rel(datei_hash, art):
        # Die Art steht im Namen: ein neu gerendertes Bild überschreibt nie
        # das aus der Datei, und man sieht im Vault, was wovon kommt.
        assert art in VORSCHAU_ARTEN
        return f"vault/vorschau/{datei_hash}.{art}.png"

    # -- Einstellungen: klein, selten geändert, kein Teil des Graphen.

    def einstellungen(self):
        try:
            with open(self._einstellungen_pfad, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def einstellungen_setzen(self, **werte):
        from .dateien import schreibe_atomar
        daten = self.einstellungen()
        daten.update(werte)
        schreibe_atomar(self._einstellungen_pfad,
                        json.dumps(daten, ensure_ascii=False, indent=1).encode("utf-8"))
