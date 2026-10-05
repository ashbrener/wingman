# Research — a review that did not run is not a round

Grounded in a read of `assets/pre-push.sample` (hook v5) and the reported
incident: a first push whose codex run failed with HTTP 401 was recorded as a
clean round.

## R-1: Where the defect is

- The reviewer is invoked with `|| true` on every path, so the hook discards the
  exit status. The only failure the payload writer can see is the
  `WINGMAN_REVIEWER_MISSING` sentinel, and even that only changes `status` —
  the ledger round is appended unconditionally.
- Every round with `p1_count == 0 and p2_count <= 2` counts toward the
  stop-rule. A run that reviewed nothing scores 0/0, so it is indistinguishable
  from a clean round.

## R-2: Outcome is classified explicitly, in one place

- **Decision**: the hook captures the reviewer's exit status
  (`WINGMAN_REVIEWER_EXIT`) and passes it to the payload writer, which
  classifies the run with `_classify_review(raw, tool, exit_status)` into
  `succeeded | failed | missing` plus a reason. The result is emitted as a
  top-level `review_outcome` object.
- **Rationale**: the classifier needs the finding parser (FR-008) and the raw
  output, both of which live in the payload writer. One function, one rule.
- **Alternatives**: classify in bash — rejected: it cannot see parsed findings,
  and grepping in two languages is how spec 002's defect happened.

## R-3: The detection rule, per reviewer

Applied in order; the first that matches decides.

| # | Condition | Outcome | Reviewers |
|---|---|---|---|
| 1 | output starts with `WINGMAN_REVIEWER_MISSING` (CLI not on PATH, or unknown reviewer name) | `missing` | all |
| 2 | exit status non-zero | `failed` | all |
| 3 | output empty or whitespace only | `failed` | all |
| 4 | a reviewer-specific error signature matches a line in the **last 5 non-empty lines**, AND the run reported **no findings** in either shape | `failed` | all, each with its own signatures |
| 5 | otherwise | `succeeded` | all |

Signatures (case-insensitive, anchored to the start of a line):

