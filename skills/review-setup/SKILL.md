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

### 1. Post-commit git hook

Detect the project's git hooks directory:
- Check `git config core.hooksPath` first
- Look for `.git-hooks/`, `.githooks/`, or `.husky/` directories
- Fall back to `.git/hooks/`

If a `post-commit` hook already exists, append the Wingman section wrapped in clearly marked comments. Do not overwrite existing hook content.

Create or append to the post-commit hook:

```bash
# --- Wingman: Codex review (non-blocking) ---
# Runs codex review in background after every commit on feature branches.
# Findings saved to .reviews/ for later analysis via /review:loop

WINGMAN_BRANCH=$(git rev-parse --abbrev-ref HEAD)
WINGMAN_TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)
WINGMAN_REVIEW_DIR=".reviews"
WINGMAN_REVIEW_FILE="${WINGMAN_REVIEW_DIR}/${WINGMAN_TIMESTAMP}-${WINGMAN_BRANCH//\//-}.json"

# Skip main/develop/master branches
if [[ "$WINGMAN_BRANCH" != "main" && "$WINGMAN_BRANCH" != "master" && "$WINGMAN_BRANCH" != "develop" ]]; then
    mkdir -p "$WINGMAN_REVIEW_DIR"

    # Run in background — commit returns immediately
    (
        REVIEW_OUTPUT=$(codex review --base main 2>&1) || true

        if [ -z "$REVIEW_OUTPUT" ]; then
            echo "{\"branch\":\"$WINGMAN_BRANCH\",\"timestamp\":\"$WINGMAN_TIMESTAMP\",\"findings\":[],\"status\":\"clean\"}" > "$WINGMAN_REVIEW_FILE"
        else
            cat > "$WINGMAN_REVIEW_FILE" <<WINGMAN_EOF
{
  "branch": "$WINGMAN_BRANCH",
  "timestamp": "$WINGMAN_TIMESTAMP",
  "raw_review": $(echo "$REVIEW_OUTPUT" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))"),
  "findings": [],
  "resolutions": [],
  "status": "needs_categorization"
}
WINGMAN_EOF
        fi
    ) &
fi
# --- End Wingman ---
```

Make the hook executable with `chmod +x`.

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

### 4. Summary

After setup, print:
- What was installed and where
- Remind the user to commit the hook and rules file
- Suggest running `/review:loop` after their next task
