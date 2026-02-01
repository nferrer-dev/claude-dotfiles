---
name: docx
description: Read, create, and edit Word documents (.docx). Use when Claude needs to extract text from, generate, or modify Word documents including tracked changes/redlining.
---

# DOCX Tools and Workflows

## Reading/Analyzing

### Text extraction
```bash
# Convert to markdown (preserves tracked changes)
pandoc --track-changes=all document.docx -o output.md
```

### Raw XML access
For comments, formatting, metadata — unpack the .docx (it's a ZIP):
```bash
python ooxml/scripts/unpack.py <office_file> <output_dir>
```

Key files inside:
- `word/document.xml` — Main content
- `word/comments.xml` — Comments
- `word/styles.xml` — Style definitions
- `word/media/` — Embedded images

## Creating New Documents (docx-js)

Use JavaScript/TypeScript with the docx library:

```javascript
const { Document, Paragraph, TextRun, Packer } = require('docx');
const fs = require('fs');

const doc = new Document({
  sections: [{
    children: [
      new Paragraph({
        children: [new TextRun({ text: "Hello World", bold: true })],
      }),
      new Paragraph({
        children: [new TextRun("Body text here.")],
      }),
    ],
  }],
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync("output.docx", buffer);
});
```

## Editing Existing Documents

### Simple edits (your own document)
1. Unpack: `python ooxml/scripts/unpack.py doc.docx unpacked/`
2. Edit XML files in `unpacked/word/document.xml`
3. Repack: `python ooxml/scripts/pack.py unpacked/ edited.docx`

### Redlining (tracked changes — for formal/shared documents)
Required for legal, academic, business, or government documents.

1. Convert to markdown: `pandoc --track-changes=all document.docx -o content.md`
2. Identify changes in batches (3-10 related changes per batch)
3. Unpack the document
4. Implement changes using OOXML tracked-change markup
5. Validate and repack

Key principle: Minimal, precise edits — only mark text that actually changes.
Break replacements into: [unchanged text] + [deletion] + [insertion] + [unchanged text].

## Converting to Images
```bash
# DOCX -> PDF -> JPEG
soffice --headless --convert-to pdf document.docx
pdftoppm -jpeg -r 150 document.pdf slide
```
