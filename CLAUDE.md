# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) for generating graphic novels from arbitrary source material.

## Project Overview

**Graphic Novel Generator** is a Claude Code-first workflow for creating AI-generated graphic novels/comic books from any source material. Claude Code IS the workflow engine - no complex parsing scripts needed.

**The Philosophy:** You (Claude) read the user's source material, extract the story structure, create databases, generate page-by-page storyboards, and iterate with the user until the comic is complete.

**Key Components:**
- `scripts/core/generate_gemini.py` - Google Gemini image generation (recommended)
- `scripts/core/generate_openai.py` - OpenAI image generation (variant selection)
- `scripts/core/review.py` - Web UI for selecting panel variants (OpenAI workflow)
- `scripts/core/assemble.py` - Page assembly and CBZ packaging
- `data/characters.json` - Character descriptions database
- `data/locations.json` - Location descriptions database
- `data/style.json` - Art style and aesthetic guidelines
- `data/pages/` - Page JSON files (you create these)

---

## The Iterative Workflow

### Phase 1: Input Processing

When the user provides source material (in `input/` or pasted directly):

1. **Read all input files** in the `input/` directory
2. **Identify and extract:**
   - Main characters with physical descriptions
   - Key locations with atmosphere/lighting details
   - Plot structure (beginning, trials/conflicts, climax, resolution)
   - Dialogue that should be preserved
3. **Ask clarifying questions:**
   - Art style preferences (manga, western comics, realistic, stylized)
   - Tone (dark, heroic, whimsical, dramatic)
   - Target audience (affects content and complexity)
   - Approximate page count / scope

### Phase 2: Database Creation

1. **Populate `data/characters.json`** with extracted characters:
   - Use PascalCase keys (no spaces): `HeroName`, `VillainName`
   - Include detailed visual descriptions in `description_components`
   - Focus on visually distinctive features for consistency

2. **Populate `data/locations.json`** with settings:
   - Include architecture, atmosphere, lighting, key features
   - Be specific about light sources (critical for mood)

3. **Update `data/style.json`** if the user wants a specific aesthetic

4. **Present databases to user** for review before proceeding

### Phase 3: Storyboard Creation

Create page JSON files in `data/pages/`:

1. **Break story into page-level beats**
   - 1 panel = Splash page (dramatic moments)
   - 2-4 panels = Standard page (dialogue, action)

2. **Create `data/pages/page-NNN.json`** files:
```json
{
  "page_num": 1,
  "title": "Chapter Title or Scene Name",
  "panel_count": 4,
  "panels": [
    {
      "panel_num": 1,
      "visual": "Detailed scene description for the artist...",
      "dialogue": "Character: \"Spoken text here.\"",
      "characters": ["HeroName", "MentorName"],
      "location": "LocationKey",
      "aspect_ratio": "3:4",
      "size": "768x1024"
    }
  ]
}
```

3. **Start with pages 1-3** for user approval before continuing
4. **Iterate** based on user feedback

### Phase 4: Image Generation

**Gemini (Recommended - Single Best Image):**
```bash
python scripts/core/generate_gemini.py 1-5    # Generate pages 1-5
```

**OpenAI (3 Variants Per Panel for Selection):**
```bash
python scripts/core/generate_openai.py 1-5   # Generate variants
python scripts/core/review.py 1              # Select best variants
```

After generation:
- Review output with user
- Regenerate specific panels if needed
- Iterate on character/location descriptions

### Phase 5: Assembly & Deployment

```bash
# Assemble pages into final format
python scripts/core/assemble.py

# Convert to WebP for web (optional)
for f in output/pages/*.png; do cwebp -q 85 "$f" -o "${f%.png}.webp"; done

# Update web reader metadata
# Edit docs/data/pages.json with page info
```

---

## JSON Schemas

### Page JSON (`data/pages/page-NNN.json`)

```json
{
  "page_num": 1,
  "title": "Scene or Chapter Title",
  "layout": "3-top-wide",
  "panels": [
    {
      "panel_num": 1,
      "visual": "Wide establishing shot of the location...",
      "dialogue": "",
      "characters": ["CharacterKey"],
      "location": "LocationKey",
      "aspect_ratio": "16:9",
      "size": "1536x864"
    },
    {
      "panel_num": 2,
      "visual": "Close-up reaction shot...",
      "dialogue": "Speaker: \"Dialogue text.\"",
      "characters": ["CharacterKey.Variant"],
      "location": "LocationKey",
      "aspect_ratio": "3:4",
      "size": "768x1024"
    },
    {
      "panel_num": 3,
      "visual": "Second character responding...",
      "dialogue": "Other: \"Response.\"",
      "characters": ["OtherCharacter"],
      "location": "LocationKey",
      "aspect_ratio": "3:4",
      "size": "768x1024"
    }
  ]
}
```

