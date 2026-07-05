from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class ConditionType(str, Enum):
    """Define los tipos de condiciones que una regla puede evaluar."""
    EXTENSION = "extension"
    SIZE = "size"
    DATE = "date"
    NAME = "name"


class ActionType(str, Enum):
    """Define los tipos de acciones permitidas sobre archivos."""
    MOVE = "move"
    COPY = "copy"
    RENAME = "rename"


@dataclass
class RuleGroup:
    """Agrupa reglas de clasificación relacionadas."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    priority: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_default: bool = False


@dataclass
class RuleAction:
    """Define una acción a ejecutar si se cumple una regla de clasificación."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    rule_id: str = ""
    action_type: ActionType = ActionType.MOVE
    target_folder: str = ""
    copy_enabled: bool = False
    rename_pattern: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Rule:
    """Define una regla para clasificar archivos basada en condiciones."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    group_id: str = ""
    name: str = ""
    enabled: bool = True
    priority: int = 0
    condition_type: ConditionType = ConditionType.EXTENSION
    condition_value: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
