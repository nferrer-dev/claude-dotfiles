---
name: tapestry
description: Unified content extraction and action planning. Use when user says "tapestry <URL>", "weave <URL>", or wants to extract content from a URL (YouTube, article, PDF) and optionally create an action plan. Automatically detects content type and processes accordingly.
allowed-tools: Bash,Read,Write
---

# Tapestry: Unified Content Extraction

Orchestrates content extraction from any URL by detecting type and using the appropriate method.

## When to Use

- User says "tapestry [URL]" or "weave [URL]"
- User wants to extract and save content from a URL
- User provides a URL and wants clean text output

## URL Detection

```bash
URL="$1"

# YouTube
if [[ "$URL" =~ youtube\.com/watch || "$URL" =~ youtu\.be/ || "$URL" =~ youtube\.com/shorts ]]; then
    CONTENT_TYPE="youtube"
# PDF
elif [[ "$URL" =~ \.pdf$ ]] || curl -sI "$URL" | grep -i "Content-Type: application/pdf" > /dev/null; then
    CONTENT_TYPE="pdf"
# Default to article
else
    CONTENT_TYPE="article"
fi
```

## Extraction by Type

### YouTube
Use youtube-transcript skill: yt-dlp for subtitles, Whisper as fallback.

### Article
Priority: `reader` (Mozilla Readability) → `trafilatura` → curl fallback.

```bash
if command -v reader &> /dev/null; then
    reader "$URL" > temp_article.txt
    TITLE=$(head -n 1 temp_article.txt | sed 's/^# //')
elif command -v trafilatura &> /dev/null; then
    METADATA=$(trafilatura --URL "$URL" --json)
    TITLE=$(echo "$METADATA" | python3 -c "import json, sys; print(json.load(sys.stdin).get('title', 'Article'))")
    trafilatura --URL "$URL" --output-format txt --no-comments > temp_article.txt
else
    TITLE=$(curl -s "$URL" | grep -oP '<title>\K[^<]+' | head -n 1)
    # Fallback HTML parser
    curl -s "$URL" | python3 -c "
from html.parser import HTMLParser
import sys
class E(HTMLParser):
    def __init__(self):
        super().__init__()
        self.content=[]; self.skip={'script','style','nav','header','footer','aside','form'}; self.ok=False
    def handle_starttag(self,t,a):
        if t not in self.skip and t in {'p','article','main'}: self.ok=True
    def handle_data(self,d):
        if self.ok and d.strip(): self.content.append(d.strip())
    def get(self): return '\n\n'.join(self.content)
p=E(); p.feed(sys.stdin.read()); print(p.get())
" > temp_article.txt
fi
```

### PDF
```bash
curl -L -o "$PDF_FILENAME" "$URL"
pdftotext "$PDF_FILENAME" "${PDF_FILENAME%.pdf}.txt"
```

## Output

Save extracted content with cleaned filename, show preview (first 10 lines), report word count.

## Dependencies

- **YouTube**: yt-dlp, Python 3
- **Articles**: reader (npm) OR trafilatura (pip), falls back to curl
- **PDFs**: curl, pdftotext (poppler-utils)