**Key fields:**
- `layout` - Named layout (see Layout System below). If omitted, auto-detects based on panel count.
- `characters` - List (database lookup) or dict (embedded descriptions). List is preferred.

### Character Entry (`data/characters.json`)

```json
{
  "CharacterName": {
    "name": "Display Name",
    "role": "Protagonist/Antagonist/Supporting",
    "full_description": "Complete visual description...",
    "description_components": {
      "head_face": "Facial features, hair, expressions...",
      "body_build": "Height, build, posture...",
      "clothing": "What they typically wear...",
      "accessories": "Items, weapons, distinguishing marks..."
    }
  }
}
```

### Location Entry (`data/locations.json`)

```json
{
  "LocationName": {
    "name": "Display Name",
    "full_description": "Complete setting description...",
    "description_components": {
      "architecture": "Built structures, terrain...",
      "atmosphere": "Mood, energy, feel...",
      "lighting": "Light sources, time of day, shadows...",
      "key_features": "Landmarks, notable elements..."
    }
  }
}
```

---

## Critical Best Practices

### 1. Centralized Descriptions with Dynamic Lookup

Descriptions are written ONCE in `data/characters.json` and `data/locations.json`, then pulled in dynamically at generation time.

**In page panels, use a LIST of character keys (not embedded descriptions):**

```json
{
  "visual": "Hero battles the dragon in formal attire",
  "characters": ["Hero.Formal", "Dragon"],
  "location": "ThroneRoom"
}
```

The generator looks up `Hero.Formal` and `Dragon` from `characters.json` and assembles the prompt dynamically.

**BAD** - Empty characters means no descriptions in prompt:
```json
{
  "visual": "Hero battles the dragon",
  "characters": []
}
```

**GOOD** - Dynamic lookup from database:
```json
{
  "visual": "Hero battles the dragon",
  "characters": ["Hero", "Dragon"]
}
```

**Note:** The generator also supports dict syntax with embedded descriptions for one-off overrides:
```json
{
  "characters": {
    "Hero": "Custom description for this specific panel only..."
  }
}
```
Use the list syntax (database lookup) by default. Use dict syntax only when you need a unique description that doesn't belong in the database.

### 2. Layout System

The layout system supports 8 named layouts with 1-4 panels. Specify in page JSON with `"layout": "layout-name"`.

| Layout | Panels | Description | Panel Aspect Ratios |
|--------|--------|-------------|---------------------|
| `splash` | 1 | Full page dramatic moment | 3:4 (1024x1536) |
| `2-horizontal` | 2 | Two stacked wide panels | 16:9 each (1536x864) |
| `2-vertical` | 2 | Two side-by-side tall panels | 9:16 each (576x1024) |
| `3-top-wide` | 3 | Wide establishing + 2 below | 16:9 top, 3:4 bottom |
| `3-bottom-wide` | 3 | 2 above + wide conclusion | 3:4 top, 16:9 bottom |
| `3-left-tall` | 3 | Tall left + 2 right | 9:16 left, 3:4 right |
| `3-right-tall` | 3 | 2 left + tall right | 3:4 left, 9:16 right |
| `grid` | 4 | Standard 2x2 grid | 3:4 all (768x1024) |

**Auto-detection:** If no layout specified:
- 1 panel → `splash`
- 2 panels → `2-horizontal`
- 3 panels → `3-top-wide`
- 4 panels → `grid`

**Layout recommendations by scene type:**
- **Establishing:** `3-top-wide`, `splash`
- **Dialogue:** `grid`, `3-left-tall`, `3-right-tall`
- **Action:** `grid`, `2-horizontal`, `splash`
- **Dramatic reveal:** `splash`, `3-bottom-wide`
- **Character focus:** `3-left-tall`, `3-right-tall`

### 3. Aspect Ratios by Position

Match your panel's aspect ratio to where it will be placed:

| Position | Ratio | Size | Use For |
|----------|-------|------|---------|
| Single cell (grid) | `3:4` | `768x1024` | Standard panels in grid or 3-panel layouts |
| Wide span | `16:9` | `1536x864` | Top/bottom in 3-panel, both in 2-horizontal |
| Tall span | `9:16` | `576x1024` | Left/right in 3-panel, both in 2-vertical |
| Full page | `3:4` | `1024x1536` | Splash pages |

**NEVER use `1:1` (square)** - creates ugly gaps in all layouts.

### 4. Gemini Aspect Ratio Mapping

The generator maps these automatically:
- `tall`, `splash`, `portrait` → `9:16`
- `wide`, `landscape` → `16:9`
- `3:4` → `3:4` (native)
- `square` → `1:1`

### 5. Prompt Assembly Flow

