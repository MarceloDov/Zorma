from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from .rule import Rule, RuleAction


class ClassificationStatus(str, Enum):
    """Define los estados posibles de una operación de clasificación."""
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"
    CONFLICT = "conflict"
    NO_RULE = "no_classified"
    FILTERED_OUT = "filtered_out"


@dataclass
class ClassificationResult:
    """Representa el resultado de una operación de clasificación sobre un archivo."""
    file_name: str = ""
    source_path: Path | None = None
    destination_path: Path | None = None
    rule_applied: Rule | None = None
    action_applied: RuleAction | None = None
    status: ClassificationStatus = ClassificationStatus.NO_RULE
    error_message: str = ""
    overwrite: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
