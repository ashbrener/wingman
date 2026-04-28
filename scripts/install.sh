#!/usr/bin/env bash
set -euo pipefail

# --- Parse flags ---
FORCE_REINSTALL=0
for arg in "$@"; do
    case "$arg" in
        --force|--reinstall)
            FORCE_REINSTALL=1
            ;;
        -h|--help)
            cat <<'USAGE'
Usage: install.sh [--force]

Options:
  --force, --reinstall   Unconditionally replace any existing Wingman block
                         in the pre-push hook, even if the installed version
                         is up to date.
USAGE
            exit 0
            ;;
        *)
            echo "Unknown argument: $arg" >&2
            echo "Try: install.sh --help" >&2
            exit 2
            ;;
    esac
done

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
END_MARKER="# --- End Wingman ---"

# Single source of truth for the hook block: assets/pre-push.sample.
# install.sh only orchestrates append/create logic; the hook content
# itself lives in one canonical file so docs and runtime stay in sync.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WINGMAN_SAMPLE="$SCRIPT_DIR/../assets/pre-push.sample"

if [ ! -f "$WINGMAN_SAMPLE" ]; then
    echo "Error: canonical hook block not found at $WINGMAN_SAMPLE" >&2
    echo "       Reinstall the wingman pack: npx skills add ashbrener/wingman" >&2
    exit 1
fi

# --- Helpers: extract version stamps ---
# Block format embeds `# wingman-hook-version: N` near the top. v1 (the
# original release) had no stamp at all, so absence == 1.
_extract_version() {
    # $1: file path
    local _v
    _v=$(grep -m1 -E "^[[:space:]]*#[[:space:]]*wingman-hook-version:[[:space:]]*[0-9]+" "$1" 2>/dev/null \
        | sed -E "s/^[[:space:]]*#[[:space:]]*wingman-hook-version:[[:space:]]*([0-9]+).*/\1/")
    if [ -z "$_v" ]; then
        echo "1"
    else
        echo "$_v"
    fi
}

SAMPLE_VERSION=$(_extract_version "$WINGMAN_SAMPLE")

_strip_wingman_block() {
    # $1: file path — removes the Wingman block in place.
    local _tmp
    _tmp=$(mktemp -t wingman-hook)
    sed '/# --- Wingman: Codex review/,/# --- End Wingman ---/d' "$1" > "$_tmp"
    # Trim trailing blank lines so re-append doesn't accumulate whitespace.
    awk 'BEGIN{blank=0} { if ($0 ~ /^[[:space:]]*$/) { blank++ } else { for (i=0;i<blank;i++) print ""; blank=0; print } }' "$_tmp" > "$1"
    rm -f "$_tmp"
}

if [ -f "$HOOK_FILE" ]; then
    if grep -q "$MARKER" "$HOOK_FILE"; then
        INSTALLED_VERSION=$(_extract_version "$HOOK_FILE")
        if [ "$FORCE_REINSTALL" -eq 1 ]; then
            _strip_wingman_block "$HOOK_FILE"
            printf "\n" >> "$HOOK_FILE"
            cat "$WINGMAN_SAMPLE" >> "$HOOK_FILE"
            echo "Pre-push hook: --force replaced Wingman block (was v$INSTALLED_VERSION → now v$SAMPLE_VERSION)."
        elif [ "$INSTALLED_VERSION" -lt "$SAMPLE_VERSION" ]; then
            _strip_wingman_block "$HOOK_FILE"
            printf "\n" >> "$HOOK_FILE"
            cat "$WINGMAN_SAMPLE" >> "$HOOK_FILE"
            echo "Pre-push hook: Upgraded Wingman block (v$INSTALLED_VERSION → v$SAMPLE_VERSION)."
        else
            echo "Pre-push hook: Wingman block already at v$INSTALLED_VERSION (current is v$SAMPLE_VERSION) — skipping."
            echo "  Use 'install.sh --force' to reinstall anyway."
        fi
    else
        printf "\n" >> "$HOOK_FILE"
        cat "$WINGMAN_SAMPLE" >> "$HOOK_FILE"
        echo "Pre-push hook: Appended Wingman block to existing hook (v$SAMPLE_VERSION)."
    fi
else
    mkdir -p "$(dirname "$HOOK_FILE")"
    {
        echo "#!/bin/bash"
        echo ""
        cat "$WINGMAN_SAMPLE"
    } > "$HOOK_FILE"
    echo "Pre-push hook: Created $HOOK_FILE (v$SAMPLE_VERSION)"
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
