# Research — findings parsed at emit time

All decisions grounded in a read of `assets/pre-push.sample` (577 lines) and the
live incident artifacts across four arcs, 2026-08-15.

## R-1: A NEW array, alongside `findings` — never repurposing it

- **Decision**: emit `parsed_findings` as a new top-level array; leave
  `"findings": []` exactly as it is.
- **Rationale**: `skills/review-loop/SKILL.md` documents `findings` as
  *"populated by /review-loop categorization"*, and `resolutions` pairs with it.
  Filling `findings` at emit time would silently redefine a contract another
  skill depends on, and would make "categorized" indistinguishable from
  "reported". Two arrays, two meanings, one migration.
- **Alternatives**: populate `findings` and add a `categorized: bool` — rejected:
  every existing reader would change meaning under it.

## R-2: Counts are the MAX of both parses

- **Decision**: `p{1,2,3}_count = max(count_from_native_parse, legacy_grep)`.
- **Rationale**: codex emits its native shape; the constructed gemini/claude
  prompt emits `[P1]`. Either reviewer may be selected per repo
  (`WINGMAN_REVIEWER`), so both must count. MAX (rather than sum) keeps a review
  that happens to contain both shapes from double-counting into a misleading
  total, and — the load-bearing property — **no single format change can return
  a count to zero while the other parser still sees findings**. That is the
  guard against this exact defect recurring.
- **Alternatives**: replace the legacy grep — rejected, it silently breaks
  gemini/claude users. Sum both — rejected, mixed output inflates.

## R-3: Severity → priority

- **Decision**: `critical|high → P1`, `medium → P2`, `low → P3`.
- **Rationale**: matches how the review-loop's own mode table treats severity
  (P1 = must-route, P2 = record/defer), and keeps the stop-rule's existing
  semantics ("zero P1, ≤2 P2") meaningful without re-tuning thresholds.

## R-4: The vocabulary IS the false-positive guard

- **Decision**: a line qualifies as a finding only if it matches
  `file[:line] | category | severity | description` **with category ∈
  {lint, logic, architecture, security} and severity ∈ {critical, high,
  medium, low}**.
- **Rationale**: prose in a `## Notes` section frequently contains pipes and
  paths; a shape-only match would manufacture findings, which erodes trust as
  fast as under-counting (SC-005). Requiring both closed vocabularies makes an
  accidental match essentially impossible while staying tolerant of spacing and
  a missing line number.

## R-5: Identity is `file:line`

- **Decision**: stagnation ids derive from the parsed finding's location,
  appended to (not replacing) the existing `[P1] <id>` / `Finding <id>`
  heuristics.
- **Rationale**: the current heuristics require a prefix the native shape never
  emits, so stagnation detection is blind for codex — the same root cause one
  layer down. Location is stable across rounds and is what a human uses to say
  "that's the same finding".

## R-6: Versioning and the upgrade path

- **Decision**: artifact `wingman_schema_version` 3 → **4**; hook marker
  `wingman-hook-version` 4 → **5**; `scripts/migrate-reviews.py` gains a 3→4
  step that adds an empty `parsed_findings` (older artifacts stay readable, and
  an empty array truthfully means "this artifact predates parsing").
- **Rationale**: the marker line is what `/review-setup` uses to detect and
  replace an installed block, so bumping it is what makes existing clones
  upgrade. Migration keeping older files readable is FR-010.

## R-7: How the parser is verified — no heavyweight harness

- **Decision**: add `scripts/verify-parser.py` + `tests/fixtures/*.txt`. The
  verifier extracts the parser block from `assets/pre-push.sample` between two
  **unique anchor comments**, asserts the anchors appear exactly once, `exec`s
  just that block, and runs it against fixtures: the recorded incident (3
  findings, 2 high 1 medium), a legacy `[P1]` review, a `NO FINDINGS` review,
  and a prose-with-pipes review. Wired as a step in `.github/workflows/wingman-ci.yml`.
- **Rationale**: this repo is a bash hook + skills — introducing pytest and a
  package layout to test one regex would be disproportionate. Extraction keeps
  the parser **single-sourced in the hook** (no copy to drift), and anchoring
  rather than slicing by line number is the lesson from anchored-splice bugs
  elsewhere in this estate: assert the anchor is unique before using it.
- **Alternatives**: duplicate the parser into a python module and import it in
  both places — rejected, two copies of the load-bearing regex is exactly the
  divergence this incident is made of. A pytest suite — rejected as
  disproportionate; revisit if the hook grows more python.
