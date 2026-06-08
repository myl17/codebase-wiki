#!/usr/bin/env bash
# Inject wiki current state into Claude Code SessionStart context.
# Output follows Claude Code hookSpecificOutput.additionalContext format.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WIKI_ROOT="$(dirname "$SCRIPT_DIR")"
HOT_FILE="$WIKI_ROOT/wiki/hot.md"
LOG_FILE="$WIKI_ROOT/wiki/log.md"
MANIFEST="$WIKI_ROOT/.manifest.json"

hot_content=""
if [ -f "$HOT_FILE" ]; then
  hot_content="$(cat "$HOT_FILE")"
fi

last_log_lines=""
if [ -f "$LOG_FILE" ]; then
  last_log_lines="$(tail -3 "$LOG_FILE" 2>/dev/null || true)"
fi

# stale_count: use --json flag so output is always a number, never "No stale repos."
stale_count=0
if [ -f "$MANIFEST" ] && command -v python3 &>/dev/null; then
  stale_count=$(python3 "$WIKI_ROOT/scripts/manifest.py" --manifest "$MANIFEST" stale --json \
    2>/dev/null || echo "0")
fi

# Build additionalContext safely: use python to produce valid JSON,
# avoiding shell interpolation of quotes/backslashes in content strings.
python3 - <<PYEOF
import json, sys

context = """## Codebase Wiki Status

{hot}

### Recent Operations

{log}

### Health

Stale dimension pages: {stale}""".format(
    hot="""$hot_content""",
    log="""$last_log_lines""",
    stale="""$stale_count""",
)

print(json.dumps({"additionalContext": context}))
PYEOF
