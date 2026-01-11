#!/usr/bin/env python3
"""
Comic book layout engine with spanning panel support.
Supports 8 named layouts from 1-4 panels with wide/tall spanning options.
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
from typing import List, Dict, Optional
import random


# Layout Configuration
PAGE_WIDTH = 1600
PAGE_HEIGHT = 2400
GUTTER = 20
PANEL_BORDER = 3
SHADOW_OFFSET = 4
SHADOW_BLUR = 6

# Background Configuration
BACKGROUND_COLOR = (245, 240, 235)  # Warm off-white/cream
TEXTURE_INTENSITY = 0.15

# Calculated dimensions
CONTENT_WIDTH = PAGE_WIDTH - 2 * GUTTER   # 1560
CONTENT_HEIGHT = PAGE_HEIGHT - 2 * GUTTER  # 2360
HALF_WIDTH = (CONTENT_WIDTH - GUTTER) // 2  # 770
HALF_HEIGHT = (CONTENT_HEIGHT - GUTTER) // 2  # 1170

# Named layout definitions
# Each layout has a list of panel positions in order
LAYOUTS = {
    # 1 panel - full page splash
    "splash": {
        "panel_count": 1,
        "description": "Full page splash - dramatic moments",
        "positions": [
            {"x": GUTTER, "y": GUTTER, "w": CONTENT_WIDTH, "h": CONTENT_HEIGHT}
        ]
    },

    # 2 panels - horizontal stack (two wide panels)
    "2-horizontal": {
        "panel_count": 2,
        "description": "Two stacked wide panels - cinematic pacing",
        "positions": [
            {"x": GUTTER, "y": GUTTER, "w": CONTENT_WIDTH, "h": HALF_HEIGHT},
            {"x": GUTTER, "y": GUTTER + HALF_HEIGHT + GUTTER, "w": CONTENT_WIDTH, "h": HALF_HEIGHT}
        ]
    },

    # 2 panels - vertical stack (two tall panels side by side)
    "2-vertical": {
        "panel_count": 2,
        "description": "Two side-by-side tall panels - parallel action or comparison",
        "positions": [
            {"x": GUTTER, "y": GUTTER, "w": HALF_WIDTH, "h": CONTENT_HEIGHT},
            {"x": GUTTER + HALF_WIDTH + GUTTER, "y": GUTTER, "w": HALF_WIDTH, "h": CONTENT_HEIGHT}
        ]
    },

    # 3 panels - wide top + 2 below
    "3-top-wide": {
        "panel_count": 3,
        "description": "Wide establishing shot on top, two panels below",
        "positions": [
            {"x": GUTTER, "y": GUTTER, "w": CONTENT_WIDTH, "h": 780},
            {"x": GUTTER, "y": GUTTER + 780 + GUTTER, "w": HALF_WIDTH, "h": CONTENT_HEIGHT - 780 - GUTTER},
            {"x": GUTTER + HALF_WIDTH + GUTTER, "y": GUTTER + 780 + GUTTER, "w": HALF_WIDTH, "h": CONTENT_HEIGHT - 780 - GUTTER}
        ]
    },

    # 3 panels - 2 on top + wide bottom
    "3-bottom-wide": {
        "panel_count": 3,
        "description": "Two panels on top, wide conclusion panel below",
        "positions": [
            {"x": GUTTER, "y": GUTTER, "w": HALF_WIDTH, "h": CONTENT_HEIGHT - 780 - GUTTER},
            {"x": GUTTER + HALF_WIDTH + GUTTER, "y": GUTTER, "w": HALF_WIDTH, "h": CONTENT_HEIGHT - 780 - GUTTER},
            {"x": GUTTER, "y": GUTTER + (CONTENT_HEIGHT - 780 - GUTTER) + GUTTER, "w": CONTENT_WIDTH, "h": 780}
        ]
    },

    # 3 panels - tall left + 2 on right
    "3-left-tall": {
        "panel_count": 3,
        "description": "Tall character focus on left, two context panels on right",
        "positions": [
            {"x": GUTTER, "y": GUTTER, "w": HALF_WIDTH, "h": CONTENT_HEIGHT},
            {"x": GUTTER + HALF_WIDTH + GUTTER, "y": GUTTER, "w": HALF_WIDTH, "h": HALF_HEIGHT},
            {"x": GUTTER + HALF_WIDTH + GUTTER, "y": GUTTER + HALF_HEIGHT + GUTTER, "w": HALF_WIDTH, "h": HALF_HEIGHT}
        ]
    },

    # 3 panels - 2 on left + tall right
    "3-right-tall": {
        "panel_count": 3,
        "description": "Two context panels on left, tall character focus on right",
        "positions": [
            {"x": GUTTER, "y": GUTTER, "w": HALF_WIDTH, "h": HALF_HEIGHT},
            {"x": GUTTER, "y": GUTTER + HALF_HEIGHT + GUTTER, "w": HALF_WIDTH, "h": HALF_HEIGHT},
            {"x": GUTTER + HALF_WIDTH + GUTTER, "y": GUTTER, "w": HALF_WIDTH, "h": CONTENT_HEIGHT}
        ]
    },

    # 4 panels - standard 2x2 grid
    "grid": {
        "panel_count": 4,
        "description": "Standard 2x2 grid - dialogue, action sequences",
        "positions": [
            {"x": GUTTER, "y": GUTTER, "w": HALF_WIDTH, "h": HALF_HEIGHT},
            {"x": GUTTER + HALF_WIDTH + GUTTER, "y": GUTTER, "w": HALF_WIDTH, "h": HALF_HEIGHT},
            {"x": GUTTER, "y": GUTTER + HALF_HEIGHT + GUTTER, "w": HALF_WIDTH, "h": HALF_HEIGHT},
            {"x": GUTTER + HALF_WIDTH + GUTTER, "y": GUTTER + HALF_HEIGHT + GUTTER, "w": HALF_WIDTH, "h": HALF_HEIGHT}
        ]
    }
}


def get_layout_info() -> Dict:
    """Return layout information for documentation/reference."""
    return {
        name: {
            "panel_count": layout["panel_count"],
            "description": layout["description"]
        }
        for name, layout in LAYOUTS.items()
    }


def create_textured_background(width: int, height: int) -> Image.Image:
    """Create subtle textured background for professional comic appearance."""
    bg = Image.new('RGB', (width, height), BACKGROUND_COLOR)

    # Generate subtle noise texture
    pixels = bg.load()
    for y in range(height):
        for x in range(width):
            variation = int((random.random() - 0.5) * TEXTURE_INTENSITY * 255)
            r, g, b = BACKGROUND_COLOR
            pixels[x, y] = (
                max(0, min(255, r + variation)),
                max(0, min(255, g + variation)),
                max(0, min(255, b + variation))
            )

    # Slight blur to smooth texture
    bg = bg.filter(ImageFilter.GaussianBlur(0.5))
    return bg


def draw_panel_with_shadow(page_img: Image.Image, panel_img: Image.Image,
                           x: int, y: int, width: int, height: int):
    """Draw a panel with drop shadow onto the page, maintaining aspect ratio."""
    # Create shadow layer
    shadow = Image.new('RGBA', (width + SHADOW_OFFSET * 2, height + SHADOW_OFFSET * 2), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rectangle(
        [SHADOW_OFFSET, SHADOW_OFFSET, width + SHADOW_OFFSET, height + SHADOW_OFFSET],
        fill=(0, 0, 0, 100)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(SHADOW_BLUR))

    # Paste shadow
    page_img.paste(shadow, (x - SHADOW_OFFSET, y - SHADOW_OFFSET), shadow)

    # Calculate panel size maintaining aspect ratio
    panel_ratio = panel_img.width / panel_img.height
    cell_ratio = width / height

    if panel_ratio > cell_ratio:
        # Panel is wider than cell - fit to width
        panel_width = width - 2 * PANEL_BORDER
        panel_height = int(panel_width / panel_ratio)
    else:
        # Panel is taller than cell - fit to height
        panel_height = height - 2 * PANEL_BORDER
        panel_width = int(panel_height * panel_ratio)

    # Center within the cell
    offset_x = (width - panel_width) // 2
    offset_y = (height - panel_height) // 2

    # Resize panel
    panel_resized = panel_img.resize((panel_width, panel_height), Image.Resampling.LANCZOS)

    # Draw border and panel
    bordered_panel = Image.new('RGB', (width, height), 'black')
    bordered_panel.paste(panel_resized, (offset_x, offset_y))

    # Paste panel onto page
    page_img.paste(bordered_panel, (x, y))


def layout_by_name(page_img: Image.Image, panel_images: List[Image.Image], layout_name: str):
    """Apply named layout to panels."""
    layout = LAYOUTS.get(layout_name, LAYOUTS["grid"])

    for i, panel in enumerate(panel_images[:len(layout["positions"])]):
        pos = layout["positions"][i]
        draw_panel_with_shadow(page_img, panel, pos["x"], pos["y"], pos["w"], pos["h"])


def auto_detect_layout(num_panels: int) -> str:
    """Auto-detect best layout based on panel count."""
    if num_panels == 1:
        return "splash"
    elif num_panels == 2:
        return "2-horizontal"
    elif num_panels == 3:
        return "3-top-wide"
    else:
        return "grid"


def assemble_page_simple(panel_images: List[Image.Image], num_panels: int,
                         layout: Optional[str] = None) -> Image.Image:
    """
    Assemble a comic page using the layout system.

    Args:
        panel_images: List of loaded panel images
        num_panels: Number of panels (for backward compatibility)
        layout: Named layout to use (auto-detected if None)

    Returns:
        Assembled page image (1600x2400)
    """
    page_img = create_textured_background(PAGE_WIDTH, PAGE_HEIGHT)

    # Auto-detect layout if not specified
    if layout is None:
        layout = auto_detect_layout(len(panel_images))

    layout_by_name(page_img, panel_images, layout)
    return page_img


def assemble_page_with_layout(panels_data: List[Dict], panel_images: List[Image.Image],
                               page_width: int = PAGE_WIDTH, page_height: int = PAGE_HEIGHT,
                               custom_layout: str = None) -> Image.Image:
    """
    Legacy wrapper for compatibility.
    Now supports named layouts via custom_layout parameter.
    """
    num_panels = len(panels_data)
    return assemble_page_simple(panel_images, num_panels, layout=custom_layout)


# Layout recommendations for different scene types
LAYOUT_RECOMMENDATIONS = {
    "establishing": ["3-top-wide", "splash"],
    "dialogue": ["grid", "3-left-tall", "3-right-tall"],
    "action": ["grid", "2-horizontal", "splash"],
    "dramatic_reveal": ["splash", "3-bottom-wide"],
    "parallel_action": ["2-vertical", "2-horizontal"],
    "character_focus": ["3-left-tall", "3-right-tall", "splash"],
    "climax": ["splash", "3-bottom-wide"],
    "transition": ["2-horizontal", "3-top-wide"]
}
