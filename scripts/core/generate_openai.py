#!/usr/bin/env python3
"""
OpenAI image generator with rate limiting.
Generates multiple variants per panel for selection.
"""

import os
import sys
import json
import base64
import asyncio
import argparse
import logging
from pathlib import Path
from openai import AsyncOpenAI
from PIL import Image, ImageDraw
from dotenv import load_dotenv
import aiofiles
from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception_type
)
from openai import RateLimitError, APIError
import time as time_module

# Load environment variables
load_dotenv()

# Configuration - paths relative to project root
PAGES_JSON_DIR = Path("data/pages")
OUTPUT_DIR = Path("output")
PANELS_DIR = OUTPUT_DIR / "panels"
PAGES_DIR = OUTPUT_DIR / "pages"
CHARACTERS_DB_PATH = Path("data/characters.json")
LOCATIONS_DB_PATH = Path("data/locations.json")
STYLE_DB_PATH = Path("data/style.json")

# Rate limiting settings
MAX_CONCURRENT = int(os.getenv('MAX_CONCURRENT', 20))
MAX_RPM = int(os.getenv('MAX_RPM', 50))
VARIANTS_PER_PANEL = 3  # Number of variants to generate per panel

# Image generation settings
PANEL_WIDTH = 1024
PANEL_HEIGHT = 1024

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class RPMLimiter:
    """Token bucket rate limiter for requests per minute."""

    def __init__(self, max_per_minute):
        self.max_per_minute = max_per_minute
        self.capacity = float(max_per_minute)
        self.last_update = time_module.time()
        self.lock = asyncio.Lock()

    async def acquire(self):
        async with self.lock:
            now = time_module.time()
            elapsed = now - self.last_update
            self.capacity = min(
                self.capacity + (self.max_per_minute * elapsed / 60.0),
                self.max_per_minute
            )
            self.last_update = now

            while self.capacity < 1.0:
                await asyncio.sleep(0.1)
                now = time_module.time()
                elapsed = now - self.last_update
                self.capacity = min(
                    self.capacity + (self.max_per_minute * elapsed / 60.0),
                    self.max_per_minute
                )
                self.last_update = now

            self.capacity -= 1.0


# Global rate limiters
semaphore = asyncio.Semaphore(MAX_CONCURRENT)
rpm_limiter = RPMLimiter(MAX_RPM)


def setup_directories():
    """Create output directory structure."""
    PANELS_DIR.mkdir(parents=True, exist_ok=True)
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Created output directories")


def load_database(path, name):
    """Load a JSON database file."""
    if not path.exists():
        logger.warning(f"{name} database not found at {path}")
        return {}
    with open(path, 'r') as f:
        data = json.load(f)
        data.pop('_schema', None)
        return data


def load_character_database():
    return load_database(CHARACTERS_DB_PATH, "Character")


def load_location_database():
    return load_database(LOCATIONS_DB_PATH, "Location")


def load_style_database():
    return load_database(STYLE_DB_PATH, "Style")


def build_location_prompt_section(location_name, locations_db):
    """Build detailed location description for prompt."""
    loc = locations_db.get(location_name)
    if not loc:
        logger.warning(f"Location '{location_name}' not found in database")
        return f"Location: {location_name} [LOCATION NOT IN DATABASE]"

    desc_components = loc.get('description_components', {})
    if desc_components and len(desc_components) > 1:
        parts = [f"Location: {loc['name']}"]
        for key in ['location_context', 'architecture', 'key_features', 'atmosphere', 'lighting_magic', 'lighting']:
            if desc_components.get(key):
                parts.append(desc_components[key])
        return " ".join(parts)
    else:
        desc = loc.get('full_description', loc.get('description', ''))
        return f"Location: {loc['name']}\n{desc}"


def build_character_prompt_section(char_name, characters_db):
    """Build detailed character description for prompt."""
    char = characters_db.get(char_name)
    if not char:
        logger.warning(f"Character '{char_name}' not found in database")
        return f"- {char_name}: [CHARACTER NOT IN DATABASE]"

    desc_components = char.get('description_components', {})
    if desc_components and len(desc_components) > 1:
        parts = [f"- {char_name}:"]
        if desc_components.get('head_face'):
            parts.append(f"  HEAD/FACE: {desc_components['head_face']}")
        if desc_components.get('body_build'):
            parts.append(f"  BUILD: {desc_components['body_build']}")
        if desc_components.get('armor_clothing') or desc_components.get('clothing'):
            parts.append(f"  CLOTHING: {desc_components.get('armor_clothing') or desc_components.get('clothing')}")
        if desc_components.get('accessories'):
            parts.append(f"  ACCESSORIES: {desc_components['accessories']}")
        return "\n".join(parts)
    else:
        desc = char.get('full_description', '')
        return f"- {char_name}: {desc}"


