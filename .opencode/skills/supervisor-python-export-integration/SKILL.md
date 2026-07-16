---
name: supervisor-python-export-integration
description: Use when supervising Python data export work that pushes records, files, or payloads to external APIs or systems
---

# Supervisor Python Export Integration

## Purpose

Supervise export work without implementing it yourself. Delegate target API research, typed payload design, TDD implementation, safe integration testing, and independent verification to workers.

## Use When

Use for Python code that pushes data to external systems: API exporters, SDK wrappers, upload pipelines, webhook dispatchers, outbound syncs, or batch sends.

Do not use for ingestions that pull external data into a warehouse; use `supervisor-python-ingest-integration` instead.

## Core Workflow

```
1. CLARIFY: target system, payloads, environment safety, credentials, and done criteria
2. RESEARCH: delegate current target API/auth/schema/rate-limit research before code
3. PLAN: slice work by observable export behavior
4. MODEL: require typed models for every outbound payload
5. IMPLEMENT: delegate each slice with TDD to one worker
6. TEST SAFELY: require unit tests plus an integration test against sandbox/staging unless live use is explicitly approved
7. FINAL VERIFY: delegate independent verification before finalizing
```

## Delegation Requirements

Implementation briefs must tell workers to load `python-export-integration`, `software-development`, and `researching-latest-practices` when available.

Require workers to:

- Research target specs before writing integration code.
- Define Pydantic or equivalent typed models for every outbound payload.
- Validate payloads locally before sending.
- Use typed, centralized config for credentials, base URLs, batch sizes, and environment targets.
- Use Polars for tabular processing when DataFrames are needed.
- Fail fast on validation, API, upload, delete, and target error responses.
- Avoid `.get()` defaults for required fields; missing required data should raise.
- Add unit tests for models/transforms and an end-to-end integration test against a safe non-live target.
- Write or update `agent_docs/development/YYYY-MM-DD-<integration-name>.md`.

## Supervisor Checks

Before accepting worker output, confirm evidence for:

- Current target API research.
- Red/green/refactor TDD steps for each implemented slice.
- Typed outbound models and local validation before send.
- Sandbox/staging integration testing, or explicit user approval for live targets.
- Fail-fast behavior instead of log-and-continue on critical failures.
- Unit and integration tests run, with failures explained.
- Development report present and accurate.
- Independent verification completed for non-trivial changes.

If any check is missing, re-delegate focused remediation before finalizing.
