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

**Present findings to the user as a numbered table, sorted by severity:**

```
Wingman Review Findings
=======================

| #  | Severity | Category     | Line | Finding                                          |
|----|----------|--------------|------|--------------------------------------------------|
| 1  | critical | security     | 109  | eval() executes arbitrary code from CLI input    |
| 2  | high     | security     | 21   | SQL injection via f-string interpolation         |
| 3  | high     | security     | 10   | Hardcoded API key in source                      |
| 4  | medium   | logic        | 26   | No null check — fetchone() may return None       |
| 5  | medium   | architecture | 33   | God function mixes 5 concerns                    |
| 6  | low      | lint         | 3    | Unused import: os                                |
| ...
```

**Then ask the user how to proceed using AskUserQuestion:**

- **"Fix all"** — Fix every finding automatically (group commits by category)
- **"Fix critical/high only"** — Fix only critical and high severity findings, skip the rest
- **"Walk through one by one"** — Present each finding individually, let user approve/skip each fix
- **"Skip — just encode patterns"** — Don't fix anything, but encode non-lint findings as learned patterns for future prevention

## Step 3: Fix issues (based on user choice)

### If "Fix all" or "Fix critical/high only":

For **logic**, **architecture**, and **security** findings (filtered by severity if applicable):
1. Fix each issue in the working branch
2. Group related fixes into commits using the format:
   ```
   fix(review): <description>

   Wingman-finding: <category>
   Resolution: <what was changed>
   ```

For **lint** findings:
1. Detect the project's linter. Check for (in order):
   - `pyproject.toml` with `[tool.ruff]` → ruff
   - `.eslintrc*` or `eslint.config.*` → eslint
   - `biome.json` → biome
   - Other common linter configs
2. Check if an existing rule already covers the finding
3. If no rule exists, add the appropriate rule to the linter config
4. Run the linter with auto-fix to apply the new rule
5. Commit separately:
   ```
   chore(lint): add rule for <pattern>
   ```

### If "Walk through one by one":

For each finding in order:
1. Show the finding with the relevant code snippet
2. Ask the user: **"Fix"**, **"Skip"**, or **"Stop here"**
3. If "Fix" — apply the fix and continue to the next
4. If "Skip" — mark as skipped and continue
5. If "Stop here" — stop the walk-through, proceed to encoding patterns for everything fixed so far

After each fix, briefly confirm what was changed (one line, no verbose summaries).

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
