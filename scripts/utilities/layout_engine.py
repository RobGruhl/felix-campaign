#!/usr/bin/env python3
"""
Comic book layout engine.
Two layouts: Splash (1 panel) and 2x2 Grid (4 panels).
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
from typing import List, Dict
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
    """Draw a panel with drop shadow onto the page."""
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

    # Resize panel to fit box (maintain aspect ratio)
    panel_resized = panel_img.resize((width, height), Image.Resampling.LANCZOS)

    # Draw border
    bordered_panel = Image.new('RGB', (width, height), 'black')
    inner_width = width - 2 * PANEL_BORDER
    inner_height = height - 2 * PANEL_BORDER
    panel_resized = panel_resized.resize((inner_width, inner_height), Image.Resampling.LANCZOS)
    bordered_panel.paste(panel_resized, (PANEL_BORDER, PANEL_BORDER))

    # Paste panel
    page_img.paste(bordered_panel, (x, y))


def layout_splash(page_img: Image.Image, panel_images: List[Image.Image]):
    """
    Splash layout: Single panel fills entire page.
    Panel is centered and scaled to fit while maintaining original aspect ratio.
    """
    if not panel_images:
        return

    panel = panel_images[0]

    available_width = PAGE_WIDTH - 2 * GUTTER
    available_height = PAGE_HEIGHT - 2 * GUTTER

    panel_ratio = panel.width / panel.height
    page_ratio = available_width / available_height

    if panel_ratio < page_ratio:
        panel_height = available_height
        panel_width = int(panel_height * panel_ratio)
    else:
        panel_width = available_width
        panel_height = int(panel_width / panel_ratio)

    x = (PAGE_WIDTH - panel_width) // 2
    y = (PAGE_HEIGHT - panel_height) // 2

    draw_panel_with_shadow(page_img, panel, x, y, panel_width, panel_height)


def layout_2x2_grid(page_img: Image.Image, panel_images: List[Image.Image]):
    """
    2x2 Grid layout: 4 panels in a grid.
    Each panel maintains original aspect ratio, centered within its cell.
    """
    available_width = PAGE_WIDTH - 3 * GUTTER
    available_height = PAGE_HEIGHT - 3 * GUTTER

    cell_width = available_width // 2
    cell_height = available_height // 2

    positions = [
        (0, 0),  # Top-left
        (1, 0),  # Top-right
        (0, 1),  # Bottom-left
        (1, 1),  # Bottom-right
    ]

    for i, panel in enumerate(panel_images[:4]):
        col, row = positions[i]
        cell_x = GUTTER + col * (cell_width + GUTTER)
        cell_y = GUTTER + row * (cell_height + GUTTER)

        panel_ratio = panel.width / panel.height
        cell_ratio = cell_width / cell_height

        if panel_ratio > cell_ratio:
            panel_width = cell_width
            panel_height = int(panel_width / panel_ratio)
        else:
            panel_height = cell_height
            panel_width = int(panel_height * panel_ratio)

        x = cell_x + (cell_width - panel_width) // 2
        y = cell_y + (cell_height - panel_height) // 2

        draw_panel_with_shadow(page_img, panel, x, y, panel_width, panel_height)


def assemble_page_simple(panel_images: List[Image.Image], num_panels: int) -> Image.Image:
    """
    Assemble a comic page using simplified layout system.

    Args:
        panel_images: List of loaded panel images
        num_panels: Number of panels (1 = splash, 2-4 = grid)

    Returns:
        Assembled page image (1600x2400)
    """
    page_img = create_textured_background(PAGE_WIDTH, PAGE_HEIGHT)

    if num_panels == 1:
        layout_splash(page_img, panel_images)
    else:
        layout_2x2_grid(page_img, panel_images)

    return page_img


def assemble_page_with_layout(panels_data: List[Dict], panel_images: List[Image.Image],
                               page_width: int = PAGE_WIDTH, page_height: int = PAGE_HEIGHT,
                               custom_layout: str = None) -> Image.Image:
    """
    Legacy wrapper for compatibility.
    Uses only splash or 2x2 grid layouts.
    """
    num_panels = len(panels_data)
    return assemble_page_simple(panel_images, num_panels)
