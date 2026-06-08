# Feature Specification: Marketplace Plugin + Pluggable Reviewer

**Feature Branch**: `feat/marketplace-plugin`

**Created**: 2026-06-08

**Status**: Draft

**Input**: User description: "Package Wingman as a Claude Code marketplace plugin AND make its code reviewer truly pluggable (codex | gemini | claude, codex default); keep the existing skills-CLI install path; lead the docs with the write-back differentiator; auto-upgrade existing installs; don't block pushes when a reviewer is missing."

## Clarifications

### Session 2026-06-08

- Q: When a user picks `claude` as the reviewer but Claude also wrote the code, how should Wingman behave? → A: Allow it (a zero-extra-account on-ramp) but surface a non-blocking note recommending a different model for true cross-model value.
- Q: How should the reviewer choice be selected and remembered? → A: Both — a per-push environment override AND a repository default persisted at setup time.
- Q: When no model is pinned for gemini/claude, which model runs? → A: Each reviewer CLI's own default/latest model (no pin), mirroring the default reviewer's behavior.
- Q: What is the packaging boundary for the published plugin? → A: Explicitly exclude local tooling and secrets (spec-kit/linear scaffolding, `.env`, machine-specific config); only plugin-relevant files ship.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Install Wingman from the marketplace (Priority: P1)

A developer using Claude Code discovers Wingman, adds it from the marketplace, and installs it. The three review commands appear under a `wingman` namespace, and a single setup command wires the current repository for cross-model review.

**Why this priority**: Being installable from the marketplace is the entire point of this release — without it, no new user can discover or adopt Wingman through the channel everyone else uses. It is the minimum shippable value.

**Independent Test**: From a clean Claude Code install, add the marketplace and install the plugin, confirm `/wingman:review-setup`, `/wingman:review-loop`, `/wingman:review-retro` are listed, run setup in a git repo, and confirm the review configuration is in place.

**Acceptance Scenarios**:

1. **Given** a developer with Claude Code and a git repository, **When** they add the Wingman marketplace and install the plugin, **Then** the three review commands are available under the `wingman` namespace.
2. **Given** the plugin is installed, **When** the developer runs the setup command, **Then** the repository is configured for review (hook, review-data location, learned-patterns file) without overwriting unrelated existing configuration.
3. **Given** the plugin source, **When** it is checked against the marketplace's automated validation, **Then** validation passes with no errors.

---

### User Story 2 - Choose which model reviews my code (Priority: P1)

A developer whose code is written by one model selects a *different* model to review it (the cross-model second opinion is the core value), choosing among codex, gemini, or claude — without editing any code.

**Why this priority**: The product promises "reviewer-agnostic," but today only one reviewer actually works. Making the choice real is what makes the promise honest and removes the single biggest barrier to a cold install (being forced onto one specific external account).

**Independent Test**: Configure each of the three reviewers in turn, trigger a review on a branch with a known issue, and confirm a review is produced by the selected model and recorded as such.

**Acceptance Scenarios**:

1. **Given** no reviewer override, **When** a developer triggers a review, **Then** the default reviewer (codex) is used and behavior is identical to the previous release.
2. **Given** a developer selects an alternate reviewer (gemini or claude), **When** they trigger a review, **Then** the review is produced by that model and the review record identifies which model/provider produced it.
3. **Given** any supported reviewer, **When** its findings are processed, **Then** they flow through the existing categorize → fix → learn loop with no reviewer-specific steps required from the user.

---

### User Story 3 - Never get blocked when a reviewer is missing (Priority: P2)

A developer selects (or defaults to) a reviewer whose tool isn't installed or authenticated. Their push still succeeds, and they get a clear explanation of how to enable reviews.

**Why this priority**: A cold install where the first push appears to "break" produces immediate abandonment and bad reviews. Graceful degradation protects the first-run experience that decides adoption.

**Independent Test**: With the configured reviewer's tool absent, perform a push (or trigger a review) and confirm the push completes and a clear "reviewer unavailable" result with setup guidance is recorded/surfaced.

**Acceptance Scenarios**:

1. **Given** the configured reviewer's tool is not available, **When** the developer pushes, **Then** the push completes successfully and is never blocked.
2. **Given** the same situation, **When** the developer looks at the review result, **Then** it clearly states the reviewer was unavailable and how to install or switch reviewers.

---

### User Story 4 - Upgrade an existing install cleanly (Priority: P2)

An existing Wingman user re-runs setup (or updates the plugin) and their repository's review configuration is upgraded in place — no duplicate configuration, no loss of accumulated review data.

**Why this priority**: Wingman already has users on earlier versions. A messy upgrade (duplicate hook blocks, lost convergence history) erodes trust in a tool whose whole thesis is reliability over time.

**Independent Test**: Install an earlier version, then run the new setup; confirm exactly one active review configuration remains at the new version and prior review data is intact.

**Acceptance Scenarios**:

1. **Given** a repository with an older Wingman review configuration, **When** the user re-runs setup, **Then** it is upgraded to the new version in place with exactly one active configuration.
2. **Given** an upgrade, **When** it completes, **Then** previously recorded review data and convergence history are preserved.

---

### User Story 5 - Keep working on non-Claude-Code agents (Priority: P3)

A developer using one of the other supported AI coding agents installs Wingman through the existing skills route, unaffected by the new plugin packaging.

**Why this priority**: The current audience spans many agents; the plugin is additive and must not strand existing non-Claude-Code users.

**Independent Test**: Use the skills-CLI install path and confirm the three skills install and function for a non-Claude-Code agent.

**Acceptance Scenarios**:

1. **Given** a non-Claude-Code agent, **When** the developer installs Wingman via the skills route, **Then** the three review skills are installed and usable.

---

### Edge Cases

