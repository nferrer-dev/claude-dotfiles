#!/usr/bin/env bash
set -euo pipefail

CLAUDE_DIR="${HOME}/.claude"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[info]${NC} $*"; }
ok()    { echo -e "${GREEN}[ok]${NC} $*"; }
warn()  { echo -e "${YELLOW}[warn]${NC} $*"; }
err()   { echo -e "${RED}[error]${NC} $*"; }

# ── Pre-flight ───────────────────────────────────────────────
command -v claude >/dev/null 2>&1 || { err "claude CLI not found. Install: https://docs.anthropic.com/en/docs/claude-code"; exit 1; }

if [ ! -d "$CLAUDE_DIR" ]; then
  info "Creating ${CLAUDE_DIR}"
  mkdir -p "$CLAUDE_DIR"
fi

# Detect platform
IS_WINDOWS=false
if [[ "$(uname -s)" == MINGW* ]] || [[ "$(uname -s)" == MSYS* ]] || [[ "$(uname -o 2>/dev/null)" == "Msys" ]]; then
  IS_WINDOWS=true
fi

# ── Backup existing config ───────────────────────────────────
if [ -f "$CLAUDE_DIR/settings.json" ]; then
  backup="${CLAUDE_DIR}/settings.json.bak.$(date +%s)"
  info "Backing up existing settings.json to ${backup}"
  cp "$CLAUDE_DIR/settings.json" "$backup"
fi

# ── Copy dotfiles ────────────────────────────────────────────
info "Installing settings.json"
cp "$REPO_DIR/settings.json" "$CLAUDE_DIR/settings.json"

info "Installing CLAUDE.md"
cp "$REPO_DIR/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md"

info "Installing statusline script"
cp "$REPO_DIR/statusline-command.sh" "$CLAUDE_DIR/statusline-command.sh"
chmod +x "$CLAUDE_DIR/statusline-command.sh"

info "Installing agents"
mkdir -p "$CLAUDE_DIR/agents"
cp "$REPO_DIR/agents/"*.md "$CLAUDE_DIR/agents/"

info "Installing skills (30)"
mkdir -p "$CLAUDE_DIR/skills"
cp -r "$REPO_DIR/skills/"* "$CLAUDE_DIR/skills/"

info "Installing commands"
mkdir -p "$CLAUDE_DIR/commands"
cp -r "$REPO_DIR/commands/"* "$CLAUDE_DIR/commands/"

# ── Install hooks ────────────────────────────────────────────
info "Installing hooks"
mkdir -p "$CLAUDE_DIR/hooks/prompt-injection-defender"
cp "$REPO_DIR/hooks/config-protection.sh" "$CLAUDE_DIR/hooks/config-protection.sh"
chmod +x "$CLAUDE_DIR/hooks/config-protection.sh"
cp "$REPO_DIR/hooks/prompt-injection-defender/post-tool-defender.py" "$CLAUDE_DIR/hooks/prompt-injection-defender/"
cp "$REPO_DIR/hooks/prompt-injection-defender/patterns.yaml" "$CLAUDE_DIR/hooks/prompt-injection-defender/"

# ── Install trace compactor ─────────────────────────────────
info "Installing claude-tools (trace compactor)..."
if command -v pip >/dev/null 2>&1; then
  pip install git+https://github.com/tarekziade/claude-tools.git --quiet 2>/dev/null || warn "Failed to install claude-tools"
elif command -v pip3 >/dev/null 2>&1; then
  pip3 install git+https://github.com/tarekziade/claude-tools.git --quiet 2>/dev/null || warn "Failed to install claude-tools"
else
  warn "pip not found — install claude-tools manually: pip install git+https://github.com/tarekziade/claude-tools.git"
fi

# ── Windows: create python3 wrapper ─────────────────────────
if $IS_WINDOWS; then
  if ! command -v python3 >/dev/null 2>&1; then
    info "Creating python3 wrapper for Windows"
    cat > /usr/bin/python3 << 'PYEOF'
#!/bin/bash
exec python "$@"
PYEOF
    chmod +x /usr/bin/python3
  fi
fi

