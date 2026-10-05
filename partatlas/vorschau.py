"""
Vorschaubilder ohne Grafikkarte.

Der 3MF Katalog rendert fehlende Vorschauen per WebGL in der Oberfläche —
auf alter Hardware ohne brauchbares WebGL entsteht dann kein Bild
(vermutete Ursache für „90 % ohne Bilder“, KONZEPT §1). Hier rendert der
Server mit numpy: kein WebGL, kein Fenster, läuft in einem Arbeitsprozess.

Verfahren: kleine Dreiecke werden mit Punkten abgetastet, grosse klassisch
über ihre Hülle gerastert; ein Tiefenpuffer entscheidet, was vorne liegt.
Gerendert wird doppelt so gross und dann verkleinert — das glättet Kanten
und schliesst die Lücken zwischen den Abtastpunkten.
"""
import io

import numpy as np
from PIL import Image

GROESSE = 320
FARBE = np.array([232, 122, 92], dtype=np.float32)   # Akzent wie im 3MF Katalog
MAX_DREIECKE = 400_000
GROSS_PX = 48          # ab dieser Fläche in Pixeln wird ein Dreieck gerastert


def _ansicht():
    # Isometrisch von vorne rechts oben, Z zeigt nach oben (Druckbett).
    a = np.radians(-45.0)
    rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    b = np.radians(-60.0)
    rx = np.array([[1, 0, 0], [0, np.cos(b), -np.sin(b)], [0, np.sin(b), np.cos(b)]])
    return rx @ rz


