"""Generate PWA icons from SVG source at multiple sizes."""

import sys
from pathlib import Path

SVG_SOURCE = Path(__file__).resolve().parent.parent / "public" / "icons" / "timer-icon.svg"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "public" / "icons"

ICONS = [
    ("icon-192.png", 192),
    ("icon-512.png", 512),
    ("apple-touch-icon.png", 180),
]


def convert_svg_to_png(svg_path: Path, png_path: Path, size: int) -> None:
    try:
        from PIL import Image
    except ImportError:
        print("Pillow not found. Install with: pip install Pillow")
        sys.exit(1)

    try:
        import io
        try:
            import cairosvg
            svg_data = svg_path.read_bytes()
            png_data = cairosvg.svg2png(
                bytestring=svg_data, output_width=size, output_height=size
            )
            img = Image.open(io.BytesIO(png_data))
        except ImportError:
            img = Image.open(svg_path)
            img = img.resize((size, size), Image.LANCZOS)

        png_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(png_path, "PNG")
        print(f"  [OK] {png_path.name} ({size}x{size}) — {png_path.stat().st_size} bytes")

    except Exception as exc:
        print(f"  [FAIL] {png_path.name}: {exc}")
        raise


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not SVG_SOURCE.exists():
        print(f"SVG source not found: {SVG_SOURCE}")
        sys.exit(1)

    print(f"Generating icons from: {SVG_SOURCE}")
    print()

    for filename, size in ICONS:
        png_path = OUTPUT_DIR / filename
        convert_svg_to_png(SVG_SOURCE, png_path, size)

    print()
    print(f"Done. Generated {len(ICONS)}/{len(ICONS)} icons.")


if __name__ == "__main__":
    main()
