# Claude Code Configuration Manifest

## Settings

| File | Purpose |
|------|---------|
| `settings.json` | Global Claude Code settings |
| `settings.local.json` | Local overrides (machine-specific) |

## Skills (17)

| Skill | Purpose |
|-------|---------|
| `article-extractor` | Extract clean article content from URLs |
| `connect-apps` | Connect Claude to 1000+ external apps via Composio |
| `context-optimization` | KV-cache optimization and context partitioning |
| `deep-research` | Autonomous multi-step research via Gemini Deep Research |
| `docx` | Read, create, and edit Word documents |
| `hugging-face-datasets` | Create and manage Hugging Face Hub datasets |
| `iterative-retrieval` | Dispatch-evaluate-refine loop for file discovery |
| `langsmith-fetch` | Debug LangChain/LangGraph agents via LangSmith traces |
| `mcp-builder` | Guide for creating MCP servers (FastMCP / MCP SDK) |
| `notebooklm` | Query Google NotebookLM for source-grounded answers |
| `pdf` | Extract, create, merge, split PDF documents |
| `pptx` | Create, edit, analyze PowerPoint presentations |
| `skill-creator` | Guide for creating new Claude Code skills |
| `tapestry` | Unified content extraction + action planning from URLs |
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

## Plugins / Marketplaces (6)

| Marketplace | Source |
|-------------|--------|
| `Mixedbread-Grep` | mgrep search tool |
| `claude-night-market` | Community plugins |
| `claude-plugins-official` | Official Anthropic plugins |
| `superpowers-marketplace` | Superpowers plugin suite |
| `trailofbits` | Trail of Bits security tools |
| `ykdojo` | YK Dojo plugins |

### Installed Plugins (from marketplaces)

Tracked in `plugins/installed_plugins.json`. Includes:
- **conserve** — Context optimization, bloat detection, token conservation
- **sanctum** — Git workflows (commit, PR, tag, docs, tests, CI updates)
- **superpowers** — TDD, code review, brainstorming, parallel agents, git worktrees
- **hookify** — Create hooks to prevent unwanted behaviors
- **memory-palace** — Knowledge organization and retrieval
- **mgrep** — Mandatory search replacement (web + local)
- **modern-python** — Python project tooling (uv, ruff, ty)
- **property-based-testing** — Property-based testing guidance
- **static-analysis** — SARIF parsing, CodeQL, Semgrep
- **dx** — GitHub Actions failure analysis, CLAUDE.md review

## MCP Servers

Configured in `mcp-servers/`. Includes external tool integrations.

## Excluded from Repo (machine-specific)

- `.credentials.json` — Auth tokens
- `history.jsonl` — Conversation history
- `projects/` — Session logs (too large)
- `cache/`, `debug/`, `downloads/` — Transient data
- `session-env/`, `session-state.md` — Active session state
- `tasks/`, `todos/`, `plans/` — Ephemeral work items
