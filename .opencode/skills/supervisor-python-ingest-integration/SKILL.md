---
name: supervisor-python-ingest-integration
description: Use when supervising Python data ingestion work that pulls data from external APIs, files, SDKs, or databases into a data warehouse
---

# Supervisor Python Ingest Integration

## Purpose

Supervise ingestion work without implementing it yourself. Delegate research, TDD implementation, data-handling checks, integration testing, and independent verification to workers.

## Use When

Use for Python code that pulls external data into a warehouse: API connectors, SDK wrappers, file readers, webhook storage, loaders, or database syncs.

Do not use for exports or pushes to external systems; use `supervisor-python-export-integration` instead.

## Core Workflow

```
1. CLARIFY: source system, target warehouse, credentials, environments, and done criteria
2. RESEARCH: delegate current API/data-format/auth/rate-limit research before code
3. PLAN: slice work by observable ingestion behavior
4. IMPLEMENT: delegate each slice with TDD to one worker
5. VERIFY DATA RULES: dynamic columns, top-level unnesting, nested JSON strings, all string columns
6. TEST: require unit tests plus an end-to-end integration test
7. FINAL VERIFY: delegate independent verification before finalizing
```

## Delegation Requirements

Implementation briefs must tell workers to load `python-ingest-integration`, `software-development`, and `researching-latest-practices` when available.

Require workers to:

- Research source specs before writing integration code.
- Use typed, centralized config for credentials and environment targets.
- Avoid fixed models for ingested records; derive columns dynamically from returned data.
- Unnest only top-level keys, JSON-encode nested values, and cast every DataFrame column to string.
- Use Polars for tabular processing.
- Fail fast on API, parsing, pagination, processing, delete, and upload failures.
- Add unit tests for transformation logic and at least one integration test for the real flow.
- Write or update `agent_docs/development/YYYY-MM-DD-<integration-name>.md`.

## Supervisor Checks

Before accepting worker output, confirm evidence for:

- Current API/data-format research.
- Red/green/refactor TDD steps for each implemented slice.
- Dynamic schema handling with no fixed ingested-data models.
- All output columns cast to strings; nested dict/list values serialized to JSON strings.
- Fail-fast behavior instead of log-and-continue on critical failures.
- Unit and integration tests run, with failures explained.
- Development report present and accurate.
- Independent verification completed for non-trivial changes.

If any check is missing, re-delegate focused remediation before finalizing.
