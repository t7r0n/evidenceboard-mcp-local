from __future__ import annotations

from pathlib import Path
from pydantic import BaseModel, Field


class Customer(BaseModel):
    id: str
    name: str
    segment_id: str
    arr: int


class Segment(BaseModel):
    id: str
    name: str


class Note(BaseModel):
    id: str
    customer_id: str
    segment_id: str
    days_ago: int
    text: str
    tags: list[str]
    feature_ids: list[str]


class Feature(BaseModel):
    id: str
    name: str
    initiative_id: str
    release: str


class Objective(BaseModel):
    id: str
    name: str
    keywords: list[str]


class Initiative(BaseModel):
    id: str
    name: str
    objective_ids: list[str]
    feature_ids: list[str]


class EvidenceSpan(BaseModel):
    note_id: str
    customer_id: str
    segment_id: str
    feature_id: str | None
    score: float
    sanitized_text: str
    sanitizer_findings: list[str] = Field(default_factory=list)


class ToolResult(BaseModel):
    tool: str
    subject_id: str
    answer: str
    score: float
    latency_ms: float
    evidence: list[EvidenceSpan] = Field(default_factory=list, serialization_alias="_evidence")


class DemoFixtures(BaseModel):
    segments: list[Segment]
    customers: list[Customer]
    notes: list[Note]
    features: list[Feature]
    objectives: list[Objective]
    initiatives: list[Initiative]


class RunSummary(BaseModel):
    run_id: str
    result_count: int
    citation_accuracy: float
    sanitizer_block_rate: float
    p95_latency_ms: float
    missing_evidence_flags: int
    pass_gates: bool


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]
