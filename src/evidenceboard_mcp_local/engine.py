from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path
from typing import Any

from evidenceboard_mcp_local.fixtures import load_fixtures
from evidenceboard_mcp_local.models import DemoFixtures, EvidenceSpan, Feature, Initiative, Objective, ToolResult
from evidenceboard_mcp_local.sanitize import sanitize_note


def cite_evidence(feature_id: str, top_k: int = 5, fixtures: DemoFixtures | None = None) -> ToolResult:
    start = time.perf_counter()
    data = fixtures or load_fixtures()
    feature = _feature(data, feature_id)
    query_terms = set(_tokens(feature.name))
    spans = []
    for note in data.notes:
        linked = feature_id in note.feature_ids
        score = 2.5 if linked else 0.0
        score += len(query_terms.intersection(_tokens(note.text))) * 0.4
        score += sum(0.2 for tag in note.tags if tag in query_terms)
        if score <= 0:
            continue
        sanitized, findings = sanitize_note(note.text)
        spans.append(
            EvidenceSpan(
                note_id=note.id,
                customer_id=note.customer_id,
                segment_id=note.segment_id,
                feature_id=feature_id if linked else None,
                score=round(score, 4),
                sanitized_text=sanitized,
                sanitizer_findings=findings,
            )
        )
    evidence = sorted(spans, key=lambda item: item.score, reverse=True)[:top_k]
    answer = f"{feature.name} has {len(evidence)} cited evidence spans across {len({item.customer_id for item in evidence})} customers."
    return _result("cite_evidence", feature_id, answer, _avg_score(evidence), start, evidence)


def align_to_objective(feature_id: str, objective_id: str, fixtures: DemoFixtures | None = None) -> ToolResult:
    start = time.perf_counter()
    data = fixtures or load_fixtures()
    feature = _feature(data, feature_id)
    objective = _objective(data, objective_id)
    evidence = cite_evidence(feature_id, top_k=8, fixtures=data).evidence
    keyword_hits = sum(1 for item in evidence for word in objective.keywords if word in item.sanitized_text.lower())
    score = min(1.0, (keyword_hits / max(1, len(evidence))) + 0.15 * len(evidence))
    answer = f"{feature.name} alignment to objective '{objective.name}' is {score:.2f} based on cited customer evidence."
    return _result("align_to_objective", f"{feature_id}:{objective_id}", answer, round(score, 4), start, evidence[:5])


def summarise_segment(segment_id: str, since_days: int = 30, fixtures: DemoFixtures | None = None) -> ToolResult:
    start = time.perf_counter()
    data = fixtures or load_fixtures()
    notes = [note for note in data.notes if note.segment_id == segment_id and note.days_ago <= since_days]
    tag_counts = Counter(tag for note in notes for tag in note.tags)
    top_tags = [tag for tag, _ in tag_counts.most_common(3)]
    evidence = []
    for note in notes:
        sanitized, findings = sanitize_note(note.text)
        evidence.append(
            EvidenceSpan(
                note_id=note.id,
                customer_id=note.customer_id,
                segment_id=note.segment_id,
                feature_id=note.feature_ids[0] if note.feature_ids else None,
                score=round(1 + len(set(note.tags).intersection(top_tags)) * 0.5, 4),
                sanitized_text=sanitized,
                sanitizer_findings=findings,
            )
        )
    evidence = sorted(evidence, key=lambda item: item.score, reverse=True)[:8]
    answer = f"Top segment themes: {', '.join(top_tags)} from {len(notes)} recent notes."
    return _result("summarise_segment", segment_id, answer, _avg_score(evidence), start, evidence)


def assess_prioritisation(initiative_id: str, fixtures: DemoFixtures | None = None) -> ToolResult:
    start = time.perf_counter()
    data = fixtures or load_fixtures()
    initiative = _initiative(data, initiative_id)
    evidence: list[EvidenceSpan] = []
    objective_scores = []
    for feature_id in initiative.feature_ids:
        for objective_id in initiative.objective_ids:
            aligned = align_to_objective(feature_id, objective_id, fixtures=data)
            objective_scores.append(aligned.score)
            evidence.extend(aligned.evidence)
    deduped = _dedupe_evidence(evidence)
    score = round((sum(objective_scores) / max(1, len(objective_scores))) * min(1.0, len(deduped) / 4), 4)
    answer = f"{initiative.name} priority confidence is {score:.2f}; {len(deduped)} cited spans support the assessment."
    return _result("assess_prioritisation", initiative_id, answer, score, start, deduped[:8])


def features_lacking_evidence(fixtures: DemoFixtures | None = None) -> list[str]:
    data = fixtures or load_fixtures()
    supported = {feature_id for note in data.notes for feature_id in note.feature_ids}
    return [feature.id for feature in data.features if feature.id not in supported]


def tool_schema(path: Path) -> None:
    schema: dict[str, Any] = {
        "tools": [
            {"name": "cite_evidence", "input": {"feature_id": "string", "top_k": "integer"}},
            {"name": "align_to_objective", "input": {"feature_id": "string", "objective_id": "string"}},
            {"name": "summarise_segment", "input": {"segment_id": "string", "since_days": "integer"}},
            {"name": "assess_prioritisation", "input": {"initiative_id": "string"}},
        ],
        "response_contract": "Every tool result includes _evidence with note_id, customer_id, segment_id, score, sanitized_text, and sanitizer_findings.",
    }
    path.write_text(json.dumps(schema, indent=2), encoding="utf-8")


def call_tool(name: str, arguments: dict[str, Any], fixtures: DemoFixtures | None = None) -> ToolResult:
    if name == "cite_evidence":
        return cite_evidence(str(arguments["feature_id"]), int(arguments.get("top_k", 5)), fixtures=fixtures)
    if name == "align_to_objective":
        return align_to_objective(str(arguments["feature_id"]), str(arguments["objective_id"]), fixtures=fixtures)
    if name == "summarise_segment":
        return summarise_segment(str(arguments["segment_id"]), int(arguments.get("since_days", 30)), fixtures=fixtures)
    if name == "assess_prioritisation":
        return assess_prioritisation(str(arguments["initiative_id"]), fixtures=fixtures)
    raise ValueError(f"unknown tool: {name}")


def _result(tool: str, subject_id: str, answer: str, score: float, start: float, evidence: list[EvidenceSpan]) -> ToolResult:
    return ToolResult(
        tool=tool,
        subject_id=subject_id,
        answer=answer,
        score=score,
        latency_ms=round((time.perf_counter() - start) * 1000, 4),
        evidence=evidence,
    )


def _tokens(text: str) -> list[str]:
    return [token for token in "".join(char.lower() if char.isalnum() else " " for char in text).split() if len(token) > 2]


def _avg_score(evidence: list[EvidenceSpan]) -> float:
    if not evidence:
        return 0.0
    return round(sum(item.score for item in evidence) / len(evidence), 4)


def _dedupe_evidence(evidence: list[EvidenceSpan]) -> list[EvidenceSpan]:
    seen = set()
    deduped = []
    for item in sorted(evidence, key=lambda span: span.score, reverse=True):
        if item.note_id in seen:
            continue
        seen.add(item.note_id)
        deduped.append(item)
    return deduped


def _feature(data: DemoFixtures, feature_id: str) -> Feature:
    return next(item for item in data.features if item.id == feature_id)


def _objective(data: DemoFixtures, objective_id: str) -> Objective:
    return next(item for item in data.objectives if item.id == objective_id)


def _initiative(data: DemoFixtures, initiative_id: str) -> Initiative:
    return next(item for item in data.initiatives if item.id == initiative_id)
