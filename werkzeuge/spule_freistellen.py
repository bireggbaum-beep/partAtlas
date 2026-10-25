"""Aus dem KI-Bild der Spule: ein freigestelltes PNG (Hintergrund durchsichtig, Schatten als weicher Schwarzton) und eine Maske für Wicklung und Aussparungen.
Eingefärbt wird später per CSS (Multiplizieren mit dem Farbwert der Spule)."""
import base64
import collections
import io

from PIL import Image, ImageFilter

QUELLE = "spule-quelle.png"          # das Originalbild (KI-erzeugt, weisser Hintergrund); nicht im Repo
AUS = "partatlas/web/"

im = Image.open(QUELLE).convert("RGB")
w, h = im.size
px = im.load()
lum = lambda p: (0.2126 * p[0] + 0.7152 * p[1] + 0.0722 * p[2])
nahweiss = lambda p: p[0] >= 244 and p[1] >= 244 and p[2] >= 244

# 1. Hintergrund: fast weisse Pixel, die vom Rand aus zusammenhängen
aussen = [[False] * w for _ in range(h)]
q = collections.deque()
for x in range(w):
    for y in (0, h - 1):
        if nahweiss(px[x, y]):
            aussen[y][x] = True
            q.append((x, y))
for y in range(h):
    for x in (0, w - 1):
        if nahweiss(px[x, y]) and not aussen[y][x]:
            aussen[y][x] = True
            q.append((x, y))
while q:
    x, y = q.popleft()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        a, b = x + dx, y + dy
        if 0 <= a < w and 0 <= b < h and not aussen[b][a] and nahweiss(px[a, b]):
            aussen[b][a] = True
            q.append((a, b))

# 2. Schatten: die graue Fläche unten, ausserhalb der schwarzen Flansche
def schatten(x, y):
    p = px[x, y]
    return y > 283 and 150 < lum(p) < 244 and abs(p[0] - p[1]) < 10 and abs(p[1] - p[2]) < 14

# Pixel, die höchstens zwei Pixel vom Hintergrund entfernt liegen
from PIL import ImageChops
aussenbild = Image.new("L", (w, h), 0)
aussenbild.putdata([255 if aussen[y][x] else 0 for y in range(h) for x in range(w)])
nahbild = aussenbild.filter(ImageFilter.MaxFilter(5))
nah = [[nahbild.getpixel((x, y)) > 0 for x in range(w)] for y in range(h)]

out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
maske = Image.new("L", (w, h), 0)
o, m = out.load(), maske.load()
for y in range(h):
    for x in range(w):
        p = px[x, y]
        if aussen[y][x]:
            continue
        if schatten(x, y):
            o[x, y] = (0, 0, 0, int((255 - lum(p)) * 0.55))       # weicher Schatten statt grauer Fläche
            continue
        o[x, y] = (p[0], p[1], p[2], 255)
        # Wicklung und Aussparungen: helle, unbunte Pixel im Inneren; die Kanten laufen weich aus
        l = lum(p)
        bunt = max(p) - min(p)
        if l > 120 and bunt < 40 and not (nah[y][x] and l < 236):         # Randpixel (Kantenglättung gegen das Weiss) bleiben ungefärbt
            m[x, y] = max(0, min(255, int((l - 120) * 255 / 70)))

# Fransen am Rand des Bildes: helle Randpixel neben dem Hintergrund durchsichtig machen, damit auf dunklem Grund kein weisser Saum bleibt
rand = []
for y in range(1, h - 1):
    for x in range(1, w - 1):
        if aussen[y][x]:
            continue
        if any(aussen[y + dy][x + dx] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))) and lum(px[x, y]) > 215 and not schatten(x, y):
            rand.append((x, y))
for x, y in rand:
    if maske.getpixel((x, y)) == 0 or lum(px[x, y]) > 238:
        o[x, y] = (o[x, y][0], o[x, y][1], o[x, y][2], 120)

out.save(AUS + "spule.png", optimize=True)
weiss = Image.new("RGBA", (w, h), (255, 255, 255, 0))
weiss.putalpha(maske.filter(ImageFilter.GaussianBlur(0.4)))
weiss.save(AUS + "spule-wicklung.png", optimize=True)
for n in ("spule.png", "spule-wicklung.png"):
    print(n, len(open(AUS + n, "rb").read()), "Byte")
