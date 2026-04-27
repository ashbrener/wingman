---
name: review-setup
description: Install the Wingman review feedback loop into the current project — git hook, .reviews/ directory, and learned patterns rule file
---

# Wingman: Setup

Install the Wingman review feedback loop into the current project.

## Prerequisites

Before running setup, verify:
1. `codex` CLI is installed and authenticated (`codex --version`)
2. The codex-plugin-cc Claude Code plugin is installed (`/codex:setup` works)
3. The project is a git repository

If any prerequisite is missing, inform the user and provide installation instructions:
- Codex CLI: `npm install -g @openai/codex`
- Codex plugin: `/plugin marketplace add openai/codex-plugin-cc` then `/plugin install codex@openai-codex`

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
