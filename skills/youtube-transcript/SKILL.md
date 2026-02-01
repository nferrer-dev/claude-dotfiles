---
name: youtube-transcript
description: Download YouTube video transcripts/subtitles. Use when user provides a YouTube URL and wants the transcript, captions, or text content from a video. Lighter-weight than WhisperX for quick transcript grabs.
allowed-tools: Bash,Read,Write
---

# YouTube Transcript Downloader

Downloads transcripts from YouTube videos using yt-dlp.

## When to Use

- User provides a YouTube URL and wants the transcript
- Quick transcript grab without speaker diarization
- Captions/subtitles extraction

## Requirements

- yt-dlp: `pip install yt-dlp` or `apt install yt-dlp`
- Python 3

## Workflow

### 1. Check available subtitles
```bash
yt-dlp --list-subs "YOUTUBE_URL"
```

### 2. Download (try manual first, then auto-generated)
```bash
# Manual subtitles (higher quality)
yt-dlp --write-sub --skip-download --sub-langs en --output "transcript" "URL"

# Auto-generated fallback
yt-dlp --write-auto-sub --skip-download --sub-langs en --output "transcript" "URL"
```

### 3. Convert VTT to clean text (deduplicate)
```bash
VIDEO_TITLE=$(yt-dlp --print "%(title)s" "$URL" | tr '/:?\"' '-')
VTT_FILE=$(ls transcript*.vtt | head -n 1)

python3 -c "
import sys, re
seen = set()
with open('$VTT_FILE', 'r') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('WEBVTT') and not line.startswith('Kind:') and not line.startswith('Language:') and '-->' not in line:
            clean = re.sub('<[^>]*>', '', line)
            clean = clean.replace('&amp;', '&').replace('&gt;', '>').replace('&lt;', '<')
            if clean and clean not in seen:
                print(clean)
                seen.add(clean)
" > "${VIDEO_TITLE}.txt"

rm "$VTT_FILE"
echo "Saved: ${VIDEO_TITLE}.txt"
```

### 4. Last resort: Whisper transcription
Only if no subtitles exist. Ask user first (downloads audio).

```bash
# Show size estimate
yt-dlp --print "%(filesize_approx)s" -f "bestaudio" "$URL"

# Download audio
yt-dlp -x --audio-format mp3 --output "audio_%(id)s.%(ext)s" "$URL"

# Transcribe
whisper audio_*.mp3 --model base --output_format vtt
```

## Error Handling

- **yt-dlp not installed**: `pip install yt-dlp`
- **No subtitles**: Offer Whisper transcription with size warning
- **Private/geo-blocked**: Inform user of restriction
- **Multiple languages**: Use `--sub-langs en` for English, or list with `--list-subs`
