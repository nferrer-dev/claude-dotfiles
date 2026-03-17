#!/usr/bin/env bash
#
# Test suite for install.sh
# Runs the installer against a fake HOME and verifies everything landed correctly.
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
FAKE_HOME="$(mktemp -d)"
PASS=0
FAIL=0

cleanup() { rm -rf "$FAKE_HOME"; }
trap cleanup EXIT

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

assert() {
  local desc="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} ${desc}"
    PASS=$((PASS + 1))
  else
    echo -e "  ${RED}✗${NC} ${desc}"
    FAIL=$((FAIL + 1))
  fi
}

assert_file()    { assert "file exists: $1"    test -f "$FAKE_HOME/.claude/$1"; }
assert_dir()     { assert "dir exists: $1"     test -d "$FAKE_HOME/.claude/$1"; }
assert_json()    { assert "valid JSON: $1"     python3 -c "import json; json.load(open('$FAKE_HOME/.claude/$1'))"; }
assert_count()   {
  local dir="$1" pattern="$2" expected="$3"
  local actual
  actual=$(find "$FAKE_HOME/.claude/$dir" -maxdepth 1 -name "$pattern" | wc -l)
  assert "$dir has $expected $pattern files (found $actual)" test "$actual" -eq "$expected"
}

# ── Stub out claude CLI so pre-flight passes ─────────────────
stub_bin="$FAKE_HOME/bin"
mkdir -p "$stub_bin"
echo '#!/bin/sh' > "$stub_bin/claude"
chmod +x "$stub_bin/claude"

# ── Test 1: Fresh install ────────────────────────────────────
echo "== Test: Fresh install =="

HOME="$FAKE_HOME" PATH="$stub_bin:$PATH" \
  bash "$REPO_DIR/install.sh" <<< $'n\nn\nn\nn\nn' 2>&1 | sed 's/^/  | /'

echo ""
echo "-- Verifying file structure --"

# settings
assert_file "settings.json"
assert_json "settings.json"

# CLAUDE.md
assert_file "CLAUDE.md"

# statusline
assert_file "statusline-command.sh"
assert "statusline is executable" test -x "$FAKE_HOME/.claude/statusline-command.sh"

# agents
assert_file "agents/general-code-reviewer.md"
assert_file "agents/security-reviewer.md"
assert_count "agents" "*.md" 2

# skills (37 skill dirs)
skills=(
  alpha-vantage article-extractor connect-apps context-optimization
  deep-research docx edgartools exploratory-data-analysis
  fred-economic-data hedgefundmonitor hugging-face-datasets
  iterative-retrieval langsmith-fetch matplotlib mcp-builder
  networkx notebooklm pdf playwright-skill plotly polars pptx
  pymc scikit-learn seaborn shap skill-creator statistical-analysis
  statsmodels sympy tapestry timesfm-forecasting verification-loop
  xlsx youtube-transcript
)
for s in "${skills[@]}"; do
  assert_dir  "skills/$s"
  assert_file "skills/$s/SKILL.md"
done

# notebooklm extras
assert_file "skills/notebooklm/requirements.txt"
assert_dir  "skills/notebooklm/scripts"
assert_dir  "skills/notebooklm/references"

# deep-research extras
assert_dir  "skills/deep-research/scripts"

# hugging-face-datasets extras
assert_dir  "skills/hugging-face-datasets/scripts"

# playwright-skill extras
assert_file "skills/playwright-skill/package.json"
assert_file "skills/playwright-skill/run.js"
assert_file "skills/playwright-skill/API_REFERENCE.md"
assert_dir  "skills/playwright-skill/lib"

# scientific skills with references
for s in alpha-vantage edgartools fred-economic-data hedgefundmonitor matplotlib networkx plotly polars pymc scikit-learn seaborn shap statistical-analysis statsmodels sympy; do
  assert_dir "skills/$s/references"
done

# skills with scripts
for s in fred-economic-data matplotlib exploratory-data-analysis; do
  assert_dir "skills/$s/scripts"
done

# commands
assert_file "commands/orchestrate.md"

# plugins
assert_file "plugins/known_marketplaces.json"
assert_json "plugins/known_marketplaces.json"

# marketplace repos cloned (9 total)
assert_dir "plugins/marketplaces/claude-plugins-official"
assert_dir "plugins/marketplaces/superpowers-marketplace"
assert_dir "plugins/marketplaces/mgrep"
assert_dir "plugins/marketplaces/skills"
assert_dir "plugins/marketplaces/claude-code-tips"
assert_dir "plugins/marketplaces/claude-night-market"
assert_dir "plugins/marketplaces/cc-marketplace"
assert_dir "plugins/marketplaces/claude-mem"
assert_dir "plugins/marketplaces/claude-notifications-go"

# settings.json content checks
assert "settings has hooks" python3 -c "import json; d=json.load(open('$FAKE_HOME/.claude/settings.json')); assert 'hooks' in d"
assert "settings has permissions" python3 -c "import json; d=json.load(open('$FAKE_HOME/.claude/settings.json')); assert 'permissions' in d"
assert "settings has env" python3 -c "import json; d=json.load(open('$FAKE_HOME/.claude/settings.json')); assert 'env' in d"
assert "settings has 15 plugins" python3 -c "import json; d=json.load(open('$FAKE_HOME/.claude/settings.json')); assert len(d['enabledPlugins']) == 15"
assert "settings has extraKnownMarketplaces" python3 -c "import json; d=json.load(open('$FAKE_HOME/.claude/settings.json')); assert 'extraKnownMarketplaces' in d"
assert "settings has statusLine" python3 -c "import json; d=json.load(open('$FAKE_HOME/.claude/settings.json')); assert 'statusLine' in d"

# ── Test 2: Backup on re-install ─────────────────────────────
echo ""
echo "== Test: Re-install backs up settings.json =="

HOME="$FAKE_HOME" PATH="$stub_bin:$PATH" \
  bash "$REPO_DIR/install.sh" <<< $'n\nn\nn\nn\nn' 2>&1 | sed 's/^/  | /'

backup_count=$(find "$FAKE_HOME/.claude" -maxdepth 1 -name 'settings.json.bak.*' | wc -l)
assert "backup file created (found $backup_count)" test "$backup_count" -ge 1

# ── Test 3: Idempotency ─────────────────────────────────────
echo ""
echo "== Test: Idempotent (no errors on third run) =="

HOME="$FAKE_HOME" PATH="$stub_bin:$PATH" \
  bash "$REPO_DIR/install.sh" <<< $'n\nn\nn\nn\nn' 2>&1 | sed 's/^/  | /'

assert "exit code 0" true

# ── Test 4: Fails without claude CLI ─────────────────────────
echo ""
echo "== Test: Fails gracefully without claude CLI =="

output=$(HOME="$FAKE_HOME" PATH="/usr/bin:/bin" bash "$REPO_DIR/install.sh" 2>&1 || true)
assert "prints error about missing claude" grep -q "claude CLI not found" <<< "$output"

# ── Summary ──────────────────────────────────────────────────
echo ""
echo "========================================"
echo -e "  ${GREEN}Passed: ${PASS}${NC}  ${RED}Failed: ${FAIL}${NC}"
echo "========================================"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
