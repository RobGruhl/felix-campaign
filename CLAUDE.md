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
      "characters": {
        "HeroName": "Contextual description for THIS panel..."
      },
      "npcs": {},
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
  "panel_count": 4,
  "is_spread": false,
  "panels": [
    {
      "panel_num": 1,
      "annotation": "Tall",
      "visual": "Detailed description of what the panel shows...",
      "dialogue": "Speaker: \"Dialogue text.\" Other: \"Response.\"",
      "characters": {
        "CharacterKey": "Character description for THIS specific panel context"
      },
      "npcs": {
        "NPCKey": "NPC description if any"
      },
      "location": "LocationKey",
      "aspect_ratio": "3:4",
      "size": "768x1024"
    }
  ]
}
```

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

### 1. EMBED Character Descriptions in Panels

**BAD** - Empty dict means no descriptions in prompt:
```json
{
  "visual": "Hero battles the dragon",
  "characters": {}
}
```

**GOOD** - Embedded descriptions for consistency:
```json
{
  "visual": "Hero battles the dragon",
  "characters": {
    "Hero": "Young warrior with bright eyes, leather armor, wielding a glowing sword. Determined expression, battle stance."
  }
}
```

### 2. Aspect Ratios for Grid Layouts

| Layout | Ratio | Size | Use For |
|--------|-------|------|---------|
| 2x2 Grid | `3:4` | `768x1024` | Standard panels |
| Wide Shot | `16:9` | `1536x1024` | Establishing shots |
| Splash | `9:16` | `1024x1536` | Dramatic moments |

**NEVER use `1:1` (square) for grid pages** - creates ugly gaps.

### 3. Gemini Aspect Ratio Mapping

The generator maps these automatically:
- `tall`, `splash`, `portrait` → `9:16`
- `wide`, `landscape` → `16:9`
- `3:4` → `3:4` (native)
- `square` → `1:1`

### 4. Prompt Assembly Flow

The generator builds prompts from:
1. **Style** (`style.json`) - Applied to ALL panels
2. **Location** - Only if `location` field points to key in `locations.json`
3. **Characters** - From panel's `characters` dict (embedded preferred)
4. **Visual** - The scene description
5. **Dialogue** - Triggers speech bubble instructions

### 5. Iterating on Descriptions

If generated images don't match expectations:
1. Update character descriptions in the page JSON
2. Be more specific about visual details
3. Regenerate just that panel:
   - Delete `output/panels/page-XXX-panel-Y*.png`
   - Run generator again for that page

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
