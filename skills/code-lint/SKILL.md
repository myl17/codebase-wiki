# /lint — Wiki Health Check

Run programmatic health checks on the wiki and report findings.

## Trigger

```
/lint
/lint --fix      # attempt auto-fix for INFO-level issues
```

## Execution Protocol

### Step 1 — Run lint.py

```bash
python scripts/lint.py --wiki wiki/ --manifest .manifest.json
```

### Step 2 — Run eval.py

```bash
python scripts/eval.py --wiki wiki/ --manifest .manifest.json
```

### Step 3 — Report findings

Present a summary organized by severity:

**Errors (must fix):**
- List each [ERROR] finding with file and detail

**Warnings (should fix):**
- List each [WARN] finding

**Info (optional):**
- List each [INFO] finding

**Health Score:**
- Coverage: X%
- Provenance: X%
- Freshness: X%

### Step 4 — Prioritize action (if errors exist)

For each [ERROR], tell the user what action to take:
- `check_broken_wikilinks` → "Run `/analyze` on the referenced repo, or remove the broken link"
- `check_stale_dimensions` → "Run `/analyze <repo> --dimensions <dim>` to refresh stale pages"

Never auto-fix errors without user confirmation. Auto-fix only INFO-level issues with `--fix`.
