# claude-dotfiles

My [Claude Code](https://docs.anthropic.com/en/docs/claude-code) configuration — optimized for SWE + quant trading on Windows 11.

## What's included

### Settings (`settings.json`)
- 84+ deny rules (destructive ops, credential files, force pushes, device access)
- 21 allow rules for power-user workflow
- Agent teams enabled (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`)
- Effort level locked to `high`
- Statusline with token/cost/git info

### Hooks (13 total)
| Event | Hook | Purpose |
|-------|------|---------|
| UserPromptSubmit | trace compactor | Auto-compacts Python tracebacks in prompts |
| PreToolUse (Edit) | config-protection.sh | Blocks edits to linter/formatter configs |
| PreToolUse (Bash) | 5 inline blockers | rm -rf, git push main, kill, rmdir, wsl |
| PostToolUse (Bash) | command logger | Timestamps all bash commands to log file |
| PostToolUse (Bash) | trace compactor | Compacts tracebacks in command output |
| PostToolUse (5 matchers) | injection defender | Scans Read/WebFetch/Bash/Grep/Task for prompt injection |

### MCP Servers (11, all lazy-loaded)
| Server | Purpose | Key Required |
|--------|---------|:---:|
| sequential-thinking | Structured reasoning | No |
| playwright | Browser automation | No |
| context-mode | Tool output sandboxing | No |
| chrome-devtools | Browser debugging (Google) | No |
| yfinance | Free market data | No |
| github-mcp | GitHub API | GitHub PAT |
| tavily | Web search | Tavily key |
| firecrawl | Web scraping | Firecrawl key |
| gemini | Gemini API (deep research, 1M context) | Gemini key |
| codex | OpenAI Codex (code second opinions) | OpenAI key |
| claude-context | Zilliz vector memory | OpenAI + Zilliz keys |

### Plugins (11)
superpowers, context7, pyright-lsp, hookify, modern-python, property-based-testing, static-analysis, dx, sanctum, claude-notifications-go, flow-next

### Skills (30)
**Finance:** alpha-vantage, edgartools, fred-economic-data, hedgefundmonitor, timesfm-forecasting
**Data/ML:** scikit-learn, statsmodels, statistical-analysis, polars, shap, pymc, sympy, networkx, exploratory-data-analysis
**Visualization:** matplotlib, plotly, seaborn
**Documents:** pdf, xlsx
**Research:** article-extractor, tapestry, youtube-transcript, deep-research, notebooklm, langsmith-fetch, hugging-face-datasets
**Dev:** verification-loop, iterative-retrieval, skill-creator, mcp-builder

### Agents (2)
- general-code-reviewer — broad quality/security/maintainability review
- security-reviewer — OWASP Top 10, secrets detection, input validation

## Installation

### Prerequisites
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed
- [Node.js](https://nodejs.org/) (LTS) — required for MCP servers
- Python 3.8+ with pip
- Git
- Windows: `C:\Program Files\nodejs` must be in your system PATH

### Quick install
```bash
git clone https://github.com/nferrer-dev/claude-dotfiles.git
cd claude-dotfiles
chmod +x install.sh
./install.sh
```

The install script will:
1. Back up your existing `settings.json`
2. Copy config, hooks, skills, agents, and commands
3. Install trace compactor (`claude-tools`)
4. Set up plugin marketplaces and install 11 plugins
5. Install MCP servers (prompts for API keys — press Enter to skip any)
6. Pre-cache npm packages for faster MCP startup
7. Check Python dependencies
8. Windows-specific: create `python3` wrapper, patch hookify, inject PATH into MCP envs

### API keys
The install script prompts for keys interactively. No keys are stored in this repo. You'll need:

| Key | Source | Required For |
|-----|--------|-------------|
| GitHub PAT | `gh auth token` or [github.com/settings/tokens](https://github.com/settings/tokens) | github-mcp |
| Tavily API key | [tavily.com](https://tavily.com) | tavily |
| Firecrawl API key | [firecrawl.dev](https://firecrawl.dev) | firecrawl |
| Gemini API key | [aistudio.google.com](https://aistudio.google.com) or GCP Console | gemini |
| OpenAI API key | [platform.openai.com](https://platform.openai.com) | codex, claude-context |
| Zilliz endpoint + token | [cloud.zilliz.com](https://cloud.zilliz.com) | claude-context |

### MCP server template
See `mcp-servers.json.template` for the full MCP configuration with placeholder keys. Useful for manual setup or non-Windows platforms.

## Windows Notes
- MCP servers use `cmd /c npx` wrapper (required on Windows)
- Each MCP server has `PATH` env var injected pointing to Node.js
- `python3` wrapper script created at `/usr/bin/python3` for Git Bash compatibility
- Hookify plugin needs `PLUGIN_ROOT` fallback patch (install script handles this)

## Model Routing
Configured in CLAUDE.md — Claude uses different models for different tasks:
- **Claude Opus**: Primary coding, architecture, complex reasoning
- **Claude Sonnet/Haiku**: Simple subagent tasks (search, formatting)
- **Gemini MCP**: Deep research, 1M context window analysis
- **Codex MCP**: Second opinion on code from GPT
- **Tavily MCP**: Quick factual web searches
- **Firecrawl MCP**: Deep web scraping

## License
Personal configuration — use at your own risk.
