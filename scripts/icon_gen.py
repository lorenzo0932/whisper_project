#!/usr/bin/env python3
"""Genera PNG / iconset ICNS da SVG usando PyQt6.QtSvg.

Nessuna dipendenza esterna (niente cairosvg/pillow): gira con il python
del venv creato da build.py.

Uso:
    icon_gen.py png <svg> <out.png> <size>
    icon_gen.py iconset <svg> <iconset_dir>
"""

import os
import sys


def svg_to_png(svg_path, png_path, size):
    from PyQt6.QtGui import QImage, QPainter
    from PyQt6.QtSvg import QSvgRenderer

    renderer = QSvgRenderer(svg_path)
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    painter = QPainter(img)
    renderer.render(painter)
    painter.end()
    return img.save(png_path)


def main():
    if len(sys.argv) < 2:
        sys.exit("Uso: icon_gen.py png|iconset ...")

    mode = sys.argv[1]

    if mode == "png":
        svg, png, size = sys.argv[2], sys.argv[3], int(sys.argv[4])
        if not svg_to_png(svg, png, size):
            sys.exit(f"Errore: conversione fallita -> {png}")
        print(f"PNG creato: {png} ({size}x{size})")

    elif mode == "iconset":
        svg, iconset = sys.argv[2], sys.argv[3]
        os.makedirs(iconset, exist_ok=True)
        for px in (16, 32, 64, 128, 256, 512):
            svg_to_png(svg, os.path.join(iconset, f"icon_{px}x{px}.png"), px)
            svg_to_png(svg, os.path.join(iconset, f"icon_{px}x{px}@2x.png"), px * 2)
        print(f"Iconsetset creato: {iconset}")

    else:
        sys.exit(f"Modalita' sconosciuta: {mode}")


if __name__ == "__main__":
    main()
