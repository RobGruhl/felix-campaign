#!/usr/bin/env python3
"""
Google Gemini image generator with adaptive rate limiting.
Generates comic panels from structured page JSON files.
"""

import os
import sys
import json
import asyncio
import logging
import time as time_module
from pathlib import Path
from google import genai
from google.genai import types
from dotenv import load_dotenv
from PIL import Image

# Load environment
load_dotenv()

# Configuration - paths relative to project root
PAGES_JSON_DIR = Path("data/pages")
OUTPUT_DIR = Path("output")
PANELS_DIR = OUTPUT_DIR / "panels"
CHARACTERS_DB_PATH = Path("data/characters.json")
LOCATIONS_DB_PATH = Path("data/locations.json")
STYLE_DB_PATH = Path("data/style.json")

# Rate limiting settings - adaptive
MIN_CONCURRENT = 2
MAX_CONCURRENT = int(os.getenv('MAX_CONCURRENT', 15))
INITIAL_CONCURRENT = 8

# Model configuration
MODEL_ID = "gemini-3-pro-image-preview"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class AdaptiveSemaphore:
    """Semaphore with adaptive concurrency based on rate limit responses."""

    def __init__(self, initial_value, min_value=2, max_value=20):
        self.value = initial_value
        self.min_value = min_value
        self.max_value = max_value
        self._semaphore = asyncio.Semaphore(initial_value)
        self._lock = asyncio.Lock()
        self._current_permits = initial_value

    async def acquire(self):
        await self._semaphore.acquire()

    def release(self):
        self._semaphore.release()

    async def increase_concurrency(self):
        async with self._lock:
            if self._current_permits < self.max_value:
                old = self._current_permits
                self._current_permits = min(self._current_permits + 1, self.max_value)
                self._semaphore.release()
                logger.info(f"Increased concurrency: {old} -> {self._current_permits}")

    async def decrease_concurrency(self):
        async with self._lock:
            if self._current_permits > self.min_value:
                old = self._current_permits
                self._current_permits = max(self._current_permits - 2, self.min_value)
                try:
                    for _ in range(2):
                        if self._current_permits < old:
                            self._semaphore.acquire_nowait()
                except:
                    pass
                logger.warning(f"Decreased concurrency: {old} -> {self._current_permits}")

    def get_current(self):
        return self._current_permits


class RPMLimiter:
    """Token bucket rate limiter for requests per minute."""

    def __init__(self, max_per_minute=50):
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
adaptive_semaphore = AdaptiveSemaphore(INITIAL_CONCURRENT, MIN_CONCURRENT, MAX_CONCURRENT)
rpm_limiter = RPMLimiter(max_per_minute=50)

# Stats tracking
stats = {
    'total': 0,
    'successful': 0,
    'skipped': 0,
    'failed': 0,
    'rate_limited': 0,
    'start_time': None
}


def setup_directories():
    """Create output directory structure."""
    PANELS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Created output directories")


def load_database(path, name):
    """Load a JSON database file."""
    if not path.exists():
        logger.warning(f"{name} database not found at {path}")
        return {}
    with open(path, 'r') as f:
        data = json.load(f)
        # Remove _schema key if present (it's documentation, not data)
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
        return f"Location: {location_name}"

    desc_components = loc.get('description_components', {})
    if desc_components:
        parts = [f"Location: {loc['name']}"]
        for key in ['location_context', 'architecture', 'key_features', 'atmosphere', 'lighting_magic', 'lighting']:
            if desc_components.get(key):
                parts.append(desc_components[key])
        return " ".join(parts)
    return f"Location: {loc.get('name', location_name)}"


def build_character_prompt_section(char_name, characters_db):
    """Build detailed character description for prompt."""
    char = characters_db.get(char_name)
    if not char:
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
        return "\n".join(parts)
    return f"- {char_name}: {char.get('full_description', '')}"


