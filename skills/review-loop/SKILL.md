---
name: review-loop
description: Run Codex cross-model review, categorize findings, fix issues, and encode learned patterns into project rules
---

# Wingman: Review Loop

Run the full review feedback loop: review code with Codex, present findings for user decision, fix issues, and encode learned patterns so they don't recur.

## Step 1: Gather findings

Check `.reviews/` for files with `"status": "needs_categorization"`.

If uncategorized findings exist, use those. If none exist (or `.reviews/` is empty), run a fresh review:
- Use `/codex:rescue` to request a structured code review of the diff between the current branch and main
- Ask Codex to report: line number, category (lint/logic/architecture/security), severity (critical/high/medium/low), and a one-line description for each finding
- Save the output to `.reviews/<timestamp>-<branch>.json` in the standard format

## Step 2: Parse, categorize, and present

For each uncategorized review file, parse the `raw_review` field and extract individual findings. Categorize each as:

| Category | Description | Action |
|---|---|---|
| **lint** | Code style, formatting, naming | Should become a linter rule |
| **logic** | Correctness, edge cases, bugs | Fix in code + add to learned patterns |
| **architecture** | Structure, coupling, abstractions | Fix in code + add to learned patterns |
| **security** | Vulnerabilities, injection, auth | Fix in code + add to learned patterns with [SECURITY] prefix |

**Present findings to the user as a numbered table, sorted by file path (alphabetical) then line number within each file:**

```
Wingman Review Findings
=======================

| #  | File              | Line | Severity | Category     | Finding                                       |
|----|-------------------|------|----------|--------------|-----------------------------------------------|
| 1  | hello_world.py    | 10   | high     | security     | Hardcoded API key committed in source          |
| 2  | hello_world.py    | 22   | high     | security     | SQL injection via f-string interpolation       |
| 3  | hello_world.py    | 27   | medium   | logic        | No null check — fetchone() may return None     |
| 4  | hello_world.py    | 109  | critical | security     | eval() executes arbitrary code from CLI input  |
| 5  | services/auth.py  | 45   | medium   | architecture | God function mixes 5 concerns                 |
| ...

Summary: 1 critical | 3 high | 4 medium | 2 low
```

Use relative file paths from the project root. This makes it easy to fix file-by-file and navigate directly to each finding.

## Step 3: Walk through findings

Walk through each finding sequentially, starting with the highest severity. Present each finding as a compact inline block — no AskUserQuestion widget, just conversational markdown:

```
**#1** critical | security | `hello_world.py:114`
`eval(user_input)` → replace with `int()` + try/except
**y** / n / all / stop?
```

Format rules:
- One finding per block: number, severity, category, file:line on first line
- Second line: the issue + proposed fix in one sentence
- Third line: options (bold the recommended default)
- Show 3-5 lines of the actual code ONLY if the fix is non-obvious
- Wait for user reply before proceeding to next finding

### When user says "y":
1. Apply the fix
2. Briefly confirm what was changed (one line)
3. Move to the next finding

### When user says "n":
1. Mark as skipped
2. Move to the next finding

### When user says "all":
1. Fix the current finding
2. Spawn a **background Agent** to fix all remaining findings in parallel:
   - The agent receives the full list of remaining findings with file paths, line numbers, and descriptions
   - It groups fixes by file for efficiency
   - It commits fixes grouped by category:
     - Security fixes: `fix(review): <description>` with `Wingman-finding: security`
     - Logic fixes: `fix(review): <description>` with `Wingman-finding: logic`
     - Architecture fixes: `fix(review): <description>` with `Wingman-finding: architecture`
     - Lint fixes: detect the project's linter (ruff/eslint/biome), add missing rules, run auto-fix, commit as `chore(lint): add rule for <pattern>`
   - The agent also encodes learned patterns into `.claude/rules/review-patterns.md` (Step 4)
   - The agent updates the review JSON file when done (Step 5)
3. Tell the user: "Background agent is fixing N remaining findings. You can keep working — you'll be notified when it's done."
4. Proceed to summary (the background agent handles encoding and review file updates)

### When user says "stop":
1. Stop the walk-through
2. Proceed to Step 4 for everything fixed so far

### Lint findings:
When fixing a lint finding (whether individually or in "all" mode):
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
2. For skipped findings, set `"status": "skipped"`
3. Set the file's `status` to `"categorized"`

## Step 6: Summary

Print a summary:

```
Wingman Review Summary
======================
Total findings: N
  - Critical: N | High: N | Medium: N | Low: N

Fixed: N
  - Security: N | Logic: N | Architecture: N | Lint: N
Skipped: N

New linter rules added: N
New patterns encoded: N (of 30 max)
Patterns archived: N

Commits created:
  - abc1234 fix(review): ...
  - def5678 chore(lint): ...
  - ghi9012 docs(review): ...
```
