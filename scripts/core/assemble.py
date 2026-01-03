#!/usr/bin/env python3
"""
Page assembly and CBZ creation for Graphic Novels.
Assembles selected panel images into full pages and packages as CBZ.
"""

import sys
import json
import zipfile
import argparse
from pathlib import Path
from PIL import Image

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from utilities.layout_engine import (
    assemble_page_with_layout,
    PAGE_WIDTH,
    PAGE_HEIGHT
)

# Configuration - paths relative to project root
PAGES_JSON_DIR = Path("data/pages")
OUTPUT_DIR = Path("output")
PANELS_DIR = OUTPUT_DIR / "panels"
PAGES_DIR = OUTPUT_DIR / "pages"
CBZ_FILE = OUTPUT_DIR / "comic.cbz"

# Simplified system: only 2 layouts
# - Splash: 1 panel (full page)
# - Grid 2x2: 4 panels (or fewer)


def setup_directories():
    """Create output directory structure."""
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Created output directories")


def load_page_data(page_num):
    """Load page data from JSON file."""
    # Handle cover page (page 0)
    if page_num == 0:
        page_file = PAGES_JSON_DIR / "cover.json"
    else:
        page_file = PAGES_JSON_DIR / f"page-{page_num:03d}.json"

    if not page_file.exists():
        raise FileNotFoundError(f"Page file not found: {page_file}")

    with open(page_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def list_available_pages():
    """List all available page JSON files."""
    if not PAGES_JSON_DIR.exists():
        return []

    page_files = sorted(PAGES_JSON_DIR.glob("page-*.json"))
    pages = []

    for page_file in page_files:
        with open(page_file, 'r', encoding='utf-8') as f:
            page_data = json.load(f)
            pages.append(page_data)

    return pages


def cleanup_variants(page_num, panels):
    """Delete variant files for a page after successful assembly."""
    deleted_count = 0

    for panel in panels:
        # Find all variant files (page-XXX-panel-X-v*.png)
        pattern = f"page-{page_num:03d}-panel-{panel['panel_num']}-v*.png"
        variant_files = list(PANELS_DIR.glob(pattern))

        for variant_file in variant_files:
            try:
                variant_file.unlink()
                deleted_count += 1
            except Exception as e:
                print(f"  Warning: Could not delete {variant_file.name}: {e}")

    if deleted_count > 0:
        print(f"  Cleaned up {deleted_count} variant file(s)")

    return deleted_count


def assemble_page(page_data, cleanup=False):
    """Assemble panels into a page using simplified layout system."""

    page_num = page_data['page_num']
    panels = page_data['panels']
    num_panels = len(panels)

    layout_type = "splash" if num_panels == 1 else "2x2 grid"
    print(f"\n-> Assembling page {page_num} ({num_panels} panels, {layout_type})...")

    # Check if all panels have been selected
    missing_panels = []
    for panel in panels:
        panel_file = PANELS_DIR / f"page-{page_num:03d}-panel-{panel['panel_num']}.png"
        if not panel_file.exists():
            missing_panels.append(panel['panel_num'])

    if missing_panels:
        print(f"  Error: Missing selected panels: {missing_panels}")
        print(f"  Run review.py to select variants first")
        return None

    # Load panel images (all 1024x1536 portrait)
    panel_images = []
    for panel in panels:
        panel_file = PANELS_DIR / f"page-{page_num:03d}-panel-{panel['panel_num']}.png"
        if panel_file.exists():
            panel_images.append(Image.open(panel_file))
        else:
            # Create placeholder if missing
            placeholder = Image.new('RGB', (1024, 1536), 'gray')
            panel_images.append(placeholder)

    # Use simplified layout engine
    page_img = assemble_page_with_layout(
        panels_data=panels,
        panel_images=panel_images,
        page_width=PAGE_WIDTH,
        page_height=PAGE_HEIGHT
    )

    # Save page
    output_file = PAGES_DIR / f"page-{page_num:03d}.png"
    page_img.save(output_file)
    print(f"Saved {output_file.name} (1600x2400)")

    # Cleanup variants if requested
    if cleanup:
        cleanup_variants(page_num, panels)

    return output_file


def create_cbz(pages_data, output_file=None, title="Graphic Novel", series="Graphic Novel"):
    """Create CBZ file from assembled pages."""

    if output_file is None:
        output_file = CBZ_FILE

    print("\n-> Creating CBZ archive...")

    # ComicInfo.xml metadata
    comic_info = f"""<?xml version="1.0"?>
<ComicInfo xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <Title>{title}</Title>
  <Series>{series}</Series>
  <Number>1</Number>
  <Summary>An AI-generated graphic novel.</Summary>
  <Publisher>AI-Generated</Publisher>
  <Genre>Fantasy</Genre>
  <PageCount>{len(pages_data)}</PageCount>
  <LanguageISO>en</LanguageISO>
</ComicInfo>"""

    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as cbz:
        # Add ComicInfo.xml
        cbz.writestr('ComicInfo.xml', comic_info)

        # Add pages in order
        for page in sorted(pages_data, key=lambda p: p['page_num']):
            page_file = PAGES_DIR / f"page-{page['page_num']:03d}.png"
            if page_file.exists():
                # CBZ readers expect sequential numbering
                cbz.write(page_file, f"{page['page_num']:03d}.png")

    print(f"Created {output_file}")
    print(f"\nComic complete! Open {output_file} in any CBZ reader.")


def parse_page_range(page_arg):
    """Parse page argument (e.g., '1', '1-5', '1,3,5')."""
    pages = []

    for part in page_arg.split(','):
        if '-' in part:
            start, end = part.split('-')
            pages.extend(range(int(start), int(end) + 1))
        else:
            pages.append(int(part))

    return sorted(set(pages))


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description='Assemble comic pages and create CBZ archive',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python assemble.py 1                    # Assemble page 1 only
  python assemble.py 1-5                  # Assemble pages 1-5
  python assemble.py                      # Assemble all available pages
  python assemble.py 1 --no-cbz           # Assemble page without creating CBZ
  python assemble.py 1 --cleanup-variants # Assemble and delete variant files
        """
    )

    parser.add_argument(
        'pages',
        type=str,
        nargs='?',
        help='Page number(s) to assemble (e.g., 1, 1-5, 1,3,5). Omit to assemble all.'
    )

    parser.add_argument(
        '--no-cbz',
        action='store_true',
        help='Skip CBZ creation (only assemble pages)'
    )

    parser.add_argument(
        '--output',
        type=str,
        help='Custom CBZ output filename'
    )

    parser.add_argument(
        '--title',
        type=str,
        default='Graphic Novel',
        help='Title for the CBZ metadata'
    )

    parser.add_argument(
        '--cleanup-variants',
        action='store_true',
        help='Delete variant files (v1, v2, etc.) after successful assembly'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("GRAPHIC NOVEL PAGE ASSEMBLY")
    print("=" * 60)

    setup_directories()

    # Determine which pages to assemble
    if args.pages:
        try:
            page_nums = parse_page_range(args.pages)
        except ValueError:
            print(f"Invalid page argument: {args.pages}")
            print(f"  Use format like: 1, 1-5, or 1,3,5")
            sys.exit(1)

        pages_data = []
        for page_num in page_nums:
            try:
                page_data = load_page_data(page_num)
                pages_data.append(page_data)
            except FileNotFoundError as e:
                print(f"Error: {e}")
                sys.exit(1)
    else:
        # Assemble all available pages
        pages_data = list_available_pages()
        if not pages_data:
            print("No page JSON files found")
            print("  Create page JSON files in data/pages/ first")
            sys.exit(1)

        page_nums = [p['page_num'] for p in pages_data]

    print(f"\n-> Assembling {len(pages_data)} page(s): {page_nums}")

    # Assemble pages
    print("\n" + "=" * 60)
    print("ASSEMBLING PAGES")
    print("=" * 60)

    assembled_pages = []
    for page_data in pages_data:
        result = assemble_page(page_data, cleanup=args.cleanup_variants)
        if result:
            assembled_pages.append(page_data)

    if not assembled_pages:
        print("\nNo pages were assembled successfully")
        sys.exit(1)

    # Create CBZ
    if not args.no_cbz:
        print("\n" + "=" * 60)
        print("PACKAGING CBZ")
        print("=" * 60)

        output_file = Path(args.output) if args.output else CBZ_FILE
        create_cbz(assembled_pages, output_file, title=args.title)
    else:
        print(f"\nAssembled {len(assembled_pages)} page(s) successfully")
        print("  Skipped CBZ creation (--no-cbz flag)")


if __name__ == "__main__":
    main()
