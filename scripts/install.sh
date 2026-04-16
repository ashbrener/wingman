#!/usr/bin/env bash
set -euo pipefail

echo "Wingman: Installing review feedback loop..."
echo ""

# --- Detect git repo ---
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "Error: Not a git repository."
    exit 1
fi

# --- Detect hooks directory ---
HOOKS_DIR=""
CUSTOM_HOOKS_PATH=$(git config core.hooksPath 2>/dev/null || true)

if [ -n "$CUSTOM_HOOKS_PATH" ]; then
    HOOKS_DIR="$CUSTOM_HOOKS_PATH"
elif [ -d ".git-hooks" ]; then
    HOOKS_DIR=".git-hooks"
elif [ -d ".githooks" ]; then
    HOOKS_DIR=".githooks"
elif [ -d ".husky" ]; then
    HOOKS_DIR=".husky"
else
    HOOKS_DIR=".git/hooks"
fi

echo "Hooks directory: $HOOKS_DIR"

# --- Install post-commit hook ---
HOOK_FILE="$HOOKS_DIR/post-commit"
MARKER="# --- Wingman: Codex review (non-blocking) ---"

WINGMAN_BLOCK='# --- Wingman: Codex review (non-blocking) ---
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
# --- End Wingman ---'

if [ -f "$HOOK_FILE" ]; then
    if grep -q "$MARKER" "$HOOK_FILE"; then
        echo "Post-commit hook: Wingman block already present — skipping."
    else
        echo "" >> "$HOOK_FILE"
        echo "$WINGMAN_BLOCK" >> "$HOOK_FILE"
        echo "Post-commit hook: Appended Wingman block to existing hook."
    fi
else
    mkdir -p "$(dirname "$HOOK_FILE")"
    echo "#!/bin/bash" > "$HOOK_FILE"
    echo "" >> "$HOOK_FILE"
    echo "$WINGMAN_BLOCK" >> "$HOOK_FILE"
    echo "Post-commit hook: Created $HOOK_FILE"
fi

chmod +x "$HOOK_FILE"

# --- Symlink if using a custom hooks dir outside .git/hooks ---
if [ "$HOOKS_DIR" != ".git/hooks" ]; then
    GIT_HOOK_LINK=".git/hooks/post-commit"
    # Build relative path from .git/hooks/ to the custom hooks dir
    RELATIVE_PATH="../../${HOOKS_DIR}/post-commit"
    if [ ! -L "$GIT_HOOK_LINK" ] || [ "$(readlink "$GIT_HOOK_LINK")" != "$RELATIVE_PATH" ]; then
        ln -sf "$RELATIVE_PATH" "$GIT_HOOK_LINK"
        echo "Symlinked: $GIT_HOOK_LINK -> $RELATIVE_PATH"
    fi
fi

# --- Create .reviews/ directory ---
mkdir -p .reviews
touch .reviews/.gitkeep
echo "Created: .reviews/"

# --- Update .gitignore ---
if [ -f .gitignore ]; then
    if ! grep -q ".reviews/\*.json" .gitignore; then
        echo "" >> .gitignore
        echo "# Wingman review data" >> .gitignore
        echo ".reviews/*.json" >> .gitignore
        echo "Updated: .gitignore"
    else
        echo ".gitignore: Wingman entry already present — skipping."
    fi
else
    echo "# Wingman review data" > .gitignore
    echo ".reviews/*.json" >> .gitignore
    echo "Created: .gitignore"
fi

# --- Create learned patterns rule file ---
RULES_FILE=".claude/rules/review-patterns.md"
if [ ! -f "$RULES_FILE" ]; then
    mkdir -p "$(dirname "$RULES_FILE")"
    cat > "$RULES_FILE" <<'PATTERNS_EOF'
# Learned Patterns from Wingman Reviews

<!-- Wingman: This file is auto-populated by /review:loop and pruned by /review:retro -->
<!-- Maximum 30 patterns. Oldest entries are archived when the cap is reached. -->

## Logic Rules
<!-- Patterns that affect correctness — Claude Code must follow these -->

## Architecture Rules
<!-- Structural patterns — Claude Code must follow these -->

## Security Rules
<!-- Security-sensitive patterns — Claude Code must follow these -->
PATTERNS_EOF
    echo "Created: $RULES_FILE"
else
    echo "$RULES_FILE already exists — skipping."
fi

echo ""
echo "Wingman installed successfully."
echo ""
echo "Next steps:"
echo "  1. Commit the hook and rules file"
echo "  2. Run /review-loop after your next task"
echo "  3. Run /review-retro weekly"
