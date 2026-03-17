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
command -v claude >/dev/null 2>&1 || { err "claude CLI not found. Install it first: https://docs.anthropic.com/en/docs/claude-code"; exit 1; }

if [ ! -d "$CLAUDE_DIR" ]; then
  info "Creating ${CLAUDE_DIR}"
  mkdir -p "$CLAUDE_DIR"
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

info "Installing skills (35)"
mkdir -p "$CLAUDE_DIR/skills"
cp -r "$REPO_DIR/skills/"* "$CLAUDE_DIR/skills/"

info "Installing commands"
mkdir -p "$CLAUDE_DIR/commands"
cp -r "$REPO_DIR/commands/"* "$CLAUDE_DIR/commands/"

info "Installing plugin marketplace config"
mkdir -p "$CLAUDE_DIR/plugins"
cp "$REPO_DIR/plugins/known_marketplaces.json" "$CLAUDE_DIR/plugins/known_marketplaces.json"

# ── Install plugin marketplaces ──────────────────────────────
info "Installing plugin marketplaces (requires network)..."
marketplaces=(
  "anthropics/claude-plugins-official"
  "obra/superpowers-marketplace"
  "mixedbread-ai/mgrep"
  "trailofbits/skills"
  "ykdojo/claude-code-tips"
  "athola/claude-night-market"
  "kenryu42/cc-marketplace"
  "thedotmack/claude-mem"
  "777genius/claude-notifications-go"
)

for repo in "${marketplaces[@]}"; do
  name=$(basename "$repo")
  dest="$CLAUDE_DIR/plugins/marketplaces/$name"
  if [ -d "$dest" ]; then
    info "Updating marketplace: $name"
    git -C "$dest" pull --quiet 2>/dev/null || warn "Failed to update $name"
  else
    info "Cloning marketplace: $name"
    git clone --quiet "https://github.com/${repo}.git" "$dest" 2>/dev/null || warn "Failed to clone $name"
  fi
done

# ── Node.js dependencies ─────────────────────────────────────
echo ""
info "Checking Node.js dependencies..."

if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
  # playwright-skill
  if [ -f "$CLAUDE_DIR/skills/playwright-skill/package.json" ]; then
    info "Installing playwright-skill node dependencies..."
    (cd "$CLAUDE_DIR/skills/playwright-skill" && npm install --quiet 2>/dev/null) || warn "Failed to npm install for playwright-skill"
    info "Installing Playwright Chromium browser..."
    (cd "$CLAUDE_DIR/skills/playwright-skill" && npx playwright install chromium 2>/dev/null) || warn "Failed to install Chromium for Playwright"
  fi
else
  warn "Node.js/npm not found. playwright-skill requires: npm install (in skills/playwright-skill/)"
fi

# Global npm packages (optional)
npm_global_pkgs=()
for pkg in "@mozilla/readability-cli" "pptxgenjs" "sharp"; do
  if ! npm list -g "$pkg" >/dev/null 2>&1; then
    npm_global_pkgs+=("$pkg")
  fi
done

if [ ${#npm_global_pkgs[@]} -gt 0 ]; then
  echo ""
  warn "Optional global npm packages not installed: ${npm_global_pkgs[*]}"
  read -rp "Install them now? (npm install -g ${npm_global_pkgs[*]}) [y/N] " answer
  if [[ "$answer" =~ ^[Yy]$ ]]; then
    npm install -g "${npm_global_pkgs[@]}" || warn "Some global npm packages failed to install"
  else
    warn "Skipped. Install later: npm install -g ${npm_global_pkgs[*]}"
  fi
fi

# ── Python dependencies ──────────────────────────────────────
echo ""
info "Checking Python dependencies..."

# Core packages used across multiple skills
core_python_pkgs=(
  httpx
  requests
  pandas
  numpy
  matplotlib
  seaborn
  scikit-learn
  plotly
  polars
  networkx
  statsmodels
  sympy
  scipy
  arviz
  pymc
  shap
  openpyxl
  pypdf
  pdfplumber
  reportlab
  pingouin
  duckdb
  edgartools
  kaleido
  huggingface_hub
)

missing_pkgs=()
for pkg in "${core_python_pkgs[@]}"; do
  # Normalize package name for import check (hyphens -> underscores)
  import_name="${pkg//-/_}"
  # Special cases
  case "$pkg" in
    scikit-learn) import_name="sklearn" ;;
    pypdf) import_name="pypdf" ;;
    huggingface_hub) import_name="huggingface_hub" ;;
    edgartools) import_name="edgar" ;;
  esac
  python3 -c "import $import_name" 2>/dev/null || missing_pkgs+=("$pkg")