# ── Install plugin marketplaces ──────────────────────────────
info "Installing plugin marketplaces..."
marketplaces=(
  "anthropics/claude-plugins-official"
  "obra/superpowers-marketplace"
  "trailofbits/skills"
  "ykdojo/claude-code-tips"
  "athola/claude-night-market"
  "kenryu42/cc-marketplace"
  "777genius/claude-notifications-go"
  "gmickel/gmickel-claude-marketplace"
)

for repo in "${marketplaces[@]}"; do
  name=$(basename "$repo")
  info "  Adding marketplace: $name"
  claude plugin marketplace remove "$name" 2>/dev/null || true
  claude plugin marketplace add "$repo" 2>/dev/null || warn "Failed to add $name"
done

# ── Install plugins ──────────────────────────────────────────
info "Installing plugins (11)..."
plugins=(
  "superpowers@claude-plugins-official"
  "context7@claude-plugins-official"
  "pyright-lsp@claude-plugins-official"
  "hookify@claude-plugins-official"
  "modern-python@trailofbits"
  "property-based-testing@trailofbits"
  "static-analysis@trailofbits"
  "dx@ykdojo"
  "sanctum@claude-night-market"
  "claude-notifications-go@claude-notifications-go"
  "flow-next@gmickel-claude-marketplace"
)

for plugin in "${plugins[@]}"; do
  info "  Installing: $plugin"
  claude plugin install "$plugin" 2>/dev/null || warn "Failed to install $plugin"
done

# ── Install MCP servers ──────────────────────────────────────
echo ""
info "Installing MCP servers..."

# Detect Node.js
if ! command -v node >/dev/null 2>&1 && ! command -v npx >/dev/null 2>&1; then
  warn "Node.js not found. MCP servers require Node.js."
  warn "Install: https://nodejs.org/ or 'winget install OpenJS.NodeJS.LTS'"
else
  # No-key servers (always install)
  info "  Adding sequential-thinking MCP"
  claude mcp add --scope user sequential-thinking -- cmd /c npx -y @modelcontextprotocol/server-sequential-thinking 2>/dev/null || true

  info "  Adding playwright MCP"
  claude mcp add --scope user playwright -- cmd /c npx -y @playwright/mcp@latest 2>/dev/null || true

  info "  Adding context-mode MCP"
  claude mcp add --scope user context-mode -- cmd /c npx -y context-mode 2>/dev/null || true

  info "  Adding chrome-devtools MCP"
  claude mcp add --scope user chrome-devtools -- cmd /c npx -y chrome-devtools-mcp@latest 2>/dev/null || true

  info "  Adding yfinance MCP"
  claude mcp add --scope user yfinance -- cmd /c npx -y yfinance-mcp 2>/dev/null || true

  # Servers requiring API keys (prompt user)
  echo ""
  info "The following MCP servers require API keys."
  info "Press Enter to skip any you don't have yet."
  echo ""

  # GitHub MCP
  read -rp "GitHub PAT (or press Enter to use 'gh auth token'): " GITHUB_PAT
  if [ -z "$GITHUB_PAT" ] && command -v gh >/dev/null 2>&1; then
    GITHUB_PAT=$(gh auth token 2>/dev/null || echo "")
  fi
  if [ -n "$GITHUB_PAT" ]; then
    claude mcp add --scope user github-mcp --env "GITHUB_PERSONAL_ACCESS_TOKEN=$GITHUB_PAT" -- cmd /c npx -y @modelcontextprotocol/server-github 2>/dev/null || true
    ok "  github-mcp added"
  else
    warn "  Skipped github-mcp (no PAT)"
  fi

  # Tavily MCP (HTTP transport)
  read -rp "Tavily API key: " TAVILY_KEY
  if [ -n "$TAVILY_KEY" ]; then
    claude mcp add --scope user --transport http tavily "https://mcp.tavily.com/mcp/?tavilyApiKey=${TAVILY_KEY}" 2>/dev/null || true
    ok "  tavily added"
  else
    warn "  Skipped tavily"
  fi

  # Firecrawl MCP
  read -rp "Firecrawl API key: " FIRECRAWL_KEY
  if [ -n "$FIRECRAWL_KEY" ]; then
    claude mcp add --scope user firecrawl --env "FIRECRAWL_API_KEY=$FIRECRAWL_KEY" -- cmd /c npx -y firecrawl-mcp 2>/dev/null || true
    ok "  firecrawl added"
  else
    warn "  Skipped firecrawl"
  fi

  # Gemini MCP
  read -rp "Gemini API key: " GEMINI_KEY
  if [ -n "$GEMINI_KEY" ]; then
    claude mcp add --scope user gemini --env "GEMINI_API_KEY=$GEMINI_KEY" -- cmd /c npx -y @rlabs-inc/gemini-mcp 2>/dev/null || true
    ok "  gemini added"
  else
    warn "  Skipped gemini"
  fi

  # Codex MCP (OpenAI)
  read -rp "OpenAI API key (for Codex MCP): " OPENAI_KEY
  if [ -n "$OPENAI_KEY" ]; then
    claude mcp add --scope user codex --env "CODEX_API_KEY=$OPENAI_KEY" --env "CODEX_API_BASE_URL=https://api.openai.com/v1" -- cmd /c npx -y @cpujia/codex-mcp-server 2>/dev/null || true
    ok "  codex added"
  else
    warn "  Skipped codex"
  fi

  # Claude Context (Zilliz)
  read -rp "OpenAI API key (for Zilliz embeddings, Enter to reuse above): " ZILLIZ_OPENAI_KEY
  if [ -z "$ZILLIZ_OPENAI_KEY" ] && [ -n "${OPENAI_KEY:-}" ]; then
    ZILLIZ_OPENAI_KEY="$OPENAI_KEY"
  fi
  if [ -n "$ZILLIZ_OPENAI_KEY" ]; then
    read -rp "Zilliz endpoint URL: " ZILLIZ_URL
    read -rp "Zilliz API token: " ZILLIZ_TOKEN
    if [ -n "$ZILLIZ_URL" ] && [ -n "$ZILLIZ_TOKEN" ]; then
      claude mcp add --scope user claude-context \
        --env "OPENAI_API_KEY=$ZILLIZ_OPENAI_KEY" \
        --env "MILVUS_ADDRESS=$ZILLIZ_URL" \
        --env "MILVUS_TOKEN=$ZILLIZ_TOKEN" \
        -- cmd /c npx -y @zilliz/claude-context-mcp@latest 2>/dev/null || true
      ok "  claude-context added"
    else
      warn "  Skipped claude-context (missing endpoint or token)"
    fi
  else
    warn "  Skipped claude-context"
  fi

  # Windows: add PATH env to all stdio MCP servers
  if $IS_WINDOWS; then
    info "Patching MCP servers with Windows PATH..."
    python -c "