def assemble_prompt(panel_data, characters_db, locations_db, style_db=None):
    """
    Dynamically assemble prompt from panel data and reference databases.

    Character descriptions embedded in panel_data take priority over database lookups.
    """
    parts = []

    # Base style
    if style_db and 'comic_aesthetic' in style_db:
        aesthetic = style_db['comic_aesthetic']
        parts.append(aesthetic.get('base_style', 'Professional comic book panel illustration.'))
    else:
        parts.append("Professional comic book panel illustration.")
    parts.append("")

    # Location
    location_name = panel_data.get('location')
    if location_name and location_name in locations_db:
        location_desc = build_location_prompt_section(location_name, locations_db)
        parts.append(location_desc)
        parts.append("")

    # Characters - check if dict (embedded descriptions) or list (names only)
    characters = panel_data.get('characters', [])
    if characters:
        parts.append("Characters:")
        if isinstance(characters, dict):
            for char_name, char_desc in characters.items():
                parts.append(f"- {char_name}: {char_desc}")
        else:
            for char_name in characters:
                char_desc = build_character_prompt_section(char_name, characters_db)
                parts.append(char_desc)
        parts.append("")

    # NPCs
    npcs = panel_data.get('npcs', [])
    if npcs:
        parts.append("NPCs:")
        if isinstance(npcs, dict):
            for npc_name, npc_desc in npcs.items():
                parts.append(f"- {npc_name}: {npc_desc}")
        else:
            for npc_name in npcs:
                npc_desc = build_character_prompt_section(npc_name, characters_db)
                parts.append(npc_desc)
        parts.append("")

    # Scene description
    visual = panel_data.get('visual', '')
    parts.append(f"Scene: {visual}\n")

    # Dialogue
    dialogue = panel_data.get('dialogue', '')
    if dialogue:
        parts.append(f"Dialogue: {dialogue}\n")
        if style_db and 'dialogue_rendering' in style_db:
            dialogue_instr = style_db['dialogue_rendering'].get('instruction', '')
            if dialogue_instr:
                parts.append(f"{dialogue_instr}\n")
        else:
            parts.append("Include speech bubbles with dialogue text clearly readable.\n")

    # Style/Aesthetic
    if style_db and 'comic_aesthetic' in style_db:
        aesthetic = style_db['comic_aesthetic']
        style_parts = []
        if aesthetic.get('art_style'):
            style_parts.append(aesthetic['art_style'])
        if aesthetic.get('setting_tone'):
            style_parts.append(aesthetic['setting_tone'])
        if style_parts:
            parts.append(f"Style: {' '.join(style_parts)}")

        restrictions = aesthetic.get('important_restrictions', [])
        if restrictions:
            parts.append(f"IMPORTANT: {' '.join(restrictions)}")
    else:
        parts.append("Style: Bold ink line art, vibrant colors, dynamic composition, sequential art style, graphic novel quality.")

    return "\n".join(parts)


def load_page_data(page_num):
    """Load page data from JSON file."""
    if page_num == 0:
        page_file = PAGES_JSON_DIR / "cover.json"
    else:
        page_file = PAGES_JSON_DIR / f"page-{page_num:03d}.json"

    if not page_file.exists():
        raise FileNotFoundError(f"Page file not found: {page_file}")

    with open(page_file, 'r', encoding='utf-8') as f:
        return json.load(f)


@retry(
    retry=retry_if_exception_type((RateLimitError, APIError)),
    wait=wait_exponential(multiplier=1, min=1, max=60),
    stop=stop_after_attempt(3)
)
async def generate_panel_variant_async(panel, page_num, variant_num, client, characters_db, locations_db, style_db):
    """Generate a single variant of a panel with retry logic."""
    variant_filename = PANELS_DIR / f"page-{page_num:03d}-panel-{panel['panel_num']}-v{variant_num}.png"

    prompt = assemble_prompt(panel, characters_db, locations_db, style_db)
    if not prompt:
        logger.error(f"Could not assemble prompt for panel {panel['panel_num']}")
        return None

    size = panel.get('size', '1024x1024')

    async with semaphore:
        await rpm_limiter.acquire()

        try:
            start_time = time_module.time()

            response = await client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                size=size,
                quality="high",
                n=1
            )

            duration = time_module.time() - start_time
            image_bytes = base64.b64decode(response.data[0].b64_json)

            async with aiofiles.open(variant_filename, 'wb') as f:
                await f.write(image_bytes)

            logger.info(f"  Panel {panel['panel_num']} variant {variant_num} generated in {duration:.1f}s")
            return variant_filename

        except Exception as e:
            logger.error(f"  Error generating panel {panel['panel_num']} variant {variant_num}: {e}")
            img = Image.new('RGB', (PANEL_WIDTH, PANEL_HEIGHT), 'lightgray')
            draw = ImageDraw.Draw(img)
            draw.text((50, 50), f"Error: {str(e)[:100]}", fill='black')
            img.save(variant_filename)
            return variant_filename


