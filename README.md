# claude-dotfiles

My [Claude Code](https://docs.anthropic.com/en/docs/claude-code) configuration — skills, agents, plugins, and settings.

## What's included

- **17 skills** — deep-research, pdf/docx/xlsx/pptx, notebooklm, mcp-builder, article-extractor, and more
- **2 agents** — general code reviewer, security reviewer (OWASP Top 10)
- **1 command** — `orchestrate` (sequential agent workflow)
- **6 plugin marketplaces** — official, superpowers, trailofbits, mgrep, ykdojo, claude-night-market
- **12 plugins enabled** — superpowers, hookify, context7, modern-python, static-analysis, and more

See [MANIFEST.md](MANIFEST.md) for the full inventory.

## Prerequisites

New to Claude Code? Follow the [official setup guide](https://code.claude.com/docs/en/setup) to install the CLI and authenticate before using this config.

## Install

```bash
git clone https://github.com/nferrer-dev/claude-dotfiles.git
cd claude-dotfiles
./install.sh
```

The install script will:
1. Back up your existing `~/.claude/settings.json`
2. Copy settings, skills, agents, and commands to `~/.claude/`
3. Clone plugin marketplaces from GitHub
4. Prompt to install Python dependencies (httpx, playwright)
5. Check for optional API keys (`GEMINI_API_KEY`, `HF_TOKEN`, `COMPOSIO_API_KEY`)

## Optional API keys

Some skills require API keys set as environment variables:

| Variable | Skill | Get one at |
|----------|-------|------------|
| `GEMINI_API_KEY` | deep-research | https://aistudio.google.com/ |
| `HF_TOKEN` | hugging-face-datasets | https://huggingface.co/settings/tokens |
| `COMPOSIO_API_KEY` | connect-apps | https://composio.dev/ |

## License

MIT