def assemble_prompt(panel_data, characters_db, locations_db, style_db=None):
    """
    Dynamically assemble prompt from panel data and reference databases.

    Character descriptions embedded in panel_data take priority over database lookups.
    """
    parts = []

    # Base style
    if style_db and 'comic_aesthetic' in style_db:
        parts.append(style_db['comic_aesthetic'].get('base_style', 'Professional comic book panel illustration.'))
    else:
        parts.append("Professional comic book panel illustration.")
    parts.append("")

    # Location
    location_name = panel_data.get('location')
    if location_name and location_name in locations_db:
        parts.append(build_location_prompt_section(location_name, locations_db))
        parts.append("")

    # Characters - check if dict (embedded descriptions) or list (names only)
    characters = panel_data.get('characters', {})
    if characters:
        parts.append("Characters:")
        if isinstance(characters, dict):
            for char_name, char_desc in characters.items():
                parts.append(f"- {char_name}: {char_desc}")
        else:
            for char_name in characters:
                parts.append(build_character_prompt_section(char_name, characters_db))
        parts.append("")

    # NPCs
    npcs = panel_data.get('npcs', {})
    if npcs:
        parts.append("NPCs:")
        if isinstance(npcs, dict):
            for npc_name, npc_desc in npcs.items():
                parts.append(f"- {npc_name}: {npc_desc}")
        else:
            for npc_name in npcs:
                parts.append(build_character_prompt_section(npc_name, characters_db))
        parts.append("")

    # Scene description
    visual = panel_data.get('visual', '')
    parts.append(f"Scene: {visual}\n")

    # Dialogue
    dialogue = panel_data.get('dialogue', '')
    if dialogue:
        parts.append(f"Dialogue: {dialogue}\n")

    # Art style
    if style_db and 'comic_aesthetic' in style_db:
        aesthetic = style_db['comic_aesthetic']
        if aesthetic.get('art_style'):
            parts.append(f"Style: {aesthetic['art_style']}")

    return "\n".join(parts)


def load_page_data(page_num):
    """Load page data from JSON file."""
    page_file = PAGES_JSON_DIR / f"page-{page_num:03d}.json"
    if not page_file.exists():
        raise FileNotFoundError(f"Page file not found: {page_file}")
    with open(page_file, 'r', encoding='utf-8') as f:
        return json.load(f)


async def generate_panel_async(panel, page_num, client, characters_db, locations_db, style_db):
    """Generate a single panel with retry logic."""
    panel_num = panel['panel_num']
    output_path = PANELS_DIR / f"page-{page_num:03d}-panel-{panel_num}.png"

    if output_path.exists():
        logger.info(f"Skipped page {page_num} panel {panel_num} (already exists)")
        stats['skipped'] += 1
        return True

    prompt = assemble_prompt(panel, characters_db, locations_db, style_db)
    if not prompt:
        logger.error(f"No prompt for page {page_num} panel {panel_num}")
        stats['failed'] += 1
        return False

    max_retries = 5
    base_delay = 2

    for attempt in range(max_retries):
        try:
            await adaptive_semaphore.acquire()
            await rpm_limiter.acquire()

            try:
                aspect_ratio = panel.get('aspect_ratio', '3:4')
                success = await asyncio.to_thread(
                    generate_panel_sync,
                    prompt, output_path, page_num, panel_num, aspect_ratio
                )

                if success:
                    stats['successful'] += 1
                    if stats['successful'] % 10 == 0:
                        await adaptive_semaphore.increase_concurrency()
                    return True
                else:
                    stats['failed'] += 1
                    return False
            finally:
                adaptive_semaphore.release()

        except Exception as e:
            error_str = str(e)
            if '429' in error_str or 'rate limit' in error_str.lower():
                stats['rate_limited'] += 1
                await adaptive_semaphore.decrease_concurrency()
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Rate limited page {page_num} panel {panel_num}, retry {attempt+1}/{max_retries} in {delay}s")
                await asyncio.sleep(delay)
                continue
            elif '503' in error_str:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Service overloaded, retry {attempt+1}/{max_retries} in {delay}s")
                await asyncio.sleep(delay)
                continue
            else:
                logger.error(f"Error page {page_num} panel {panel_num}: {e}")
                stats['failed'] += 1
                return False

    logger.error(f"Failed page {page_num} panel {panel_num} after {max_retries} attempts")
    stats['failed'] += 1
    return False


def generate_panel_sync(prompt, output_path, page_num, panel_num, aspect_ratio='3:4'):
    """Synchronous generation (called from thread pool)."""
    try:
        client = genai.Client(api_key=os.getenv('GOOGLE_API_KEY'))

        # Map aspect ratios to Gemini-supported values
        gemini_aspect = aspect_ratio
        if aspect_ratio in ['tall', 'splash', 'portrait']:
            gemini_aspect = '9:16'
        elif aspect_ratio in ['wide', 'landscape']:
            gemini_aspect = '16:9'
        elif aspect_ratio == 'square':
            gemini_aspect = '1:1'
        elif aspect_ratio == '2:3':
            gemini_aspect = '9:16'
        elif aspect_ratio == '16:10':
            gemini_aspect = '16:9'

        config = types.GenerateContentConfig(
            response_modalities=['Image'],
            image_config=types.ImageConfig(aspect_ratio=gemini_aspect)
        )

        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=config
        )

        for part in response.parts:
            if image := part.as_image():
                image.save(str(output_path))
                pil_img = Image.open(str(output_path))
                size = pil_img.size
                logger.info(f"Generated page {page_num:03d} panel {panel_num} ({size[0]}x{size[1]})")
                return True

        logger.error(f"No image in response for page {page_num} panel {panel_num}")
        return False

    except Exception as e:
        raise


