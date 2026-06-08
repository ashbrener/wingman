---
name: review-setup
description: Install the Wingman review feedback loop into the current project — git hook, .reviews/ directory, and learned patterns rule file
---

# Wingman: Setup

Install the Wingman review feedback loop into the current project.

## Prerequisites

Before running setup, verify:
1. The project is a git repository.
2. A reviewer CLI is available. Wingman defaults to `codex` but supports any of
   `codex | gemini | claude` via the `WINGMAN_REVIEWER` environment variable or a
   `.wingman-reviewer` repo file. The reviewer should be a **different model than
   the one writing the code** — that cross-model second opinion is the value.

Detect which reviewer CLIs are present (`command -v codex`, `command -v gemini`,
`command -v claude`) and report them. If the user's chosen reviewer is missing,
print its install hint and continue — setup must NOT block on a missing reviewer
(the hook degrades gracefully, writing a `reviewer_missing` review file rather
than failing the push):
- Codex CLI: `npm install -g @openai/codex`
- Gemini CLI / Claude CLI: install per their official instructions.

Note: choosing `claude` while Claude wrote the code still works, but it isn't a
true cross-model opinion — prefer `codex` or `gemini` when Claude is the author.

## What to install

### 1. Pre-push git hook

Detect the project's git hooks directory:
- Check `git config core.hooksPath` first
- Look for `.git-hooks/`, `.githooks/`, or `.husky/` directories
- Fall back to `.git/hooks/`

If a `pre-push` hook already exists, append the Wingman section wrapped in clearly marked comments. Do not overwrite existing hook content.

The canonical hook block lives at `assets/pre-push.sample` in the wingman pack — single source of truth. `scripts/install.sh` reads it and appends to the user's hook (or creates one with a `#!/bin/bash` shebang if no hook exists).

To install manually without `scripts/install.sh`, append the contents of `assets/pre-push.sample` to your hook:

```bash
cat <wingman-pack>/assets/pre-push.sample >> .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

The block detects with marker comment `# --- Wingman: Codex review (non-blocking) ---` so re-installation is idempotent. Make the hook executable with `chmod +x`.

### 1b. Persist the chosen reviewer (optional)

Ask the user which reviewer to use (default `codex`; options `codex | gemini |
claude` — prefer a different model than the code's author). If they pick a
non-default, write the bare reviewer name to a `.wingman-reviewer` file at the
repo root:

```bash
echo gemini > .wingman-reviewer
```

The hook resolves the reviewer as: `WINGMAN_REVIEWER` env var → `.wingman-reviewer`
file → `codex`. The file holds no secret and is safe to commit so collaborators
inherit the default. A per-push override is always available via the env var.

### 2. Reviews directory

Create `.reviews/` and add a `.gitkeep` file.

Add to `.gitignore` if not already present:
```
# Wingman review data
.reviews/*.json
```

### 3. Learned patterns rule file

Create `.claude/rules/review-patterns.md` if it doesn't exist:

```markdown
# Learned Patterns from Wingman Reviews

<!-- Wingman: This file is auto-populated by /review:loop and pruned by /review:retro -->
<!-- Maximum 30 patterns. Oldest entries are archived when the cap is reached. -->

## Logic Rules
<!-- Patterns that affect correctness — Claude Code must follow these -->

## Architecture Rules
<!-- Structural patterns — Claude Code must follow these -->

## Security Rules
<!-- Security-sensitive patterns — Claude Code must follow these -->
```

### 4. Migration from post-commit

If a post-commit hook exists with the Wingman marker (`# --- Wingman:`), inform the user that Wingman has moved to pre-push and offer to remove the old block.

### 5. Summary

After setup, print:
- What was installed and where
- Remind the user to commit the hook and rules file
- Suggest: "Push your branch, then run `/review-loop` to process findings before opening a PR"
