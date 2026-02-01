---
name: pptx
description: Create, edit, and analyze PowerPoint presentations (.pptx). Use when Claude needs to generate slides from scratch, modify existing presentations, or extract content from .pptx files.
---

# PPTX Creation, Editing, and Analysis

## Reading and Analyzing

### Text extraction
```bash
python -m markitdown path-to-file.pptx
```

### Raw XML access
For comments, speaker notes, layouts, animations, design elements:
```bash
python ooxml/scripts/unpack.py <office_file> <output_dir>
```

Key file structures:
- `ppt/presentation.xml` — Main metadata and slide references
- `ppt/slides/slide{N}.xml` — Individual slide contents
- `ppt/notesSlides/notesSlide{N}.xml` — Speaker notes
- `ppt/theme/` — Theme and styling
- `ppt/media/` — Images and media

## Creating New Presentations (from scratch)

Use the **html2pptx** workflow: convert HTML slides to PowerPoint.

### Design Principles
1. Analyze content and choose design elements matching the subject
2. Use web-safe fonts only: Arial, Helvetica, Times New Roman, Georgia, Courier New, Verdana, Tahoma, Trebuchet MS, Impact
3. Build color palette: 3-5 colors (dominant + supporting + accent)
4. Ensure strong contrast and readability
5. Be consistent across slides

### Layout Tips
- **Two-column layout (preferred)**: Header spanning full width, two columns below
- **Full-slide layout**: Let charts/tables take the entire slide
- **NEVER vertically stack** charts/tables below text in a single column

### Workflow
1. Read html2pptx.md reference completely
2. Create HTML file per slide (720pt x 405pt for 16:9)
3. Convert via html2pptx.js, add charts/tables with PptxGenJS API
4. Visual validation: `python scripts/thumbnail.py output.pptx` — check for text cutoff, overlap, contrast issues
5. Fix and regenerate until correct

## Editing Existing Presentations

1. Read ooxml.md reference completely
2. Unpack: `python ooxml/scripts/unpack.py <file> <output_dir>`
3. Edit XML files (primarily `ppt/slides/slide{N}.xml`)
4. Validate after each edit: `python ooxml/scripts/validate.py <dir> --original <file>`
5. Repack: `python ooxml/scripts/pack.py <input_dir> <output_file>`

## Using Templates

1. Extract text: `python -m markitdown template.pptx > template-content.md`
2. Create thumbnails: `python scripts/thumbnail.py template.pptx`
3. Analyze template and create inventory (slide-by-slide, 0-indexed)
4. Map content to template slides, create outline
5. Rearrange: `python scripts/rearrange.py template.pptx working.pptx 0,34,34,50,52`
6. Extract text shapes: `python scripts/inventory.py working.pptx text-inventory.json`
7. Create replacement JSON with paragraphs, formatting, bullets
8. Apply: `python scripts/replace.py working.pptx replacement-text.json output.pptx`

## Converting to Images
```bash
soffice --headless --convert-to pdf presentation.pptx
pdftoppm -jpeg -r 150 presentation.pdf slide
```

## Dependencies
- markitdown: `pip install "markitdown[pptx]"`
- pptxgenjs: `npm install -g pptxgenjs`
- playwright: `npm install -g playwright`
- sharp: `npm install -g sharp`
- LibreOffice: `sudo apt-get install libreoffice`
- Poppler: `sudo apt-get install poppler-utils`
- defusedxml: `pip install defusedxml`
