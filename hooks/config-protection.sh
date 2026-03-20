#!/bin/bash
# Config Protection Hook - blocks edits to linter/formatter configs
# Prevents Claude from loosening quality gates instead of fixing code

INPUT=$(cat)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path')

# Direct linter/formatter config files
if echo "$FILE" | grep -qiE '\.(eslintrc|prettierrc|flake8|pylintrc|stylelintrc)'; then
  echo "BLOCKED: Do not modify linter/formatter configs to pass checks — fix the code instead" >&2
  exit 2
fi

if echo "$FILE" | grep -qiE '(eslint\.config\.|prettier\.config\.|\.editorconfig$|\.ruff\.toml$|\.mypy\.ini$|\.flake8$)'; then
  echo "BLOCKED: Do not modify linter/formatter configs to pass checks — fix the code instead" >&2
  exit 2
fi

# pyproject.toml / setup.cfg edits targeting tool config sections
if echo "$FILE" | grep -qiE '(pyproject\.toml|setup\.cfg|tox\.ini)$'; then
  # Edit tool uses new_string, Write tool uses content
  NEW_STRING=$(echo "$INPUT" | jq -r '.tool_input.new_string // ""')
  CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // ""')
  CHECK_TEXT="${NEW_STRING}${CONTENT}"
  if echo "$CHECK_TEXT" | grep -qiE '\[(tool\.(ruff|pylint|flake8|mypy|black|isort|pytest)|pylint|flake8)'; then
    echo "BLOCKED: Do not modify linter/formatter sections in $FILE — fix the code instead" >&2
    exit 2
  fi
fi

exit 0
