# Verification Report: Dangerous Operation Prevention Concept Page

**Verified Page**: `concept/dangerous-operation-prevention.md`
**Date**: 2026-06-17
**Method**: Source code audit of openclaw (openclaw-main) and hermes (hermes-agent)

---

## Overall Verdict

The Concept page is **substantially accurate** with 4 factual errors to fix:
3 in the openclaw sections, 1 in the hermes section.

---

## Openclaw: 7-Layer Pipeline

### Claim 1: 7 层 pipeline (profile -> provider profile -> global -> global provider -> agent -> agent provider -> group)

**VERDICT: ACCURATE**

Source: `src/agents/tool-policy-pipeline.ts`, function `buildDefaultToolPolicyPipelineSteps()` (lines 29-62).

The function constructs exactly 7 `ToolPolicyPipelineStep` objects with labels:
1. `tools.profile` (profilePolicy)
2. `tools.byProvider.profile` (providerProfilePolicy)
3. `tools.allow` (globalPolicy)
4. `tools.byProvider.allow` (globalProviderPolicy)
5. `agents.<agentId>.tools.allow` (agentPolicy)
6. `agents.<agentId>.tools.byProvider.allow` (agentProviderPolicy)
7. `group tools.allow` (groupPolicy)

Each layer is independently configurable. The pipeline is applied in `applyToolPolicyPipeline()` (lines 65-108), which iterates sequentially and skips layers with no policy defined (pass-through behavior).

### Claim 2: "LLM 看不到工具就不可能调用" — filtering happens at tool list generation before LLM sees tools

**VERDICT: ACCURATE**

Source: `src/agents/tool-policy-pipeline.ts`, function `applyToolPolicyPipeline()` (lines 104-105):
```typescript
const expanded = expandPolicyWithPluginGroups(policy, pluginGroups);
filtered = expanded ? filterToolsByPolicy(filtered, expanded) : filtered;
```

The pipeline takes the complete tool list, applies successive filters, and returns the reduced set. This happens in the tool resolution phase — before the LLM receives its function-calling tool definitions. The LLM never knows about excluded tools.

### Claim 3: Denylist 优先，无 allow 条目时隐式 allow-all，有 allow 条目时只允许匹配项

**VERDICT: ACCURATE**

Source: `src/agents/pi-tools.policy.ts`, function `makeToolPolicyMatcher()` (lines 15-39):
```typescript
// 1. Check deny first
if (matchesAnyGlobPattern(normalized, deny)) {
  return false;
}
// 2. No allow entries -> implicit allow-all
if (allow.length === 0) {
  return true;
}
// 3. Has allow entries -> only matched tools pass
if (matchesAnyGlobPattern(normalized, allow)) {
  return true;
}
return false;
```

**FILE PATH ERROR**: The Concept page references `src/agents/tool-policy-match.ts` as the location of `filterToolsByPolicy()`. This file does not exist. The correct path is `src/agents/pi-tools.policy.ts`.

---

## Openclaw: Exec Approval

### Claim 4: safeBins 包含 git/npm/docker

**VERDICT: FACTUAL ERROR**

Source: `src/infra/exec-command-resolution.ts`, line 7:
```typescript
export const DEFAULT_SAFE_BINS = ["jq", "cut", "uniq", "head", "tail", "tr", "wc"];
```

The actual DEFAULT_SAFE_BINS are text-processing utilities (`jq`, `cut`, `uniq`, `head`, `tail`, `tr`, `wc`). They are NOT `git`, `npm`, `docker` as the Concept page claims. These are safe precisely because they are read-only text filters with no filesystem side effects.

Git, npm, and docker are fundamentally different — they are mutable operations and would be inappropriate for a default safe-bin list. The Concept page should correct this example.

### Claim 5: 默认 timeout 5 分钟

**VERDICT: FACTUAL ERROR**

Source: `src/agents/bash-tools.exec-runtime.ts`, line 70:
```typescript
export const DEFAULT_APPROVAL_TIMEOUT_MS = 120_000;
```

The actual default approval timeout is **120 seconds (2 minutes)**, not 5 minutes. The hermes gateway timeout IS 5 minutes (`gateway_timeout` defaults to 300 in `tools/approval.py` line 838), but the Concept page incorrectly attributes this to openclaw in the cross-repo comparison table.

