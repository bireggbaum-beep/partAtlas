"""
Stückliste als PDF — zum Ausdrucken für die Werkstatt oder zum Weitergeben.

Aufbau wie eine Stückliste aus dem Maschinenbau:

  1  Strukturstückliste   jede Ebene mit Positionsnummer (1, 1.1, 1.2 …),
                          Menge je übergeordnete Einheit und gesamt
  2  Mengenübersicht      jedes Druckteil einmal, mit der Gesamtmenge über
                          alle Ebenen — das, was man tatsächlich druckt
  3  Einkaufsliste        Kaufteile über alle Ebenen
  4  Filament             je Material und Farbe, mit Rollenanteil

Mit Abhakkästchen zum Ausdrucken. Schriften sind die eingebauten PDF-
Schriften (Helvetica): keine Schriftdatei nötig, unter Linux wie unter
Windows gleich. Zeichen ausserhalb von WinAnsi (etwa „≈“) kommen deshalb
nicht vor.
"""
import io
import os
import time

from reportlab.graphics.shapes import Circle, Drawing, Rect
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from .baugruppen import ARTEN, BAUGRUPPE, KAUFTEIL

AKZENT = colors.HexColor("#c8553d")
TINTE = colors.HexColor("#222222")
GRAU = colors.HexColor("#777777")
LINIE = colors.HexColor("#d9d4cf")
HELL = colors.HexColor("#f4f1ee")

S = {
    "titel": ParagraphStyle("titel", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=TINTE),
    "unter": ParagraphStyle("unter", fontName="Helvetica", fontSize=9.5, leading=13, textColor=GRAU),
    "h": ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=11.5, leading=15, textColor=TINTE, spaceBefore=10, spaceAfter=4),
    "zelle": ParagraphStyle("zelle", fontName="Helvetica", fontSize=8.2, leading=10, textColor=TINTE),
    "zelle_b": ParagraphStyle("zelle_b", fontName="Helvetica-Bold", fontSize=8.4, leading=10.5, textColor=TINTE),
    "klein": ParagraphStyle("klein", fontName="Helvetica", fontSize=6.8, leading=8.4, textColor=GRAU),
    "rechts": ParagraphStyle("rechts", fontName="Helvetica", fontSize=8.2, leading=10, textColor=TINTE, alignment=TA_RIGHT),
    "kopf": ParagraphStyle("kopf", fontName="Helvetica-Bold", fontSize=7, leading=9, textColor=GRAU),
    "zahl": ParagraphStyle("zahl", fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=TINTE),
}


