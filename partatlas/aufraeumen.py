"""
Aufräumen: Vorschläge, was Platz kostet und vermutlich weg kann — mit Grund und mit dem, was daran hängt.

Anlass (03.10.2026): ein Tester mit vielen Konstruktionsständen je Teil, „das Zumüllen ist echt das Problem“. Gewünscht ist eine Ansicht
wie eine feingranulare Firewall: jede Entscheidung einzeln, nachvollziehbar, nichts geschieht von selbst. partAtlas löscht hier nichts
(KONZEPT §3.3); es zeigt, sortiert und merkt sich, was der Anwender behalten will.

Gedrucktes, Verbautes und Favoriten erscheinen nur, wo der Anwender sie selbst markiert hat (Entwurf) oder wo nichts verloren geht
(Kopien gleichen Inhalts) — und dann mit dem Hinweis, was daran hängt.
"""
import os
import time

from .bestand import DATEI, MODELL

GROSS_AB = 10 * 1024 * 1024          # ab 10 MB lohnt ein Blick
GROSS_HOECHSTENS = 30
UNGENUTZT_TAGE = 365


def _ref(sammlung, kennung):
    return f"{sammlung}/{kennung}"


def vorschlaege(katalog, baugruppen, jetzt=None):
    """{"gruppen": [...], "behalten": n}. Jede Gruppe: art, titel, erklaerung, n, bytes, eintraege; jeder Eintrag: id, name, format,
    bytes, pfade, grund, haengt (Liste von Texten), vorsicht (hängt etwas daran?)."""
    jetzt = jetzt or time.time()
    dateien = katalog.db.list_nodes(DATEI, readonly=True)
    gruppen = {"entwuerfe": [], "kopien": [], "gross": [], "ungenutzt": []}
    behalten = 0
    for m in katalog.modelle():
        d = dateien.get(m["hash"]) or {}
        orte = d.get("orte") or []
        if not orte:
            continue                                   # ohne Datei gibt es nichts aufzuräumen
        roh = katalog.db.get_node(_ref(MODELL, m["id"]), readonly=True) or {}
        if roh.get("aufraeumen_behalten"):
            behalten += 1
            continue
        in_bg = [b["name"] for b in baugruppen.verwendet_in(_ref(MODELL, m["id"]))]
        haengt = ([f"{m['drucke_n']}× gedruckt"] if m.get("drucke_n") else ["gedruckt"] if m.get("gedruckt") else []) \
            + [f"in Baugruppe {n}" for n in in_bg] + (["Favorit"] if m.get("favorit") else [])
        groesse = orte[0].get("groesse") or 0
        pfade = [katalog.absoluter_pfad(o) or o["pfad"] for o in orte]
        eintrag = {"id": m["id"], "name": m["name"], "format": m["format"], "bytes": groesse * len(orte), "pfade": pfade,
                   "haengt": haengt, "vorsicht": bool(haengt), "entwurf": m.get("entwurf", False)}
        if m.get("entwurf"):
            gruppen["entwuerfe"].append({**eintrag, "grund": "als Entwurf markiert"})
            continue
        if len(orte) > 1:
            # Nur die zusätzlichen Kopien kosten Platz; das Modell bleibt mit einer.
            gruppen["kopien"].append({**eintrag, "bytes": groesse * (len(orte) - 1),
                                      "grund": f"{len(orte)} Kopien mit gleichem Inhalt — eine genügt"})
        if haengt:
            continue
        juengste = max((o.get("mtime") or 0) for o in orte)
        if groesse >= GROSS_AB:
            gruppen["gross"].append({**eintrag, "grund": "gross, nie gedruckt, in keiner Baugruppe"})
        elif juengste and jetzt - juengste > UNGENUTZT_TAGE * 86400:
            jahre = (jetzt - juengste) / (365 * 86400)
            gruppen["ungenutzt"].append({**eintrag, "grund": f"nie gedruckt, in keiner Baugruppe, seit {jahre:.0f} "
                                                             f"{'Jahr' if round(jahre) == 1 else 'Jahren'} unverändert"})
    gruppen["gross"] = sorted(gruppen["gross"], key=lambda e: -e["bytes"])[:GROSS_HOECHSTENS]
    texte = {
        "entwuerfe": ("Entwürfe", "Was du als Entwurf markiert hast. Hängt noch etwas daran, steht es dabei."),
        "kopien": ("Kopien gleichen Inhalts", "Dieselbe Datei an mehreren Orten. Löschst du Kopien, bleibt das Modell mit einer — "
                                              "nichts geht verloren."),
        "gross": ("Grosse Dateien ohne Verwendung", f"Ab {GROSS_AB // 1048576} MB, nie gedruckt, in keiner Baugruppe, kein Favorit."),
        "ungenutzt": ("Lange nicht angefasst", f"Nie gedruckt, in keiner Baugruppe, kein Favorit, seit über {UNGENUTZT_TAGE} Tagen "
                                               f"unverändert."),
    }
    aus = []
    for art, eintraege in gruppen.items():
        eintraege.sort(key=lambda e: (-e["bytes"], (e["name"] or "").lower()))
        titel, erklaerung = texte[art]
        aus.append({"art": art, "titel": titel, "erklaerung": erklaerung, "n": len(eintraege),
                    "bytes": sum(e["bytes"] for e in eintraege), "eintraege": eintraege})
    return {"gruppen": aus, "behalten": behalten}


def behalten(katalog, mid, an=True):
    """„Behalten“: nicht mehr vorschlagen — wie eine Ausnahme in der Firewall. Zurücknehmbar."""
    from .katalog import KatalogFehler
    if katalog.db.get_node(_ref(MODELL, mid), readonly=True) is None:
        raise KatalogFehler(f"Modell {mid} gibt es nicht.")
    katalog.db.update_node(MODELL, mid, {"aufraeumen_behalten": bool(an) or None})


def behaltene(katalog):
    """Die Ausnahmen, damit man sie wieder aufheben kann."""
    return [{"id": m["id"], "name": m["name"], "format": m["format"]} for m in katalog.modelle()
            if (katalog.db.get_node(_ref(MODELL, m["id"]), readonly=True) or {}).get("aufraeumen_behalten")]


def pfad_von(katalog, mid, pfad):
    """Nur ein Pfad, den das Modell wirklich hat, darf im Dateimanager gezeigt werden — kein beliebiger Pfad über die Schnittstelle."""
    m = katalog.modell(mid)
    bekannt = {o["absolut"] for o in m["orte"] if o.get("absolut")}
    return pfad if pfad in bekannt and os.path.exists(pfad) else None