import json, os
config_path = os.path.expanduser('~/.claude.json')
with open(config_path, 'r') as f:
    config = json.load(f)
node_path = r'C:\Program Files\nodejs;C:\WINDOWS\system32;C:\WINDOWS;C:\Program Files\Git\cmd'
for name, server in config.get('mcpServers', {}).items():
    if server.get('type') == 'stdio':
        if 'env' not in server:
            server['env'] = {}
        server['env']['PATH'] = node_path
with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)
print('  PATH injected into all stdio MCP servers')
" 2>/dev/null || warn "Failed to patch MCP PATH — may need manual fix"
  fi
fi

# ── Node.js dependencies ─────────────────────────────────────
echo ""
info "Pre-caching MCP npm packages..."
if command -v npm >/dev/null 2>&1; then
  npm install -g \
    @modelcontextprotocol/server-github \
    @modelcontextprotocol/server-sequential-thinking \
    firecrawl-mcp \
    @playwright/mcp \
    context-mode \
    chrome-devtools-mcp \
    @rlabs-inc/gemini-mcp \
    @cpujia/codex-mcp-server \
    yfinance-mcp \
    @zilliz/claude-context-mcp \
    2>/dev/null || warn "Some npm packages failed to pre-cache"
fi

# ── Python dependencies ──────────────────────────────────────
echo ""
info "Checking Python dependencies..."

core_python_pkgs=(
  httpx requests pandas numpy matplotlib seaborn scikit-learn
  plotly polars networkx statsmodels sympy scipy arviz pymc
  shap openpyxl pypdf pdfplumber reportlab pingouin duckdb
  edgartools kaleido huggingface_hub
)

missing_pkgs=()
for pkg in "${core_python_pkgs[@]}"; do
  import_name="${pkg//-/_}"
  case "$pkg" in
    scikit-learn) import_name="sklearn" ;;
    edgartools) import_name="edgar" ;;
  esac
  python -c "import $import_name" 2>/dev/null || missing_pkgs+=("$pkg")
