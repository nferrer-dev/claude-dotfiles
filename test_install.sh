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

# ── Stub out external tools so install doesn't modify system state ──
stub_bin="$FAKE_HOME/bin"
mkdir -p "$stub_bin"
for cmd in claude npm npx pip pip3 uv; do
  echo '#!/bin/sh' > "$stub_bin/$cmd"
  chmod +x "$stub_bin/$cmd"
done

# ── Test 1: Fresh install ────────────────────────────────────
echo "== Test: Fresh install =="

HOME="$FAKE_HOME" PATH="$stub_bin:$PATH" \
  bash "$REPO_DIR/install.sh" <<< $'\n\n\n\n\n\n\n\n\n' 2>&1 | sed 's/^/  | /'

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

# skills (30 skill dirs)
skills=(
  alpha-vantage article-extractor deep-research edgartools
  exploratory-data-analysis fred-economic-data hedgefundmonitor
  hugging-face-datasets iterative-retrieval langsmith-fetch
  matplotlib mcp-builder networkx notebooklm pdf plotly polars
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

# scientific skills with references
for s in alpha-vantage edgartools fred-economic-data hedgefundmonitor matplotlib networkx plotly polars pymc scikit-learn seaborn shap statistical-analysis statsmodels sympy; do
  assert_dir "skills/$s/references"
done

# skills with scripts
for s in fred-economic-data matplotlib exploratory-data-analysis; do
  assert_dir "skills/$s/scripts"
done

# commands (4)
assert_file "commands/orchestrate.md"
assert_file "commands/telegram.md"
assert_file "commands/desktop.md"
assert_file "commands/update.md"

# hooks
assert_file "hooks/config-protection.sh"
assert "config-protection is executable" test -x "$FAKE_HOME/.claude/hooks/config-protection.sh"
assert_file "hooks/interface-guard.sh"
assert "interface-guard is executable" test -x "$FAKE_HOME/.claude/hooks/interface-guard.sh"
assert_file "hooks/prompt-injection-defender/post-tool-defender.py"
assert_file "hooks/prompt-injection-defender/patterns.yaml"

# settings.json content checks
assert "settings has hooks" python3 -c "import json; d=json.load(open('$FAKE_HOME/.claude/settings.json')); assert 'hooks' in d"
assert "settings has permissions" python3 -c "import json; d=json.load(open('$FAKE_HOME/.claude/settings.json')); assert 'permissions' in d"
assert "settings has env" python3 -c "import json; d=json.load(open('$FAKE_HOME/.claude/settings.json')); assert 'env' in d"
assert "settings has 11 plugins" python3 -c "import json; d=json.load(open('$FAKE_HOME/.claude/settings.json')); assert len(d['enabledPlugins']) == 11, f'got {len(d[\"enabledPlugins\"])}'"
assert "settings has extraKnownMarketplaces" python3 -c "import json; d=json.load(open('$FAKE_HOME/.claude/settings.json')); assert 'extraKnownMarketplaces' in d"
assert "settings has statusLine" python3 -c "import json; d=json.load(open('$FAKE_HOME/.claude/settings.json')); assert 'statusLine' in d"

# ── Test 2: Backup on re-install ─────────────────────────────
echo ""
echo "== Test: Re-install backs up settings.json =="

HOME="$FAKE_HOME" PATH="$stub_bin:$PATH" \
  bash "$REPO_DIR/install.sh" <<< $'\n\n\n\n\n\n\n\n\n' 2>&1 | sed 's/^/  | /'

backup_count=$(find "$FAKE_HOME/.claude" -maxdepth 1 -name 'settings.json.bak.*' | wc -l)
assert "backup file created (found $backup_count)" test "$backup_count" -ge 1

# ── Test 3: Idempotency ─────────────────────────────────────
echo ""
echo "== Test: Idempotent (no errors on third run) =="

HOME="$FAKE_HOME" PATH="$stub_bin:$PATH" \
  bash "$REPO_DIR/install.sh" <<< $'\n\n\n\n\n\n\n\n\n' 2>&1 | sed 's/^/  | /'

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