async def generate_panel_variants(panel, page_num, client, characters_db, locations_db, style_db):
    """Generate all variants for a single panel concurrently."""
    final_filename = PANELS_DIR / f"page-{page_num:03d}-panel-{panel['panel_num']}.png"

    if final_filename.exists():
        logger.info(f"  Panel {panel['panel_num']} already selected, skipping")
        return

    all_exist = all(
        (PANELS_DIR / f"page-{page_num:03d}-panel-{panel['panel_num']}-v{i}.png").exists()
        for i in range(1, VARIANTS_PER_PANEL + 1)
    )

    if all_exist:
        logger.info(f"  Panel {panel['panel_num']} variants already generated, skipping")
        return

    logger.info(f"  Generating {VARIANTS_PER_PANEL} variants for panel {panel['panel_num']}...")

    tasks = [
        generate_panel_variant_async(panel, page_num, variant_num, client, characters_db, locations_db, style_db)
        for variant_num in range(1, VARIANTS_PER_PANEL + 1)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    successes = sum(1 for r in results if r is not None and not isinstance(r, Exception))
    logger.info(f"  Panel {panel['panel_num']}: {successes}/{VARIANTS_PER_PANEL} variants generated")


async def generate_page_panels(page_data, client, characters_db, locations_db, style_db):
    """Generate all panels for a page."""
    page_num = page_data['page_num']
    panels = page_data['panels']

    logger.info(f"\nPage {page_num} ({len(panels)} panels, {len(panels) * VARIANTS_PER_PANEL} total images)")

    tasks = [
        generate_panel_variants(panel, page_num, client, characters_db, locations_db, style_db)
        for panel in panels
    ]
    await asyncio.gather(*tasks)


async def generate_pages_async(page_nums, concurrent=None, rpm=None):
    """Generate panels for specified pages."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        logger.error("Set it in .env file or: export OPENAI_API_KEY='your-key-here'")
        return

    client = AsyncOpenAI(api_key=api_key)

    logger.info("Loading databases...")
    characters_db = load_character_database()
    locations_db = load_location_database()
    style_db = load_style_database()
    logger.info(f"Loaded {len(characters_db)} characters, {len(locations_db)} locations")

    concurrent = concurrent or MAX_CONCURRENT
    rpm = rpm or MAX_RPM

    logger.info("=" * 60)
    logger.info("GRAPHIC NOVEL GENERATOR (OpenAI)")
    logger.info(f"Concurrent requests: {concurrent} | RPM limit: {rpm}")
    logger.info(f"Variants per panel: {VARIANTS_PER_PANEL}")
    logger.info("=" * 60)

    setup_directories()

    pages_data = []
    for page_num in page_nums:
        try:
            page_data = load_page_data(page_num)
            pages_data.append(page_data)
            logger.info(f"Loaded page {page_num}: '{page_data.get('title', 'Untitled')}' ({page_data['panel_count']} panels)")
        except FileNotFoundError as e:
            logger.error(f"Error loading page {page_num}: {e}")
            return

    if not pages_data:
        logger.error("No valid pages to generate")
        return

    logger.info("\n" + "=" * 60)
    logger.info("GENERATING PANEL VARIANTS")
    logger.info("=" * 60)

    start_time = time_module.time()

    for page_data in pages_data:
        await generate_page_panels(page_data, client, characters_db, locations_db, style_db)

    duration = time_module.time() - start_time
    total_variants = sum(p['panel_count'] * VARIANTS_PER_PANEL for p in pages_data)

    logger.info("\n" + "=" * 60)
    logger.info(f"Generation complete in {duration:.1f}s ({total_variants} images)")
    logger.info(f"Next step: python scripts/core/review.py {page_nums[0]}")
    logger.info("=" * 60)

    await client.close()


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
        description='Generate comic panel variants with OpenAI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_openai.py 1          # Generate page 1
  python generate_openai.py 1-5        # Generate pages 1-5
  python generate_openai.py 1,3,5      # Generate pages 1, 3, and 5
        """
    )

    parser.add_argument('pages', type=str, help='Page number(s) to generate (e.g., 1, 1-5, 1,3,5)')
    parser.add_argument('--concurrent', type=int, default=MAX_CONCURRENT,
                       help=f'Maximum concurrent requests (default: {MAX_CONCURRENT})')
    parser.add_argument('--rpm', type=int, default=MAX_RPM,
                       help=f'Maximum requests per minute (default: {MAX_RPM})')

    args = parser.parse_args()

    global semaphore, rpm_limiter
    semaphore = asyncio.Semaphore(args.concurrent)
    rpm_limiter = RPMLimiter(args.rpm)

    try:
        page_nums = parse_page_range(args.pages)
    except ValueError:
        logger.error(f"Invalid page argument: {args.pages}")
        logger.error("Use format like: 1, 1-5, or 1,3,5")
        sys.exit(1)

    asyncio.run(generate_pages_async(page_nums, args.concurrent, args.rpm))


if __name__ == "__main__":
    main()
