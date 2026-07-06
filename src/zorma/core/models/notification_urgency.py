from __future__ import annotations

from enum import Enum


class NotificationUrgency(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    CRITICAL = "critical"
