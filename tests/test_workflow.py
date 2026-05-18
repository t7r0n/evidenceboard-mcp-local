from __future__ import annotations

import json
import subprocess

from evidenceboard_mcp_local.dashboard import build_dashboard
from evidenceboard_mcp_local.engine import align_to_objective, assess_prioritisation, cite_evidence, summarise_segment
from evidenceboard_mcp_local.runner import export_demo_pack, run_suite, verify_outputs


def test_cite_evidence_returns_citations_and_sanitizes_hostile_notes() -> None:
    result = cite_evidence("feat-latency-diagnostics", top_k=5)
    assert result.evidence
    assert any("system-tag" in span.sanitizer_findings for span in result.evidence)
    assert all("<system>" not in span.sanitized_text.lower() for span in result.evidence)


def test_judgment_tools_return_evidence() -> None:
    aligned = align_to_objective("feat-onboarding-checklist", "obj-activation")
    segment = summarise_segment("seg-enterprise", 30)
    priority = assess_prioritisation("init-enterprise-trust")
    assert aligned.score > 0.7
    assert segment.evidence
    assert priority.evidence


def test_run_suite_and_verify_pass() -> None:
    summary = run_suite(iterations=50)
    assert summary.result_count == 250
    assert summary.citation_accuracy == 1.0
    assert summary.sanitizer_block_rate == 1.0
    assert summary.pass_gates
    ok, checks = verify_outputs()
    assert ok, checks


def test_dashboard_and_demo_pack() -> None:
    run_suite(iterations=50)
    dashboard = build_dashboard()
    assert "Evidenceboard MCP Dashboard" in dashboard.read_text(encoding="utf-8")
    pack = export_demo_pack()
    assert (pack / "manifest.json").exists()


def test_jsonl_tool_loop() -> None:
    payload = {"tool": "cite_evidence", "arguments": {"feature_id": "feat-onboarding-checklist", "top_k": 2}}
    completed = subprocess.run(
        ["uv", "run", "--project", "elite_projects/evidenceboard-mcp-local", "evidenceboard-local", "tool-loop"],
        input=json.dumps(payload) + "\n",
        text=True,
        capture_output=True,
        check=True,
    )
    result = json.loads(completed.stdout)
    assert result["tool"] == "cite_evidence"
    assert result["_evidence"]
