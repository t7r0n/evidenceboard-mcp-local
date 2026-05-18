from __future__ import annotations

import json
import sys

import typer
from rich.console import Console
from rich.table import Table

from evidenceboard_mcp_local.dashboard import build_dashboard
from evidenceboard_mcp_local.engine import (
    align_to_objective,
    assess_prioritisation,
    call_tool,
    cite_evidence,
    summarise_segment,
)
from evidenceboard_mcp_local.fixtures import load_fixtures
from evidenceboard_mcp_local.runner import export_demo_pack, init_demo, run_suite, verify_outputs


app = typer.Typer(help="Local evidence-first product feedback MCP-style demo.")
console = Console()


@app.command("init-demo")
def init_demo_command(force: bool = typer.Option(False, "--force")) -> None:
    init_demo(force=force)
    console.print("[green]Initialized local synthetic demo store.[/green]")


@app.command("cite-evidence")
def cite_evidence_command(feature_id: str, top_k: int = typer.Option(5, "--top-k", min=1, max=20)) -> None:
    console.print_json(cite_evidence(feature_id, top_k=top_k).model_dump_json(indent=2, by_alias=True))


@app.command("align-to-objective")
def align_to_objective_command(feature_id: str, objective_id: str) -> None:
    console.print_json(align_to_objective(feature_id, objective_id).model_dump_json(indent=2, by_alias=True))


@app.command("summarise-segment")
def summarise_segment_command(segment_id: str, since_days: int = typer.Option(30, "--since-days", min=1)) -> None:
    console.print_json(summarise_segment(segment_id, since_days).model_dump_json(indent=2, by_alias=True))


@app.command("assess-prioritisation")
def assess_prioritisation_command(initiative_id: str) -> None:
    console.print_json(assess_prioritisation(initiative_id).model_dump_json(indent=2, by_alias=True))


@app.command("tool-loop")
def tool_loop_command() -> None:
    data = load_fixtures()
    for line in sys.stdin:
        if not line.strip():
            continue
        payload = json.loads(line)
        result = call_tool(str(payload["tool"]), dict(payload.get("arguments", {})), fixtures=data)
        print(result.model_dump_json(by_alias=True))


@app.command("run-suite")
def run_suite_command(iterations: int = typer.Option(50, "--iterations", min=1)) -> None:
    summary = run_suite(iterations=iterations)
    console.print_json(summary.model_dump_json(indent=2))
    if not summary.pass_gates:
        raise typer.Exit(1)


@app.command("verify")
def verify_command() -> None:
    ok, checks = verify_outputs()
    table = Table(title="Verification")
    table.add_column("Gate")
    table.add_column("Status")
    for gate, status in checks.items():
        table.add_row(gate, "PASS" if status else "FAIL")
    console.print(table)
    if not ok:
        raise typer.Exit(1)


@app.command("dashboard")
def dashboard_command() -> None:
    path = build_dashboard()
    console.print(f"[green]Dashboard written:[/green] {path}")


@app.command("benchmark")
def benchmark_command(iterations: int = typer.Option(200, "--iterations", min=1)) -> None:
    summary = run_suite(iterations=iterations)
    table = Table(title="Benchmark")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("tool results", str(summary.result_count))
    table.add_row("citation accuracy", f"{summary.citation_accuracy:.2%}")
    table.add_row("sanitizer block rate", f"{summary.sanitizer_block_rate:.2%}")
    table.add_row("p95 latency", f"{summary.p95_latency_ms} ms")
    table.add_row("pass gates", str(summary.pass_gates))
    console.print(table)
    if not summary.pass_gates:
        raise typer.Exit(1)


@app.command("export-demo-pack")
def export_demo_pack_command() -> None:
    path = export_demo_pack()
    console.print(f"[green]Demo pack exported:[/green] {path}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
