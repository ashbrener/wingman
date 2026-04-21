---
name: review-loop
description: Run Codex cross-model review, categorize findings, fix issues, and encode learned patterns into project rules
---

# Wingman: Review Loop

Run the full review feedback loop: review code with Codex, present findings for user decision, fix issues, and encode learned patterns so they don't recur.

## Protocol: auto-surface after push

Whenever the agent runs `git push` in a repo that has Wingman installed
(detectable by the presence of the `# --- Wingman: Codex review` marker
in the repo's `pre-push` hook), the review runs in the background and
finishes ~60-120 seconds later. The agent MUST:

1. Return control to the user immediately after `git push` completes
   (the hook is non-blocking — don't wait for the review).
2. Tell the user: *"Pushed. Wingman review running in the background;
   I'll surface the findings table here when it's ready."*
3. Schedule a follow-up check (e.g. `ScheduleWakeup(delaySeconds: 120)`)
   that re-enters this skill.
4. On wake-up, scan `.reviews/*.json` for the latest file whose `status`
   is `needs_categorization`; if present, proceed to Step 1 below and
   render the findings table inline in chat, unprompted.

This makes the review an ambient part of the push flow, not a manual
step the developer has to remember.

## Step 1: Gather findings

Check `.reviews/` for files with `"status": "needs_categorization"`.

If uncategorized findings exist, use those. If none exist (or `.reviews/` is empty), run a fresh review:
- Use `/codex:rescue` to request a structured code review of the diff between the current branch and main
- Ask Codex to report: line number, category (lint/logic/architecture/security), severity (critical/high/medium/low), and a one-line description for each finding
- Save the output to `.reviews/<timestamp>-<branch>.json` in the standard format

## Step 2: Parse, categorize, and present overview

For each uncategorized review file, parse the `raw_review` field and extract individual findings. Categorize each as:

| Category | Description |
|---|---|
| **lint** | Code style, formatting, naming |
| **logic** | Correctness, edge cases, bugs |
| **architecture** | Structure, coupling, abstractions |
| **security** | Vulnerabilities, injection, auth |

For EACH finding, Claude must also provide its own independent assessment in a "Claude" column:
- **Agree** — Claude concurs with the finding and severity
- **Agree, bump severity** — Claude agrees but thinks severity should be higher/lower (explain why)
- **Disagree** — Claude thinks this is a false positive or not worth fixing (explain why)
- **Skip** — Not applicable in this context (e.g., test file, intentional pattern)

**Present the full overview table sorted by file path (alphabetical) then line number.**

Table formatting rules:
- Use zero-padded finding numbers: `01/16`, `02/16`, etc.
- Severity uses colored emoji: 🔴 CRITICAL, 🟠 HIGH, 🟡 MEDIUM, 🔵 LOW
- Pad header cells with centered text between bullets: `· Header ·`
- File and Claude columns must be wide — pad headers with spaces to set minimum column width
- Keep Claude opinions concise but informative (~40-50 chars)

Example:

```markdown
| · # · | · Severity ·   | · Category · | ·                    File                    · | ·                              Claude                              · |
|-------|----------------|--------------|------------------------------------------------|--------------------------------------------------------------------|
| 01/16 | 🔴 CRITICAL    | security     | `hello_world.py:114`                           | Agree — eval() is never safe on user input                         |
| 02/16 | 🟠 HIGH        | security     | `hello_world.py:22`                            | Agree — classic SQL injection                                      |
| 03/16 | 🟠 HIGH        | security     | `hello_world.py:60`                            | Agree — same pattern as #2                                         |
| ...   | ...            | ...          | ...                                            | ...                                                                |
| 14/16 | 🟡 MEDIUM      | architecture | `hello_world.py:34`                            | Disagree — test file, refactoring adds no value                    |
| 15/16 | 🔵 LOW         | lint         | `hello_world.py:81`                            | Agree — ruff already catches this with F841                        |
```

After the table, show the action bar:

> **all** fix everything · **agreed** fix only where Claude agrees · **one** walk through 1-by-1 · **defer** mark non-actionable with rationale · **per-row** e.g. `01:fix 02:defer 03:fix` · **none** done

### Per-row response format

Users may reply with a space-delimited list pairing each finding number
with an action (`fix`, `defer`, `skip`). Examples:

- `02:fix 03:fix 01:defer` — fix two, defer one
- `all:fix` — same as the top-level `all`
- `all:defer` — defer everything (record rationale for each)

When the user defers a finding, **always** prompt once for a one-line
rationale unless they included it inline (e.g. `01:defer="hifi-aligned"`).
That rationale lands in the review JSON AND in the rules file (Step 4),
so future reviews know not to re-flag the same pattern.

## Step 3: Fix findings (based on user choice)

### If "all":
Spawn a **background Agent** to fix all findings in parallel:
- The agent receives the full list of findings with file paths, line numbers, descriptions, and proposed fixes
- It groups fixes by file for efficiency
- It commits fixes grouped by category:
  - Security fixes: `fix(review): <description>` with `Wingman-finding: security`
  - Logic fixes: `fix(review): <description>` with `Wingman-finding: logic`
  - Architecture fixes: `fix(review): <description>` with `Wingman-finding: architecture`
  - Lint fixes: detect the project's linter (ruff/eslint/biome), add missing rules, run auto-fix, commit as `chore(lint): add rule for <pattern>`
- The agent also encodes learned patterns into `.claude/rules/review-patterns.md` (Step 4)
- The agent updates the review JSON file when done (Step 5)
- Tell the user: "Background agent is fixing N findings. You can keep working — you'll be notified when it's done."

### If "agreed":
Same as "all" but only fix findings where Claude's assessment is "Agree" (including "Agree, bump severity"). Skip findings where Claude said "Disagree" or "Skip". Run as background agent.

### If "one":
Walk through each finding sequentially. Present each finding using this exact format:

Example:

```markdown
| · # · | · Severity ·   | · Category · | ·                    File                    · | ·                              Claude                              · |
|-------|----------------|--------------|------------------------------------------------|--------------------------------------------------------------------|
| 01/16 | 🔴 CRITICAL    | security     | `hello_world.py:114`                           | Agree — eval() is never safe on user input                         |

​```diff
- result = eval(user_input)
+ try:
+     result = int(user_input)
+ except ValueError:
+     print("Invalid input"); sys.exit(1)
​```

> **y** fix · **n** skip · **all** fix remaining · **stop** done
```

Format rules:
- Single-row markdown table using the same padded header format as the overview table
- Diff block showing the proposed change (red for removals, green for additions)
- Blockquote action bar
- Separator `---` between findings
- Wait for user reply before proceeding to next finding
- Do NOT use AskUserQuestion — this is a conversational inline flow

**When user says "y":**
1. Apply the fix
2. Briefly confirm what was changed (one line)
3. Move to the next finding

**When user says "n":**
1. Mark as skipped
2. Move to the next finding

**When user says "all":**
1. Fix the current finding
2. Spawn a background Agent to fix all remaining findings (same as "all" above)
3. Tell the user: "Background agent is fixing N remaining findings. You can keep working — you'll be notified when it's done."

**When user says "stop":**
1. Stop the walk-through
2. Proceed to Step 4 for everything fixed so far

### If "defer" (or per-row `defer`):
Don't modify code. For each deferred finding:

1. Record a one-line rationale from the user (prompt if not given inline).
2. In the review JSON, set the finding's `resolution: "deferred"` and add
   `rationale: "<user's reason>"`.
3. Append a **Deferrals** entry to `.claude/rules/review-patterns.md` under
   a dedicated `### Known false positives / deferrals` subsection within
   the appropriate category (Logic / Architecture / Security Rules), so
   future reviews from the same reviewer model don't re-flag the pattern.
   Include the commit SHA where the deferred state was recorded.

Deferrals are a first-class resolution — they are NOT "skip". Skip means
"not applicable to this repo"; defer means "legitimate pattern, but the
reviewer doesn't have the context to understand why it's correct".

### If "none":
Skip all fixes. Proceed directly to Step 4 to encode patterns for future prevention.

### Lint findings:
When fixing a lint finding (whether individually or in bulk mode):
1. Detect the project's linter. Check for (in order):
   - `pyproject.toml` with `[tool.ruff]` → ruff
   - `.eslintrc*` or `eslint.config.*` → eslint
   - `biome.json` → biome
   - Other common linter configs
2. Check if an existing rule already covers the finding
3. If no rule exists, add the appropriate rule to the linter config
4. Run the linter with auto-fix to apply the new rule
5. Commit separately: `chore(lint): add rule for <pattern>`

## Step 4: Encode learned patterns

For non-lint findings that were fixed (not skipped), add new entries to `.claude/rules/review-patterns.md` under the appropriate section (Logic Rules, Architecture Rules, or Security Rules).

Each pattern entry should be a single clear sentence that Claude Code can follow. Include enough context to apply the rule but keep it concise. Example:

```markdown
## Logic Rules
- Always check for None before accessing `.metadata` on Lead objects — the field is nullable but commonly assumed present
- QuerySet.update() calls must explicitly set `updated_at=timezone.now()` since it bypasses Model.save()
```

**Cap enforcement:** If the file exceeds 30 patterns, remove the oldest entries from each section. Mention which patterns were archived in the summary.

Commit pattern updates separately:
```
docs(review): add learned patterns from Wingman review
```

## Step 5: Update review files

For each processed review file:
1. Populate the `findings` array with structured entries:
   ```json
   {
     "file": "campaigns/services/lead_service.py",
     "line": 42,
     "category": "logic",
     "severity": "medium",
     "description": "Missing null check on lead.metadata",
     "resolution": "Added guard clause in process_lead()",
     "status": "fixed",
     "commit": "abc1234"
   }
   ```
2. For skipped findings, set `"status": "skipped"`.
3. For deferred findings, set `"status": "deferred"` and include a
   `"rationale"` field with the user's one-line reason. Also include a
   `"pattern_rule"` field pointing at the heading in
   `.claude/rules/review-patterns.md` where the deferral was encoded,
   so future review passes can cross-reference.
4. Set the file's `status` to `"categorized"`.

## Step 6: Summary

Print a summary:

```
Wingman Review Summary
======================
Total findings: N
  - Critical: N | High: N | Medium: N | Low: N

Fixed: N
  - Security: N | Logic: N | Architecture: N | Lint: N
Deferred: N (with rationale encoded to rules)
Skipped: N

New linter rules added: N
New patterns encoded: N (of 30 max)
Patterns archived: N

Commits created:
  - abc1234 fix(review): ...
  - def5678 chore(lint): ...
  - ghi9012 docs(review): ...
```