### Claim 6: Two-phase protocol — registerExecApprovalRequest -> waitForExecApprovalDecision

**VERDICT: ACCURATE**

Source: `src/agents/bash-tools.exec-approval-request.ts`:
- `registerExecApprovalRequest()` (line 50): registers the approval with the gateway server-side before exec returns
- `waitForExecApprovalDecision()` (line 88): blocks until the user responds with `/approve` or `/deny`
- `requestAndWaitForExecApproval()` (line 107): convenience that combines both phases

The two-phase design prevents a race condition where `/approve` could arrive before the registration completes.

### Claim 7: 命令分析在 exec-approvals-allowlist.ts — 解析 shell 命令链，逐段匹配

**VERDICT: ACCURATE**

Source: `src/infra/exec-approvals-allowlist.ts`, function `evaluateShellAllowlist()` (lines 448-551):
1. Splits by chain operators (&&, ||, ;) via `splitCommandChain()`
2. For each chain part, parses shell pipeline via `splitShellPipeline()`
3. Resolves each segment's command resolution (executable path, argv) via `analyzeShellCommand()`
4. Evaluates each segment against allowlist/safeBins/skills via `evaluateSegments()`
5. safeBins additionally requires: path in trusted dirs, valid profile, argv validated against profile constraints

The skill trust mechanism (`autoAllowSkills` + `isSkillAutoAllowedSegment()`) is verified in lines 150-172: when `autoAllowSkills` is true and the executable is in the skill bin trust index, the segment auto-passes.

---

## Hermes: 44 Patterns

### Claim 8: 44 个正则模式

**VERDICT: ACCURATE**

Manual count of `DANGEROUS_PATTERNS` in `tools/approval.py` (lines 75-138) confirms exactly 44 tuple entries.

### Claim 9: 44 个模式分 8 类

**VERDICT: IMPRECISE — CODE HAS NO EXPLICIT CATEGORIES**

The `DANGEROUS_PATTERNS` array is a flat list of 44 `(pattern, description)` tuples with no category labels, no grouping, and no tiering. The source code does not categorize patterns.

The Concept page's cross-repo comparison table organizes them into 7 logical categories (not 8):
1. File system destruction (rm/chmod/chown/mkfs/dd/tee)
2. SQL destruction (DROP/DELETE/TRUNCATE)
3. System service control (systemctl/kill/pkill)
4. Shell injection (curl|sh/heredoc/process substitution)
5. Git destruction (reset --hard/force push/clean -f/branch -D)
6. Gateway self-protection (hermes process termination)
7. Sensitive path writes (/etc/, ~/.ssh, .hermes/.env)

A reasonable person could organize the 44 patterns into anywhere from 5-10 categories. The 7 categories listed in the table are a useful interpretation but are not source-level truth. The "8 类" claim in the text (intro section: "44 种危险模式正则 + tirith 安全扫描") does not explicitly say 8 categories, but the verification task asks "是否真的分 8 类". Answer: the code has zero explicit categories, and the table shows 7, not 8.

### Claim 10: 所有模式是否真的被同等对待（无危险等级区分）

**VERDICT: ACCURATE**

Source: `tools/approval.py`, function `detect_dangerous_command()` (lines 186-197):
```python
for pattern, description in DANGEROUS_PATTERNS:
    if re.search(pattern, command_lower, re.IGNORECASE | re.DOTALL):
        pattern_key = description
        return (True, pattern_key, description)
```

All 44 patterns are iterated in a flat loop. The first match returns immediately. There is no severity level, no weight, no tiered escalation — every match triggers the same approval flow. The `description` serves as the approval key and is what gets persisted in `command_allowlist` or session state, but this doesn't affect the detection/approval logic.

---

## Hermes: Interception Location

### Claim 11: 命令执行前拦截的位置 — 在 tool handler 中而不是独立的中间件

**VERDICT: ACCURATE**

Source: `tools/terminal_tool.py`, function `terminal_tool()` (lines 1286-1314):
```python
# Pre-exec security checks (tirith + dangerous command detection)
# Skip check if force=True (user has confirmed they want to run it)
approval_note = None
if not force:
    approval = _check_all_guards(command, env_type)
    if not approval["approved"]:
        # ... handle approval_required or blocked
```

The call to `_check_all_guards()` (which delegates to `check_all_command_guards()` in `tools/approval.py`) happens:

