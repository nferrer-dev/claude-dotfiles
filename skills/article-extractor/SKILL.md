---
name: article-extractor
description: Extract clean article content from URLs (blog posts, articles, tutorials) and save as readable text. Use when user wants to download, extract, or save an article/blog post from a URL without ads, navigation, or clutter.
allowed-tools: Bash,Write
---

# Article Extractor

Extracts main content from web articles, removing navigation, ads, and clutter.

## When to Use

- User provides an article/blog URL and wants the text
- User asks to "download this article" or "extract content from [URL]"
- Need clean article text for analysis

## Tool Priority

1. **reader** (Mozilla Readability) — best all-around
2. **trafilatura** — best for blogs/news, non-English
3. **Fallback** — curl + basic HTML parsing

## Installation

```bash
# Option 1 (recommended)
npm install -g @mozilla/readability-cli

# Option 2
pip3 install trafilatura
```

## Workflow

```bash
ARTICLE_URL="$1"

# Detect tool
if command -v reader &> /dev/null; then
    TOOL="reader"
elif command -v trafilatura &> /dev/null; then
    TOOL="trafilatura"
else
    TOOL="fallback"
fi

# Extract
case $TOOL in
    reader)
        reader "$ARTICLE_URL" > temp_article.txt
        TITLE=$(head -n 1 temp_article.txt | sed 's/^# //')
        ;;
    trafilatura)
        METADATA=$(trafilatura --URL "$ARTICLE_URL" --json)
        TITLE=$(echo "$METADATA" | python3 -c "import json, sys; print(json.load(sys.stdin).get('title', 'Article'))")
        trafilatura --URL "$ARTICLE_URL" --output-format txt --no-comments > temp_article.txt
        ;;
    fallback)
        TITLE=$(curl -s "$ARTICLE_URL" | grep -oP '<title>\K[^<]+' | head -n 1)
        TITLE=${TITLE%% - *}
        curl -s "$ARTICLE_URL" | python3 -c "
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
        ;;
esac

# Clean filename and save
FILENAME=$(echo "$TITLE" | tr '/:?\"<>|' '-' | cut -c 1-80 | sed 's/ *$//').txt
mv temp_article.txt "$FILENAME"
echo "Saved: $FILENAME"
head -n 10 "$FILENAME"
```

## Error Handling

- **Paywall/login**: Inform user extraction requires authentication
- **No content**: Try alternate tool, then inform user
- **Tool not installed**: Offer install command, use fallback
