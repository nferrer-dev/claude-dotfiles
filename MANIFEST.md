# Claude Code Configuration Manifest

## Settings

| File | Purpose |
|------|---------|
| `settings.json` | Global settings (env, permissions, hooks, plugins, statusline) |
| `settings.local.json` | Local overrides (machine-specific, not in repo) |
| `CLAUDE.md` | Global workflow principles and code quality standards |
| `statusline-command.sh` | Custom status bar (dir, git branch, model, tokens, cost) |

## Skills (35)

| Skill | Purpose |
|-------|---------|
| `alpha-vantage` | Stock market, forex, crypto data via Alpha Vantage API |
| `article-extractor` | Extract clean article content from URLs |
| `connect-apps` | Connect Claude to 1000+ external apps via Composio |
| `context-optimization` | KV-cache optimization and context partitioning |
| `deep-research` | Autonomous multi-step research via Gemini Deep Research |
| `docx` | Read, create, and edit Word documents |
| `edgartools` | SEC EDGAR filings, company data, XBRL analysis |
| `exploratory-data-analysis` | Scientific data formats and EDA workflows |
| `fred-economic-data` | Federal Reserve Economic Data (FRED) API |
| `hedgefundmonitor` | Hedge fund monitoring and analysis |
| `hugging-face-datasets` | Create and manage Hugging Face Hub datasets |
| `iterative-retrieval` | Dispatch-evaluate-refine loop for file discovery |
| `langsmith-fetch` | Debug LangChain/LangGraph agents via LangSmith traces |
| `matplotlib` | Publication-quality plots with matplotlib |
| `mcp-builder` | Guide for creating MCP servers (FastMCP / MCP SDK) |
| `networkx` | Graph analysis, network algorithms, visualization |
| `notebooklm` | Query Google NotebookLM for source-grounded answers |
| `pdf` | Extract, create, merge, split PDF documents |
| `playwright-skill` | Browser automation with Playwright (auto-detect, testing) |
| `plotly` | Interactive charts and dashboards with Plotly |
| `polars` | Fast DataFrame operations with Polars |
| `pptx` | Create, edit, analyze PowerPoint presentations |
| `pymc` | Bayesian modeling and probabilistic programming |
| `scikit-learn` | Machine learning pipelines, classification, regression |
| `seaborn` | Statistical visualization with seaborn |
| `shap` | Model explainability with SHAP values |
| `skill-creator` | Guide for creating new Claude Code skills |
| `statistical-analysis` | Hypothesis testing, regression, diagnostics |
| `statsmodels` | Time series, econometrics, statistical models |
| `sympy` | Symbolic mathematics, algebra, calculus |
| `tapestry` | Unified content extraction + action planning from URLs |
| `timesfm-forecasting` | Time series forecasting with Google TimesFM |
| `verification-loop` | 6-phase verification after code changes |
| `xlsx` | Create, edit, analyze Excel spreadsheets |
| `youtube-transcript` | Download YouTube video transcripts |

## Agents (2)

| Agent | Purpose |
|-------|---------|
| `general-code-reviewer` | Code quality, security, and maintainability reviews |
| `security-reviewer` | OWASP Top 10, secrets, injection, unsafe crypto detection |

## Commands (1)

| Command | Purpose |
|---------|---------|
| `orchestrate` | Sequential agent workflow for complex tasks |

## Plugins / Marketplaces (9)

| Marketplace | Source |
|-------------|--------|
| `claude-plugins-official` | Official Anthropic plugins |
| `superpowers-marketplace` | Superpowers plugin suite |
| `Mixedbread-Grep` | mgrep search tool |
| `trailofbits` | Trail of Bits security tools |
| `ykdojo` | YK Dojo plugins |
| `claude-night-market` | Community plugins |
| `cc-marketplace` | CC Marketplace (safety-net) |
| `thedotmack` | claude-mem persistent memory |
| `claude-notifications-go` | Desktop notifications |

### Enabled Plugins (15)

| Plugin | Marketplace |
|--------|-------------|
| superpowers | claude-plugins-official |
| context7 | claude-plugins-official |
| pyright-lsp | claude-plugins-official |
| hookify | claude-plugins-official |
| mgrep | Mixedbread-Grep |
| modern-python | trailofbits |
| property-based-testing | trailofbits |
| static-analysis | trailofbits |
| dx | ykdojo |
| conserve | claude-night-market |
| sanctum | claude-night-market |
| memory-palace | claude-night-market |
| safety-net | cc-marketplace |
| claude-mem | thedotmack |
| claude-notifications-go | claude-notifications-go |

## Hooks

| Hook | Trigger | Action |
|------|---------|--------|
| Block rm -rf | PreToolUse (Bash) | Prevents recursive force-delete, suggests trash |
| Block push to main | PreToolUse (Bash) | Blocks git push to main/master |
| Command logger | PostToolUse (Bash) | Logs all bash commands to bash-commands.log |

## Security (Deny Rules)

Blocks: `rm -rf`, `sudo`, `mkfs`, `dd`, `wget|bash`, `git push --force`, `git reset --hard`
Protects: `~/.ssh`, `~/.gnupg`, `~/.aws`, `~/.azure`, `~/.config/gh`, `~/.git-credentials`, `~/.docker/config.json`, `~/.kube`, `~/.npmrc`, `~/.pypirc`, `~/.gem/credentials`, `~/.bashrc`, `~/.zshrc`

## Dependencies

### System (required)
- `jq` — hooks parse JSON
- `bc` — statusline cost calculation
- `git` — marketplace cloning

### Node.js
- `playwright` — playwright-skill (installed via `npm install` in skill dir)
- `@mozilla/readability-cli` — article-extractor (global, optional)
- `pptxgenjs` — pptx skill (global, optional)
- `sharp` — image processing (global, optional)

### Python (core)
httpx, requests, pandas, numpy, matplotlib, seaborn, scikit-learn, plotly, polars, networkx, statsmodels, sympy, scipy, arviz, pymc, shap, openpyxl, pypdf, pdfplumber, reportlab, pingouin, duckdb, edgartools, kaleido, huggingface_hub

### Python (optional/heavy)
torch, timesfm, xgboost, mlflow, dash, yt-dlp, defusedxml, markitdown, pdf2image, pytesseract, joblib

### Python (notebooklm only)
patchright, python-dotenv

## Excluded from Repo (machine-specific)

- `.credentials.json` — Auth tokens
- `settings.local.json` — Machine-specific allow rules
- `history.jsonl` — Conversation history
- `bash-commands.log` — Command log
- `projects/` — Per-project session data
- `cache/`, `debug/`, `downloads/` — Transient data
- `session-env/`, `session-state.md` — Active session state
- `tasks/`, `todos/`, `plans/` — Ephemeral work items
- `skills/playwright-skill/node_modules/` — Installed by install.sh
