from __future__ import annotations

import json
from pathlib import Path

from evidenceboard_mcp_local.models import DemoFixtures, project_root


def fixture_path() -> Path:
    return project_root() / "fixtures" / "product_data.json"


def load_fixtures(path: Path | None = None) -> DemoFixtures:
    target = path or fixture_path()
    return DemoFixtures.model_validate(json.loads(target.read_text(encoding="utf-8")))