done

if [ ${#missing_pkgs[@]} -gt 0 ]; then
  warn "Missing Python packages (${#missing_pkgs[@]}): ${missing_pkgs[*]}"
  read -rp "Install them now? [y/N] " answer
  if [[ "$answer" =~ ^[Yy]$ ]]; then
    pip install "${missing_pkgs[@]}" || warn "Some packages failed"
  fi
fi

# ── System dependencies ──────────────────────────────────────
echo ""
info "Checking system dependencies..."

if ! command -v jq >/dev/null 2>&1; then
  info "jq not found — required for hooks. Installing..."
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get install -y jq 2>/dev/null || warn "Failed to install jq"
  elif command -v brew >/dev/null 2>&1; then
    brew install jq 2>/dev/null || warn "Failed to install jq"
  elif command -v winget.exe >/dev/null 2>&1; then
    winget.exe install jqlang.jq --accept-package-agreements --accept-source-agreements 2>/dev/null || warn "Failed to install jq"
  else
    warn "Install jq manually: https://jqlang.github.io/jq/download/"
  fi
fi

if ! command -v uv >/dev/null 2>&1; then
  info "uv not found — required for prompt injection defender. Installing..."
  pip install uv 2>/dev/null || warn "Failed to install uv. Install manually: pip install uv"
fi

# ── Install settings.local.json (permissions) ────────────────
if [ ! -f "$CLAUDE_DIR/settings.local.json" ]; then
  info "Installing settings.local.json"
  cp "$REPO_DIR/settings.local.json.template" "$CLAUDE_DIR/settings.local.json"
fi

# ── Hookify patch (Windows) ──────────────────────────────────
if $IS_WINDOWS; then
  info "Patching hookify hooks for Windows (PLUGIN_ROOT fallback)..."
  HOOKIFY_DIR="$CLAUDE_DIR/plugins/cache/claude-plugins-official/hookify"
  if [ -d "$HOOKIFY_DIR" ]; then
    for version_dir in "$HOOKIFY_DIR"/*/hooks; do
      for f in "$version_dir"/{stop,pretooluse,posttooluse,userpromptsubmit}.py; do
        if [ -f "$f" ]; then
          sed -i "s|PLUGIN_ROOT = os.environ.get('CLAUDE_PLUGIN_ROOT')|PLUGIN_ROOT = os.environ.get('CLAUDE_PLUGIN_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))|" "$f" 2>/dev/null
        fi
      done
    done
    ok "  Hookify patched"
  fi
fi

# ── Summary ──────────────────────────────────────────────────
echo ""
ok "Installation complete!"
echo ""
echo "Installed:"
echo "  - settings.json (permissions, hooks, env, plugins)"
echo "  - CLAUDE.md (global workflow + model routing rules)"
echo "  - statusline-command.sh (token/cost/git status bar)"
echo "  - 2 agents (general-code-reviewer, security-reviewer)"
echo "  - 30 skills (finance, ML, viz, research, dev)"
echo "  - 4 commands (orchestrate, telegram, desktop, update)"
echo "  - 8 plugin marketplaces"
echo "  - 11 plugins"
echo "  - 16 hooks (security, quality, trace compaction, injection defense)"
echo "  - 11 MCP servers (key-dependent ones only if keys provided)"
echo ""
echo "  Hooks:"
echo "    - UserPromptSubmit: Python traceback compactor"
echo "    - PreToolUse (Edit): Config protection (blocks linter config edits)"
echo "    - PreToolUse (Bash): 5 destructive command blockers"
echo "    - PostToolUse (Bash): Command logger + trace compactor + injection defender"
echo "    - PostToolUse (Read/WebFetch/Grep/Task): Prompt injection defender"
echo ""
echo "  MCP Servers:"
echo "    - sequential-thinking, playwright, context-mode, chrome-devtools, yfinance"
echo "    - github-mcp, tavily, firecrawl, gemini, codex, claude-context (if keys provided)"
echo ""
if $IS_WINDOWS; then
  warn "Windows users: ensure C:\\Program Files\\nodejs is in your system PATH"
  warn "  Settings > 'environment variables' > User Path > Add 'C:\\Program Files\\nodejs'"
fi
echo ""
echo "Run 'claude' to start using your configuration."
