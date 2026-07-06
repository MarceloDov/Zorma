from __future__ import annotations

import logging
import shutil
from collections.abc import Callable
from pathlib import Path

from ...adapters.persistence.zorma_repository import ZormaRepository
from ..models.classification import ClassificationResult, ClassificationStatus
from ..models.rule import ActionType, RuleAction
from ..models.undo_entry import UndoEntry
from .action_executor import ActionExecutor

logger = logging.getLogger(__name__)


class UndoManager:
    def __init__(self, repo: ZormaRepository, executor: ActionExecutor) -> None:
        self._repo = repo
        self._executor = executor
        self._result_callback: Callable[[ClassificationResult], None] | None = None

    def set_result_callback(self, callback: Callable[[ClassificationResult], None]) -> None:
        self._result_callback = callback

    def record(self, result: ClassificationResult) -> None:
        if result.status != ClassificationStatus.SUCCESS:
            return
        self._repo.redo_clear()
        entry = UndoEntry(
            file_name=result.file_name,
            source_path=result.source_path or Path(),
            destination_path=result.destination_path or Path(),
            action_type=result.action_applied.action_type if result.action_applied else ActionType.MOVE,
            rule_name=result.rule_applied.name if result.rule_applied else "",
        )
        self._repo.undo_push(entry)

    def undo(self) -> ClassificationResult | None:
        entry = self._repo.undo_pop()
        if entry is None:
            return None
        result = self._execute_undo(entry)
        if result is not None and result.status == ClassificationStatus.SUCCESS:
            entry.reverted = False
            self._repo.redo_push(entry)
        return result

    def undo_by_source_path(self, source_path: Path) -> ClassificationResult | None:
        for entry in self._repo.undo_get_all():
            if entry.source_path == source_path and not entry.reverted:
                removed = self._repo.undo_remove_by_id(entry.id)
                if removed is not None:
                    result = self._execute_undo(removed)
                    if result is not None and result.status == ClassificationStatus.SUCCESS:
                        removed.reverted = False
                        self._repo.redo_push(removed)
                    return result
        return None

    def redo(self) -> ClassificationResult | None:
        entry = self._repo.redo_pop()
        if entry is None:
            return None
        return self._execute_redo(entry)

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
            self._repo.undo_mark_reverted(entry.id)
            if self._result_callback:
                self._result_callback(result)
        return result

    def _execute_redo(self, entry: UndoEntry) -> ClassificationResult | None:
        src = entry.source_path
        dest = entry.destination_path

        if not src.exists():
            logger.warning("Cannot redo: source file not found: %s", src)
            return None

        result = ClassificationResult(
            file_name=entry.file_name,
            source_path=src,
            destination_path=dest,
        )

        try:
            if dest.exists():
                logger.warning("Cannot redo: destination exists: %s", dest)
                result.status = ClassificationStatus.SKIPPED
                result.error_message = f"Destination exists: {dest}"
                return result

            if entry.action_type in (ActionType.MOVE, ActionType.COPY):
                dest.parent.mkdir(parents=True, exist_ok=True)
                if entry.action_type == ActionType.MOVE:
                    shutil.move(str(src), str(dest))
                else:
                    shutil.copy2(str(src), str(dest))
            elif entry.action_type == ActionType.RENAME:
                src.rename(dest)

            result.status = ClassificationStatus.SUCCESS
            entry.reverted = False
            self._repo.undo_push(entry)
            if self._result_callback:
                self._result_callback(result)
        except OSError as e:
            result.status = ClassificationStatus.ERROR
            result.error_message = str(e)

        return result

    def get_undoable(self) -> list[UndoEntry]:
        return self._repo.undo_get_all()

    def can_undo(self) -> bool:
        return self._repo.undo_size() > 0

    def can_redo(self) -> bool:
        return self._repo.redo_size() > 0
