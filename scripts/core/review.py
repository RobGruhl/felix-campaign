#!/usr/bin/env python3
"""
Interactive review interface for selecting comic panel variants.
Displays panel descriptions, dialogue, and variant images for selection.
"""

import os
import json
import sys
import shutil
import subprocess
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify, redirect, url_for, send_file
from PIL import Image
import io

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from utilities.layout_engine import assemble_page_with_layout, PAGE_WIDTH, PAGE_HEIGHT

# Configuration - paths relative to project root
PAGES_JSON_DIR = Path("data/pages")
OUTPUT_DIR = Path("output")
PANELS_DIR = OUTPUT_DIR / "panels"
PAGES_DIR = OUTPUT_DIR / "pages"
SELECTIONS_FILE = OUTPUT_DIR / "selections.json"
VARIANTS_PER_PANEL = 3

# Layout settings
GUTTER = 20

app = Flask(__name__)

# Store current page in global state
current_page_data = None
current_page_num = None


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


def load_selections():
    """Load previous selections."""
    if SELECTIONS_FILE.exists():
        with open(SELECTIONS_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_selections(selections):
    """Save selections to JSON file."""
    SELECTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SELECTIONS_FILE, 'w') as f:
        json.dump(selections, f, indent=2)


def get_panel_variants(page_num, panel_num):
    """Get all available variants for a panel."""
    variants = []
    variant_num = 1

    while True:
        variant_path = PANELS_DIR / f"page-{page_num:03d}-panel-{panel_num}-v{variant_num}.png"
        if not variant_path.exists():
            break
        variants.append({
            'num': variant_num,
            'path': variant_path,
            'url': f"/image/page-{page_num:03d}-panel-{panel_num}-v{variant_num}.png"
        })
        variant_num += 1

    return variants


def get_panel_selection(page_num, panel_num):
    """Check if a panel has been selected."""
    final_path = PANELS_DIR / f"page-{page_num:03d}-panel-{panel_num}.png"
    return final_path.exists()


def get_total_pages():
    """Get total number of pages available."""
    page_files = list(PAGES_JSON_DIR.glob("page-*.json"))
    return len(page_files)


def is_page_finalized(page_num):
    """Check if a page has been finalized (assembled)."""
    page_file = PAGES_DIR / f"page-{page_num:03d}.png"
    return page_file.exists()


@app.route('/image/<path:filename>')
def serve_image(filename):
    """Serve panel images."""
    from flask import send_file
    image_path = PANELS_DIR / filename
    if image_path.exists():
        return send_file(image_path, mimetype='image/png')
    return "Image not found", 404


@app.route('/')
def index():
    """Redirect to page review."""
    if current_page_num:
        return redirect(url_for('review_page', page_num=current_page_num))
    return "No page specified. Run with: python review.py <page_num>", 400


