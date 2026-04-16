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

# --- Install pre-push hook (append to existing) ---
HOOK_FILE="$HOOKS_DIR/pre-push"
MARKER="# --- Wingman: Codex review (non-blocking) ---"

WINGMAN_BLOCK='# --- Wingman: Codex review (non-blocking) ---
# Runs codex review in background after push on feature branches.
# Push proceeds immediately — findings saved to .reviews/ for /review-loop.

WINGMAN_BRANCH=$(git rev-parse --abbrev-ref HEAD)
WINGMAN_TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)
WINGMAN_REVIEW_DIR=".reviews"
WINGMAN_REVIEW_FILE="${WINGMAN_REVIEW_DIR}/${WINGMAN_TIMESTAMP}-${WINGMAN_BRANCH//\//-}.json"

# Skip main/develop/master branches
if [[ "$WINGMAN_BRANCH" != "main" && "$WINGMAN_BRANCH" != "master" && "$WINGMAN_BRANCH" != "develop" ]]; then
    mkdir -p "$WINGMAN_REVIEW_DIR"

    # Run in background — push proceeds immediately
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
        echo "Pre-push hook: Wingman block already present — skipping."
    else
        echo "" >> "$HOOK_FILE"
        echo "$WINGMAN_BLOCK" >> "$HOOK_FILE"
        echo "Pre-push hook: Appended Wingman block to existing hook."
    fi
else
    mkdir -p "$(dirname "$HOOK_FILE")"
    echo "#!/bin/bash" > "$HOOK_FILE"
    echo "" >> "$HOOK_FILE"
    echo "$WINGMAN_BLOCK" >> "$HOOK_FILE"
    echo "Pre-push hook: Created $HOOK_FILE"
fi

chmod +x "$HOOK_FILE"

# --- Symlink if using a custom hooks dir outside .git/hooks ---
if [ "$HOOKS_DIR" != ".git/hooks" ]; then
    GIT_HOOK_LINK=".git/hooks/pre-push"
    RELATIVE_PATH="../../${HOOKS_DIR}/pre-push"
    if [ ! -L "$GIT_HOOK_LINK" ] || [ "$(readlink "$GIT_HOOK_LINK")" != "$RELATIVE_PATH" ]; then
        ln -sf "$RELATIVE_PATH" "$GIT_HOOK_LINK"
        echo "Symlinked: $GIT_HOOK_LINK -> $RELATIVE_PATH"
    fi
fi

# --- Remove old post-commit hook if it has Wingman block ---
OLD_HOOK="$HOOKS_DIR/post-commit"
if [ -f "$OLD_HOOK" ] && grep -q "$MARKER" "$OLD_HOOK"; then
    # Check if the file ONLY contains the Wingman block (plus shebang)
    NON_WINGMAN_LINES=$(sed '/# --- Wingman/,/# --- End Wingman ---/d' "$OLD_HOOK" | grep -v '^#!/' | grep -v '^$' | wc -l | tr -d ' ')
    if [ "$NON_WINGMAN_LINES" -eq 0 ]; then
        rm "$OLD_HOOK"
        # Also remove symlink if it exists
        OLD_LINK=".git/hooks/post-commit"
        [ -L "$OLD_LINK" ] && rm "$OLD_LINK"
        echo "Removed old post-commit hook (was Wingman-only)."
    else
        echo "Warning: post-commit hook has Wingman block from a previous install."
        echo "  It also has other content, so it was NOT removed automatically."
        echo "  You may want to manually remove the Wingman block from $OLD_HOOK."
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
echo "  2. Push your branch — Codex reviews in background"
echo "  3. Run /review-loop to process findings before opening PR"
echo "  4. Run /review-retro weekly"
