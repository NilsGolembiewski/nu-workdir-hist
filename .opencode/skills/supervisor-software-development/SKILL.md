---
name: supervisor-software-development
description: Use when supervising software feature work, bug fixes, refactors, or behavior changes through delegated TDD execution and independent verification
---

# Supervisor Software Development

## Overview

Lead software work without executing it yourself. Shape delivery into small vertical slices, require modular implementation with minimal tangling between horizontal components, delegate implementation to workers, require Test-Driven Development (TDD), independently verify outcomes, and keep the user informed from evidence rather than assumptions.

## When to Use

Use when the user asks for new applications, feature work, bug fixes, refactors, migrations, behavior changes, or codebase improvements. This skill is only available to supervisors, not workers.

Lightweight exceptions: throwaway prototypes, generated code, config-only changes, trivial glue code, and small styling tweaks. Even for exceptions, still delegate execution and request appropriate validation evidence.

## Supervisor Workflow

```
1. UNDERSTAND: Clarify behavior, acceptance criteria, edge cases, and affected areas
2. SLICE: Break work into thin, observable vertical slices
3. MODULARIZE: Ensure implementation keeps cohesive modules and clean boundaries between horizontal components
4. DELEGATE RED/GREEN/REFACTOR: Instruct one implementation worker to complete the full TDD loop for the slice
5. CHECK TDD: Confirm the worker produced evidence of red, green, and any refactor while green
6. REPEAT: Continue one behavior at a time
7. VERIFY + REPORT: Delegate independent verification after TDD loops are complete and require/update the development report
```

## 1. Understand and Slice

Before delegating implementation, ensure the plan answers:

- What behavior needs to change?
- What does done look like?
- What edge cases and errors matter?
- What is the smallest useful testable slice?
- Which worker is responsible for implementation, review, and verification?

Plan by vertical slices: thin observable behaviors that cross the required layers. Avoid broad horizontal plans like "database first, then API, then UI" unless a small enabling step is necessary for the next slice.

Vertical slicing is a delivery strategy, not permission to tangle the implementation. Require workers to keep the code modular: cohesive domain/application/UI/data boundaries, narrow interfaces, minimal cross-layer coupling, and no duplicated glue that ties horizontal components together unnecessarily.

## 2. Delegation Requirements

Every implementation brief must instruct the worker to follow the regular software-development principles:

- Load the `software-development` skill when available and relevant. This skill is only available to workers, not the supervisor.
- Start each new behavior or bug fix with a failing test or a clear bug reproduction.
- Make the test pass with the simplest production change.
- Refactor only while tests are green.
- Keep red, green, and refactor steps for a slice with the same implementation worker; do not split those steps across different subagents.
- Keep tests focused, independent, fast, and tied to observable behavior.
- Keep implementation modular with minimal tangling between horizontal components; prefer cohesive modules and explicit interfaces over scattered cross-layer coupling.
- Update or create `agent_docs/development/YYYY-MM-DD-<feature-name>.md` when code, tests, or configuration changed.

If the task involves debugging, also instruct the worker to load `debugging`. If it involves external libraries or SDKs, instruct the worker to load `researching-latest-practices`. If it affects a web UI, instruct the worker to perform browser verification after automated checks pass.

### Implementation Brief Checklist

Include the following in implementation delegations:

- Objective and acceptance criteria for one slice.
- Relevant paths, reports, and prior findings.
- Required skills to load, usually `software-development` plus any task-specific skills.
- Explicit TDD expectation: failing test first, green implementation, refactor while green.
- Instruction that the same implementation worker owns red, green, and refactor for the slice.
- Modular implementation expectations: cohesive boundaries, narrow interfaces, minimal cross-component coupling, and no unnecessary pass-through layers.
- Required tests/checks and expected evidence.
- Required development report path or instruction to create one.
- Output format that includes changes made, tests run, verification evidence, caveats, and blockers.

## 3. Red: Require Test First

For each delegated slice, require the worker to provide evidence that the test failed for the expected reason before implementation. Acceptable evidence includes:

- The new or changed test name and assertion.
- The failing command output or a concise quoted failure.
- For bug fixes, a reproduction that fails before the fix.

If a worker cannot write a useful test, re-delegate exploration or ask the user for clarification before implementation proceeds.

## 4. Green: Minimal Passing Change

Implementation delegations should constrain the worker to solve the current behavior, not future ones. If a worker reports unrelated refactors, scope expansion, or missing tests, re-delegate narrowly before moving on.

## 5. Refactor While Green

Allow refactoring only after tests pass. Refactors should improve names, remove duplication, clarify boundaries, or simplify logic without changing behavior.

Prefer deep modules: simple public interfaces with cohesive internal behavior. Avoid plans or worker outputs that scatter small pass-through logic across many shallow files without a clear boundary.

## 6. Review and Verification

When correctness matters, delegate review or verification to a fresh worker session that did not produce the implementation.

Verification briefs must include:

- Original user request and acceptance criteria.
- Relevant plan, report, and changed paths.
- Required checks, tests, and manual verification.
- A request to confirm the development report is present and accurate.

For web applications, automated tests are not enough. Require browser verification of affected flows, including visual output, interactions, console errors, and network requests when tooling is available.

## Development Report Governance

If workers changed code, tests, or configuration, require them to write or update `agent_docs/development/YYYY-MM-DD-<feature-name>.md` before finishing. Treat the report as handoff memory for later verification and user synthesis.

The report should include:

```markdown
# [Feature/Change Name] Development Report

**Date:** YYYY-MM-DD
**Status:** [in-progress | complete]

## What Changed
[Summary and files changed.]

## Why
[Requirement, bug, or motivation.]

## Approach
[Key decisions, constraints, and trade-offs.]

## Tests
[Tests added/changed and how to run them.]

## Verification
[Test output, manual checks, before/after behavior.]

## Caveats
[Known limitations, assumptions, or deferred work.]
```

## Supervisor Verification Checklist

Before finalizing to the user:

- [ ] Work was delegated; the supervisor did not execute implementation.
- [ ] Plan is sliced by observable behavior.
- [ ] Implementation worker was instructed to use TDD and relevant non-supervisor skills.
- [ ] The same implementation worker completed red, green, and refactor for each slice; those steps were not split across subagents.
- [ ] The supervisor checked that TDD was applied correctly from evidence, not just claimed by the worker.
- [ ] New or changed behavior started with a failing test or bug reproduction, unless explicitly exempted.
- [ ] Relevant tests and project checks passed or failures are explained.
- [ ] Refactoring happened only while tests were green.
- [ ] Slice was verified end-to-end across touched layers.
- [ ] Implementation remains modular despite vertical slicing: cohesive boundaries, minimal tangling between horizontal components, and no unnecessary shallow pass-through layers.
- [ ] Web app changes were browser-verified when applicable.
- [ ] Development report was written or updated when code, tests, or configuration changed.
- [ ] Independent verification was delegated when correctness mattered.

Can't check the required boxes? Re-delegate remediation or surface the blocker instead of finalizing.