1. **Inside the `terminal_tool()` function** — not in a middleware, not in a decorator
2. **After environment setup** (sandbox creation, etc.)
3. **Before `subprocess` execution** (the actual command run happens later, after line 1458)
4. **Only when `force=False`** — providing an override path for trusted replay

This is correctly described by the Concept page as pre-exec interception within the command execution path, not an external middleware layer.

---

## Hermes: Other Claims

### Claim 12: 三层递进审批 — YOLO bypass -> aux LLM -> human

**VERDICT: ACCURATE**

Source: `tools/approval.py`, function `check_all_command_guards()` (lines 693-922):

Phase 1 (lines 703-710): YOLO check — `os.getenv("HERMES_YOLO_MODE") or is_current_session_yolo_enabled() or approval_mode == "off"` → bypass all

Phase 2.5 (lines 766-786): Smart approval — when `approval_mode == "smart"`, calls `_smart_approve()` which uses an auxiliary LLM to return approve/deny/escalate. "escalate" falls through to Phase 3.

Phase 3 (lines 790-922): Human interactive approval — blocks on gateway FIFO queue or CLI input().

### Claim 13: Tirith 发现时不允许 always

**VERDICT: ACCURATE**

Source: `tools/approval.py`, lines 864-871:
```python
for key, _, is_tirith in warnings:
    if choice == "session" or (choice == "always" and is_tirith):
        # tirith: session only (no permanent broad allowlisting)
        approve_session(session_key, key)
    elif choice == "always":
        # dangerous patterns: permanent allowed
        approve_session(session_key, key)
        approve_permanent(key)
        save_permanent_allowlist(_permanent_approved)
```

When `is_tirith=True`, even a user choice of "always" is downgraded to "session". This prevents permanently allowlisting content-level security findings.

### Claim 14: _normalize_command_for_detection() 剥离 ANSI、null 字节、NFKC Unicode

**VERDICT: ACCURATE**

Source: `tools/approval.py`, lines 168-183:
```python
def _normalize_command_for_detection(command: str) -> str:
    command = strip_ansi(command)          # ANSI escape sequences
    command = command.replace('\x00', '')   # null bytes
    command = unicodedata.normalize('NFKC', command)  # Unicode normalization
    return command
```

### Claim 15: 容器环境自动跳过

**VERDICT: ACCURATE**

Source: `tools/approval.py`, line 703:
```python
if env_type in ("docker", "singularity", "modal", "daytona"):
    return {"approved": True, "message": None}
```

Both `check_dangerous_command()` and `check_all_command_guards()` skip all checks for container environments.

### Claim 16: always 持久化到 config.yaml 的 command_allowlist

**VERDICT: ACCURATE**

Source: `tools/approval.py`, `save_permanent_allowlist()` (lines 394-402):
```python
def save_permanent_allowlist(patterns: set):
    config = load_config()
    config["command_allowlist"] = list(patterns)
    save_config(config)
```

---

## Summary of Errors Found

| # | Location | Claim | Error | Fix |
|---|----------|-------|-------|-----|
| 1 | table: 检测机制 > openclaw | safeBins 白名单包含 git/npm/docker | `DEFAULT_SAFE_BINS = ["jq", "cut", "uniq", "head", "tail", "tr", "wc"]` | Correct the examples to text-processing tools. Git/npm/docker would be added via explicit allowlist entries, not safeBins. |
| 2 | table: 审批流程 > openclaw | 默认 timeout 5 分钟 | `DEFAULT_APPROVAL_TIMEOUT_MS = 120_000` (2 minutes) | Change to "默认 timeout 2 分钟" |
| 3 | 溯源 > 源码验证 (line references) | `tool-policy-match.ts` 包含 `filterToolsByPolicy()` | 此文件不存在。实际文件是 `pi-tools.policy.ts` | Correct the file path. The denylist-first logic is in `makeToolPolicyMatcher()` within `pi-tools.policy.ts`. |
| 4 | table: 检测机制 > hermes | 44 种正则模式隐含"分 8 类" | 源码中 DANGEROUS_PATTERNS 是无分类标签的扁平数组；跨仓库对比表中列出 7 个类别 | Clarify that categorization is an interpretation, not a code-level organization. The table lists 7, not 8, categories. |
