# Feature Specification: A review that did not run is not a round

**Feature Branch**: `fix/failed-review-not-a-round`

**Created**: 2026-10-05

**Status**: Draft

**Input**: Codex review of an installed copy of the hook, 2026-10-05 — *"a missing or failing reviewer still records a zero-finding round in `_convergence.json`; two such pushes set `stop_rule_met: true`."* Confirmed live: a first push failed with HTTP 401 (reviewer not logged in) and was recorded as a clean round.

## Context

Wingman's convergence signal says "two consecutive rounds with no P1 and at most two P2 — you can stop reviewing." Spec 002 made the counts truthful for every review that **ran**. This spec closes the remaining hole: a review that **did not run**.

When the reviewer cannot run — its CLI is not installed, the configured name is unknown, or it starts and then exits with an error (a 401 because the user is not logged in, a quota error, a network failure) — the hook still writes an artifact and still appends a round to the ledger. That round carries zero findings, because nothing was reviewed. Zero findings is exactly what a clean round looks like, so the stop-rule counts it. Two such pushes in a row report `stop_rule_met: true` and print a notice recommending the author declare convergence — on a branch nobody has reviewed.

This is the same failure class as spec 002, one step earlier: **a signal that cannot fail is worse than none.** A missing reviewer must read as "no review happened", never as "the review was clean".

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A review that did not run never counts toward convergence (Priority: P1)

An author pushes twice while the reviewer is unavailable — not installed, or installed but not logged in. Neither push produces a convergence notice, the ledger does not claim the stop-rule is met, and each artifact says plainly that the review did not run and why.

**Why this priority**: this is the defect. A false "converged" ends the review loop on unreviewed code.

**Independent Test**: drive the emitter twice with a missing-reviewer output, and twice with a recorded authentication failure; verify the stop-rule is never met, no round is recorded, and no convergence notice is emitted.

**Acceptance Scenarios**:

1. **Given** a reviewer that is not installed, **When** the author pushes twice, **Then** neither push is counted as a round, the stop-rule is not met, and no convergence notice appears.
2. **Given** a reviewer that starts but exits with an error (for example an authentication failure), **When** the author pushes twice, **Then** the same holds.
3. **Given** a reviewer run that did not complete, **When** its artifact is written, **Then** the artifact still exists, records the reviewer's output, and states explicitly that the review failed or the reviewer was missing, with the reason.

---

### User Story 2 - An outage neither breaks nor advances the streak (Priority: P1)

An author has one clean round. The reviewer then fails once (a transient login expiry). The author fixes the login and pushes again; that review is also clean. The two real clean rounds are consecutive for the stop-rule — the failure between them is invisible to the arithmetic, neither resetting the streak nor adding to it.

**Why this priority**: equal-first. Resetting the streak on an outage punishes the author for an infrastructure problem; advancing it is the defect itself.

**Independent Test**: drive clean → failed → clean; verify the failed run is not a round, the second clean run is round 2, and the stop-rule is met on round 2.

**Acceptance Scenarios**:

1. **Given** one clean round, **When** a failed run follows, **Then** the round count, the clean streak and the stop-rule state are unchanged.
2. **Given** clean → failed → clean, **When** the second clean run is recorded, **Then** it is round 2 and the stop-rule is met.
3. **Given** a round with findings followed by a failed run, **When** stagnation and trend are assessed on the next real round, **Then** they compare against the last real round, not the failed run.

---

### User Story 3 - Real reviews behave exactly as before (Priority: P2)

Reviews that run are untouched: findings still count, clean reviews still converge, the continuous-integration and stagnation signals are unchanged.

**Independent Test**: drive two genuinely clean reviews and verify the stop-rule is met on round 2; drive a review with findings and verify the counts are non-zero and the stop-rule is not met.

**Acceptance Scenarios**:

1. **Given** two consecutive clean reviews, **When** the second is recorded, **Then** the stop-rule is met exactly as today.
2. **Given** a review whose text happens to contain an error-like phrase but which reported findings, **When** it is classified, **Then** it counts as a review that ran.

---

### Edge Cases

- The reviewer exits non-zero but printed a full review — failed: the exit status is the reviewer's own statement that it did not complete, and an uncounted run only delays convergence, while a false round can fake it.
- The reviewer exits zero but its output ends in an authentication or HTTP error — failed.
- The reviewer exits zero with no output at all — failed: an empty output is not evidence of a clean review.
- A review that quotes a diff or file containing error-like text mid-transcript — not failed on that account; only the tail of the output is inspected, and a run that reported findings is never reclassified.
- A ledger written by an older hook (rounds with no outcome recorded) — every existing round is treated as counted, as before.
- The exit status is not provided (an older caller) — classification falls back to the output alone.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every review run MUST record an explicit outcome — succeeded, failed, or missing — with the reason and, where available, the reviewer's exit status.
- **FR-002**: Only succeeded runs MAY count as rounds. A failed or missing run MUST NOT be numbered as a round, MUST NOT contribute to the stop-rule, and MUST NOT reset or advance the consecutive-clean streak.
- **FR-003**: A failed or missing run MUST NOT emit a convergence notice, and its artifact MUST report the stop-rule as not met.
- **FR-004**: A failed or missing run MUST still write its review artifact, marked with its outcome and carrying the reviewer's raw output, so the author can see what went wrong.
- **FR-005**: A failed or missing run MUST be recorded in the ledger as an uncounted run, separately from rounds, so the history stays visible without polluting round arithmetic.
- **FR-006**: Stagnation and trend MUST compare real rounds only.
- **FR-007**: Failure detection MUST be defined per reviewer and documented: a missing or unknown CLI is missing; a non-zero exit status is failed; an empty output is failed; a reviewer-specific error signature at the end of the output, on a run that reported no findings, is failed.
- **FR-008**: Detection MUST NOT reclassify a run that reported findings as failed on the strength of an error signature alone.
- **FR-009**: Existing behaviours MUST be preserved: the hook never blocks a push, runs in the background, and treats successful reviews exactly as before.
- **FR-010**: The installed-copy version marker MUST be raised so existing installations upgrade through the normal setup path, and the documentation MUST state the current version.
- **FR-011**: No new dependency may be introduced.

### Key Entities

- **Review outcome**: whether the reviewer actually ran to completion — succeeded, failed or missing — with the reason, the exit status, and whether the run counted as a round.
- **Round**: a succeeded review, numbered, contributing to the stop-rule, streak, stagnation and trend.
- **Uncounted run**: a failed or missing review, recorded for visibility but excluded from all round arithmetic.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Two consecutive missing-reviewer pushes leave zero rounds and the stop-rule unmet, where the previous version reported it met.
- **SC-002**: Two consecutive authentication-failure pushes leave zero rounds and the stop-rule unmet.
- **SC-003**: Clean → failed → clean yields exactly two rounds and the stop-rule met on round 2.
- **SC-004**: Two genuinely clean reviews still meet the stop-rule on round 2; a review with findings still does not.
- **SC-005**: Every failed or missing artifact states its outcome and reason and retains the raw reviewer output.

## Assumptions

- A reviewer that exits non-zero did not complete its review, even if it printed partial output.
- Reviewer error messages appear at the end of their output; content quoted during a review appears earlier.
- Rounds already recorded by older hooks cannot be reliably reclassified and are left as they are.

## Out of Scope

- Retrying a failed reviewer, or switching to another reviewer automatically.
- Reclassifying rounds already recorded in existing ledgers.
- Blocking pushes on reviewer failure — review remains advisory.
