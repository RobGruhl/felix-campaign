#!/usr/bin/env python3
"""Extract full text from Campaign Events PDF into part files."""
import fitz  # pymupdf
import re
from pathlib import Path

# (book, part, slug, start_chapter, end_chapter)
PARTS = [
    (1, 1, "shared-curse", 1, 10),
    (1, 2, "journey-west", 11, 19),
    (1, 3, "silneas", 20, 27),
    (1, 4, "golden-wizard", 28, 36),
    (1, 5, "death", 37, 46),
    (2, 6, "city-of-demons", 47, 57),
    (2, 7, "into-the-woods", 58, 65),
    (2, 8, "regroup-north", 66, 72),
    (2, 9, "city-of-angels", 73, 80),
    (2, 10, "peeking-day", 81, 84),
    (3, 11, "dwarf-lands", 85, 90),
    (3, 12, "say-no-slavery", 91, 97),
    (3, 13, "nightmare", 98, 107),
    (3, 14, "ice-age", 108, 114),
    (3, 15, "siege", 115, 134),
    (4, 16, "heading-north", 135, 141),
]

# Paths relative to project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
PDF_PATH = PROJECT_ROOT / "Campaign Events (1).pdf"
OUTPUT_DIR = PROJECT_ROOT / "source-docs"


def extract_all_text(pdf_path: Path) -> str:
    """Extract text from entire PDF."""
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


def find_chapter_starts(text: str) -> dict[int, int]:
    """Find position of each 'Chapter N' marker."""
    pattern = r'\bChapter\s+(\d+)\b'
    positions = {}
    for match in re.finditer(pattern, text, re.IGNORECASE):
        chapter_num = int(match.group(1))
        # Only record first occurrence of each chapter
        if chapter_num not in positions:
            positions[chapter_num] = match.start()
    return positions


def extract_part_text(text: str, chapter_positions: dict, start_ch: int, end_ch: int) -> str:
    """Extract text for chapters start_ch through end_ch."""
    start_pos = chapter_positions.get(start_ch, 0)
    # End at next chapter after end_ch, or end of text
    next_ch = end_ch + 1
    end_pos = chapter_positions.get(next_ch, len(text))
    return text[start_pos:end_pos].strip()


def main():
    print(f"Reading PDF: {PDF_PATH}")
    if not PDF_PATH.exists():
        print(f"ERROR: PDF not found at {PDF_PATH}")
        return

    text = extract_all_text(PDF_PATH)
    print(f"Extracted {len(text)} characters from PDF")

    chapter_positions = find_chapter_starts(text)
    print(f"Found {len(chapter_positions)} chapter markers")

    # Debug: show which chapters were found
    found_chapters = sorted(chapter_positions.keys())
    print(f"Chapters found: {found_chapters[:10]}...{found_chapters[-5:]}")

    OUTPUT_DIR.mkdir(exist_ok=True)

    for book, part, slug, start_ch, end_ch in PARTS:
        part_text = extract_part_text(text, chapter_positions, start_ch, end_ch)

        # Create markdown with header
        filename = f"book{book}-part{part}-{slug}-full.md"
        header = f"# Book {book}, Part {part}: Full Text (Chapters {start_ch}-{end_ch})\n\n"

        output_path = OUTPUT_DIR / filename
        output_path.write_text(header + part_text)
        print(f"Created {filename} ({len(part_text)} chars)")

    print("\nDone! Created 16 full-text files in source-docs/")


if __name__ == "__main__":
    main()
