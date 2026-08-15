# Feature Specification: Findings parsed at emit time — the review artifact must reflect what the reviewer found

**Feature Branch**: `fix/emit-time-finding-parse`

**Created**: 2026-08-15

**Status**: Draft

**Input**: Operator report, 2026-08-15 — *"wingman ominously always 0 findings now, when before there were 20 rounds."* Investigated across four live arcs the same evening.

## Context

Wingman's value is that a second model reviews every push and the author routes what it found. That loop depends on one thing: the emitted review artifact telling the truth about what the reviewer said.

It currently does not. A review run tonight against a real branch produced **three genuine findings** — two high-severity logic defects (one an audit-event race emitting stale prior values, breaking reconstructibility) and one medium — and the artifact recorded **zero findings, zero priority counts, stop-rule met**, plus a notice recommending the author *declare convergence*. Two further arcs showed the same shape; on one, six real findings across two rounds counted as zero both times.

The cause is a contract split introduced when the reviewer became pluggable: the default reviewer keeps its **native output shape** (one line per finding: file and line, category, severity, description), while the round-tracking counter recognises only the **legacy priority shape** (`[P1]`, `P2:`, `Priority 3`) that is now used solely by the constructed prompts for the alternative reviewers. Every review by the default reviewer therefore counts zero.

Zero counts are not merely a display defect. They drive the stop-rule, so the convergence signal fires on round one and actively tells the author to stop reviewing — while the findings sit unread. **A signal that cannot fail is worse than no signal**, because silence would prompt a human to look, whereas a confident "converged" does not.

Separately but compounding: the artifact's categorized-findings list is empty by design (categorization belongs to the review loop). That is correct — but combined with blind counts it means *nothing* in the artifact reflects what the reviewer found, so any reader glancing at the file concludes the review was clean.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The artifact reflects what the reviewer found (Priority: P1)

An author pushes a branch. The reviewer reports problems in its native shape. The emitted artifact carries those findings in a machine-readable list, so the author — or an agent, or a dashboard — can see at a glance that the review was not clean, without reading a wall of raw output.

**Why this priority**: this is the defect. Everything else is a consequence of it.

**Independent Test**: feed the emitter the exact reviewer output recorded in tonight's incident and verify the artifact carries three findings with their files, lines, categories and severities — where it previously carried none.

**Acceptance Scenarios**:

1. **Given** reviewer output in the native line shape, **When** the artifact is emitted, **Then** it carries one machine-readable entry per finding, each with file, line where stated, category, severity and description.
2. **Given** the same output, **When** the artifact is emitted, **Then** the categorized-findings list remains empty and untouched, because categorization is still the review loop's job.
3. **Given** reviewer output in the legacy priority shape, **When** the artifact is emitted, **Then** the findings are still represented — support for one shape must never remove support for the other.

---

### User Story 2 - Counts and the stop-rule tell the truth (Priority: P1)

The author trusts the round summary. When findings exist, the counts are non-zero, the stop-rule does not fire, and nothing advises declaring convergence. When the review really is clean, the same summary says so honestly.

**Why this priority**: equal-first. A wrong count is worse than a missing one — it ends the review loop early with a recommendation the author has no reason to doubt.

**Independent Test**: replay the recorded incident and verify the round summary reports the true priority counts, the stop-rule does not fire, and no convergence recommendation is emitted; then replay a genuinely clean review and verify it reports zero and converges.

**Acceptance Scenarios**:

1. **Given** a review containing findings of any severity, **When** the round summary is computed, **Then** its priority counts are non-zero and the stop-rule does not report as met.
2. **Given** a review with no findings, **When** the round summary is computed, **Then** counts are zero and convergence behaviour is unchanged from today.
3. **Given** either output shape, **When** counts are computed, **Then** the count is the truthful one for whichever shape the reviewer used — a change in one reviewer's format can never silently zero the counts again.
4. **Given** findings that repeat across rounds, **When** stagnation is assessed, **Then** repeated findings are recognised even when the reviewer emits no identifier prefix.

---

### User Story 3 - Honest zero, and no false positives (Priority: P2)

A clean review reports clean. Ordinary prose that happens to contain the same punctuation as a finding line is not mistaken for a finding.

**Why this priority**: the fix's own failure mode. Over-counting would erode trust as fast as under-counting, and the "clean" path is the common case.

**Independent Test**: emit artifacts from a clean review, from a review whose notes contain pipe characters and file paths, and from a reviewer that could not run; verify each reports honestly.

**Acceptance Scenarios**:

