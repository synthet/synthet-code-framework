"""Vendored from synthet/image-scoring-ui icons/render_icons.py at b6bcbc6 (canonical copy there).

Render a project's Synth-family app icon and favicons from its vector masters.

Generalised from synthet/zed ``script/apply_branding_icons.py`` (the renderer behind the Synth Zed and Warp
icons). A project keeps its masters in one folder:

- ``mark.svg``     1024 master: the family plate plus the project's silver mark (start from <skill-dir>/templates/mark-1024.svg)
- ``mark-32.svg``  optional hand-simplified master used at 24-32 px (templates/mark-32.svg)
- ``mark-16.svg``  optional hand-simplified master used at 16 px (templates/mark-16.svg)

Usage::

    uv run --with pillow python <skill-dir>/scripts/render_icons.py --masters <dir> --out <dir> [--tint #RRGGBB]
    uv run --with pillow python <skill-dir>/scripts/render_icons.py --check <dir>

Outputs in ``--out``: ``png/<size>.png`` for every family size, ``favicon.ico`` (16/32/48, BMP32),
``app.ico`` (16-128 BMP32 + 256 PNG, the layout Windows shortcuts and Inno Setup expect), ``favicon.svg``
(the 32 px master, so browsers scale a legible mark), ``apple-touch-icon.png`` (180) and
``icon-192.png`` / ``icon-512.png`` for a web manifest.

Requires ImageMagick 7 (``magick``) with SVG support. Rasterises at each target size instead of downscaling
from 1024, so small sizes keep their transparent margin.
"""

from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile

from PIL import Image

TOKENS = json.loads((Path(__file__).resolve().parent / "tokens.json").read_text(encoding="utf-8"))
PNG_SIZES = tuple(TOKENS["sizes"]["png"])
FAVICON_ICO_SIZES = tuple(TOKENS["sizes"]["favicon_ico"])
APP_ICO_SIZES = tuple(TOKENS["sizes"]["app_ico"])
SILVER_FILL = 'fill="url(#silver)"'
FLAT_FILL = f'fill="{TOKENS["glyph"]["flat_silver"]}"'


def source_for(masters: Path, size: int) -> Path:
    """Small sizes use hand-simplified geometry so strokes stay above one pixel."""
    if size <= 16 and (masters / "mark-16.svg").exists():
        return masters / "mark-16.svg"
    if size <= 32 and (masters / "mark-32.svg").exists():
        return masters / "mark-32.svg"
    return masters / "mark.svg"


def render_svg(source: Path, size: int, tint: str | None = None) -> Image.Image:
    magick = shutil.which("magick")
    if magick is None:
        raise SystemExit("ImageMagick 7 with SVG support is required (magick)")
    markup = source.read_text(encoding="utf-8")
    if tint:
        markup = markup.replace(SILVER_FILL, f'fill="{tint}"').replace(FLAT_FILL, f'fill="{tint}"')
    markup = markup.replace('width="1024" height="1024"', f'width="{size}" height="{size}"', 1)
    with tempfile.TemporaryDirectory(prefix="synth-icon-") as temporary:
        staged = Path(temporary) / source.name
        staged.write_text(markup, encoding="utf-8")
        result = subprocess.run([magick, "-background", "none", str(staged), "-strip", "png32:-"],
                                check=True, capture_output=True)
    image = Image.open(io.BytesIO(result.stdout)).convert("RGBA")
    if image.size != (size, size):
        raise SystemExit(f"{source} rendered at {image.size}, expected {size}x{size}")
    return image


def check_transparent_surround(image: Image.Image, label: str) -> None:
    """The plate is inset, so every canvas edge must be clear (no black frame on the Windows desktop)."""
    w, h = image.size
    for point in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (0, h // 2), (w // 2, 0), (w - 1, h // 2), (w // 2, h - 1)):
        if image.getpixel(point)[3] != 0:
            raise SystemExit(f"{label} is opaque at {point}; the surround must be clear")


def save_png(path: Path, image: Image.Image) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)


def read_ico_entries(path: Path) -> dict[tuple[int, int], tuple[bytes, bytes]]:
    data = path.read_bytes()
    reserved, image_type, count = struct.unpack_from("<HHH", data, 0)
    if reserved != 0 or image_type != 1:
        raise SystemExit(f"{path} is not a Windows icon")
    entries = {}
    for index in range(count):
        offset = 6 + index * 16
        width, height = data[offset] or 256, data[offset + 1] or 256
        size, payload_offset = struct.unpack_from("<II", data, offset + 8)
        entries[(width, height)] = (data[offset : offset + 8], data[payload_offset : payload_offset + size])
    return entries


def write_ico_entries(path: Path, entries: list[tuple[bytes, bytes]]) -> None:
    payload_offset = 6 + len(entries) * 16
    directory = bytearray(struct.pack("<HHH", 0, 1, len(entries)))
    payloads = bytearray()
    for metadata, payload in entries:
        directory.extend(metadata)
        directory.extend(struct.pack("<II", len(payload), payload_offset))
        payloads.extend(payload)
        payload_offset += len(payload)
    path.write_bytes(bytes(directory + payloads))