@app.route('/page/<int:page_num>')
def review_page(page_num):
    """Main review interface for a page."""
    try:
        page_data = load_page_data(page_num)
    except FileNotFoundError as e:
        return f"Error: {e}", 404

    selections = load_selections()
    total_pages = get_total_pages()
    is_finalized = is_page_finalized(page_num)

    # Prepare panel data with variants
    panels_with_variants = []
    for panel in page_data['panels']:
        panel_num = panel['panel_num']
        variants = get_panel_variants(page_num, panel_num)
        is_selected = get_panel_selection(page_num, panel_num)

        selected_variant = selections.get(f"{page_num}-{panel_num}")

        panels_with_variants.append({
            'panel': panel,
            'variants': variants,
            'is_selected': is_selected,
            'selected_variant': selected_variant,
            'total_variants': len(variants)
        })

    # HTML template
    template = """
<!DOCTYPE html>
<html>
<head>
    <title>Comic Panel Review - Page {{ page_num }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #1a1a1a; color: #e0e0e0; padding: 20px; line-height: 1.6;
        }
        .header {
            background: #2a2a2a; padding: 20px; border-radius: 8px;
            margin-bottom: 30px; border-left: 4px solid #4a9eff;
        }
        .header h1 { font-size: 28px; margin-bottom: 8px; color: #fff; }
        .header .subtitle { color: #999; font-size: 14px; }
        .progress { background: #333; height: 8px; border-radius: 4px; overflow: hidden; margin-top: 12px; }
        .progress-bar { background: #4a9eff; height: 100%; transition: width 0.3s ease; }
        .panel-section {
            background: #2a2a2a; padding: 30px; border-radius: 8px;
            margin-bottom: 40px; border: 2px solid #333;
        }
        .panel-section.selected { border-color: #4a9eff; background: #2d3540; }
        .panel-header {
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid #444;
        }
        .panel-title { font-size: 20px; font-weight: bold; color: #4a9eff; }
        .selected-badge {
            background: #4a9eff; color: white; padding: 4px 12px;
            border-radius: 12px; font-size: 12px; font-weight: bold;
        }
        .panel-info {
            background: #1f1f1f; padding: 15px; border-radius: 6px;
            margin-bottom: 20px; border-left: 3px solid #666;
        }
        .panel-info h3 {
            font-size: 14px; text-transform: uppercase; color: #999;
            margin-bottom: 8px; font-weight: 600;
        }
        .panel-info p { color: #ddd; font-size: 14px; line-height: 1.8; }
        .variants-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px; margin-bottom: 20px;
        }
        .variant-card {
            background: #1f1f1f; border-radius: 8px; overflow: hidden;
            transition: transform 0.2s, box-shadow 0.2s; cursor: pointer; border: 2px solid #333;
        }
        .variant-card:hover {
            transform: translateY(-4px); box-shadow: 0 8px 24px rgba(74, 158, 255, 0.3);
            border-color: #4a9eff;
        }
        .variant-image { width: 100%; height: auto; display: block; background: #000; }
        .variant-footer { padding: 15px; text-align: center; }
        .variant-number { font-size: 12px; color: #999; margin-bottom: 8px; }
        .select-btn {
            background: #4a9eff; color: white; border: none; padding: 10px 20px;
            border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer;
            transition: background 0.2s; width: 100%;
        }
        .select-btn:hover { background: #3a8ee5; }
        .actions { display: flex; gap: 10px; justify-content: center; margin-top: 15px; }
        .generate-more-btn {
            background: #666; color: white; border: none; padding: 12px 24px;
            border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer;
        }
        .generate-more-btn:hover { background: #777; }
        .preview-btn {
            background: #4a9eff; color: white; border: none; padding: 12px 24px;
            border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer;
        }
        .preview-btn:hover { background: #3a8ee5; }
        .preview-btn:disabled { background: #555; cursor: not-allowed; }
        .message {
            position: fixed; top: 20px; right: 20px; background: #4a9eff;
            color: white; padding: 15px 25px; border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3); z-index: 1000;
        }
        .navigation-bar {
            display: flex; justify-content: space-between; align-items: center;
            margin-top: 15px; gap: 10px;
        }
        .nav-button {
            background: #4a9eff; color: white; border: none; padding: 10px 20px;
            border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 14px;
        }
        .nav-button:disabled { background: #555; cursor: not-allowed; opacity: 0.5; }
        .finalize-button {
            background: #22c55e; color: white; border: none; padding: 12px 24px;
            border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 14px;
        }
        .finalize-button:disabled { background: #555; cursor: not-allowed; opacity: 0.5; }
        .finalize-button.finalized { background: #666; cursor: default; }
        .loading { text-align: center; padding: 40px; color: #999; }
        .spinner {
            border: 3px solid #333; border-top: 3px solid #4a9eff; border-radius: 50%;
            width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 20px;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="header">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h1>Page {{ page_num }}: {{ page_data.title }}</h1>
            <div style="color: #999; font-size: 13px;">Page {{ page_num }} of {{ total_pages }}</div>
        </div>
        <div class="subtitle">{{ page_data.panel_count }} panels | Select your favorite variant for each panel</div>
        <div class="progress">
            <div class="progress-bar" style="width: {{ (selected_count / page_data.panel_count * 100) }}%"></div>
        </div>
        <div class="subtitle" style="margin-top: 8px;">
            Progress: {{ selected_count }}/{{ page_data.panel_count }} panels selected
            {% if selected_count >= page_data.panel_count %}
            <button class="preview-btn" onclick="previewPage({{ page_num }})" style="margin-left: 10px;">
                Preview Final Page
            </button>
            {% endif %}
        </div>
        <div class="navigation-bar">
            <button class="nav-button" onclick="navigatePage({{ page_num - 1 }})"
                    {% if page_num <= 1 %}disabled{% endif %}>← Previous</button>
            {% if is_finalized %}
            <button class="finalize-button finalized" disabled>✓ Page Finalized</button>
            {% elif selected_count >= page_data.panel_count %}
            <button class="finalize-button" onclick="finalizePage({{ page_num }})">Finalize Page</button>
            {% else %}
            <button class="finalize-button" disabled>Finalize ({{ page_data.panel_count - selected_count }} remaining)</button>
            {% endif %}
            <button class="nav-button" onclick="navigatePage({{ page_num + 1 }})"
                    {% if page_num >= total_pages %}disabled{% endif %}>Next →</button>
        </div>
    </div>

    {% for item in panels_with_variants %}
    <div class="panel-section {% if item.is_selected %}selected{% endif %}" id="panel-{{ item.panel.panel_num }}">
        <div class="panel-header">
            <div class="panel-title">Panel {{ item.panel.panel_num }}</div>
            {% if item.is_selected %}
            <div class="selected-badge">✓ SELECTED (Variant {{ item.selected_variant }})</div>
            {% endif %}
        </div>

        <div class="panel-info">
            <h3>Scene Description</h3>
            <p>{{ item.panel.visual }}</p>
        </div>

        {% if item.panel.dialogue %}
        <div class="panel-info">
            <h3>Dialogue</h3>
            <p>{{ item.panel.dialogue }}</p>
        </div>
        {% endif %}

        {% if item.is_selected %}
        <div class="variants-grid">
            <div class="variant-card" style="border: 3px solid #4a9eff;">
                <img src="/image/page-{{ '%03d' % page_num }}-panel-{{ item.panel.panel_num }}.png" class="variant-image" alt="Selected">
                <div class="variant-footer">
                    <div class="variant-number">✓ Selected (Variant {{ item.selected_variant }})</div>
                </div>
            </div>
        </div>
        <div class="actions">
            <button class="generate-more-btn" onclick="generateMore({{ page_num }}, {{ item.panel.panel_num }})">
                Generate More Variants
            </button>
        </div>
        {% elif item.variants %}
        <div class="variants-grid">
            {% for variant in item.variants %}
            <div class="variant-card" onclick="selectVariant({{ page_num }}, {{ item.panel.panel_num }}, {{ variant.num }})">
                <img src="{{ variant.url }}" class="variant-image" alt="Variant {{ variant.num }}">
                <div class="variant-footer">
                    <div class="variant-number">Variant {{ variant.num }}</div>
                    <button class="select-btn">Select This</button>
                </div>
            </div>
            {% endfor %}
        </div>
        <div class="actions">
            <button class="generate-more-btn" onclick="generateMore({{ page_num }}, {{ item.panel.panel_num }})">
                Generate More Variants
            </button>
        </div>
        {% else %}
        <div class="loading">
            <div class="spinner"></div>
            <p>No variants generated yet. Run: python scripts/core/generate_openai.py {{ page_num }}</p>
        </div>
        {% endif %}
    </div>
    {% endfor %}

    <script>
        function selectVariant(pageNum, panelNum, variantNum) {
            fetch('/select/' + pageNum + '/' + panelNum + '/' + variantNum, { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showMessage('Panel ' + panelNum + ' - Variant ' + variantNum + ' selected!');
                    setTimeout(() => location.reload(), 800);
                } else {
                    alert('Error: ' + data.error);
                }
            });
        }

        function generateMore(pageNum, panelNum) {
            if (!confirm('Generate 3 more variants for panel ' + panelNum + '?')) return;
            showMessage('Generating variants...');
            fetch('/more/' + pageNum + '/' + panelNum, { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showMessage('Generated ' + data.new_variants + ' new variants!');
                    setTimeout(() => location.reload(), 1500);
                } else {
                    alert('Error: ' + data.error);
                }
            });
        }

        function previewPage(pageNum) {
            window.open('/preview/' + pageNum, '_blank');
        }

        function navigatePage(pageNum) {
            window.location.href = '/page/' + pageNum;
        }

        function finalizePage(pageNum) {
            if (!confirm('Finalize page ' + pageNum + '?')) return;
            showMessage('Finalizing page...');
            fetch('/finalize/' + pageNum, { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showMessage('Page finalized!');
                    setTimeout(() => location.reload(), 1500);
                } else {
                    alert('Error: ' + data.error);
                }
            });
        }

        function showMessage(text) {
            const existing = document.querySelector('.message');
            if (existing) existing.remove();
            const msg = document.createElement('div');
            msg.className = 'message';
            msg.textContent = text;
            document.body.appendChild(msg);
            setTimeout(() => msg.remove(), 3000);
        }
    </script>
</body>
</html>
    """

    selected_count = sum(1 for item in panels_with_variants if item['is_selected'])

    return render_template_string(
        template,
        page_num=page_num,
        page_data=page_data,
        panels_with_variants=panels_with_variants,
        selected_count=selected_count,
        total_pages=total_pages,
        is_finalized=is_finalized
    )


