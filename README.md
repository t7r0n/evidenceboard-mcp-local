# Evidenceboard MCP Local

Evidenceboard MCP Local is an offline reference implementation for evidence-first product feedback reasoning. It exposes MCP-style tools over deterministic synthetic product data: customer notes, themes, features, objectives, initiatives, segments, and releases.

The project does not call real product-management APIs and does not contain customer data or credentials. It is designed to show how an agent-facing product feedback server can return evidence, citations, and sanitized customer-authored text by default.

## Quick Start

```bash
uv sync
uv run evidenceboard-local init-demo
uv run evidenceboard-local run-suite --iterations 50
uv run evidenceboard-local verify
uv run evidenceboard-local dashboard
```

Try one tool:

```bash
uv run evidenceboard-local cite-evidence feat-onboarding-checklist --top-k 5
```

## Tool Surface

- `cite_evidence(feature_id)`
- `align_to_objective(feature_id, objective_id)`
- `summarise_segment(segment_id, since_days)`
- `assess_prioritisation(initiative_id)`
- `tool-loop` for JSONL MCP-style local calls

## Outputs

- `runs/latest/evidenceboard.duckdb`
- `outputs/tool_results.json`
- `outputs/summary.json`
- `outputs/tool_schema.json`
- `outputs/dashboard.html`
- `outputs/demo_pack/`
