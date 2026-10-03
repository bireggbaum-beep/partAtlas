"""
Zuordnen: Tag, Material, Sammlung oder Baugruppe für viele Modelle auf einmal — eine Schnittstelle für alle vier.

Vorher gab es vier Muster für dieselbe Aufgabe (Textfeld, Dialog mit Chips, Dialog mit Auswahlliste, Auswahlliste in der Leiste).
Jetzt fragt die Oberfläche `optionen` (was gibt es, bei wie vielen der Gewählten ist es schon) und ruft `zuordnen` (hinzufügen,
oder neu anlegen und hinzufügen). Es wird nur hinzugefügt, nie entfernt; entfernen geht je Modell im Inspektor.

Wichtig für Baugruppen: ein Modell ein zweites Mal hinzuzufügen erhöht dort die Menge (so fühlt sich Ziehen richtig an). Ein Auswahlfenster,
das man mehrfach anklickt, darf das nicht tun — hier werden Modelle übersprungen, die schon in der Baugruppe stehen.
"""
from .bestand import MODELL, SAMMLUNG
from .baugruppen import BAUGRUPPE
from .katalog import KatalogFehler, ref

ARTEN = ("tag", "material", "sammlung", "baugruppe")


def _modelle(katalog, modelle):
    gueltig = [m for m in dict.fromkeys(modelle or []) if katalog.db.get_node(ref(MODELL, m), readonly=True) is not None]
    if not gueltig:
        raise KatalogFehler("Keine Modelle gewählt.")
    return gueltig


def _hat(katalog, baugruppen, art, mid):
    """Die Kennungen, die dieses Modell für `art` schon hat."""
    if art == "tag":
        return set(katalog.tags_von(mid))
    if art == "material":
        return set(katalog.materialien_von(mid)["vorgesehen"])
    if art == "sammlung":
        return {s["id"] for s in katalog.sammlungen_von(mid)}
    return {b["id"] for b in baugruppen.verwendet_in(ref(MODELL, mid))}


def optionen(katalog, baugruppen, art, modelle):
    """[{id, name, bei, gesamt}] — `bei`: bei wie vielen der Gewählten es das schon gibt; `gesamt`: wie viele Modelle es insgesamt tragen
    (nur wo bekannt)."""
    if art not in ARTEN:
        raise KatalogFehler("Das lässt sich nicht zuordnen.")
    modelle = _modelle(katalog, modelle)
    bei = {}
    for mid in modelle:
        for k in _hat(katalog, baugruppen, art, mid):
            bei[k] = bei.get(k, 0) + 1
    if art == "tag":
        quelle = [(t["name"], t["name"], t["anzahl"]) for t in katalog.tags()]
    elif art == "material":
        quelle = [(m, m, None) for m in katalog.materialien()]
    elif art == "sammlung":
        quelle = [(s["id"], s["name"], s["anzahl"]) for s in katalog.sammlungen()]
    else:
        quelle = [(b["id"], b["name"], None) for b in baugruppen.liste()]
    return {"n": len(modelle), "optionen": [{"id": i, "name": n, "bei": bei.get(i, 0), "gesamt": g} for i, n, g in quelle]}


def zuordnen(katalog, baugruppen, art, modelle, ziel=None, neu=None):
    """Hinzufügen. `ziel`: Kennung (bei Tag und Material der Name, auch ein neuer); `neu`: Name einer neuen Sammlung oder Baugruppe.
    Gibt zurück, wie vielen es hinzugefügt wurde und bei wie vielen es schon war."""
    if art not in ARTEN:
        raise KatalogFehler("Das lässt sich nicht zuordnen.")
    modelle = _modelle(katalog, modelle)
    with katalog.db.transaction():
        if art in ("tag", "material"):
            name = (ziel or neu or "").strip()
            if not name:
                raise KatalogFehler("Name fehlt.")
            schon = 0
            for mid in modelle:
                if art == "tag":
                    vorher = set(katalog.tags_von(mid))
                    gesetzt = katalog._tag_verbinden(mid, name)
                    schon += gesetzt in vorher
                else:
                    vorher = set(katalog.materialien_von(mid)["vorgesehen"])
                    gesetzt = katalog.material_vorsehen(mid, name)
                    schon += gesetzt in vorher
            return {"art": art, "ziel": gesetzt, "name": gesetzt, "neu": False, "hinzugefuegt": len(modelle) - schon, "schon": schon}
        if art == "sammlung":
            if neu:
                sid = katalog.sammlung_anlegen(neu, modelle)
                return {"art": art, "ziel": sid, "name": katalog._name_pruefen(neu), "neu": True, "hinzugefuegt": len(modelle), "schon": 0}
            katalog._sammlung_pruefen(ziel)
            schon = sum(1 for mid in modelle if ziel in _hat(katalog, baugruppen, art, mid))
            katalog._hinzufuegen(ziel, modelle)
            return {"art": art, "ziel": ziel, "name": katalog.db.get_node(ref(SAMMLUNG, ziel), readonly=True)["name"], "neu": False,
                    "hinzugefuegt": len(modelle) - schon, "schon": schon}
        # Baugruppe
        if neu:
            bid = baugruppen.aus_modellen(neu, modelle)
            return {"art": art, "ziel": bid, "name": neu.strip(), "neu": True, "hinzugefuegt": len(modelle), "schon": 0}
        baugruppen._pruefen(ziel)
        fehlen = [mid for mid in modelle if ziel not in _hat(katalog, baugruppen, art, mid)]
        for mid in fehlen:
            baugruppen.hinzufuegen(ziel, ref(MODELL, mid))
        return {"art": art, "ziel": ziel, "name": baugruppen.db.get_node(ref(BAUGRUPPE, ziel), readonly=True)["name"], "neu": False,
                "hinzugefuegt": len(fehlen), "schon": len(modelle) - len(fehlen)}
