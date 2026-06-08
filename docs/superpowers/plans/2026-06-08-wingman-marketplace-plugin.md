# Wingman Marketplace Plugin + Pluggable Reviewer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package Wingman as an installable Claude Code marketplace plugin and make its reviewer genuinely pluggable (`WINGMAN_REVIEWER` = codex | gemini | claude), so the "reviewer-agnostic" claim becomes true and cold installs succeed.

**Architecture:** Add two manifests (`plugin.json` + single-repo `marketplace.json`) — skills are auto-discovered from the existing root `skills/`, no file moves. Abstract the one Codex-coupled region of the pre-push hook behind a `WINGMAN_REVIEWER` switch with a uniform `[P1/P2/P3]` output contract so the existing convergence parser is unchanged. De-Codex the skills + README. Bump the hook version 3→4; the install marker stays byte-identical so existing installs auto-upgrade.

**Tech Stack:** Bash (git hook + installer), Python 3 (embedded heredocs), JSON (manifests), Markdown (skills/docs), GitHub Actions (shellcheck / bash -n / py_compile / install-smoke).

**Branch:** `feat/marketplace-plugin` (already created, design spec already committed there).

---

## File Structure

**Create:**
- `.claude-plugin/plugin.json` — plugin manifest (identity, version, metadata).
- `.claude-plugin/marketplace.json` — single-repo marketplace listing this plugin.

**Modify:**
- `assets/pre-push.sample` — `WINGMAN_REVIEWER` dispatch + per-reviewer metadata + `WINGMAN_TOOL` into the Python payload + version stamp 3→4 + header comments. **Marker line 1 unchanged.**
- `scripts/install.sh` — cosmetic message generalization (version auto-derives from the sample stamp; detection logic untouched).
- `.github/workflows/wingman-ci.yml` — retarget upgrade scenarios to v4, add a v3→v4 scenario, add reviewer-dispatch + `reviewer.tool` assertions.
- `skills/review-setup/SKILL.md`, `skills/review-loop/SKILL.md`, `skills/review-retro/SKILL.md` — de-Codex.
- `README.md` — lead with the write-back wedge, add plugin install path, document `WINGMAN_REVIEWER`.
- `.gitignore` — finalize to marketplace-relevant ignores (keep `.env` secret hygiene; drop spec-kit-specific lines from the published file).

**Remove:**
- `./.wingman-exemptions.yaml.sample` (stray root duplicate; canonical copy is `assets/.wingman-exemptions.yaml.sample`).

