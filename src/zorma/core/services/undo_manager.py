from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from ..models.classification import ClassificationResult, ClassificationStatus
from ..models.rule import ActionType, RuleAction
from ..ports.undo_stack import UndoEntry, UndoStack
from .action_executor import ActionExecutor

logger = logging.getLogger(__name__)


class UndoManager:
    def __init__(self, undo_stack: UndoStack, executor: ActionExecutor) -> None:
        self._stack = undo_stack
        self._executor = executor
        self._result_callback: Callable[[ClassificationResult], None] | None = None

    def set_result_callback(self, callback: Callable[[ClassificationResult], None]) -> None:
        self._result_callback = callback

    def record(self, result: ClassificationResult) -> None:
        if result.status != ClassificationStatus.SUCCESS:
            return
        entry = UndoEntry(
            file_name=result.file_name,
            source_path=result.source_path or Path(),
            destination_path=result.destination_path or Path(),
            action_type=result.action_applied.action_type if result.action_applied else ActionType.MOVE,
            rule_name=result.rule_applied.name if result.rule_applied else "",
        )
        self._stack.push(entry)

    def undo(self) -> ClassificationResult | None:
        entry = self._stack.pop()
        if entry is None:
            return None
        return self._execute_undo(entry)

    def undo_by_source_path(self, source_path: Path) -> ClassificationResult | None:
        for entry in self._stack.get_all():
            if entry.source_path == source_path and not entry.reverted:
                removed = self._stack.remove_by_id(entry.id)
                if removed is not None:
                    return self._execute_undo(removed)
        return None

    def _execute_undo(self, entry: UndoEntry) -> ClassificationResult | None:
        dest = entry.destination_path
        src = entry.source_path

        if entry.action_type in (ActionType.MOVE, ActionType.COPY):
            if not dest.exists():
                logger.warning("Cannot undo: destination file not found: %s", dest)
                return None
            action = RuleAction(action_type=entry.action_type)
            result = self._executor.rollback(action, dest, src)
        elif entry.action_type == ActionType.RENAME:
            if not dest.exists():
                logger.warning("Cannot undo: renamed file not found: %s", dest)
                return None
            action = RuleAction(action_type=ActionType.RENAME)
            result = self._executor.rollback(action, dest, src)
        else:
            logger.warning("Cannot undo: unknown action type: %s", entry.action_type)
            return None

        if result.status == ClassificationStatus.SUCCESS:
            result.file_name = entry.file_name
            result.source_path = dest
            result.destination_path = src
            self._stack.mark_reverted(entry.id)
            if self._result_callback:
                self._result_callback(result)
        return result

    def get_undoable(self) -> list[UndoEntry]:
        return self._stack.get_all()

    def can_undo(self) -> bool:
        return self._stack.size() > 0
