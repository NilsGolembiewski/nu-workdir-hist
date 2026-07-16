---
name: supervisor-frontend-development
description: Use when supervising frontend or web UI work through UX/spec design, implementation planning, TDD, e2e testing, and real browser verification with Playwright CLI
---

# Supervisor Frontend Development

## Purpose

Orchestrate frontend work without implementing it yourself. Delegate design, planning, TDD implementation, automated e2e testing, and real browser verification to workers, then verify from evidence.

## Use When

Use for web UI, frontend apps, pages, components, workflows, interactions, layout, responsive behavior, accessibility, visual changes, or any browser-visible behavior.

Do not use for backend-only, CLI-only, data-only, or config-only work unless it changes what users see or do in a browser.

## Core Workflow

```
1. TRIAGE: clarify UI scope, user goals, acceptance criteria, and approval needs
2. SPEC + UX: delegate specs and UX design before implementation planning
3. PLAN: delegate a vertical-slice plan with TDD, e2e, and browser verification
4. IMPLEMENT: delegate each slice to one worker for red/green/refactor
5. E2E: require automated e2e coverage for critical user flows
6. BROWSER VERIFY: require Playwright CLI verification in a real browser
7. FINAL VERIFY: delegate independent verification before finalizing
```

## Hard Gates

- **UX/spec before implementation:** screens, flows, states, accessibility, responsive behavior, and acceptance criteria must be clear.
- **Plan before code:** plans must reference the spec/design and break work into thin, observable vertical slices.
- **TDD for UI code:** each slice starts with a failing test or reproduction, then minimal implementation, then refactor while green.
- **E2E for critical flows:** forms, navigation, auth-sensitive behavior, data mutation, and regressions need automated e2e tests when feasible.
- **Real browser verification:** no web UI change ships without Playwright CLI snapshots, screenshots, interactions, console checks, and network checks.

## Delegation Requirements

### Spec and UX

Delegate to a worker and instruct them to load:

- `spec-definition` for broad, raw, or ambiguous requirements.
- `ux-design` for new screens, workflows, redesigns, or non-trivial interactions.
- `researching-latest-practices` for frontend frameworks, browser APIs, component libraries, or test tools.

Expected outputs:

- Spec: `agent_docs/specs/YYYY-MM-DD-<feature>-spec.md` when needed.
- UX design: `agent_docs/design/YYYY-MM-DD-<feature>.md` when needed.
- Coverage of screens/routes, user flows, loading/empty/populated/error/validation states, accessibility, keyboard behavior, responsive behavior, and acceptance criteria.

For major UX choices, present the design to the user for approval unless they explicitly asked to proceed without review.

### Implementation Plan

Delegate to a worker and instruct them to load `writing-plans` plus `researching-latest-practices` when external frontend APIs are involved.

The plan must:

- Reference spec/design paths.
- Use exact files, routes, commands, and tests.
- Slice by observable user behavior, not horizontal layers.
- Include TDD steps for each slice.
- Identify unit/component/integration tests, e2e tests, and Playwright CLI verification flows.
- Save to `agent_docs/plans/YYYY-MM-DD-<feature>.md`.

### TDD Implementation

Delegate one vertical slice at a time unless slices are independent.

Each implementation brief must include:

- The slice text copied inline.
- Relevant spec/design/plan paths.
- Acceptance criteria and out-of-scope items.
- Required skills: usually `software-development`; add `debugging` for bugs and `researching-latest-practices` for libraries.
- Explicit instruction that the same worker owns red, green, and refactor.
- Required evidence: failing test/reproduction, passing test output, changed files, caveats, blockers.
- Development report: `agent_docs/development/YYYY-MM-DD-<feature>.md` when code, tests, or configuration changed.

Reject implementation results that claim TDD without red/green evidence.

### E2E Testing

Require automated e2e tests for critical flows when feasible.

Workers must follow existing project e2e conventions, assert user-visible outcomes, avoid arbitrary sleeps, control test data, run the exact e2e command, and report results. If e2e is infeasible, require a written rationale plus compensating integration tests and stronger browser verification.

### Playwright CLI Browser Verification

Delegate browser verification after automated checks pass. Instruct the worker to load `browser-verification` or a profile-specific Playwright CLI verification skill.

Required evidence:

- URL/routes and viewport sizes tested.
- `playwright-cli snapshot` before interactions and after page changes.
- `playwright-cli screenshot` for visual confirmation.
- User interactions performed: click, fill, type, press keys, navigate, submit, retry errors as relevant.
- `playwright-cli console` results.
- `playwright-cli requests` results.
- Responsive checks when layout changed, at minimum mobile `375x667` and desktop `1280x800`.
- Keyboard/focus checks for forms, modals, menus, dialogs, and custom controls.

Console errors or relevant failed network requests are blockers unless explained as pre-existing and irrelevant.

## Final Verification

For non-trivial frontend work, delegate independent verification to a fresh worker. Include the original request, acceptance criteria, report paths, changed paths, automated checks, e2e commands, and Playwright CLI flows.

If verification fails, delegate focused remediation, then re-verify. Stop after three verify/remediate cycles and escalate the blocker to the user.

## Exit Checklist

- [ ] Spec/UX is complete enough or a lightweight exception is justified.
- [ ] Plan references spec/UX and uses vertical slices.
- [ ] Each implemented slice has red/green/refactor evidence.
- [ ] Relevant unit/component/integration tests passed.
- [ ] Critical flows have e2e coverage or documented infeasibility.
- [ ] Playwright CLI browser verification passed for affected flows.
- [ ] Console, network, responsive, keyboard, and accessibility-relevant checks are clean or explained.
- [ ] Development and verification reports exist when required.
- [ ] Independent verification passed or blockers are surfaced.