**Do NOT stage (local spec-kit/linear setup):** `.specify/`, root `CLAUDE.md` (spec-kit's generic one), `.env`, `.claude/skills/` spec-kit additions, `.reviews/`. The final PR uses explicit `git add <path>` per task — never `git add -A`.

---

## Task 1: Plugin + marketplace manifests

**Files:**
- Create: `/Users/ashbrener/Code/AI/wingman/.claude-plugin/plugin.json`
- Create: `/Users/ashbrener/Code/AI/wingman/.claude-plugin/marketplace.json`

- [ ] **Step 1: Create the plugin manifest**

Create `.claude-plugin/plugin.json`:

```json
{
  "$schema": "https://json.schemastore.org/claude-code-plugin-manifest.json",
  "name": "wingman",
  "displayName": "Wingman",
  "version": "1.0.0",
  "description": "Cross-model code review that deletes its own findings. A different AI model reviews your diff on push; accepted findings are encoded back into your project rules and linter config so the same mistake can't recur.",
  "author": { "name": "Ash Brener", "url": "https://github.com/ashbrener" },
  "homepage": "https://github.com/ashbrener/wingman",
  "repository": "https://github.com/ashbrener/wingman",
  "license": "MIT",
  "keywords": ["code-review", "cross-model", "review", "linting", "git-hook", "code-quality", "self-improving"]
}
```

- [ ] **Step 2: Create the marketplace manifest**

Create `.claude-plugin/marketplace.json`:

```json
{
  "name": "wingman",
  "owner": { "name": "Ash Brener", "url": "https://github.com/ashbrener" },
  "plugins": [
    {
      "name": "wingman",
      "source": "./",
      "description": "Cross-model code review that learns from every review and makes itself progressively unnecessary."
    }
  ]
}
```

- [ ] **Step 3: Validate the manifests**

Run: `cd /Users/ashbrener/Code/AI/wingman && claude plugin validate . --strict`
Expected: PASS (no errors). If `--strict` flags an unrecognized field, remove that field and re-run. If `claude plugin validate` is unavailable in this environment, fall back to `python3 -c "import json,sys; json.load(open('.claude-plugin/plugin.json')); json.load(open('.claude-plugin/marketplace.json')); print('json ok')"` and note that `claude plugin validate` must be run before submission.

- [ ] **Step 4: Verify skills are discovered as `/wingman:*`**

Run: `ls skills/*/SKILL.md`
Expected: lists `skills/review-setup/SKILL.md`, `skills/review-loop/SKILL.md`, `skills/review-retro/SKILL.md` (these become `/wingman:review-setup`, etc. — no moves needed).

- [ ] **Step 5: Commit**

```bash
cd /Users/ashbrener/Code/AI/wingman
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "feat(plugin): add plugin.json + single-repo marketplace.json"
```

---

## Task 2: Extend CI smoke tests for v4 + reviewer dispatch (write the failing tests first)

This is the "test" for the hook change. We extend `wingman-ci.yml` first and run the new assertions locally against the **current v3 hook** to confirm they fail, proving the test is real.

**Files:**
- Modify: `/Users/ashbrener/Code/AI/wingman/.github/workflows/wingman-ci.yml`

- [ ] **Step 1: Bump fresh-install version assertion + add reviewer-dispatch asserts (Scenario 1)**

In `.github/workflows/wingman-ci.yml`, Scenario 1 ("fresh install"), change:

```yaml
          assert_contains "$HOOK" "# wingman-hook-version: 3"
```
to:
```yaml
          assert_contains "$HOOK" "# wingman-hook-version: 4"
          assert_contains "$HOOK" "WINGMAN_REVIEWER"
          assert_contains "$HOOK" "gemini|claude)"
          assert_contains "$HOOK" "WINGMAN_REVIEWER_MISSING"
```

- [ ] **Step 2: Retarget v1→ and v2→ upgrade scenarios to v4**

In Scenario 2 ("v1 -> v3 upgrade"): change the `echo "::group::v1 -> v3 upgrade"` label to `v1 -> v4`, and change the two post-install assertions from version `3` to `4`:

```yaml
          assert_contains .git/hooks/pre-push "# wingman-hook-version: 4"
          assert_contains .git/hooks/pre-push "WINGMAN_REVIEW_INPUT"
```

In Scenario 3 ("v2 -> v3 upgrade"): change the label to `v2 -> v4`, and change:
```yaml
          assert_contains .git/hooks/pre-push "# wingman-hook-version: 4"
          assert_not_contains .git/hooks/pre-push "# wingman-hook-version: 2"
```
(The `WINGMAN_CONVERGENCE_FILE` / `WINGMAN_EXEMPTIONS_FILE` assertions stay — v4 still has them.)

- [ ] **Step 3: Add a v3→v4 upgrade scenario**

Insert a new scenario block immediately after Scenario 3's `echo "::endgroup::"`:

```yaml
          # --- Scenario 3b: v3 -> v4 upgrade ---
          echo "::group::v3 -> v4 upgrade"
          rm -rf "$WORK" && WORK=$(mktemp -d) && cd "$WORK"
          git init -q -b main && git config user.email ci@e.com && git config user.name ci
          git commit -q --allow-empty -m init
          mkdir -p .git/hooks
          # The v3 sample lives at SHA fb82fed (PR #8 merge on main).
          {
              echo "#!/bin/bash"
              echo ""
              git -C "$WINGMAN_SRC" show fb82fed:assets/pre-push.sample
          } > .git/hooks/pre-push
          chmod +x .git/hooks/pre-push
          assert_contains .git/hooks/pre-push "# wingman-hook-version: 3"
          assert_not_contains .git/hooks/pre-push "WINGMAN_REVIEWER"
          "$WINGMAN_SRC/scripts/install.sh"
          assert_contains .git/hooks/pre-push "# wingman-hook-version: 4"
          assert_not_contains .git/hooks/pre-push "# wingman-hook-version: 3"
          assert_contains .git/hooks/pre-push "WINGMAN_REVIEWER"
          [ "$(count_blocks .git/hooks/pre-push)" = "1" ] || { echo "expected 1 block after v3->v4 upgrade"; exit 1; }
          echo "::endgroup::"
```

- [ ] **Step 4: Retarget the --force scenario to v4**

In Scenario 4 ("--force replaces"), change:
```yaml
          assert_contains .git/hooks/pre-push "# wingman-hook-version: 4"
```

- [ ] **Step 5: Add a reviewer.tool assertion using the payload heredoc (new Scenario 8)**

Insert before the final `echo "All install-smoke scenarios passed."` (the payload heredoc `/tmp/payload.py` is already extracted by Scenario 6, which runs earlier in the same job, so it is available):

```yaml
          # --- Scenario 8: reviewer.tool in the JSON reflects WINGMAN_TOOL ---
          echo "::group::reviewer.tool reflects WINGMAN_TOOL"
          printf '[P3] x.py:1 (lint) — a nit\n' > /tmp/fake-review.txt
          RT=".reviews/tool-check.json"
          WINGMAN_REVIEW_INPUT=/tmp/fake-review.txt \
          WINGMAN_CI_STATUS_INPUT=/tmp/fake-ci.json \
          WINGMAN_PR_NUMBER="" \
          WINGMAN_TOOL="gemini" \
          WINGMAN_TOOL_VERSION="x" \
          WINGMAN_MODEL_USED="gemini-x" \
          WINGMAN_PROVIDER="google" \
          WINGMAN_REASONING="" \
          WINGMAN_SESSION_ID="" \
          WINGMAN_WALL_SECONDS="1" \
          WINGMAN_BRANCH="feat/smoke" \
          WINGMAN_TIMESTAMP="$(date +%Y-%m-%d-%H%M%S)" \
          WINGMAN_BASE="main" \
          WINGMAN_REVIEW_FILE="$RT" \
          WINGMAN_EXEMPTIONS_FILE="" \
          WINGMAN_CONVERGENCE_FILE=".reviews/_convergence.json" \
          python3 /tmp/payload.py
          python3 -c "import json; d=json.load(open('$RT')); assert d['reviewer']['tool']=='gemini', d['reviewer']; print('reviewer.tool ok')"
          echo "::endgroup::"
```

- [ ] **Step 6: Update the install-smoke job name**

Change line 72:
```yaml
    name: install-smoke (fresh / v1->v4 / v2->v4 / v3->v4 / --force / exemptions / convergence)
```

- [ ] **Step 7: Run the new assertions locally against the CURRENT v3 hook to confirm they FAIL**

Run (this drives the smoke logic against the not-yet-changed sample):
```bash
cd /Users/ashbrener/Code/AI/wingman
WORK=$(mktemp -d) && cd "$WORK" && git init -q -b main \
  && git -c user.email=ci@e.com -c user.name=ci commit -q --allow-empty -m init
/Users/ashbrener/Code/AI/wingman/scripts/install.sh >/dev/null
grep -q "# wingman-hook-version: 4" .git/hooks/pre-push && echo "UNEXPECTED PASS" || echo "EXPECTED FAIL: still v3"
grep -q "WINGMAN_REVIEWER" .git/hooks/pre-push && echo "UNEXPECTED PASS" || echo "EXPECTED FAIL: no WINGMAN_REVIEWER yet"
```
Expected: two `EXPECTED FAIL` lines (the current sample is v3 and has no `WINGMAN_REVIEWER`). This proves the tests are real before Task 3 implements the hook.

- [ ] **Step 8: Commit the tests**

```bash
cd /Users/ashbrener/Code/AI/wingman
git add .github/workflows/wingman-ci.yml
git commit -m "test(ci): assert v4 hook + reviewer dispatch + reviewer.tool"
```

---

## Task 3: Implement the pluggable reviewer in the hook

**Files:**
- Modify: `/Users/ashbrener/Code/AI/wingman/assets/pre-push.sample`

- [ ] **Step 1: Bump the version stamp**

Change line 2 from `# wingman-hook-version: 3` to `# wingman-hook-version: 4`. **Leave line 1 (`# --- Wingman: Codex review (non-blocking) ---`) byte-for-byte unchanged** — `install.sh` greps it for detection/strip and a rename would orphan existing installs.

- [ ] **Step 2: Document the new env var in the header + add v4 history**

In the header comment block, under the `WINGMAN_MODEL` line, add:
```bash
#   WINGMAN_REVIEWER     reviewer CLI: codex | gemini | claude (default: codex)
```
Generalize the `WINGMAN_MODEL` comment to `pin a model for the selected reviewer`. Add a `#   v4 — pluggable reviewer …` entry to the History section.

- [ ] **Step 3: Default the reviewer env var**

After the `WINGMAN_EXEMPTIONS_FILE=...` assignment (≈ line 41), add:
```bash
WINGMAN_REVIEWER="${WINGMAN_REVIEWER:-codex}"
```

- [ ] **Step 4: Add a temp file for the constructed prompt**

In the `local` declaration at the top of `_wingman_run` (≈ line 49) add `_full_prompt_file` to the list. After the `_prompt_file=$(mktemp ...)` line (≈ 53) add:
```bash
        _full_prompt_file=$(mktemp -t wingman-fullprompt.XXXXXX)
```
Update the `trap` (≈ line 58) to include it:
```bash
        trap "rm -f '$_review_file' '$_prompt_file' '$_full_prompt_file' '$_ci_status_file' '$_ci_summary_file'" RETURN
```

- [ ] **Step 5: Replace the Codex-only invocation block with the dispatch**

Replace the entire `# --- Run codex review (with optional model pin) ---` block (current lines 154–163) with:

```bash
        # --- Run the configured reviewer (WINGMAN_REVIEWER) ---------------
        # codex has a native `review` subcommand that computes the diff itself.
        # gemini/claude have no review mode, so we construct the full prompt
        # (uniform-format preamble + audit prompt + the diff) and pipe it via
        # stdin — NOT argv — because the diff can exceed ARG_MAX (see v2 note).
        if ! command -v "$WINGMAN_REVIEWER" >/dev/null 2>&1; then
            {
                echo "WINGMAN_REVIEWER_MISSING: reviewer '$WINGMAN_REVIEWER' not found on PATH."
                echo "Install it, or set WINGMAN_REVIEWER to one of: codex, gemini, claude."
            } > "$_review_file"
        else
            case "$WINGMAN_REVIEWER" in
                codex)
                    if [ -n "${WINGMAN_MODEL:-}" ]; then
                        codex review -c "model=\"$WINGMAN_MODEL\"" --base "$WINGMAN_BASE" --prompt-file "$_prompt_file" >"$_review_file" 2>&1 \
                            || codex review -c "model=\"$WINGMAN_MODEL\"" --base "$WINGMAN_BASE" >"$_review_file" 2>&1 \
                            || true
                    else
                        codex review --base "$WINGMAN_BASE" --prompt-file "$_prompt_file" >"$_review_file" 2>&1 \
                            || codex review --base "$WINGMAN_BASE" >"$_review_file" 2>&1 \
                            || true
                    fi
                    ;;
                gemini|claude)
                    {
                        echo "You are a code reviewer giving a second opinion on a diff."
                        echo "For EACH finding, output exactly one line in this format:"
                        echo "  [P1|P2|P3] <file>:<line> (<category>) - <one-line description>"
                        echo "category is one of: logic, security, architecture, lint."
                        echo "Use [P1] critical, [P2] should-fix, [P3] nit."
                        echo "If there are no issues, output the single line: No findings."
                        echo ""
                        cat "$_prompt_file"
                        echo ""
                        echo "=== DIFF: git diff $WINGMAN_BASE...HEAD ==="
                        git diff "$WINGMAN_BASE"...HEAD 2>/dev/null
                    } > "$_full_prompt_file"
                    if [ "$WINGMAN_REVIEWER" = "gemini" ]; then
                        if [ -n "${WINGMAN_MODEL:-}" ]; then
                            gemini -m "$WINGMAN_MODEL" < "$_full_prompt_file" >"$_review_file" 2>&1 || true
                        else
                            gemini < "$_full_prompt_file" >"$_review_file" 2>&1 || true
                        fi
                    else
                        if [ -n "${WINGMAN_MODEL:-}" ]; then
                            claude -p --model "$WINGMAN_MODEL" < "$_full_prompt_file" >"$_review_file" 2>&1 || true
                        else
                            claude -p < "$_full_prompt_file" >"$_review_file" 2>&1 || true
                        fi
                    fi
                    ;;
                *)
                    {
                        echo "WINGMAN_REVIEWER_MISSING: unknown reviewer '$WINGMAN_REVIEWER'."
                        echo "Set WINGMAN_REVIEWER to one of: codex, gemini, claude."
                    } > "$_review_file"
                    ;;
            esac
        fi
```

**Verification note for gemini/claude flags:** before finishing this task, run `gemini --help 2>&1 | head -40` and `claude --help 2>&1 | grep -iA1 'print\|-p'` to confirm non-interactive stdin behavior. If `gemini` needs an explicit non-interactive flag (e.g. `-p`/`--prompt`), add it to both `gemini` invocations. The `|| true` keeps a wrong guess non-fatal (push still succeeds; review file just ends up empty), but the goal is a working default.

- [ ] **Step 6: Replace the Codex-only metadata extraction with per-reviewer logic**

Replace the `# --- Reviewer banner extraction (unchanged from v2) ---` block (current lines 183–189) with:

```bash
        # --- Reviewer metadata extraction (per WINGMAN_REVIEWER) ----------
        local _tool _tool_version _model _provider _reasoning _session_id
        _tool="$WINGMAN_REVIEWER"
        case "$WINGMAN_REVIEWER" in
            codex)
                _tool_version=$(grep -m1 "^OpenAI Codex" "$_review_file" | sed -E "s/^OpenAI Codex ([^ ]+).*/\1/")
                _model=$(grep -m1 "^model:" "$_review_file" | sed "s/^model: *//")
                _provider=$(grep -m1 "^provider:" "$_review_file" | sed "s/^provider: *//")
                _reasoning=$(grep -m1 "^reasoning effort:" "$_review_file" | sed "s/^reasoning effort: *//")
                _session_id=$(grep -m1 "^session id:" "$_review_file" | sed "s/^session id: *//")
                ;;
            gemini)
                _tool_version=$(gemini --version 2>/dev/null | head -n1)
                _model="${WINGMAN_MODEL:-default}"; _provider="google"; _reasoning=""; _session_id=""
                ;;
            claude)
                _tool_version=$(claude --version 2>/dev/null | head -n1)
                _model="${WINGMAN_MODEL:-default}"; _provider="anthropic"; _reasoning=""; _session_id=""
                ;;
            *)
                _tool_version=""; _model="${WINGMAN_MODEL:-}"; _provider=""; _reasoning=""; _session_id=""
                ;;
        esac
```

- [ ] **Step 7: Pass `WINGMAN_TOOL` into the Python payload**

In the env-var prefix before `python3 - <<'WINGMAN_PYEOF'` (the block starting ≈ line 194), add a line alongside the other `WINGMAN_*` exports:
```bash
        WINGMAN_TOOL="$_tool" \
```

- [ ] **Step 8: Use `WINGMAN_TOOL` for `reviewer.tool` and add the `reviewer_missing` status**

In the Python heredoc: change the `"tool": "codex",` line (≈ 449) to:
```python
        "tool": os.environ.get("WINGMAN_TOOL") or "codex",
```
And immediately after the `status = "clean" if not prepended.strip() else "needs_categorization"` line (≈ 441), add:
```python
if raw.startswith("WINGMAN_REVIEWER_MISSING"):
    status = "reviewer_missing"
```

- [ ] **Step 9: Static checks**

```bash
cd /Users/ashbrener/Code/AI/wingman
bash -n assets/pre-push.sample && echo "bash -n OK"
shellcheck --severity=error --shell=bash assets/pre-push.sample && echo "shellcheck OK"
```
Expected: both OK. Fix any shellcheck `error`-level findings before continuing.

- [ ] **Step 10: Verify the embedded Python still compiles**

```bash
cd /Users/ashbrener/Code/AI/wingman
awk '/python3 - <<.WINGMAN_PYEOF./{c=1;next} /^WINGMAN_PYEOF$/&&c{c=0;next} c' assets/pre-push.sample > /tmp/extracted.py
python3 -c "import py_compile; py_compile.compile('/tmp/extracted.py', doraise=True); print('py_compile OK')"
```
Expected: `py_compile OK`.

- [ ] **Step 11: Run the full install-smoke locally**

```bash
cd /Users/ashbrener/Code/AI/wingman
act -j install-smoke 2>/dev/null || echo "no act; running scenarios inline"
```
If `act` is unavailable, replicate the job by hand: extract the `run install scenarios` script body from `.github/workflows/wingman-ci.yml`, set `WINGMAN_SRC=/Users/ashbrener/Code/AI/wingman`, and run it in `bash -euo pipefail`. Expected final line: `All install-smoke scenarios passed.` (This now exercises v1→v4, v2→v4, v3→v4, --force, exemptions, convergence, and reviewer.tool.)

- [ ] **Step 12: Commit**

```bash
cd /Users/ashbrener/Code/AI/wingman
git add assets/pre-push.sample
git commit -m "feat(hook): pluggable reviewer (WINGMAN_REVIEWER) + bump hook v4"
```

---

## Task 4: Generalize the installer message

**Files:**
- Modify: `/Users/ashbrener/Code/AI/wingman/scripts/install.sh`

- [ ] **Step 1: Generalize the post-install hint**

Change line 248 from:
```bash
echo "  2. Push your branch — Codex reviews in background"
```
to:
```bash
echo "  2. Push your branch — your reviewer (WINGMAN_REVIEWER, default codex) runs in background"
```

- [ ] **Step 2: Static check + confirm version auto-derives to 4**

```bash
cd /Users/ashbrener/Code/AI/wingman
shellcheck --severity=error scripts/install.sh && bash -n scripts/install.sh && echo "install.sh OK"
grep -m1 "wingman-hook-version" assets/pre-push.sample
```
Expected: `install.sh OK` and the sample shows version `4` (the installer reads this stamp; no installer detection change needed).

- [ ] **Step 3: Commit**

```bash
cd /Users/ashbrener/Code/AI/wingman
git add scripts/install.sh
git commit -m "chore(install): generalize reviewer message (codex no longer hardcoded)"
```

---

## Task 5: De-Codex the skills

**Files:**
- Modify: `/Users/ashbrener/Code/AI/wingman/skills/review-setup/SKILL.md`
- Modify: `/Users/ashbrener/Code/AI/wingman/skills/review-loop/SKILL.md`
- Modify: `/Users/ashbrener/Code/AI/wingman/skills/review-retro/SKILL.md`

- [ ] **Step 1: review-setup — make prerequisites reviewer-agnostic**

Replace the `## Prerequisites` section (lines 11–19) with:

```markdown
## Prerequisites

Before running setup, verify:
1. The project is a git repository.
2. A reviewer CLI is available. Wingman defaults to `codex` but supports any of
   `codex | gemini | claude` via the `WINGMAN_REVIEWER` environment variable.
   The reviewer should be a *different model than the one writing the code* —
   that cross-model second opinion is where the value comes from.

Detect which reviewer CLIs are present (`command -v codex`, `command -v gemini`,
`command -v claude`) and report them. If the user's chosen reviewer is missing,
give its install hint and continue (the hook degrades gracefully — a missing
reviewer writes a `reviewer_missing` review file rather than blocking the push):
- Codex CLI: `npm install -g @openai/codex`
- Gemini CLI / Claude CLI: install per their official instructions.
```

- [ ] **Step 2: review-setup — soften the marker prose**

Line 41 references the marker. Leave the literal marker string as-is (it must match the hook), but it's fine. No change required beyond Step 1.

- [ ] **Step 3: review-loop — generalize description + fresh-review path**

Change the frontmatter `description` (line 3) to:
```yaml
description: Run cross-model review, categorize findings, fix issues, and encode learned patterns into project rules
```
Change the opening sentence (line 8) "review code with Codex" → "review code with the configured reviewer". In Step 1 (lines 35–36), replace:
```markdown
- Use `/codex:rescue` to request a structured code review of the diff between the current branch and main
- Ask Codex to report: line number, category (lint/logic/architecture/security), severity (critical/high/medium/low), and a one-line description for each finding
```
with:
```markdown
- Run the configured reviewer (`WINGMAN_REVIEWER`, default `codex`) to review the diff between the current branch and `main`. For codex use `/codex:rescue` or `codex review`; for gemini/claude the pre-push hook constructs the prompt automatically.
- Ask the reviewer to report, per finding: line number, category (lint/logic/architecture/security), severity (critical/high/medium/low), and a one-line description.
```
In the schema example, change the `"tool": "codex",` comment to note the value reflects `WINGMAN_REVIEWER` (add `// reviewer.tool reflects WINGMAN_REVIEWER (codex|gemini|claude)` on that line).

- [ ] **Step 4: review-retro — generalize wording**

Line 29: "codex performance regressions" → "reviewer performance regressions". In the Step 1 "Schema-aware reading" list, add a bullet: "Group findings by `reviewer.tool` (codex/gemini/claude) as well as `reviewer.model` to compare reviewers."

- [ ] **Step 5: Commit**

```bash
cd /Users/ashbrener/Code/AI/wingman
git add skills/review-setup/SKILL.md skills/review-loop/SKILL.md skills/review-retro/SKILL.md
git commit -m "docs(skills): make review skills reviewer-agnostic"
```

---

## Task 6: README repositioning + dual install + WINGMAN_REVIEWER

**Files:**
- Modify: `/Users/ashbrener/Code/AI/wingman/README.md`

- [ ] **Step 1: Lead with the write-back wedge**

Replace the opening two lines (after the `# Wingman` title, lines 3–5) with:

```markdown
**The code review tool that deletes its own findings.** A different AI model
reviews your diff on every push — then every finding you accept is encoded back
into your project's rules and linter config, so the same mistake can't recur.
Reviews trend toward empty. Wingman makes itself progressively unnecessary.

Other tools review. Wingman *learns* — cross-model review + write-back +
convergence tracking in one pre-push loop.
```

- [ ] **Step 2: Add the plugin install path (keep npx skills)**

Replace the `## Install` section body (lines 17–27) so it presents BOTH paths, plugin first:

```markdown
## Install

**As a Claude Code plugin (recommended):**

```bash
/plugin marketplace add ashbrener/wingman
/plugin install wingman
/wingman:review-setup
```

Commands install under the `wingman` namespace: `/wingman:review-setup`,
`/wingman:review-loop`, `/wingman:review-retro`.

**As skills for any agent (45+ supported):**

```bash
npx skills add ashbrener/wingman
```

This installs three skills (`review-setup`, `review-loop`, `review-retro`).

| Skill | Plugin command | Skills-CLI command | Purpose |
|---|---|---|---|
| review-setup | `/wingman:review-setup` | `/review-setup` | Install git hook, `.reviews/` dir, patterns rule file |
| review-loop | `/wingman:review-loop` | `/review-loop` | Review → categorize → fix → encode learned patterns |
| review-retro | `/wingman:review-retro` | `/review-retro` | Weekly retrospective — trends, pruning, automation recs |
```

- [ ] **Step 2b: Update the Quick start command references**

In the `## Quick start` section, change the bare `/review-setup`, `/review-loop`, `/review-retro` references to show the plugin form first, e.g. `/wingman:review-setup` (`/review-setup` on the skills CLI). Keep the rest of the flow text intact.

- [ ] **Step 3: Document `WINGMAN_REVIEWER` in the Configuration table**

In the `## Configuration` table (after the `WINGMAN_BASE` / `WINGMAN_MODEL` rows ≈ lines 83–84), add a row:
```markdown
| `WINGMAN_REVIEWER` | `codex` | Reviewer CLI: `codex`, `gemini`, or `claude`. Pick a *different model than the one that wrote the code*. codex uses its native review mode; gemini/claude get a constructed diff+prompt. A missing reviewer CLI writes a `reviewer_missing` review file instead of blocking the push. |
```
And generalize the `WINGMAN_MODEL` row text from "Pin a specific codex model" to "Pin a specific model for the selected reviewer".

- [ ] **Step 4: Verify markdown is well-formed**

```bash
cd /Users/ashbrener/Code/AI/wingman
grep -n "wingman:review-setup" README.md && grep -n "WINGMAN_REVIEWER" README.md
```
Expected: both grep hits present.

- [ ] **Step 5: Commit**

```bash
cd /Users/ashbrener/Code/AI/wingman
git add README.md
git commit -m "docs(readme): lead with write-back wedge; add plugin install + WINGMAN_REVIEWER"
```

---

## Task 7: Housekeeping (stray sample + .gitignore)

**Files:**
- Remove: `/Users/ashbrener/Code/AI/wingman/.wingman-exemptions.yaml.sample`
- Modify: `/Users/ashbrener/Code/AI/wingman/.gitignore`

- [ ] **Step 1: Remove the stray root sample**

```bash
cd /Users/ashbrener/Code/AI/wingman
rm -f .wingman-exemptions.yaml.sample
ls assets/.wingman-exemptions.yaml.sample && echo "canonical copy intact"
```
Expected: canonical copy at `assets/` still listed.

- [ ] **Step 2: Finalize `.gitignore` for the published repo**

Set `.gitignore` to exactly (drops the spec-kit-specific `.specify/...local.yml` line from the published file, keeps `.env` secret hygiene which is universally good — note `.env` itself stays gitignored and untracked locally):

```
node_modules/
.DS_Store

# Wingman review data
.reviews/*.json
.reviews/_convergence.json

# Local secrets — never commit
.env
.env.local
```

Confirm the secret stays ignored after the edit:
```bash
cd /Users/ashbrener/Code/AI/wingman
git check-ignore .env && echo ".env still IGNORED"
```
Expected: `.env still IGNORED`.

- [ ] **Step 3: Commit**

```bash
cd /Users/ashbrener/Code/AI/wingman
git add .gitignore
git rm --cached --ignore-unmatch .wingman-exemptions.yaml.sample 2>/dev/null || true
git commit -m "chore: drop stray root exemptions sample; finalize .gitignore"
```
(The root sample was untracked, so `git rm --cached` is a no-op guard; the `rm -f` in Step 1 is what removes it from the working tree.)

---

## Task 8: Final verification + PR

**Files:** none (verification + delivery).

- [ ] **Step 1: Full local verification gate**

```bash
cd /Users/ashbrener/Code/AI/wingman
claude plugin validate . --strict && echo "PLUGIN VALID"
shellcheck --severity=error scripts/install.sh
shellcheck --severity=error --shell=bash assets/pre-push.sample
bash -n scripts/install.sh && bash -n assets/pre-push.sample && echo "SYNTAX OK"
```
Expected: `PLUGIN VALID`, no shellcheck output, `SYNTAX OK`. (If `claude plugin validate` is unavailable here, record that it MUST be run before submission per Task 1 Step 3.)

- [ ] **Step 2: Confirm only marketplace paths are staged (no spec-kit leakage)**

```bash
cd /Users/ashbrener/Code/AI/wingman
git status --short
git log --oneline origin/main..HEAD
```
Expected: working tree shows untracked `.specify/`, `CLAUDE.md`, `.claude/`, `.reviews/`, `.env` (none staged); the commit list contains only the spec + the 7 implementation commits — no `.specify/` or `CLAUDE.md` committed.

- [ ] **Step 3: Push and open the PR**

```bash
cd /Users/ashbrener/Code/AI/wingman
git push -u origin feat/marketplace-plugin
gh pr create --base main --title "feat: marketplace plugin + pluggable reviewer (v4)" \
  --body "$(cat <<'EOF'
Packages Wingman as a Claude Code marketplace plugin and makes the reviewer truly pluggable.

## What
- `.claude-plugin/plugin.json` + single-repo `marketplace.json` → installable via `/plugin marketplace add ashbrener/wingman`.
- `WINGMAN_REVIEWER` = codex (default) | gemini | claude. codex path unchanged; gemini/claude get a constructed diff+prompt with a uniform `[P1/P2/P3]` output contract. Hook bumped v3 → v4 (auto-upgrades; marker unchanged).
- Skills + README de-Codex'd; README now leads with the write-back wedge.
- CI smoke extended: v1→v4, v2→v4, v3→v4, --force, exemptions, convergence, reviewer.tool.

## Verification
- `claude plugin validate . --strict` passes.
- shellcheck (error) + `bash -n` + py_compile clean.
- install-smoke green.

Design: `docs/superpowers/specs/2026-06-08-wingman-marketplace-plugin-design.md`
EOF
)"
```

- [ ] **Step 4: Wait for CI green, then report**

```bash
cd /Users/ashbrener/Code/AI/wingman
gh pr checks --watch
```
Expected: `lint`, `syntax`, `install-smoke` all pass. Report the PR URL.

- [ ] **Step 5: Hand off the marketplace submission (manual web step)**

After merge, the maintainer submits via `https://claude.ai/settings/plugins/submit` (or `https://platform.claude.com/plugins/submit`). Provide this ready-to-paste blurb:
> **Wingman** — The code review tool that deletes its own findings. A different AI model reviews your diff on push; accepted findings are encoded back into your project's rules + linter config so the same mistake can't recur. Cross-model review + write-back + convergence tracking in one pre-push loop. Repo: github.com/ashbrener/wingman

---

## Self-Review (completed during planning)

**Spec coverage:** Component 1 (manifests) → Task 1. Component 2 (pluggable reviewer) → Tasks 2+3. Component 3 (skills) → Task 5. Component 4 (README) → Task 6. Component 5 (housekeeping) → Task 7. Hook v3→v4 + CI → Tasks 2–4. Validation/delivery → Task 8. No spec section is unmapped.

**Placeholder scan:** No TBD/TODO; every code step shows the literal JSON/bash/markdown. The only deferred items are the explicit `gemini`/`claude` `--help` flag verification (Task 3 Step 5) and the `claude plugin validate` availability fallback (Task 1 Step 3) — both are real verification steps with defined fallbacks, not gaps.

**Type/name consistency:** `WINGMAN_REVIEWER` (env, default codex), `WINGMAN_TOOL` (shell→python bridge for `reviewer.tool`), `_full_prompt_file` (temp), `reviewer_missing` (status string), marker line 1 unchanged, version `4` — all used consistently across Tasks 2, 3, and 8. The CI `WINGMAN_TOOL` env (Task 2 Step 5) matches the hook export (Task 3 Step 7) and the Python read (Task 3 Step 8).