- **Reviewer tool present but unauthenticated or erroring**: treated like "unavailable" — the push still completes and the result explains the problem rather than failing silently or blocking.
- **An unrecognized reviewer value is configured**: treated as "unavailable" with guidance listing the supported reviewers.
- **A very large diff is reviewed by an alternate reviewer**: the review must not fail due to input-size limits of how the diff is handed to the reviewer.
- **Upgrading a repository whose review configuration was hand-edited**: the user can force a clean re-install that results in exactly one active configuration.
- **Reviewer equals the writer's model**: the review still runs, with a non-blocking note recommending a different model for true cross-model value.
- **No persisted default and no override set**: the built-in default reviewer (codex) is used.
- **Publishing the plugin**: no local secrets or machine-specific configuration are included in the published package.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST be installable as a Claude Code plugin through the marketplace (add-marketplace then install).
- **FR-002**: The installed plugin MUST expose the three review capabilities under the `wingman` namespace (`/wingman:review-setup`, `/wingman:review-loop`, `/wingman:review-retro`).
- **FR-003**: System MUST retain a separate installation path for non-Claude-Code agents so existing users are not stranded.
- **FR-004**: Users MUST be able to select which model reviews their code from at least three options: codex, gemini, and claude.
- **FR-005**: The default reviewer MUST remain codex, so users who do not opt in experience no behavioral change from the prior release.
- **FR-006**: Regardless of which reviewer is selected, findings MUST be expressed in the same severity and category structure the rest of the review loop already consumes, so categorize/fix/learn behaves identically.
- **FR-007**: When the configured reviewer is unavailable (missing, unauthenticated, erroring, or unrecognized), the system MUST NOT block or fail the push and MUST record a clear, actionable result explaining how to enable reviews.
- **FR-008**: Each review record MUST identify the reviewer that produced it (tool, model, provider) so findings can be compared and audited across reviewers.
- **FR-009**: Re-running setup (or updating) on a repository with an older Wingman configuration MUST upgrade it in place, leaving exactly one active review configuration with no duplicates.
- **FR-010**: Upgrades MUST preserve previously recorded review data and convergence/round-tracking history.
- **FR-011**: The exemptions, CI-status awareness, and convergence/round-tracking behavior MUST be unchanged by reviewer selection.
- **FR-012**: For non-default reviewers, the code presented for review MUST be scoped to the current branch's changes relative to its base, consistent with the default reviewer's scope.
- **FR-013**: Documentation MUST lead with the differentiator — accepted findings are written back into the project's rules and linter configuration so the same issue does not recur — and MUST document how to select a reviewer.
- **FR-014**: The published package MUST NOT introduce duplicate or stray configuration artifacts and MUST NOT include local secrets or machine-specific configuration.
- **FR-015**: The plugin MUST pass the marketplace's automated validation prior to submission.
- **FR-016**: Users MUST be able to set a per-push reviewer override AND persist a repository-default reviewer at setup time, so the choice does not have to be repeated on every push. The per-push override takes precedence over the persisted default, which takes precedence over the built-in default (codex).
- **FR-017**: When the selected reviewer is the same model as the one that wrote the code (e.g. choosing `claude` in a Claude-authored repository), the system MUST still run the review but MUST surface a non-blocking note recommending a different model for genuine cross-model value. It MUST NOT block or refuse the review.
- **FR-018**: When no specific model is pinned, each reviewer MUST use its own CLI's default/latest model (no hardcoded model pin), consistent with the default reviewer's current behavior.
- **FR-019**: The published plugin package MUST exclude local development tooling and secrets — including spec-kit/linear scaffolding, `.env` files, and machine-specific configuration — and ship only files relevant to the plugin itself.

### Key Entities *(include if feature involves data)*

- **Plugin / marketplace listing**: Wingman's published identity — name, version, description, and the entry that makes it discoverable and installable.
- **Reviewer**: the model that produces a second-opinion review — characterized by tool, model, and provider; selectable by the user; distinct from the model that wrote the code.
- **Review record**: the saved outcome of a review — findings, the reviewer that produced them, and a status (including an "unavailable" status when no review could be produced).
- **Review configuration**: the per-repository setup that triggers reviews — carries a version so it can be upgraded in place.
- **Learned patterns / exemptions / convergence history**: accumulated project knowledge that must survive upgrades and remain reviewer-neutral.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new user can go from discovery to their first cross-model review in 5 steps or fewer and in under 5 minutes.
- **SC-002**: A user can change which model reviews their code with a single configuration change and zero code edits.
- **SC-003**: 100% of pushes complete successfully even when the configured reviewer is unavailable (zero blocked pushes attributable to Wingman).
- **SC-004**: After upgrading from any prior version, a repository has exactly one active review configuration (zero duplicates) and retains 100% of prior review data.
- **SC-005**: Findings from every supported reviewer are processed by the categorize/fix/learn loop with zero reviewer-specific actions required from the user.
- **SC-006**: The plugin passes the marketplace's automated validation on first submission.
- **SC-007**: Existing non-Claude-Code installations continue to function with no regression after this release.

## Assumptions

- Cross-model value depends on the reviewer being a *different* model than the one that wrote the code; codex remains the default because it is the proven path.
- The community marketplace is the submission target; the curated/official marketplace is selected by Anthropic at its discretion and has no application process.
- The marketplace submission step itself is a manual web form, outside the scope of automation in this feature.
- The existing exemptions, CI-awareness, and convergence logic is already reviewer-neutral and is reused unchanged.
- In-place upgrade relies on a stable installation marker so older configurations are detected and replaced rather than duplicated.
- Out of scope for this release: an on-demand review command, a stop-hook trigger, a zero-dependency Claude-as-default on-ramp, and a convergence-statistics visualization.
