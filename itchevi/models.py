from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ALLOWED_TERMINAL_STATES = {"OBSERVED", "MISSING", "FAILED", "NOT_APPLICABLE"}
ALLOWED_REQUIREMENTS = {"critical", "required", "optional"}
ALLOWED_GATE_STATUS = {"PASS", "WEAK", "FAIL", "NOT_TESTED", ""}


@dataclass(frozen=True)
class QualificationRun:
    qualification_rows: list[dict[str, Any]]
    terminal_ledger: list[dict[str, Any]]
    validation_rows: list[dict[str, Any]]
    summary: dict[str, Any]