@app.route('/select/<int:page_num>/<int:panel_num>/<int:variant_num>', methods=['POST'])
def select_variant(page_num, panel_num, variant_num):
    """Select a variant and make it the final version."""
    try:
        selections = load_selections()
        source = PANELS_DIR / f"page-{page_num:03d}-panel-{panel_num}-v{variant_num}.png"
        dest = PANELS_DIR / f"page-{page_num:03d}-panel-{panel_num}.png"

        if not source.exists():
            return jsonify({'success': False, 'error': 'Variant file not found'}), 404

        shutil.copy(source, dest)

        # Delete unchosen variants
        variant_num_check = 1
        while True:
            variant_path = PANELS_DIR / f"page-{page_num:03d}-panel-{panel_num}-v{variant_num_check}.png"
            if not variant_path.exists():
                break
            if variant_num_check != variant_num:
                variant_path.unlink()
            variant_num_check += 1

        selections[f"{page_num}-{panel_num}"] = variant_num
        save_selections(selections)

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/preview/<int:page_num>')
def preview_page(page_num):
    """Generate a preview of the assembled page."""
    try:
        page_data = load_page_data(page_num)
        panels = page_data['panels']

        missing_panels = []
        for panel in panels:
            panel_file = PANELS_DIR / f"page-{page_num:03d}-panel-{panel['panel_num']}.png"
            if not panel_file.exists():
                missing_panels.append(panel['panel_num'])

        if missing_panels:
            return f"Error: Missing selected panels: {missing_panels}", 400

        panel_images = []
        for panel in panels:
            panel_file = PANELS_DIR / f"page-{page_num:03d}-panel-{panel['panel_num']}.png"
            if panel_file.exists():
                panel_images.append(Image.open(panel_file))
            else:
                placeholder = Image.new('RGB', (1024, 1536), 'gray')
                panel_images.append(placeholder)

        page_img = assemble_page_with_layout(
            panels_data=panels,
            panel_images=panel_images,
            page_width=PAGE_WIDTH,
            page_height=PAGE_HEIGHT
        )

        img_io = io.BytesIO()
        page_img.save(img_io, 'PNG')
        img_io.seek(0)

        return send_file(img_io, mimetype='image/png')

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/more/<int:page_num>/<int:panel_num>', methods=['POST'])
def generate_more(page_num, panel_num):
    """Generate more variants for a panel."""
    try:
        page_data = load_page_data(page_num)
        panel_data = next((p for p in page_data['panels'] if p['panel_num'] == panel_num), None)

        if not panel_data:
            return jsonify({'success': False, 'error': 'Panel not found'}), 404

        # Delete the final selection if it exists
        final_file = PANELS_DIR / f"page-{page_num:03d}-panel-{panel_num}.png"
        if final_file.exists():
            final_file.unlink()

        # Find the next available variant number
        next_variant_num = 1
        while (PANELS_DIR / f"page-{page_num:03d}-panel-{panel_num}-v{next_variant_num}.png").exists():
            next_variant_num += 1

        import asyncio
        from openai import AsyncOpenAI
        import base64
        import aiofiles

        async def generate_additional_variants():
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set")

            client = AsyncOpenAI(api_key=api_key)
            prompt = panel_data.get('prompt', '')
            size = panel_data.get('size', '1024x1024')

            new_variants = []
            for i in range(3):
                variant_num = next_variant_num + i
                filename = PANELS_DIR / f"page-{page_num:03d}-panel-{panel_num}-v{variant_num}.png"

                response = await client.images.generate(
                    model="gpt-image-1",
                    prompt=prompt,
                    size=size,
                    quality="high",
                    n=1
                )

                image_bytes = base64.b64decode(response.data[0].b64_json)
                async with aiofiles.open(filename, 'wb') as f:
                    await f.write(image_bytes)

                new_variants.append(variant_num)

            await client.close()
            return new_variants

        new_variants = asyncio.run(generate_additional_variants())

        return jsonify({'success': True, 'new_variants': len(new_variants)})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/finalize/<int:page_num>', methods=['POST'])