1. **Given** a review stating it found nothing, **When** the artifact is emitted, **Then** it carries no findings and reports zero counts.
2. **Given** narrative prose containing pipe characters, **When** the artifact is emitted, **Then** no finding is recorded from it — the recognised category and severity vocabularies are what qualify a line.
3. **Given** a reviewer that is missing or produced no output, **When** the artifact is emitted, **Then** the existing missing-reviewer outcome is preserved and no finding is invented.
4. **Given** a run where the continuous-integration state contributes a synthetic finding, **When** counts are computed, **Then** that contribution is still included exactly as today.

---

### Edge Cases

- A finding line with no line number — recorded, with the line left unstated.
- A finding whose description itself contains pipe characters — the description survives intact.
- Severity or category outside the recognised vocabulary — not recorded as a finding; it is prose.
- Mixed output (native lines plus legacy priority bullets in one review) — every finding is represented once; nothing is double-counted into a misleading total.
- A very large review — parsing must not slow the push path or change its non-blocking behaviour.
- An artifact written by an older version — remains readable; the reader can tell which version wrote it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The emitted review artifact MUST carry a machine-readable list of the findings the reviewer reported, with file, line (where stated), category, severity and description per finding.
- **FR-002**: That list MUST be distinct from the categorized-findings list the review loop populates; the review loop's contract MUST NOT change.
- **FR-003**: Priority counts MUST be derived from what the reviewer actually reported, in whichever supported output shape it used, and MUST be truthful for both the native and legacy shapes.
- **FR-004**: Supporting an additional output shape MUST NOT reduce support for the existing one; a future change to any single reviewer's format MUST NOT be able to silently return counts to zero.
- **FR-005**: Severity MUST map to priority consistently: the two most severe levels are highest priority, the middle level is second, the lowest is third.
- **FR-006**: The stop-rule and any convergence recommendation MUST be computed from the truthful counts, so no recommendation to stop reviewing can be emitted while findings exist.
- **FR-007**: Repeat-finding (stagnation) detection MUST work without requiring the reviewer to emit an identifier prefix; a finding's location is sufficient identity.
- **FR-008**: A review reporting nothing MUST produce an honest zero, and prose MUST NOT be mistaken for findings — the recognised category and severity vocabularies are the qualifying test.
- **FR-009**: Existing behaviours MUST be preserved: the hook never blocks a push, runs in the background, and continues to record missing-reviewer and continuous-integration-derived outcomes exactly as today.
- **FR-010**: The artifact's version identifier MUST be raised, artifacts written by older versions MUST remain readable, and the documented upgrade path MUST cover the change.
- **FR-010a**: The upgrade path MUST **backfill** older artifacts rather than stub them: the reviewer's raw output was captured correctly all along, so migrating an older artifact MUST parse it and populate the findings and the round counts from it. An empty findings list may only survive migration when the raw output genuinely contains none. Backfill MUST preserve every existing field, including the raw output, and MUST be re-runnable without changing an already-migrated artifact.
- **FR-011**: The installed-copy version marker MUST be raised so existing installations upgrade through the normal setup path.
- **FR-012**: No new dependency may be introduced.

### Key Entities

- **Finding**: one problem the reviewer reported — location (file, optional line), category, severity, description, and the priority derived from severity.
- **Round summary**: the per-push record of how many findings of each priority were reported, whether the stop-rule is met, and how the round compares with previous ones.
- **Review artifact**: the emitted record of one review — reviewer metadata, the raw output, the parsed findings, the (initially empty) categorized findings, and the round summary.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Replaying the recorded incident produces three findings and non-zero priority counts, where the current version produces zero and none.
- **SC-002**: No review containing at least one finding can emit a stop-rule-met or convergence recommendation.
- **SC-003**: A genuinely clean review still reports zero findings and converges — verified alongside SC-001 so the fix cannot be achieved by counting everything.
- **SC-004**: Both supported output shapes yield truthful counts, verified by replaying one recorded review of each shape.
- **SC-005**: Narrative prose containing pipe characters yields zero findings — no false positives.
- **SC-006**: The push path remains non-blocking and its behaviour on a missing reviewer is unchanged.
- **SC-007**: An artifact written by the previous version is still readable by the current tooling.
- **SC-008**: Backfilling the recorded backlog recovers the findings that were reported but never counted — verified against the live set: every artifact whose raw output contains findings ends migration with a non-empty findings list and non-zero counts, and no artifact that was genuinely clean gains one.

## Assumptions

- The reviewer's native output shape is stable enough to parse; the fix's own guard against future drift is that both shapes are supported and counts take whichever is truthful.
- Categorization remains a human/agent step in the review loop; this feature only makes the reviewer's raw report machine-legible.
- Findings appearing in both shapes within one review are rare; the requirement is that the total is never misleading, not that duplicates are perfectly reconciled.

## Out of Scope

- Changing what the reviewer is asked to produce.
- Changing the review loop's categorization contract or its routing decisions.
- Automatically fixing, filing, or routing findings.
- Blocking pushes or merges on findings — review remains advisory.
