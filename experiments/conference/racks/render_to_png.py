#!/usr/bin/env python3
"""
SVG to PNG Renderer
Converts SVG files to high-quality PNG images.
Run: python render_to_png.py [scale_factor]
Default scale: 5.0 (500%)
"""

import os
import sys
import glob
import re

try:
    import cairosvg
except ImportError:
    print("❌ cairosvg not installed. Install with: pip install cairosvg")
    sys.exit(1)


def preprocess_svg(svg_content):
    """Preprocess SVG to handle fonts and special characters better."""
    # Replace monospace font with sans-serif for better rendering
    svg_content = svg_content.replace(
        'font-family="monospace"', 'font-family="Arial, sans-serif"'
    )

    # Replace monospace font-family in style tags if present
    svg_content = re.sub(
        r"font-family:\s*monospace", "font-family: Arial, sans-serif", svg_content
    )

    return svg_content


def render_svg_to_png(svg_file, scale=5.0):
    """Convert SVG to PNG with given scale factor."""
    if not os.path.exists(svg_file):
        print(f"❌ File not found: {svg_file}")
        return False

    output_file = svg_file.replace(".svg", ".png")

    try:
        # Read and preprocess the SVG
        with open(svg_file, "r") as f:
            svg_content = f.read()

        svg_content = preprocess_svg(svg_content)

        # Render the processed SVG
        cairosvg.svg2png(
            bytestring=svg_content.encode("utf-8"), write_to=output_file, scale=scale
        )
        print(f"✓ Rendered {svg_file} → {output_file} (scale: {scale}x)")
        return True
    except Exception as e:
        print(f"❌ Error rendering {svg_file}: {e}")
        return False


def main():
    scale = 5.0

    if len(sys.argv) > 1:
        try:
            scale = float(sys.argv[1])
        except ValueError:
            print(f"Invalid scale factor: {sys.argv[1]}")
            sys.exit(1)

    # Find all SVG files ending with _out.svg
    svg_files = sorted(glob.glob("*_out.svg"))

    if not svg_files:
        print("No *_out.svg files found in current directory")
        sys.exit(1)

    print(f"Rendering {len(svg_files)} SVG file(s) with scale {scale}x...\n")

    success_count = 0
    for svg_file in svg_files:
        if render_svg_to_png(svg_file, scale):
            success_count += 1

    print(f"\n✓ Successfully rendered {success_count}/{len(svg_files)} files")


if __name__ == "__main__":
    main()