def farbe_aus_hex(text):
    """'#RRGGBB' oder '#RRGGBBAA' aus slice_info → RGB, sonst None."""
    t = (text or "").lstrip("#")
    if len(t) in (6, 8) and all(c in "0123456789abcdefABCDEF" for c in t):
        return np.array([int(t[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)
    return None


def rendere(netz, groesse=GROESSE, farbe=None):
    """PNG-Bytes mit transparentem Hintergrund, oder None ohne Dreiecke.
    `farbe`: '#RRGGBB' des ersten Filaments aus dem Slicer, sonst der Akzent."""
    if netz is None or len(netz) == 0:
        return None
    rnd = np.random.default_rng(0)
    if len(netz) > MAX_DREIECKE:
        netz = netz[rnd.choice(len(netz), MAX_DREIECKE, replace=False)]
    w = groesse * 2
    v = netz.astype(np.float64) @ _ansicht().T          # (n,3,3) Sicht
    punkte = v.reshape(-1, 3)
    mini, maxi = punkte.min(axis=0), punkte.max(axis=0)
    spanne = max(maxi[0] - mini[0], maxi[1] - mini[1], 1e-9)
    skala = (w * 0.9) / spanne
    mitte = (mini + maxi) / 2
    sx = (v[..., 0] - mitte[0]) * skala + w / 2
    sy = w / 2 - (v[..., 1] - mitte[1]) * skala
    tiefe = v[..., 2]

    normale = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0])
    laenge = np.linalg.norm(normale, axis=1)
    gueltig = laenge > 0
    normale[gueltig] /= laenge[gueltig, None]
    licht = np.array([0.35, 0.45, 0.82])
    licht /= np.linalg.norm(licht)
    # Zweiseitig: offene oder falsch orientierte Netze sollen nicht schwarz werden.
    hell = 0.28 + 0.72 * np.abs(normale @ licht)

    flaeche = 0.5 * np.abs((sx[:, 1] - sx[:, 0]) * (sy[:, 2] - sy[:, 0])
                           - (sx[:, 2] - sx[:, 0]) * (sy[:, 1] - sy[:, 0]))
    gross = (flaeche > GROSS_PX) & gueltig
    klein = ~gross & gueltig

    px, py, pz, pc = [], [], [], []

    # Kleine Dreiecke: Punkte mit gleichverteilten Baryzentrischen Koordinaten.
    idx = np.nonzero(klein)[0]
    if len(idx):
        k = np.clip(np.ceil(flaeche[idx] * 4.0).astype(np.int64) + 1, 1, 64)
        wer = np.repeat(idx, k)
        r1 = np.sqrt(rnd.random(len(wer)))
        r2 = rnd.random(len(wer))
        a, b, c = 1 - r1, r1 * (1 - r2), r1 * r2
        px.append(a * sx[wer, 0] + b * sx[wer, 1] + c * sx[wer, 2])
        py.append(a * sy[wer, 0] + b * sy[wer, 1] + c * sy[wer, 2])
        pz.append(a * tiefe[wer, 0] + b * tiefe[wer, 1] + c * tiefe[wer, 2])
        pc.append(hell[wer])

    # Grosse Dreiecke: jedes Pixel der Hülle prüfen. Das sind bei feinen
    # Netzen wenige, bei groben (Würfel: 12) wenige, aber grosse.
    for i in np.nonzero(gross)[0][:50_000]:
        x0, x1 = int(max(0, np.floor(sx[i].min()))), int(min(w - 1, np.ceil(sx[i].max())))
        y0, y1 = int(max(0, np.floor(sy[i].min()))), int(min(w - 1, np.ceil(sy[i].max())))
        if x1 < x0 or y1 < y0:
            continue
        # Ohne np.meshgrid: ein Zeilen- und ein Spaltenvektor genügen, NumPy rechnet sie beim Verknüpfen zum Gitter aus. Gleiche Werte,
        # aber ein Siebtel der Rechenzeit (gemessen am 5.10.2026 an 12 STL: 0,6 von 4,3 s liefen in meshgrid).
        gx, gy = (np.arange(x0, x1 + 1) + 0.5)[None, :], (np.arange(y0, y1 + 1) + 0.5)[:, None]
        (ax, bx, cx), (ay, by, cy) = sx[i], sy[i]
        d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(d) < 1e-12:
            continue
        l1 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / d
        l2 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / d
        l3 = 1 - l1 - l2
        drin = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
        if not drin.any():
            continue
        gxv, gyv = np.broadcast_arrays(gx, gy)
        px.append(gxv[drin])
        py.append(gyv[drin])
        pz.append(l1[drin] * tiefe[i, 0] + l2[drin] * tiefe[i, 1] + l3[drin] * tiefe[i, 2])
        pc.append(np.full(int(drin.sum()), hell[i]))

    if not px:
        return None
    px, py = np.concatenate(px), np.concatenate(py)
    pz, pc = np.concatenate(pz), np.concatenate(pc)
    ix = np.clip(px.astype(np.int64), 0, w - 1)
    iy = np.clip(py.astype(np.int64), 0, w - 1)
    pixel = iy * w + ix
    # Tiefenpuffer ohne Schleife: je Pixel der Punkt mit der grössten Tiefe
    # (zum Betrachter hin) gewinnt.
    reihe = np.lexsort((-pz, pixel))
    pixel, pc = pixel[reihe], pc[reihe]
    erste = np.ones(len(pixel), dtype=bool)
    erste[1:] = pixel[1:] != pixel[:-1]

    bild = np.zeros((w * w, 4), dtype=np.float32)
    grund = farbe_aus_hex(farbe)
    if grund is None:
        grund = FARBE
    # Sehr dunkles Filament (Schwarz) bekäme keine Schattierung mehr: anheben.
    grund = np.maximum(grund, 48)
    bild[pixel[erste], :3] = np.minimum(grund * pc[erste, None] * 1.1, 255)
    bild[pixel[erste], 3] = 255
    bild = bild.reshape(w, w, 4)
    # Punktlücken schliessen: ein leeres Pixel übernimmt einen belegten Nachbarn.
    leer = bild[..., 3] == 0
    for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0)):
        nachbar = np.roll(bild, (dy, dx), axis=(0, 1))
        fuellen = leer & (nachbar[..., 3] > 0)
        bild[fuellen] = nachbar[fuellen]
        leer &= ~fuellen

    img = Image.fromarray(bild.astype(np.uint8), "RGBA").resize((groesse, groesse), Image.LANCZOS)
    puffer = io.BytesIO()
    img.save(puffer, "PNG", optimize=True)
    return puffer.getvalue()