def _esc(t):
    return str(t if t is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _zahl(x, stellen=0):
    if x is None:
        return "–"
    t = f"{x:,.{stellen}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return t


def _dauer(s):
    if not s:
        return "–"
    h, m = int(s // 3600), int(round((s % 3600) / 60))
    return f"{h} h {m:02d} min" if h else f"{m} min"


def _tupfer(farbe, groesse=7):
    d = Drawing(groesse + 2, groesse + 2)
    if farbe:
        d.add(Circle(groesse / 2 + 1, groesse / 2 + 1, groesse / 2, fillColor=colors.HexColor(farbe),
                     strokeColor=GRAU, strokeWidth=0.4))
    else:
        d.add(Circle(groesse / 2 + 1, groesse / 2 + 1, groesse / 2, fillColor=colors.white,
                     strokeColor=GRAU, strokeWidth=0.4, strokeDashArray=[1, 1]))
    return d


def _kaestchen(gefuellt=False):
    d = Drawing(10, 10)
    d.add(Rect(1, 1, 8, 8, fillColor=AKZENT if gefuellt else colors.white, strokeColor=GRAU, strokeWidth=0.6))
    return d


def _material(material, farbe, angenommen=False):
    t = Table([[_tupfer(farbe), Paragraph(_esc(material) + (" <font color='#999999' size='6'>Std.</font>" if angenommen else ""),
                                          S["zelle"])]], colWidths=[11, None])
    t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                           ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    return t


class _Seiten(rl_canvas.Canvas):
    """Fusszeile mit „Seite x von y“ — y steht erst nach der letzten Seite fest."""

    def __init__(self, *a, fuss="", **k):
        super().__init__(*a, **k)
        self._seiten, self._fuss = [], fuss

    def showPage(self):
        self._seiten.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        n = len(self._seiten)
        for zustand in self._seiten:
            self.__dict__.update(zustand)
            self.setFont("Helvetica", 7)
            self.setFillColor(GRAU)
            self.setStrokeColor(LINIE)
            self.line(15 * mm, 12 * mm, A4[0] - 15 * mm, 12 * mm)
            self.drawString(15 * mm, 8 * mm, self._fuss)
            self.drawRightString(A4[0] - 15 * mm, 8 * mm, f"Seite {self._pageNumber} von {n}")
            super().showPage()
        super().save()


# Was das PDF enthält; der Anwender stellt es in den Einstellungen ein (Abschnitt „PDF-Export“).
PDF_STANDARD = {"struktur": True, "mengen": True, "einkauf": True, "filament": True,
                "kennzahlen": True, "bilder": True, "kaestchen": True, "pfade": True}


class Stueckliste:
    def __init__(self, baugruppen, optionen=None):
        self.opt = {**PDF_STANDARD, **{k: bool(v) for k, v in (optionen or {}).items() if k in PDF_STANDARD}}
        self.bg = baugruppen
        self.k = baugruppen.k
        self.b = baugruppen.k.b

    def _ok(self, gefuellt=False):
        return _kaestchen(gefuellt) if self.opt["kaestchen"] else ""

    def _bild(self, kurz, seite=11 * mm):
        if not self.opt["bilder"]:
            return ""
        pfad = None
        if kurz.get("bild"):
            pfad = self.k.bild_pfad(kurz["id"])
        elif kurz.get("hash"):
            pfad = self.k.vorschau_datei(kurz["hash"])
        if pfad and os.path.exists(pfad):
            # reportlab liest das Bild erst beim Zusammenbauen — ein kaputtes
            # eingebettetes Vorschaubild liesse dann das ganze PDF scheitern.
            # Deshalb vorher ganz lesen; was nicht geht, bleibt weg.
            try:
                from PIL import Image as PILBild
                with PILBild.open(pfad) as probe:
                    probe.load()
                return Image(pfad, width=seite, height=seite, kind="proportional")
            except Exception:
                return ""
        return ""

    # -- Strukturstückliste: rekursiv mit Positionsnummern

    def _struktur(self, bid, praefix, faktor, ebene, zeilen, stil, standard, pfad=()):
        if bid in pfad:
            return
        for i, (_, ziel, kante) in enumerate(self.bg._positionen(bid), 1):
            col, _, kid = ziel.partition("/")
            art = ARTEN[col]
            nr = f"{praefix}{i}"
            menge = kante.get("menge", 1)
            gesamt = menge * faktor
            einzug = "&nbsp;" * 3 * ebene
            zeile = len(zeilen)
            if art == "modell":
                kurz, d = self.bg._modell_daten(kid, kante.get("material"), kante.get("farbe"), standard)
                ort = next(iter((self.k.db.get_node(f"PART_GEOMETRY/{kurz['hash']}", readonly=True) or {}).get("orte", [])), None)
                pfadzeile = (f"<br/>{einzug}<font size='6.5' color='#888888'>{_esc(ort['pfad'] if ort else 'Datei fehlt')}</font>"
                             if self.opt["pfade"] else "")
                name = Paragraph(f"{einzug}{_esc(kurz['name'])}{pfadzeile}", S["zelle"])
                zeilen.append([nr, self._bild(kurz), name, str(menge), str(gesamt),
                               _material(d["material"], d["farbe"], d["material_angenommen"]),
                               Paragraph(f"{_zahl((d['gewicht_g'] or 0) * gesamt, 0)} g" + (" *" if d["geschaetzt"] else ""), S["rechts"]),
                               Paragraph(_dauer((d["zeit_s"] or 0) * gesamt) if d["zeit_s"] else "–", S["rechts"]),
                               self._ok(kante.get("erledigt", 0) >= gesamt)])
            elif art == "kaufteil":
                t = self.k.db.get_node(f"{KAUFTEIL}/{kid}", readonly=True)
                zeilen.append([nr, "", Paragraph(f"{einzug}{_esc(t['name'])}<br/>{einzug}<font size='6.5' color='#888888'>"
                                                 f"Kaufteil{' · ' + _esc(t['norm']) if t.get('norm') else ''}</font>", S["zelle"]),
                               str(menge), f"{gesamt}" + ("" if t.get("einheit", "Stück") == "Stück" else f" {t['einheit']}"), "", "", "",
                               self._ok(kante.get("erledigt", 0) >= gesamt)])
            else:
                u = self.k.db.get_node(ziel, readonly=True)
                zeilen.append([nr, "", Paragraph(f"{einzug}<b>{_esc(u['name'])}</b> <font size='6.5' color='#888888'>Baugruppe</font>",
                                                 S["zelle"]), str(menge), str(gesamt), "", "", "", ""])
                stil.append(("BACKGROUND", (0, zeile), (-1, zeile), HELL))
                self._struktur(kid, f"{nr}.", gesamt, ebene + 1, zeilen, stil, standard, (*pfad, bid))

    def pdf(self, bid):
        d = self.bg.detail(bid)
        s = d["summen"]
        f = d["fortschritt"]
        standard = self.bg.standard()
        heute = time.strftime("%d.%m.%Y")
        puffer = io.BytesIO()
        doc = SimpleDocTemplate(puffer, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                                topMargin=15 * mm, bottomMargin=18 * mm, title=f"Stückliste {d['name']}",
                                author="partAtlas", subject="Stückliste")
        breite = A4[0] - 30 * mm
        inhalt = []

        # -- Kopf
        titelbild = ""
        for p in d["positionen"]:
            if p["art"] == "modell":
                titelbild = self._bild({"id": p["id"], "hash": p.get("hash"), "vorschau": p.get("vorschau")}, 32 * mm)
                if titelbild:
                    break
        kopf = [Paragraph("STÜCKLISTE", S["kopf"]), Paragraph(_esc(d["name"]), S["titel"])]
        if d["beschreibung"]:
            kopf.append(Paragraph(_esc(d["beschreibung"]), S["unter"]))
        kopf.append(Paragraph(f"Stand {heute} · {f['druck_bedarf']} Druckteile, {f['kauf_bedarf']} Kaufteile"
                              + (f" · steckt in {', '.join(_esc(v['name']) for v in d['verwendet_in'])}" if d["verwendet_in"] else ""),
                              S["unter"]))
        t = Table([[kopf, titelbild]], colWidths=[breite - 36 * mm, 36 * mm])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        inhalt += [t, Spacer(1, 4 * mm)]

        # -- Kennzahlen
        if self.opt["kennzahlen"]:
            mat_kurz = ", ".join(f"{_zahl(m['gesamt_g'])} g {_esc(m['material'])}" for m in s["materialien"][:4]) or "–"
            kz = [[Paragraph("DRUCKTEILE", S["kopf"]), Paragraph("KAUFTEILE", S["kopf"]),
                   Paragraph("FILAMENT", S["kopf"]), Paragraph("DRUCKZEIT", S["kopf"])],
                  [Paragraph(f"{f['druck_bedarf']}", S["zahl"]), Paragraph(f"{f['kauf_bedarf']}", S["zahl"]),
                   Paragraph(f"{_zahl(s['gewicht_g'])} g", S["zahl"]), Paragraph(_dauer(s["zeit_s"]), S["zahl"])],
                  [Paragraph(f"Stück, {len({kid for art, kid, _, _ in self.bg._aufloesen(bid) if art == 'modell'})} verschiedene", S["klein"]),
                   Paragraph(f"Stück, {len(s['einkauf'])} verschiedene", S["klein"]),
                   Paragraph(mat_kurz + (" · * teils geschätzt" if s["gewicht_geschaetzt"] else ""), S["klein"]),
                   Paragraph(f"{s['ohne_zeit']} Teile ohne Slicer-Zeit" if s["ohne_zeit"] else "aus dem Slicer", S["klein"])]]
            t = Table(kz, colWidths=[breite / 4] * 4)
            t.setStyle(TableStyle([("BOX", (0, 0), (0, -1), 0.5, LINIE), ("BOX", (1, 0), (1, -1), 0.5, LINIE),
                                   ("BOX", (2, 0), (2, -1), 0.5, LINIE), ("BOX", (3, 0), (3, -1), 0.5, LINIE),
                                   ("BACKGROUND", (0, 0), (-1, -1), HELL), ("TOPPADDING", (0, 0), (-1, 0), 5),
                                   ("BOTTOMPADDING", (0, -1), (-1, -1), 6)]))
            inhalt += [t, Spacer(1, 2 * mm)]

        tabellenstil = [
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7), ("TEXTCOLOR", (0, 0), (-1, 0), GRAU),
            ("LINEBELOW", (0, 0), (-1, 0), 0.8, TINTE), ("LINEBELOW", (0, 1), (-1, -1), 0.3, LINIE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("FONT", (0, 1), (0, -1), "Helvetica-Bold", 8),
            ("FONT", (3, 1), (4, -1), "Helvetica", 8.5), ("ALIGN", (3, 0), (4, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]

        nr = iter(range(1, 5))
        ok = "OK" if self.opt["kaestchen"] else ""
        # -- 1 Strukturstückliste
        if self.opt["struktur"]:
            zeilen = [["POS.", "", "BENENNUNG / DATEI", "MENGE", "GESAMT", "MATERIAL", "GEWICHT", "DRUCKZEIT", ok]]
            stil = list(tabellenstil)
            self._struktur(bid, "", 1, 0, zeilen, stil, standard)
            inhalt.append(Paragraph(f"{next(nr)}  Strukturstückliste", S["h"]))
            inhalt.append(Paragraph("Menge je übergeordneter Einheit, Gesamt über alle Ebenen. "
                                    "Gewicht und Zeit gelten für die Gesamtmenge. * Gewicht ohne Slicer-Daten geschätzt.", S["klein"]))
            inhalt.append(Spacer(1, 2 * mm))
            t = Table(zeilen, colWidths=[12 * mm, 13 * mm, None, 13 * mm, 14 * mm, 25 * mm, 17 * mm, 19 * mm, 9 * mm], repeatRows=1)
            t.setStyle(TableStyle(stil))
            inhalt.append(t)

        # -- 2 Mengenübersicht Druckteile
        gesamt = {}
        for art, kid, kante, bedarf in self.bg._aufloesen(bid):
            if art != "modell":
                continue
            kurz, dd = self.bg._modell_daten(kid, kante.get("material"), kante.get("farbe"), standard)
            e = gesamt.setdefault((kid, dd["material"], dd["farbe"]),
                                  {"kurz": kurz, "d": dd, "menge": 0, "fertig": 0})
            e["menge"] += bedarf
            e["fertig"] += min(kante.get("erledigt", 0), bedarf)
        if gesamt and self.opt["mengen"]:
            zeilen = [["MENGE", "", "BENENNUNG", "MATERIAL", "GEWICHT", "DRUCKZEIT", "GEDRUCKT"]]
            for e in sorted(gesamt.values(), key=lambda e: e["kurz"]["name"].lower()):
                dd = e["d"]
                zeilen.append([f"{e['menge']}×", self._bild(e["kurz"], 9 * mm), Paragraph(_esc(e["kurz"]["name"]), S["zelle"]),
                               _material(dd["material"], dd["farbe"], dd["material_angenommen"]),
                               Paragraph(f"{_zahl((dd['gewicht_g'] or 0) * e['menge'])} g" + (" *" if dd["geschaetzt"] else ""), S["rechts"]),
                               Paragraph(_dauer((dd["zeit_s"] or 0) * e["menge"]) if dd["zeit_s"] else "–", S["rechts"]),
                               Paragraph(f"{e['fertig']} / {e['menge']}", S["rechts"])])
            t = Table(zeilen, colWidths=[13 * mm, 11 * mm, None, 28 * mm, 20 * mm, 22 * mm, 18 * mm], repeatRows=1)
            t.setStyle(TableStyle(tabellenstil + [("FONT", (0, 1), (0, -1), "Helvetica-Bold", 9), ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                                                  ("ALIGN", (3, 0), (4, -1), "LEFT")]))
            inhalt += [Paragraph(f"{next(nr)}  Mengenübersicht Druckteile", S["h"]),
                       Paragraph("Jedes Druckteil einmal, mit der Menge über alle Ebenen — das, was tatsächlich gedruckt wird.", S["klein"]),
                       Spacer(1, 2 * mm), t]

        # -- 3 Einkaufsliste
        if s["einkauf"] and self.opt["einkauf"]:
            zeilen = [["MENGE", "EINHEIT", "BENENNUNG", "KATEGORIE", ok]]
            for e in s["einkauf"]:
                t_node = self.k.db.get_node(f"{KAUFTEIL}/{e['id']}", readonly=True) or {}
                zeilen.append([str(e["bedarf"]), e["einheit"],
                               Paragraph(_esc(e["name"]) + (f" <font size='6.5' color='#888888'>{_esc(t_node.get('norm'))}</font>"
                                                            if t_node.get("norm") else ""), S["zelle"]),
                               Paragraph(_esc(e.get("kategorie") or ""), S["zelle"]), self._ok(e["offen"] == 0)])
            t = Table(zeilen, colWidths=[15 * mm, 16 * mm, None, 35 * mm, 9 * mm], repeatRows=1)
            t.setStyle(TableStyle(tabellenstil + [("FONT", (0, 1), (0, -1), "Helvetica-Bold", 9), ("FONT", (1, 1), (1, -1), "Helvetica", 8),
                                                  ("ALIGN", (0, 0), (1, -1), "LEFT")]))
            inhalt += [KeepTogether([Paragraph(f"{next(nr)}  Einkaufsliste Kaufteile", S["h"]),
                                     Paragraph("Über alle Ebenen zusammengezählt.", S["klein"]), Spacer(1, 2 * mm), t])]

        # -- 4 Filament
        if s["materialien"] and self.opt["filament"]:
            zeilen = [["MATERIAL", "FARBEN", "GESAMT", "ROLLEN"]]
            for m in s["materialien"]:
                farben = Table([[_tupfer(x["farbe"]), Paragraph(f"{_zahl(x['gesamt_g'])} g", S["zelle"])] for x in m["farben"]],
                               colWidths=[11, 40])
                farben.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 1),
                                            ("BOTTOMPADDING", (0, 0), (-1, -1), 1), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
                zeilen.append([Paragraph(f"<b>{_esc(m['material'])}</b>" + (f"<br/><font size='6.5' color='#888888'>davon {_zahl(m['angenommen_g'])} g Standard</font>"
                                                                            if m["angenommen_g"] else ""), S["zelle"]),
                               farben, Paragraph(f"<b>{_zahl(m['gesamt_g'])} g</b>", S["rechts"]),
                               Paragraph(f"{_zahl(m['rollen'], 2)} × {s['rolle_g']} g", S["rechts"])])
            t = Table(zeilen, colWidths=[35 * mm, None, 25 * mm, 30 * mm], repeatRows=1)
            t.setStyle(TableStyle(tabellenstil))
            inhalt += [KeepTogether([Paragraph(f"{next(nr)}  Filament", S["h"]), t])]

        fuss = f"partAtlas · Stückliste {d['name']} · Stand {heute}"
        doc.build(inhalt, canvasmaker=lambda *a, **k: _Seiten(*a, fuss=fuss, **k))
        return puffer.getvalue()
