"""Draw the app icons: web/icon-192.png and web/icon-512.png.

    python scripts/make_icons.py

The mark is the depth glyph at about a third full: a paper disc on the night ground, water
rising from the bottom. Colours are the design tokens. No imaging library is needed: the
PNG is written with the standard library, so the icons can always be made again.
"""

import re
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
SAMPLES = 3                      # per side, for smooth edges
RADIUS = 0.30                    # of the icon's width: inside the 80% safe circle for maskable use
FILL = 0.36                      # how much of the disc is water


def token(name):
    css = (WEB / "tokens.css").read_text(encoding="utf-8")
    value = re.search(rf"--{name}:\s*#([0-9A-Fa-f]{{6}})", css).group(1)
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def pixel(x, y, size, colours):
    """The colour at one point, as an average of SAMPLES x SAMPLES samples."""
    night, paper, water = colours
    total = [0, 0, 0]
    for sy in range(SAMPLES):
        for sx in range(SAMPLES):
            u = (x + (sx + 0.5) / SAMPLES) / size - 0.5
            v = (y + (sy + 0.5) / SAMPLES) / size - 0.5
            if u * u + v * v <= RADIUS * RADIUS:
                waterline = RADIUS - 2 * RADIUS * FILL          # v of the water's surface
                colour = water if v >= waterline else paper
            else:
                colour = night
            for k in range(3):
                total[k] += colour[k]
    return bytes(round(t / (SAMPLES * SAMPLES)) for t in total)


def png(size, colours):
    rows = b"".join(b"\x00" + b"".join(pixel(x, y, size, colours) for x in range(size)) for y in range(size))

    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b""))


def main():
    colours = (token("night"), token("paper"), token("water"))
    for size in (192, 512):
        path = WEB / f"icon-{size}.png"
        path.write_bytes(png(size, colours))
        print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
