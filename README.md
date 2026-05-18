# Evidenceboard MCP Local

Evidenceboard MCP Local is an offline reference implementation for evidence-first product feedback reasoning. It exposes MCP-style tools over deterministic synthetic product data: customer notes, themes, features, objectives, initiatives, segments, and releases.

The project does not call real product-management APIs and does not contain customer data or credentials. It is designed to show how an agent-facing product feedback server can return evidence, citations, and sanitized customer-authored text by default.

## Thesis

Local evidence-first MCP-style product feedback reasoning server.

## Primitives

- Replays the main `evidenceboard-mcp-local` scenario from source-controlled fixtures.
- Pushes degraded `Evidenceboard MCP Local` cases through the same path as clean cases, then compares the evidence.
- Frames `Evidenceboard MCP Local` as a working evaluator rather than a static concept mock.
- Leaves `evidenceboard-mcp-local` generated state outside git while keeping the rebuild path short.

## Reproduce locally

```bash
uv sync
uv run evidenceboard-local init-demo
uv run evidenceboard-local run-suite --iterations 50
uv run evidenceboard-local verify
uv run evidenceboard-local dashboard
```

```bash
uv run evidenceboard-local cite-evidence feat-onboarding-checklist --top-k 5
```

## Review packet

- `runs/latest/evidenceboard.duckdb`
- `outputs/tool_results.json`
- `outputs/summary.json`
- `outputs/tool_schema.json`
- `outputs/dashboard.html`
- `outputs/demo_pack/`

## Confidence checks

```bash
uv run ruff check .
uv run pytest -q
uv run evidenceboard-local verify
```

## Data limits

`Evidenceboard MCP Local` checks in synthetic fixtures only. Runtime state, dashboards, caches, virtual environments, and generated packs stay out of git.
