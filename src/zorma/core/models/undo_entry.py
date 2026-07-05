from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .rule import ActionType


@dataclass
class UndoEntry:
    id: str = field(default_factory=lambda: uuid4().hex)
    file_name: str = ""
    source_path: Path = field(default_factory=Path)
    destination_path: Path = field(default_factory=Path)
    action_type: ActionType = ActionType.MOVE
    rule_name: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reverted: bool = False