def save_ico(path: Path, frames: dict[int, Image.Image], sizes: tuple[int, ...]) -> None:
    """Frames below 256 px as BMP32 (ImageMagick), the 256 px frame as embedded PNG (Pillow)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    magick = shutil.which("magick")
    if magick is None:
        raise SystemExit("ImageMagick 7 is required to generate Windows icons")
    with tempfile.TemporaryDirectory(prefix="synth-icon-ico-") as temporary:
        tmp = Path(temporary)
        small = [s for s in sizes if s < 256]
        frame_paths = []
        for size in small:
            frame_path = tmp / f"{size}.png"
            save_png(frame_path, frames[size])
            frame_paths.append(str(frame_path))
        bitmap_entries = {}
        if frame_paths:
            bitmap_icon = tmp / "bitmap.ico"
            subprocess.run([magick, *frame_paths, str(bitmap_icon)], check=True)
            bitmap_entries = read_ico_entries(bitmap_icon)
        png_entries = {}
        if 256 in sizes:
            png_icon = tmp / "png.ico"
            frames[256].save(png_icon, format="ICO", sizes=[(256, 256)])
            png_entries = read_ico_entries(png_icon)
        combined = []
        for size in sizes:
            source = png_entries if size == 256 else bitmap_entries
            if (size, size) not in source:
                raise SystemExit(f"ICO generator omitted the {size}x{size} frame")
            combined.append(source[(size, size)])
        write_ico_entries(path, combined)


def check_ico(path: Path, expected_sizes: tuple[int, ...]) -> None:
    with Image.open(path) as icon:
        actual = icon.ico.sizes()
        if actual != {(s, s) for s in expected_sizes}:
            raise SystemExit(f"{path} contains {sorted(actual)}, expected {sorted(expected_sizes)}")
        for size in expected_sizes:
            check_transparent_surround(icon.ico.getimage((size, size)).convert("RGBA"), f"{path} {size}x{size}")
    data = path.read_bytes()
    for index in range(struct.unpack_from("<H", data, 4)[0]):
        offset = 6 + index * 16
        width = data[offset] or 256
        payload_offset = struct.unpack_from("<I", data, offset + 12)[0]
        is_png = data[payload_offset : payload_offset + 8] == b"\x89PNG\r\n\x1a\n"
        if is_png != (width == 256):
            raise SystemExit(f"{path} stores {width}px as {'PNG' if is_png else 'BMP32'}, "
                             f"expected {'PNG' if width == 256 else 'BMP32'}")
        if not is_png:
            header, depth = struct.unpack_from("<I", data, payload_offset)[0], struct.unpack_from("<H", data, payload_offset + 14)[0]
            if header != 40 or depth != 32:
                raise SystemExit(f"{path} stores {width}px as a {header}-byte, {depth}-bit DIB; expected BMP32")


def render(masters: Path, out: Path, tint: str | None) -> list[Path]:
    if not (masters / "mark.svg").exists():
        raise SystemExit(f"{masters / 'mark.svg'} is missing (start from <skill-dir>/templates/mark-1024.svg)")
    frames = {size: render_svg(source_for(masters, size), size, tint) for size in sorted(set(PNG_SIZES) | set(APP_ICO_SIZES))}
    written = []
    for size in PNG_SIZES:
        save_png(out / "png" / f"{size}.png", frames[size])
        written.append(out / "png" / f"{size}.png")
    for name, size in (("apple-touch-icon.png", 180), ("icon-192.png", 192), ("icon-512.png", 512)):
        save_png(out / name, frames[size])
        written.append(out / name)
    save_ico(out / "favicon.ico", frames, FAVICON_ICO_SIZES)
    save_ico(out / "app.ico", frames, APP_ICO_SIZES)
    svg_source = masters / "mark-32.svg" if (masters / "mark-32.svg").exists() else masters / "mark.svg"
    svg = svg_source.read_text(encoding="utf-8")
    if tint:
        svg = svg.replace(SILVER_FILL, f'fill="{tint}"').replace(FLAT_FILL, f'fill="{tint}"')
    (out / "favicon.svg").write_text(svg, encoding="utf-8")
    written += [out / "favicon.ico", out / "app.ico", out / "favicon.svg"]
    check(out)
    return written


def check(out: Path) -> None:
    for size in PNG_SIZES:
        with Image.open(out / "png" / f"{size}.png") as image:
            if image.size != (size, size):
                raise SystemExit(f"png/{size}.png is {image.size}")
            check_transparent_surround(image.convert("RGBA"), f"png/{size}.png")
    check_ico(out / "favicon.ico", FAVICON_ICO_SIZES)
    check_ico(out / "app.ico", APP_ICO_SIZES)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Render Synth-family app icons and favicons from vector masters.")
    p.add_argument("--masters", type=Path, help="folder with mark.svg [mark-32.svg] [mark-16.svg]")
    p.add_argument("--out", type=Path, help="output folder")
    p.add_argument("--tint", help="optional glyph tint (#RRGGBB), e.g. a release channel")
    p.add_argument("--check", type=Path, metavar="OUT", help="only verify an existing output folder")
    a = p.parse_args(argv)
    if a.check:
        check(a.check)
        print(f"Verified icons under {a.check}")
        return 0
    if not (a.masters and a.out):
        p.error("--masters and --out are required unless --check is given")
    written = render(a.masters, a.out, a.tint)
    print(f"Rendered and verified {len(written)} files under {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
