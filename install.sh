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

info "Installing agents"
mkdir -p "$CLAUDE_DIR/agents"
cp "$REPO_DIR/agents/"*.md "$CLAUDE_DIR/agents/"

info "Installing skills"
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

# ── Python dependencies for skills ───────────────────────────
echo ""
info "Checking Python dependencies for skills..."

missing_pkgs=()
for pkg in httpx playwright; do
  python3 -c "import $pkg" 2>/dev/null || missing_pkgs+=("$pkg")
done

if [ ${#missing_pkgs[@]} -gt 0 ]; then
  echo ""
  warn "Some skills need Python packages: ${missing_pkgs[*]}"
  read -rp "Install them now? (pip install ${missing_pkgs[*]}) [y/N] " answer
  if [[ "$answer" =~ ^[Yy]$ ]]; then
    pip install "${missing_pkgs[@]}"
  else
    warn "Skipped. Install later: pip install ${missing_pkgs[*]}"
  fi
fi

# notebooklm skill has its own requirements.txt
if [ -f "$CLAUDE_DIR/skills/notebooklm/requirements.txt" ]; then
  read -rp "Install NotebookLM skill dependencies? (requires Chromium via playwright) [y/N] " answer
  if [[ "$answer" =~ ^[Yy]$ ]]; then
    pip install -r "$CLAUDE_DIR/skills/notebooklm/requirements.txt"
    python3 -m playwright install chromium 2>/dev/null || warn "Failed to install Chromium for playwright"
  fi
fi

# ── Optional API keys ────────────────────────────────────────
echo ""
info "Some skills use optional API keys. Set them in your shell profile if needed:"
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

check_key "GEMINI_API_KEY"  "deep-research"        "https://aistudio.google.com/"
check_key "HF_TOKEN"        "hugging-face-datasets" "https://huggingface.co/settings/tokens"
check_key "COMPOSIO_API_KEY" "connect-apps"         "https://composio.dev/"

# ── Summary ──────────────────────────────────────────────────
echo ""
ok "Installation complete!"
echo ""
echo "Installed:"
echo "  - 2 agents (general-code-reviewer, security-reviewer)"
echo "  - 17 skills"
echo "  - 1 command (orchestrate)"
echo "  - 6 plugin marketplaces"
echo ""
echo "Run 'claude' to start using your new configuration."