done

if [ ${#missing_pkgs[@]} -gt 0 ]; then
  echo ""
  warn "Missing core Python packages (${#missing_pkgs[@]}): ${missing_pkgs[*]}"
  read -rp "Install them now? (pip install ${missing_pkgs[*]}) [y/N] " answer
  if [[ "$answer" =~ ^[Yy]$ ]]; then
    pip install "${missing_pkgs[@]}" || warn "Some packages failed to install"
  else
    warn "Skipped. Install later: pip install ${missing_pkgs[*]}"
  fi
fi

# Optional/heavy Python packages
echo ""
info "Checking optional Python packages..."

optional_python_pkgs=()
optional_labels=()

# timesfm (large, requires torch)
python3 -c "import timesfm" 2>/dev/null || {
  optional_python_pkgs+=("timesfm[torch]")
  optional_labels+=("timesfm — time series forecasting (requires PyTorch)")
}

# torch
python3 -c "import torch" 2>/dev/null || {
  optional_python_pkgs+=("torch")
  optional_labels+=("torch — PyTorch (large download)")
}

# xgboost
python3 -c "import xgboost" 2>/dev/null || {
  optional_python_pkgs+=("xgboost")
  optional_labels+=("xgboost — gradient boosting")
}

# mlflow
python3 -c "import mlflow" 2>/dev/null || {
  optional_python_pkgs+=("mlflow")
  optional_labels+=("mlflow — experiment tracking")
}

# dash
python3 -c "import dash" 2>/dev/null || {
  optional_python_pkgs+=("dash")
  optional_labels+=("dash — interactive dashboards")
}

# yt-dlp
command -v yt-dlp >/dev/null 2>&1 || {
  optional_python_pkgs+=("yt-dlp")
  optional_labels+=("yt-dlp — YouTube transcript downloads")
}

# defusedxml
python3 -c "import defusedxml" 2>/dev/null || {
  optional_python_pkgs+=("defusedxml")
  optional_labels+=("defusedxml — safe XML parsing for xlsx/pptx")
}

# markitdown
python3 -c "import markitdown" 2>/dev/null || {
  optional_python_pkgs+=("markitdown[pptx]")
  optional_labels+=("markitdown — document conversion for pptx")
}

# pdf2image + pytesseract
python3 -c "import pdf2image" 2>/dev/null || {
  optional_python_pkgs+=("pdf2image")
  optional_labels+=("pdf2image — PDF to image conversion")
}
python3 -c "import pytesseract" 2>/dev/null || {
  optional_python_pkgs+=("pytesseract")
  optional_labels+=("pytesseract — OCR for scanned PDFs")
}

# joblib
python3 -c "import joblib" 2>/dev/null || {
  optional_python_pkgs+=("joblib")
  optional_labels+=("joblib — model persistence for scikit-learn")
}

if [ ${#optional_python_pkgs[@]} -gt 0 ]; then
  echo ""
  warn "Optional Python packages not installed:"
  for label in "${optional_labels[@]}"; do
    echo -e "  ${YELLOW}-${NC} $label"
  done
  read -rp "Install all optional packages? [y/N] " answer
  if [[ "$answer" =~ ^[Yy]$ ]]; then
    pip install "${optional_python_pkgs[@]}" || warn "Some optional packages failed to install"
  else
    warn "Skipped. Install individually as needed."
  fi
fi

# notebooklm skill has its own requirements.txt (patchright)
if [ -f "$CLAUDE_DIR/skills/notebooklm/requirements.txt" ]; then
  echo ""
  read -rp "Install NotebookLM skill dependencies? (patchright + chrome) [y/N] " answer
  if [[ "$answer" =~ ^[Yy]$ ]]; then
    pip install -r "$CLAUDE_DIR/skills/notebooklm/requirements.txt"
    python3 -m patchright install chrome 2>/dev/null || warn "Failed to install Chrome for patchright"
  fi
fi

# ── System dependencies ──────────────────────────────────────
echo ""
info "Checking system dependencies..."

# jq is required for hooks — auto-install if missing
if ! command -v jq >/dev/null 2>&1; then
  info "jq not found — required for hooks. Installing..."
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get install -y jq 2>/dev/null || warn "Failed to install jq via apt"
  elif command -v brew >/dev/null 2>&1; then
    brew install jq 2>/dev/null || warn "Failed to install jq via brew"
  elif command -v winget >/dev/null 2>&1 || command -v winget.exe >/dev/null 2>&1; then
    winget.exe install jqlang.jq --accept-package-agreements --accept-source-agreements 2>/dev/null || warn "Failed to install jq via winget"
    # On Windows, ensure jq is accessible from bash
    jq_winget="$HOME/AppData/Local/Microsoft/WinGet/Links/jq.exe"
    if [ -f "$jq_winget" ] && ! command -v jq >/dev/null 2>&1; then
      mkdir -p "$HOME/bin"
      cp "$jq_winget" "$HOME/bin/jq.exe"
      info "Copied jq to ~/bin for bash PATH access"
    fi
  else
    warn "Could not auto-install jq. Install manually: https://jqlang.github.io/jq/download/"
  fi
fi

sys_missing=()
command -v jq >/dev/null 2>&1    || sys_missing+=("jq — required for hooks (install failed)")
command -v bc >/dev/null 2>&1    || sys_missing+=("bc — used by statusline for cost calculation (optional)")
command -v git >/dev/null 2>&1   || sys_missing+=("git — required for plugin marketplaces")
command -v tesseract >/dev/null 2>&1 || sys_missing+=("tesseract — OCR engine for pytesseract (optional)")

if [ ${#sys_missing[@]} -gt 0 ]; then
  warn "System packages not found:"
  for pkg in "${sys_missing[@]}"; do
    echo -e "  ${YELLOW}-${NC} $pkg"
  done
fi

# ── Install settings.local.json (permissions) ────────────────
if [ ! -f "$CLAUDE_DIR/settings.local.json" ]; then
  info "Installing settings.local.json (auto-allow non-destructive operations)"
  cp "$REPO_DIR/settings.local.json.template" "$CLAUDE_DIR/settings.local.json"
elif ! grep -q '"Bash(\*)"' "$CLAUDE_DIR/settings.local.json" 2>/dev/null; then
  echo ""
  warn "Your settings.local.json doesn't have broad Bash permissions."
  read -rp "Replace with auto-allow template? (existing file backed up) [y/N] " answer
  if [[ "$answer" =~ ^[Yy]$ ]]; then
    cp "$CLAUDE_DIR/settings.local.json" "$CLAUDE_DIR/settings.local.json.bak.$(date +%s)"
    cp "$REPO_DIR/settings.local.json.template" "$CLAUDE_DIR/settings.local.json"
    ok "settings.local.json updated"
  fi
fi

# ── Optional API keys ────────────────────────────────────────
echo ""
info "API keys status:"
echo ""

check_key() {
  local var="$1" skill="$2" url="$3"
  if [ -z "${!var:-}" ]; then
    echo -e "  ${YELLOW}${var}${NC} — used by ${skill}"
    echo -e "    Get one at: ${CYAN}${url}${NC}"
  else
    echo -e "  ${GREEN}${var}${NC} — already set ✓"
  fi
}

check_key "GEMINI_API_KEY"     "deep-research"          "https://aistudio.google.com/"
check_key "HF_TOKEN"           "hugging-face-datasets"  "https://huggingface.co/settings/tokens"
check_key "COMPOSIO_API_KEY"   "connect-apps"           "https://composio.dev/"
check_key "ALPHA_VANTAGE_API_KEY" "alpha-vantage"       "https://www.alphavantage.co/support/#api-key"
check_key "FRED_API_KEY"       "fred-economic-data"     "https://fred.stlouisfed.org/docs/api/api_key.html"
check_key "FINNHUB_API_KEY"    "finnhub MCP server"     "https://finnhub.io/"

# ── Summary ──────────────────────────────────────────────────
echo ""
ok "Installation complete!"
echo ""
echo "Installed:"
echo "  - settings.json (permissions, hooks, env, statusline, plugins)"
echo "  - CLAUDE.md (global workflow principles)"
echo "  - statusline-command.sh (token/cost/git status bar)"
echo "  - 2 agents (general-code-reviewer, security-reviewer)"
echo "  - 35 skills"
echo "  - 1 command (orchestrate)"
echo "  - 9 plugin marketplaces"
echo "  - 15 enabled plugins"
echo ""
echo "Run 'claude' to start using your new configuration."
