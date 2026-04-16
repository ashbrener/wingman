---
name: review-loop
description: Run Codex cross-model review, categorize findings, fix issues, and encode learned patterns into project rules
---

# Wingman: Review Loop

Run the full review feedback loop: review code with Codex, categorize findings, fix issues, and encode learned patterns so they don't recur.

## Step 1: Gather findings

Check `.reviews/` for files with `"status": "needs_categorization"`.

If uncategorized findings exist, use those. If none exist (or `.reviews/` is empty), run a fresh review:
- Use `/codex:review` (or `/codex:adversarial-review` if the user requests it) against the base branch
- Save the output to `.reviews/<timestamp>-<branch>.json` in the standard format

## Step 2: Parse and categorize

For each uncategorized review file, parse the `raw_review` field and extract individual findings. Categorize each finding as one of:

| Category | Description | Action |
|---|---|---|
| **lint** | Code style, formatting, naming | Should become a linter rule |
| **logic** | Correctness, edge cases, bugs | Fix in code + add to learned patterns |
| **architecture** | Structure, coupling, abstractions | Fix in code + add to learned patterns |
| **security** | Vulnerabilities, injection, auth | Fix in code + add to learned patterns with [SECURITY] prefix |

## Step 3: Fix issues

For **logic**, **architecture**, and **security** findings:
1. Fix each issue in the working branch
2. Commit each fix (or group related fixes) using the format:
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

## Step 4: Encode learned patterns

For non-lint findings, add new entries to `.claude/rules/review-patterns.md` under the appropriate section (Logic Rules, Architecture Rules, or Security Rules).

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
     "description": "Missing null check on lead.metadata",
     "resolution": "Added guard clause in process_lead()",
     "commit": "abc1234"
   }
   ```
2. Set `status` to `"categorized"`

## Step 6: Summary

Print a summary:
- Total findings processed
- Breakdown by category (lint / logic / architecture / security)
- New linter rules added
- New patterns added to `.claude/rules/review-patterns.md`
- Any patterns archived due to cap
- Files modified
