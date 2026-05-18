from __future__ import annotations

import json
import shutil
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import duckdb

try:
    import fcntl
except ImportError:  # pragma: no cover - POSIX is the target runtime for this local tool.
    fcntl = None

from evidenceboard_mcp_local.engine import (
    align_to_objective,
    assess_prioritisation,
    cite_evidence,
    features_lacking_evidence,
    summarise_segment,
    tool_schema,
)
from evidenceboard_mcp_local.fixtures import fixture_path, load_fixtures
from evidenceboard_mcp_local.models import RunSummary, ToolResult, project_root


def runs_dir() -> Path:
    return project_root() / "runs" / "latest"


def outputs_dir() -> Path:
    return project_root() / "outputs"


def init_demo(force: bool = False) -> None:
    with _workspace_lock():
        _init_demo_unlocked(force=force)


def _init_demo_unlocked(force: bool = False) -> None:
    if force:
        shutil.rmtree(runs_dir(), ignore_errors=True)
        shutil.rmtree(outputs_dir(), ignore_errors=True)
    runs_dir().mkdir(parents=True, exist_ok=True)
    outputs_dir().mkdir(parents=True, exist_ok=True)
    _connect().close()


def run_suite(iterations: int = 50) -> RunSummary:
    with _workspace_lock():
        return _run_suite_unlocked(iterations=iterations)


def _run_suite_unlocked(iterations: int = 50) -> RunSummary:
    _init_demo_unlocked(force=True)
    data = load_fixtures()
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    results: list[ToolResult] = []
    for _ in range(iterations):
        results.extend(
            [
                cite_evidence("feat-onboarding-checklist", fixtures=data),
                align_to_objective("feat-latency-diagnostics", "obj-enterprise-trust", fixtures=data),
                summarise_segment("seg-enterprise", 30, fixtures=data),
                assess_prioritisation("init-feedback-quality", fixtures=data),
                cite_evidence("feat-latency-diagnostics", fixtures=data),
            ]
        )
    _write_results(run_id, results)
    tool_schema(outputs_dir() / "tool_schema.json")
    summary = summarize(run_id, results)
    (outputs_dir() / "summary.json").write_text(summary.model_dump_json(indent=2), encoding="utf-8")
    return summary


def summarize(run_id: str, results: list[ToolResult]) -> RunSummary:
    latencies = sorted(result.latency_ms for result in results)
    p95 = latencies[int(len(latencies) * 0.95) - 1] if latencies else 0.0
    cited = [result for result in results if result.evidence]
    citation_accuracy = len(cited) / max(1, len(results))
    sanitized_evidence = [span for result in results for span in result.evidence if span.sanitizer_findings]
    hostile_mentions = [span for result in results for span in result.evidence if "sanitized" in span.sanitized_text]
    sanitizer_block_rate = len(sanitized_evidence) / max(1, len(hostile_mentions))
    missing = len(features_lacking_evidence())
    return RunSummary(
        run_id=run_id,
        result_count=len(results),
        citation_accuracy=round(citation_accuracy, 4),
        sanitizer_block_rate=round(sanitizer_block_rate, 4),
        p95_latency_ms=round(p95, 4),
        missing_evidence_flags=missing,
        pass_gates=len(results) >= 250 and citation_accuracy == 1.0 and sanitizer_block_rate == 1.0 and p95 < 600 and missing == 0,
    )


def verify_outputs() -> tuple[bool, dict[str, Any]]:
    with _workspace_lock():
        summary_path = outputs_dir() / "summary.json"
        if not summary_path.exists():
            return False, {"error": "run-suite has not produced summary.json"}
        summary = RunSummary.model_validate_json(summary_path.read_text(encoding="utf-8"))
        con = _connect()
        try:
            result_rows = con.execute("select count(*) from tool_results").fetchone()[0]
            evidence_rows = con.execute("select count(*) from evidence_spans").fetchone()[0]
            sanitized_rows = con.execute("select count(*) from evidence_spans where sanitizer_findings <> ''").fetchone()[0]
        finally:
            con.close()
    checks = {
        "result_count_match": result_rows == summary.result_count,
        "evidence_present": evidence_rows >= summary.result_count,
        "sanitizer_exercised": sanitized_rows > 0,
        "citation_accuracy": summary.citation_accuracy == 1.0,
        "sanitizer_block_rate": summary.sanitizer_block_rate == 1.0,
        "latency_gate": summary.p95_latency_ms < 600,
        "no_features_lacking_evidence": summary.missing_evidence_flags == 0,
        "tool_schema_exists": (outputs_dir() / "tool_schema.json").exists(),
        "overall_pass": summary.pass_gates,
    }
    return all(checks.values()), checks


def export_demo_pack() -> Path:
    with _workspace_lock():
        if not (outputs_dir() / "summary.json").exists():
            _run_suite_unlocked()
        pack = outputs_dir() / "demo_pack"
        shutil.rmtree(pack, ignore_errors=True)
        pack.mkdir(parents=True, exist_ok=True)
        for source in [
            fixture_path(),
            outputs_dir() / "summary.json",
            outputs_dir() / "tool_schema.json",
            outputs_dir() / "tool_results.json",
        ]:
            shutil.copy2(source, pack / source.name)
        (pack / "manifest.json").write_text(
            json.dumps(
                {
                    "artifact": "evidenceboard-mcp-local demo pack",
                    "contents": sorted(path.name for path in pack.iterdir()),
                    "data": "synthetic only",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return pack


def _write_results(run_id: str, results: list[ToolResult]) -> None:
    con = _connect()
    try:
        con.execute("delete from tool_results")
        con.execute("delete from evidence_spans")
        for result in results:
            result_id = str(uuid.uuid4())
            con.execute(
                "insert into tool_results values (?, ?, ?, ?, ?, ?, ?)",
                [run_id, result_id, result.tool, result.subject_id, result.answer, result.score, result.latency_ms],
            )
            for span in result.evidence:
                con.execute(
                    "insert into evidence_spans values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [
                        run_id,
                        result_id,
                        span.note_id,
                        span.customer_id,
                        span.segment_id,
                        span.feature_id,
                        span.score,
                        span.sanitized_text,
                        ",".join(span.sanitizer_findings),
                    ],
                )
    finally:
        con.close()
    (outputs_dir() / "tool_results.json").write_text(
        json.dumps([result.model_dump(mode="json", by_alias=True) for result in results], indent=2),
        encoding="utf-8",
    )


def _connect() -> duckdb.DuckDBPyConnection:
    runs_dir().mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(runs_dir() / "evidenceboard.duckdb"))
    con.execute(
        """
        create table if not exists tool_results (
            run_id varchar,
            result_id varchar,
            tool varchar,
            subject_id varchar,
            answer varchar,
            score double,
            latency_ms double
        )
        """
    )
    con.execute(
        """
        create table if not exists evidence_spans (
            run_id varchar,
            result_id varchar,
            note_id varchar,
            customer_id varchar,
            segment_id varchar,
            feature_id varchar,
            score double,
            sanitized_text varchar,
            sanitizer_findings varchar
        )
        """
    )
    return con


@contextmanager
def _workspace_lock() -> Any:
    lock_path = project_root() / ".evidenceboard.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
