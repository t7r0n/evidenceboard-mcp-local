# Security Review

## Scope

Local CLI, deterministic synthetic product-management fixtures, evidence retrieval, prompt-injection sanitizer, MCP-style JSONL tool loop, DuckDB run store, dashboard, and demo-pack export.

## Assessment

The application is offline and synthetic-only. It does not contact external product-management APIs, load credentials, mutate global configuration, or execute shell commands. Customer-authored note fixtures are treated as hostile and sanitized before being returned in tool responses.

## Controls

- JSON fixtures are parsed through Pydantic models.
- Tool responses include structured `_evidence` spans with source IDs.
- Prompt-injection-like note content is escaped and marked with sanitizer findings.
- DuckDB writes use parameterized inserts.
- Dashboard rendering uses explicit Jinja autoescaping.
- Runtime state, outputs, caches, and virtual environments are ignored by git.

## Focused Scan Status

Completed 2026-05-18.

Threat model: local offline CLI and dashboard over synthetic fixtures. Primary risks are accidental credential/data inclusion, prompt-injection text being returned unsanitized, unsafe command execution, unsafe database writes, and unsafe HTML rendering.

Finding discovery:

- Secret/public-hygiene scan found no credentials, private tokens, campaign artifacts, or private customer data in committed source candidates.
- Dangerous sink scan found no runtime shell execution, network clients, dynamic `eval`/`exec`, pickle, YAML loading, or socket use in `src/`.
- The only `subprocess` use is in tests to black-box validate the CLI JSONL tool loop.
- DuckDB writes use parameterized statements and a workspace-local file lock to avoid cross-process write corruption.
- Dashboard output is generated from local JSON through Jinja autoescaping.

Validation: no reportable findings.

Residual risk: this is a reference local implementation, not a production-authenticated MCP server. Production use would need transport authentication, authorization, audit retention policy, request limits, and integration-specific privacy controls.