- **codex** — `ERROR:` lines (codex's own error prefix), `unexpected status
  NNN`, `NNN Unauthorized` / `Forbidden`, `stream error`, `stream disconnected`,
  `exceeded retry limit`, `not logged in`, `please run codex login`, usage-limit
  messages.
- **claude** (`claude -p`) — `Invalid API key`, `Please run /login`,
  `API Error:`, `Credit balance is too low`, `Error:`, `not logged in`.
- **gemini** — `Error:`, `[API Error`, `Error when talking to Gemini API`, `Please set an Auth method`,
  `API key not valid`, `GEMINI_API_KEY`, `Quota exceeded`, `not logged in`.

- **Rationale for each guard**:
  - *Exit status first.* It is the reviewer's own statement that it did not
    complete. `codex review` exits non-zero on an authentication failure; when
    the hook retries without `--prompt-file`, the status of the **last**
    attempt is the one recorded.
  - *Empty output.* Every real review prints something — codex its banner, the
    others at least `No findings.` An empty file is not evidence of a clean
    review.
  - *Tail only.* codex's transcript quotes the commands it ran, including diffs
    and file contents, so an error-like phrase can appear mid-transcript in a
    perfectly good review (this very change quotes a 401 fixture). A failed run
    ends in its error; a successful one ends in its review.
  - *Line-anchored.* Diff lines start with `+`, `-` or a space, so a quoted diff
    never matches an anchored signature.
  - *No findings.* A run that reported findings reviewed something. FR-008: a
    signature alone never discards real findings.
- **Bias**: when in doubt the rule says `failed`. An uncounted run only delays
  convergence by one push; a false round can fake it.

## R-4: Failed runs are recorded, but not as rounds

- **Decision**: the ledger keeps `rounds` for succeeded reviews only and gains
  `uncounted_runs` for failed and missing ones. A failed run does not recompute
  the ledger's `convergence` summary at all.
- **Rationale**: `rounds` is read by length (round numbering), by tail (the
  stop-rule's last two), by reverse scan (the zero-P1 streak) and pairwise
  (stagnation, trend). Keeping non-rounds out of that list makes every one of
  those computations correct with no further change, and neither resets nor
  advances the streak (FR-002) — the failure is simply absent from the
  arithmetic. A separate list keeps the history visible (FR-005).
- **Alternatives**: append to `rounds` with a `counted: false` flag and filter
  everywhere — rejected: every reader, present and future, would have to know to
  filter, and the first one that forgets reintroduces the defect.

## R-5: The artifact for a failed run

- `review_outcome` = `{state, reason, exit_status, counted}`.
- `status` = `review_failed` (new) or `reviewer_missing` (existing).
- `convergence.round` = `null`, `convergence.counted` = `false`,
  `stop_rule_met` = `false`, trend `n/a`, no stagnation; the streak value is the
  ledger's current one, unchanged.
- A `[REVIEW FAILED]` or `[REVIEWER MISSING]` notice explains that the push was
  not counted and how to fix it. `raw_review` still carries the reviewer's
  output, so the 401 is visible.

## R-6: Versioning

- **Decision**: hook marker `wingman-hook-version` 5 → **6**. Artifact schema
  stays **4**: `review_outcome` and `convergence.counted` are additive, and an
  artifact without them was written by a hook that did not classify outcomes.
- **Rationale**: the marker is what `/review-setup` compares to upgrade an
  installed block. A schema bump would add a migration step for two additive
  fields that a reader can already treat as "unknown" when absent, and would
  interact with `migrate-reviews.py`'s backfill, which rewrites schema 2–4 files.

## R-6a: CI results are used whenever they parse

- **Defect**: `gh pr checks … > file || echo '{"state":"UNKNOWN",…}' > file`.
  `gh pr checks` exits **1 when any check fails** and **8 when any is
  pending**, while still printing valid JSON. The `||` fallback therefore
  overwrote the red-CI JSON with an empty list exactly when CI was red. The
  writer saw no checks, recorded `NONE`, added no synthetic P1, and two clean
  reviews met the stop-rule on a red branch.
- **Decision**: capture stdout (`_ci_raw`) and the exit status (`_ci_rc`)
  separately. If the output is non-empty and parses as JSON, write it as is,
  whatever the exit status. Otherwise write
  `{"state":"UNKNOWN","checks":[],"gh_exit":N}`. "No PR" and "gh missing" keep
  the existing `NONE` default because the block never calls `gh pr checks`.
- **Rationale**: the exit status of `gh pr checks` reports the checks' state,
  not whether the command worked. The output is the source of truth, and
  validity of the output is the only fallback condition. Validation uses
  `python3 -c json.load`, which the hook already requires, so no new dependency.

## R-7: How it is verified

- **Decision**: `scripts/verify-convergence.py` + fixtures under
  `tests/fixtures/`, in the style of `scripts/verify-parser.py`. It extracts the
  payload writer from `assets/pre-push.sample` (asserting its heredoc delimiters
  appear exactly once), runs it as the hook does — same env vars, a scratch
  `.reviews/` — across sequences of pushes, and asserts the ledger and the
  artifacts. Wired into CI next to the parser verifier.
- The CI block is bash, so the verifier also slices it from the hook, between
  its unique `# --- v3 Feature 2: CI awareness` and
  `# --- Reviewer metadata extraction` headers, and runs it with a fake `gh` on
  `PATH`. The fake prints the check results and exits 1 (failing), 8 (pending),
  0 (green), or 1 with no output or with non-JSON output. Its output is then
  fed through the payload writer.
- **Rationale**: convergence is ledger arithmetic across several runs, so it
  must be exercised end to end, not by unit-testing a slice. Extraction keeps
  the code single-sourced in the hook.
