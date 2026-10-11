"""
Teilezugriff: die einzige Stelle, an der Baugruppen den Kern ansprechen.

Baugruppen sind ein eigener Bereich (Sidecar): sie kennen ein Einzelteil nur
über seine ID und fragen alles, was die Oberfläche über das Teil zeigen muss
(Name, Bild, Gewicht, Zeit), hier ab — statt die Teileverwaltung nachzubauen
oder in ihre Knoten zu greifen. Ändert sich der Kern, ändert sich nur diese
Datei.

Regel: `baugruppen.py` und alles Neue darin (Tausch, Fork, Druckplatten …)
liest Modelle, Material und Einstellungen nur über `Teilezugriff`, nie über
`katalog._kurz`, `PART_GEOMETRY` oder `db.get_node` auf ein Modell.
Die eigenen Knoten der Baugruppen (Baugruppe, Kaufteil, Kanten) bleiben im
Modul.
"""
from .bestand import MODELL
from .katalog import ref


class Teilezugriff:
    def __init__(self, katalog):
        self._k = katalog
        self._db = katalog.db

    # ---------------------------------------------------------------- Modelle

    def existiert(self, ziel):
        """Gibt es den Knoten `Sammlung/id` (Modell, Baugruppe, Kaufteil …) überhaupt?"""
        return self._db.get_node(ziel, readonly=True) is not None

    def modell_name(self, mid):
        m = self._db.get_node(ref(MODELL, mid), readonly=True)
        return None if m is None else m.get("name")

    def modell(self, mid):
        """Kachelangaben des Modells und seine Geometrie (Platten, Volumen, Fläche) —
        beides roh; was daraus für die Stückliste folgt, rechnet Baugruppen."""
        m = self._db.get_node(ref(MODELL, mid), readonly=True)
        kurz = self._k._kurz(mid, m)
        h = kurz["hash"]
        geometrie = self._db.get_node(f"PART_GEOMETRY/{h}", readonly=True) if h else None
        return kurz, geometrie or {}

    def modelle(self, **filter):
        """Die Kacheln der Ansicht (Ordner, Sammlung …), wie `Katalog.modelle`."""
        return self._k.modelle(**filter)

    def bild_datei(self, mid):
        """Eigenes Bild des Modells (Pfad) oder None."""
        return self._k.bild_pfad(mid)

    def vorschau_datei(self, hash_):
        return self._k.vorschau_datei(hash_)

    def ort(self, hash_):
        """Erster bekannter Ort (Pfad) der Datei, sonst None."""
        g = self._db.get_node(f"PART_GEOMETRY/{hash_}", readonly=True) or {}
        return next(iter(g.get("orte", [])), None)

    def in_warteschlange(self, mid):
        self._k.in_warteschlange(mid)

    # ---------------------------------------------------------------- Ordner, Material, Einstellungen

    def ordner_name(self, ordner_id):
        return self._k.wurzeln().get(ordner_id, {}).get("name")

    def einstellungen(self):
        return self._k.b.einstellungen()

    def material_knoten(self, name):
        return self._k.material_knoten(name)

    def materialien(self):
        return self._k.materialien()

    def bild_pfad(self, *teile):
        """Pfad einer Bilddatei im Bestand (z. B. eines eigenen Bildes)."""
        return self._k.b.pfad(*teile)
