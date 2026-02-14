#!/usr/bin/env python3
"""Gera nitro-boost-ib.png a partir do design do SVG (ventoinha verde/ciano)."""
from PIL import Image, ImageDraw
import math
import os

SIZE = 256
CENTER = SIZE // 2
BG = (13, 13, 18)
ACCENT = (0, 212, 170)
ACCENT_DIM = (0, 168, 132)

img = Image.new("RGBA", (SIZE, SIZE), (*BG, 255))
draw = ImageDraw.Draw(img)

# Fundo arredondado (retângulo com cantos)
draw.rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=56, fill=BG)

# 3 pás da ventoinha (elipses rotacionadas)
for i in range(3):
    angle = i * 120
    rad = math.radians(angle)
    # Elipse: centro em (0, -55) relativo, rx=18, ry=45
    cx = CENTER + 55 * math.sin(rad)
    cy = CENTER - 55 * math.cos(rad)
    # Desenhar elipse rotacionada (aproximação com polígono)
    pts = []
    for j in range(36):
        a = math.radians(j * 10 + angle)
        x = cx + 18 * math.cos(a)
        y = cy + 45 * math.sin(a)
        pts.append((x, y))
    draw.polygon(pts, fill=ACCENT, outline=ACCENT_DIM)

# Centro (hub)
draw.ellipse([CENTER - 28, CENTER - 28, CENTER + 28, CENTER + 28], fill=BG, outline=ACCENT_DIM)
draw.ellipse([CENTER - 14, CENTER - 14, CENTER + 14, CENTER + 14], fill=ACCENT)

out = os.path.join(os.path.dirname(__file__), "nitro-boost-ib.png")
img.save(out)
print(f"Icon saved: {out}")