async def generate_page(page_num, client, characters_db, locations_db, style_db):
    """Generate all panels for a page."""
    try:
        page_data = load_page_data(page_num)
        panels = page_data.get('panels', [])

        if not panels:
            logger.warning(f"No panels found for page {page_num}")
            return []

        logger.info(f"Page {page_num}: {len(panels)} panels")
        tasks = [generate_panel_async(panel, page_num, client, characters_db, locations_db, style_db) for panel in panels]
        results = await asyncio.gather(*tasks)
        return results

    except FileNotFoundError:
        logger.warning(f"Page {page_num} JSON not found, skipping")
        return []
    except Exception as e:
        logger.error(f"Error processing page {page_num}: {e}")
        return []


async def main():
    """Main generation pipeline."""
    import argparse

    parser = argparse.ArgumentParser(description='Generate comic panels with Google Gemini')
    parser.add_argument('pages', nargs='?', default='1-10',
                       help='Page range (e.g., "1-10", "1,3,5", "5")')
    parser.add_argument('--concurrent', type=int, default=INITIAL_CONCURRENT,
                       help=f'Initial concurrent requests (default: {INITIAL_CONCURRENT})')
    args = parser.parse_args()

    global adaptive_semaphore
    adaptive_semaphore = AdaptiveSemaphore(args.concurrent, MIN_CONCURRENT, MAX_CONCURRENT)

    # Parse page range
    pages = []
    if '-' in args.pages:
        start, end = map(int, args.pages.split('-'))
        pages = list(range(start, end + 1))
    elif ',' in args.pages:
        pages = [int(p.strip()) for p in args.pages.split(',')]
    else:
        pages = [int(args.pages)]

    setup_directories()

    logger.info("Loading databases...")
    characters_db = load_character_database()
    locations_db = load_location_database()
    style_db = load_style_database()
    logger.info(f"Loaded {len(characters_db)} characters, {len(locations_db)} locations")

    # Count total panels
    total_panels = 0
    for page_num in pages:
        try:
            page_data = load_page_data(page_num)
            total_panels += len(page_data.get('panels', []))
        except:
            pass

    logger.info("=" * 60)
    logger.info("GRAPHIC NOVEL GENERATOR (Gemini)")
    logger.info("=" * 60)
    logger.info(f"Model: {MODEL_ID}")
    logger.info(f"Pages: {args.pages} ({len(pages)} pages)")
    logger.info(f"Total panels: {total_panels}")
    logger.info(f"Initial concurrency: {args.concurrent}")
    logger.info(f"Output: {PANELS_DIR}/")
    logger.info("=" * 60)

    stats['total'] = total_panels
    stats['start_time'] = time_module.time()

    client = genai.Client(api_key=os.getenv('GOOGLE_API_KEY'))

    logger.info("\nStarting generation...")

    for page_num in pages:
        await generate_page(page_num, client, characters_db, locations_db, style_db)
        completed = stats['successful'] + stats['skipped']
        logger.info(f"Progress: {completed}/{total_panels} panels "
                   f"({stats['successful']} generated, {stats['skipped']} skipped, "
                   f"{stats['failed']} failed) [Concurrency: {adaptive_semaphore.get_current()}]")

    elapsed = time_module.time() - stats['start_time']
    completed = stats['successful'] + stats['skipped']

    logger.info("\n" + "=" * 60)
    logger.info("GENERATION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Time: {elapsed/60:.1f} minutes ({elapsed:.0f}s)")
    logger.info(f"Total: {completed}/{total_panels} panels")
    logger.info(f"  Generated: {stats['successful']}")
    logger.info(f"  Skipped: {stats['skipped']}")
    logger.info(f"  Failed: {stats['failed']}")
    logger.info(f"Output: {PANELS_DIR}/")
    logger.info("=" * 60)

    if stats['failed'] > 0:
        logger.warning(f"\n{stats['failed']} panels failed - re-run to retry")


if __name__ == "__main__":
    asyncio.run(main())