The generator builds prompts from:
1. **Style** (`style.json`) - Applied to ALL panels
2. **Location** - Looked up from `locations.json` using the `location` key
3. **Characters** - Two modes:
   - **List** (preferred): `["Hero", "Villain"]` → looks up each from `characters.json`
   - **Dict** (override): `{"Hero": "custom desc..."}` → uses embedded description
4. **Visual** - The scene description
5. **Dialogue** - Triggers speech bubble instructions

### 6. Iterating on Descriptions

If generated images don't match expectations:
1. Update the character/location description in the database
2. Be more specific about visual details
3. Regenerate just that panel:
   - Delete `output/panels/page-XXX-panel-Y*.png`
   - Run generator again for that page

### 7. Character and Location Variants

Use **dot notation** for character/location variants (different outfits, states, transformations):

```
Base character: Hero
Formal outfit:  Hero.Formal
Injured state:  Hero.Injured
Transformed:    Hero.Transformed
```

Each variant is a **complete, standalone entry** in the database - not a partial override.

**Common variant types:**
| Category | Examples | Use For |
|----------|----------|---------|
| Outfits | `.Formal`, `.Casual`, `.Battle`, `.Ceremonial` | Different clothing/armor |
| States | `.Injured`, `.Exhausted`, `.Triumphant` | Physical conditions |
| Transformations | `.Transformed`, `.Corrupted`, `.Glowing` | Magical changes |
| Timeline | `.Young`, `.Old`, `.Flashback` | Age/time differences |

**When to create a variant vs modify base:**
- **New variant:** Character appears significantly different (new outfit, injured, transformed)
- **Modify base:** Minor tweaks to improve generation consistency

**In page panels, reference variants by full key:**
```json
{
  "visual": "Hero arrives at the royal ball",
  "characters": ["Hero.Formal", "Princess"],
  "location": "ThroneRoom.Decorated"
}
```

---

## Commands Reference

### Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys in .env
```

### Generation
```bash
# Generate with Gemini (recommended)
python scripts/core/generate_gemini.py 1        # Single page
python scripts/core/generate_gemini.py 1-10     # Page range
python scripts/core/generate_gemini.py 1,3,5    # Specific pages

# Generate with OpenAI (creates 3 variants per panel)
python scripts/core/generate_openai.py 1-10

# Review and select variants (OpenAI workflow)
python scripts/core/review.py 1
```

### Assembly
```bash
# Assemble single page
python scripts/core/assemble.py 1

# Assemble all pages
python scripts/core/assemble.py

# Assemble with CBZ packaging
python scripts/core/assemble.py --title "My Graphic Novel"

# Cleanup variants after assembly
python scripts/core/assemble.py --cleanup-variants
```

---

## Cost Estimates

| Provider | Cost/Image | Notes |
|----------|------------|-------|
| Gemini 3 Pro | ~$0.13 | Daily quota limits, 1 image per panel |
| OpenAI gpt-image-1 | ~$0.02-0.04 | Higher quality, 3 variants for selection |

**Example:** 24-page comic with 4 panels each = 96 images
- Gemini: ~$12.50
- OpenAI (with variants): ~$6-12

---

## Resuming Interrupted Work

The generators automatically skip existing files:

```bash
# Check what's been generated
ls output/panels/ | wc -l

# Continue where you left off (skips existing)
python scripts/core/generate_gemini.py 1-24
```

---

## Output Structure

```
output/
├── panels/
│   ├── page-001-panel-1.png      # Final selected panel
│   ├── page-001-panel-1-v1.png   # Variant (OpenAI workflow)
│   ├── page-001-panel-1-v2.png   # Variant
│   └── ...
├── pages/
│   ├── page-001.png              # Assembled page (1600x2400)
│   └── ...
└── comic.cbz                     # Packaged comic
```

---

## Web Reader Deployment

The `docs/` folder contains a GitHub Pages-ready comic reader:

1. Convert pages to WebP:
```bash
for f in output/pages/*.png; do
  cwebp -q 85 "$f" -o "docs/images/pages/$(basename ${f%.png}.webp)"
done
```

2. Generate thumbnails:
```bash
for f in docs/images/pages/*.webp; do
  convert "$f" -resize 300x "docs/images/thumbnails/$(basename $f)"
done
```

3. Update `docs/data/pages.json` with page metadata

4. Push to GitHub and enable Pages

---

## Example Prompts for Users

When starting a new project, users might say:

- "I have a short story in input/story.md - turn it into a 12-page comic"
- "Here's my D&D campaign notes - create a graphic novel from the adventure"
- "I'll paste my screenplay - help me visualize it as a comic"
- "I have a children's book outline - make it into an illustrated story"

Your job is to:
1. Read and understand their source material
2. Extract characters, locations, plot
3. Create the databases and storyboard
4. Generate images iteratively with their feedback
5. Assemble and package the final comic