def finalize_page(page_num):
    """Finalize a page by assembling it."""
    try:
        page_data = load_page_data(page_num)
        panels = page_data['panels']

        missing_panels = []
        for panel in panels:
            panel_file = PANELS_DIR / f"page-{page_num:03d}-panel-{panel['panel_num']}.png"
            if not panel_file.exists():
                missing_panels.append(panel['panel_num'])

        if missing_panels:
            return jsonify({'success': False, 'error': f'Missing panels: {missing_panels}'}), 400

        panel_images = []
        for panel in panels:
            panel_file = PANELS_DIR / f"page-{page_num:03d}-panel-{panel['panel_num']}.png"
            if panel_file.exists():
                panel_images.append(Image.open(panel_file))
            else:
                placeholder = Image.new('RGB', (1024, 1536), 'gray')
                panel_images.append(placeholder)

        page_img = assemble_page_with_layout(
            panels_data=panels,
            panel_images=panel_images,
            page_width=PAGE_WIDTH,
            page_height=PAGE_HEIGHT
        )

        PAGES_DIR.mkdir(parents=True, exist_ok=True)
        output_file = PAGES_DIR / f"page-{page_num:03d}.png"
        page_img.save(output_file)

        return jsonify({'success': True, 'output_file': str(output_file)})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python review.py <page_num>")
        print("Example: python review.py 1")
        sys.exit(1)

    try:
        page_num = int(sys.argv[1])
    except ValueError:
        print("Error: Page number must be an integer")
        sys.exit(1)

    global current_page_num
    current_page_num = page_num

    try:
        load_page_data(page_num)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Create page JSON files in data/pages/ first")
        sys.exit(1)

    port = int(os.getenv('FLASK_PORT', 5001))

    print(f"\n{'='*60}")
    print(f"COMIC PANEL REVIEW - PAGE {page_num}")
    print(f"{'='*60}")
    print(f"\nOpening review interface at http://127.0.0.1:{port}")
    print("Press Ctrl+C to stop the server\n")

    import webbrowser
    import threading
    def open_browser():
        import time
        time.sleep(1)
        webbrowser.open(f'http://127.0.0.1:{port}/page/{page_num}')

    threading.Thread(target=open_browser, daemon=True).start()

    app.run(debug=False, port=port, host='127.0.0.1')


if __name__ == "__main__":
    main()
