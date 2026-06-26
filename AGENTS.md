# Agent Development Protocol

This repository uses a lightweight multi-agent development protocol. Every agent must treat these files as the shared source of truth before changing code or project state.

## Startup Rules

1. Read this file first.
2. Read `.omx/development/current.md` and `.omx/development/handoff.md` before making changes.
3. Inspect the current worktree before relying on previous conversation context.
4. Preserve user or agent changes you did not make. Never revert unrelated work unless explicitly asked.
5. Keep records short, factual, and useful for the next agent.

## Development Loop

1. Ground yourself in the current repo state.
2. Before meaningful work, identify objective, dependencies, risks, impact scope, and acceptance criteria.
3. Update the plan or current status before starting meaningful work.
4. Implement in small, verifiable steps.
5. Run the narrowest useful verification after each risky change.
6. Record decisions, mistakes, unresolved risks, and next steps as they appear.
7. Before ending work, run the applicable completion checks, add a reflection, and update the handoff.

## Required Records

- `.omx/development/current.md`: current objective, status, last verification, blockers, and next action.
- `.omx/development/worklog.md`: meaningful development events, not noisy command-by-command output.
- `.omx/development/decisions.md`: important choices, rejected alternatives, and consequences.
- `.omx/development/error-ledger.md`: mistakes, wrong assumptions, root causes, fixes, and prevention rules.
- `.omx/development/handoff.md`: concise state for the next agent.
- `.omx/development/reflections.md`: task-end retrospectives, lessons, waste, and process improvements.
- `.omx/development/quality-gates.md`: adaptive pre-change and pre-delivery checklists.
- `.omx/development/skill-candidates.md`: reusable lessons that may become future skills, scripts, or project rules.

## Recording Rules

- Update `current.md` whenever the objective, status, blocker, verification result, or next action changes.
- Append to `worklog.md` for meaningful phases: planning, implementation milestone, verification, blocker, handoff.
- Add to `decisions.md` when choosing between plausible approaches.
- Add to `error-ledger.md` when an assumption, command, design choice, or implementation path turns out wrong.
- Add to `reflections.md` before declaring a meaningful task finished.
- Use `quality-gates.md` for release, handoff, or risky changes; mark irrelevant checks as not applicable.
- Add to `skill-candidates.md` when a lesson is repeated, high-cost, cross-project, or easy to automate.

## Error Ledger Format

Each error entry should include:

- Symptom
- Wrong assumption
- Root cause
- Detection method
- Fix
- Prevention rule
- Skill candidate: yes/no

## Handoff Standard

Before stopping, update `.omx/development/handoff.md` with:

- Current objective
- What changed
- What is verified
- What is not verified
- Known risks or blockers
- Exact next recommended action

## Quality Gate Standard

Before high-risk changes, delivery, or release, check the applicable categories in `.omx/development/quality-gates.md`.

Use these statuses:

- Pass: verified with evidence.
- Warn: partially covered or residual risk remains.
- Fail: must fix or explicitly defer.
- N/A: not relevant to this project or change.

Always include file, command, or inspection evidence for pass, warn, and fail results.

## Experience Distillation

At task completion, review `error-ledger.md`, `decisions.md`, `worklog.md`, and `reflections.md`.

Promote lessons as follows:

- One-off project detail: keep only in the relevant log.
- Stable project rule: add to `AGENTS.md`.
- Cross-project workflow: add to `skill-candidates.md`.
- Repeated fragile operation: create or update a script/template.
- Repeated agent behavior rule: create or update a global skill.