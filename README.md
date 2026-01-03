# Graphic Novel Generator

Create AI-generated graphic novels from any story, transcript, or creative writing using Claude Code as your creative partner.

## Overview

This project provides a complete workflow for generating professional-quality graphic novels/comic books using AI image generation. It's designed to work with **Claude Code** (claude.ai/code) as the intelligent orchestrator that reads your source material, extracts characters and locations, creates storyboards, and generates images iteratively.

**What makes this different:** No complex scripts to configure. Just give Claude Code your story and let it handle the extraction, storyboarding, and generation process.

## Features

- **Dual API Support**: Google Gemini and OpenAI image generation
- **Intelligent Extraction**: Claude Code reads your source and builds character/location databases
- **Iterative Workflow**: Review and refine each page before moving on
- **Variant Selection**: Generate multiple options per panel (OpenAI mode)
- **Page Assembly**: Automatic layout with professional comic book styling
- **CBZ Packaging**: Export to standard comic book format
- **Web Reader**: GitHub Pages-ready comic viewer included

## Prerequisites

- Python 3.10+
- [Claude Code](https://claude.ai/code) CLI
- Google API key (for Gemini) and/or OpenAI API key

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/yourusername/graphic-novel-generator.git
cd graphic-novel-generator

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
cp .env.example .env
# Edit .env and add your API keys
```

### 3. Add Your Source Material

Put your story, transcript, or outline in the `input/` folder. Supported formats:
- Markdown files (`.md`)
- Plain text (`.txt`)
- Or just paste content directly to Claude Code

### 4. Start Claude Code

```bash
claude
```

### 5. Tell Claude What You Want

Example prompts:
- "I have a short story in input/story.md - turn it into a 12-page comic"
- "Read my D&D campaign notes and create a graphic novel from the adventure"
- "Help me visualize this screenplay as a comic book"

Claude Code will:
1. Read your source material
2. Ask clarifying questions about style and scope
3. Extract characters and locations into databases
4. Create page-by-page storyboards for your approval
5. Generate images and iterate based on your feedback
6. Assemble and package the final comic

## Project Structure

```
graphic-novel-generator/
├── CLAUDE.md              # Instructions for Claude Code
├── README.md              # This file
├── .env.example           # API key template
├── requirements.txt       # Python dependencies
│
├── scripts/
│   ├── core/
│   │   ├── generate_gemini.py   # Gemini image generation
│   │   ├── generate_openai.py   # OpenAI image generation
│   │   ├── review.py            # Web UI for variant selection
│   │   └── assemble.py          # Page assembly + CBZ
│   └── utilities/
│       └── layout_engine.py     # Page layout algorithms
│
├── data/
│   ├── characters.json    # Character descriptions (Claude populates)
│   ├── locations.json     # Location descriptions (Claude populates)
│   ├── style.json         # Art style configuration
│   └── pages/             # Page JSON files (Claude creates)
│
├── input/                 # Your source material goes here
│   └── example.md         # Sample input format
│
├── output/
│   ├── panels/            # Generated panel images
│   ├── pages/             # Assembled pages
│   └── comic.cbz          # Packaged comic
│
└── docs/                  # GitHub Pages web reader
```

## Manual Commands

While Claude Code handles most of the workflow, you can run scripts directly:

```bash
# Generate panels with Gemini
python scripts/core/generate_gemini.py 1-10

# Generate panels with OpenAI (3 variants each)
python scripts/core/generate_openai.py 1-10

# Review and select variants (OpenAI workflow)
python scripts/core/review.py 1

# Assemble pages
python scripts/core/assemble.py

# Assemble with custom title
python scripts/core/assemble.py --title "My Epic Story"
```

## Cost Estimates

| Provider | Cost/Image | Best For |
|----------|------------|----------|
| Gemini 3 Pro | ~$0.13 | Fast iteration, single best image |
| OpenAI gpt-image-1 | ~$0.02-0.04 | Variant selection, higher quality |

**Example:** A 24-page comic with 4 panels per page (96 images):
- Gemini: ~$12.50
- OpenAI with variants: ~$6-12

## Input Formats

Claude Code can work with various input formats:

### Story/Prose
```markdown
# Chapter 1: The Beginning

Elena stood at the edge of the cliff, wind whipping her red hair...
```

### Transcript/Dialogue
```
NARRATOR: The city slept under a blanket of fog.
DETECTIVE: [examining the crime scene] Something doesn't add up.
PARTNER: What do you mean?
```

### Outline/Notes
```
- Scene 1: Hero receives the call to adventure
  - Location: Small village, morning
  - Characters: Hero (reluctant), Mentor (wise elder)
  - Key moment: The prophecy is revealed
```

## Web Reader

The `docs/` folder contains a ready-to-deploy comic reader for GitHub Pages:

1. Generate your comic
2. Convert pages to WebP and update metadata
3. Push to GitHub and enable Pages
4. Share your comic with the world

## Tips for Best Results

1. **Be specific about characters**: Include distinctive visual features that can be consistently rendered
2. **Describe lighting**: Lighting dramatically affects mood and consistency
3. **Start small**: Begin with 3-5 pages to refine your style before generating the full comic
4. **Iterate on descriptions**: If a character doesn't look right, update their description and regenerate
5. **Use 3:4 aspect ratio** for grid panels to avoid layout issues

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions welcome! Please open an issue or PR.

## Acknowledgments

Built with:
- [Claude Code](https://claude.ai/code) by Anthropic
- [Google Gemini](https://ai.google.dev/) for image generation
- [OpenAI](https://openai.com/) for image generation
- [Pillow](https://pillow.readthedocs.io/) for image processing
