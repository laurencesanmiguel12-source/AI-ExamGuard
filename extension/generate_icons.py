"""Generates the extension's icon set (16/32/48/128px PNGs) - a solid crimson rounded-square
background with a white shield glyph, matching the main app's actual branding (Login.jsx's Shield
icon from lucide-react, --primary: #c8192e in frontend/src/index.css). Solid color + white
silhouette rather than the app's light-background/colored-icon treatment, since a light background
doesn't read clearly at 16px in a browser toolbar - this needs to work as a tiny icon first.

Draws everything at 4x the target size then downsamples (LANCZOS) for clean anti-aliased edges,
since PIL has no native vector/path rendering.

Usage: ../.venv/Scripts/python.exe generate_icons.py
"""
import os

from PIL import Image, ImageDraw

PRIMARY = (200, 25, 46)  # #c8192e, matches frontend/src/index.css's --primary exactly
WHITE = (255, 255, 255)
SIZES = (16, 32, 48, 128)
SUPERSAMPLE = 4
OUT_DIR = os.path.join(os.path.dirname(__file__), "icons")


def shield_polygon(w, h):
    """A simple, recognizable shield silhouette - flat top with a small notch, angled shoulders,
    tapering to a point at the bottom. Coordinates as fractions of (w, h)."""
    pts = [
        (0.50, 0.06),  # top point (little peak)
        (0.82, 0.16),  # right shoulder
        (0.82, 0.48),  # right side
        (0.50, 0.94),  # bottom point
        (0.18, 0.48),  # left side
        (0.18, 0.16),  # left shoulder
    ]
    return [(x * w, y * h) for x, y in pts]


def make_icon(size):
    s = size * SUPERSAMPLE
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded-square background
    radius = s * 0.22
    draw.rounded_rectangle([0, 0, s - 1, s - 1], radius=radius, fill=PRIMARY)

    # White shield glyph, inset a bit from the edges
    margin = s * 0.24
    inner_w, inner_h = s - 2 * margin, s - 2 * margin
    poly = [(x + margin, y + margin) for x, y in shield_polygon(inner_w, inner_h)]
    draw.polygon(poly, fill=WHITE)

    # A small crimson checkmark cut into the shield - echoes the app's "verified/guarded" idea
    # without needing to exactly match lucide's shield-check path.
    ck_w, ck_h = inner_w, inner_h
    ck = [
        (0.30 * ck_w + margin, 0.52 * ck_h + margin),
        (0.44 * ck_w + margin, 0.66 * ck_h + margin),
        (0.72 * ck_w + margin, 0.34 * ck_h + margin),
    ]
    draw.line(ck, fill=PRIMARY, width=max(2, int(s * 0.05)), joint="curve")

    return img.resize((size, size), Image.LANCZOS)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for size in SIZES:
        icon = make_icon(size)
        path = os.path.join(OUT_DIR, f"icon{size}.png")
        icon.save(path)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
