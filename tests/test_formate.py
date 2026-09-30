"""Die Leser: was sie aus einer Datei holen, und dass eine kaputte Datei
einen FormatFehler wirft statt den Scan anzuhalten."""
import os
import tempfile

import muster
from muster import check
from partatlas import formate, vorschau

d = tempfile.mkdtemp()

muster.stl_binaer(os.path.join(d, "b.stl"))
a = formate.analysiere(os.path.join(d, "b.stl"))
check("Binäres STL: Masse 10 × 20 × 30 mm, obwohl der Kopf mit „solid“ beginnt", a.masse_mm == [10.0, 20.0, 30.0])
check("Binäres STL: Volumen 6 cm³ aus dem geschlossenen Netz", a.volumen_cm3 == 6.0)
check("Binäres STL: 12 Dreiecke", a.dreiecke == 12)
check("Binäres STL: Oberfläche 22 cm² (für die Gewichtsschätzung)", a.flaeche_cm2 == 22.0)

muster.stl_ascii(os.path.join(d, "a.stl"))
a = formate.analysiere(os.path.join(d, "a.stl"))
check("ASCII-STL: gleiche Masse und gleiches Volumen", a.masse_mm == [10.0, 20.0, 30.0] and a.volumen_cm3 == 6.0)

muster.obj(os.path.join(d, "q.obj"))
a = formate.analysiere(os.path.join(d, "q.obj"))
check("OBJ mit Vierecken und v/vt/vn-Indizes: 12 Dreiecke, Volumen 6 cm³", a.dreiecke == 12 and a.volumen_cm3 == 6.0)

muster.dreimf(os.path.join(d, "p.3mf"))
a = formate.analysiere(os.path.join(d, "p.3mf"))
check("3MF: Komponenten aus 3D/Objects werden aufgelöst (2 × 12 Dreiecke)", a.dreiecke == 24)
check("3MF: Transformationen von Build und Komponente wirken (30 × 10 × 20 mm)", a.masse_mm == [30.0, 10.0, 20.0])
check("3MF: Volumen 1 + 2 cm³", a.volumen_cm3 == 3.0)
check("3MF: zwei Objekte im Build", a.objekte == 2)
check("3MF: Titel und Designer aus den Metadaten", (a.titel, a.designer) == ("Quader-Paar", "Tester"))
check("3MF: eingebettetes Vorschaubild über _rels gefunden", a.vorschau_png == muster.PNG_1PX)
check("3MF: zwei Platten mit Gewicht aus slice_info.config",
      [p["gewicht_g"] for p in a.platten] == [12.5, 3.25])
check("3MF: Filamenttyp und Grammzahl je Platte", a.platten[0]["filamente"][0]["typ"] == "PETG"
      and a.platten[0]["filamente"][0]["g"] == 12.5)

muster.dreimf(os.path.join(d, "bambu.3mf"), vorschau_als_platte=True)
a = formate.analysiere(os.path.join(d, "bambu.3mf"))
check("3MF ohne Vorschau-Verweis: Metadata/plate_1.png wird gefunden (der 3MF Katalog findet es nicht)",
      a.vorschau_png == muster.PNG_1PX)

muster.step(os.path.join(d, "w.step"))
a = formate.analysiere(os.path.join(d, "w.step"))
check("STEP: aufgenommen ohne Geometrie, Titel aus dem Kopf", a.format == "step" and a.titel == "Welle" and a.masse_mm is None)

for name, inhalt in [("kaputt.stl", b"\x00" * 90), ("kaputt.3mf", b"PK kein zip"), ("leer.obj", b"# nichts\n")]:
    with open(os.path.join(d, name), "wb") as f:
        f.write(inhalt)
    try:
        formate.analysiere(os.path.join(d, name))
        check(f"{name}: kaputte Datei wirft FormatFehler", False)
    except formate.FormatFehler:
        check(f"{name}: kaputte Datei wirft FormatFehler", True)

a = formate.analysiere(os.path.join(d, "b.stl"), mit_netz=True)
png = vorschau.rendere(a.netz)
check("Vorschau: rendert ohne Grafikkarte ein PNG", png is not None and png[:8] == b"\x89PNG\r\n\x1a\n")
from PIL import Image
import io
bild = Image.open(io.BytesIO(png))
alpha = bild.getchannel("A")
check("Vorschau: Modell sichtbar (deckend) und Hintergrund durchsichtig",
      alpha.getpixel((bild.width // 2, bild.height // 2)) == 255 and alpha.getpixel((0, 0)) == 0)

muster.ende()
