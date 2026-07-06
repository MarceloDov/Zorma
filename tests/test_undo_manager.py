from pathlib import Path
from unittest.mock import MagicMock, create_autospec

from zorma.adapters.persistence.zorma_repository import ZormaRepository
from zorma.core.models.classification import ClassificationResult, ClassificationStatus
from zorma.core.models.rule import ActionType, Rule, RuleAction
from zorma.core.models.undo_entry import UndoEntry
from zorma.core.services.action_executor import ActionExecutor
from zorma.core.services.undo_manager import UndoManager


class TestUndoManager:
    def setup_method(self) -> None:
        self.repo = create_autospec(ZormaRepository, instance=True)
        self.executor = create_autospec(ActionExecutor)
        self.manager = UndoManager(self.repo, self.executor)

    def _make_result(self, status: ClassificationStatus = ClassificationStatus.SUCCESS) -> ClassificationResult:
        rule = Rule(name="TestRule")
        action = RuleAction(action_type=ActionType.MOVE, target_folder="/tmp")
        return ClassificationResult(
            file_name="test.txt",
            source_path=Path("/src/test.txt"),
            destination_path=Path("/dst/test.txt"),
            rule_applied=rule,
            action_applied=action,
            status=status,
        )

    def test_record_success(self) -> None:
        result = self._make_result()
        self.manager.record(result)
        self.repo.redo_clear.assert_called_once()
        self.repo.undo_push.assert_called_once()

    def test_record_non_success_ignored(self) -> None:
        result = self._make_result(ClassificationStatus.ERROR)
        self.manager.record(result)
        self.repo.undo_push.assert_not_called()

    def test_can_undo(self) -> None:
        self.repo.undo_size.return_value = 1
        assert self.manager.can_undo()
        self.repo.undo_size.return_value = 0
        assert not self.manager.can_undo()

    def test_can_redo(self) -> None:
        self.repo.redo_size.return_value = 1
        assert self.manager.can_redo()
        self.repo.redo_size.return_value = 0
        assert not self.manager.can_redo()

    def test_undo_returns_none_when_empty(self) -> None:
        self.repo.undo_pop.return_value = None
        assert self.manager.undo() is None

    def test_undo_move_success(self, tmp_path: Path) -> None:
        src = tmp_path / "src" / "test.txt"
        dst = tmp_path / "dst" / "test.txt"
        dst.parent.mkdir(parents=True)
        dst.write_text("moved file")
        entry = UndoEntry(
            file_name="test.txt",
            source_path=src,
            destination_path=dst,
            action_type=ActionType.MOVE,
            rule_name="TestRule",
        )
        self.repo.undo_pop.return_value = entry
        rollback_result = ClassificationResult(status=ClassificationStatus.SUCCESS)
        self.executor.rollback.return_value = rollback_result

        result = self.manager.undo()
        assert result is not None
        assert result.status == ClassificationStatus.SUCCESS
        self.repo.undo_mark_reverted.assert_called_once_with(entry.id)
        self.repo.redo_push.assert_called_once()

    def test_undo_empty_stack(self) -> None:
        self.repo.undo_pop.return_value = None
        result = self.manager.undo()
        assert result is None

    def test_undo_callback_called(self, tmp_path: Path) -> None:
        src = tmp_path / "src" / "test.txt"
        dst = tmp_path / "dst" / "test.txt"
        dst.parent.mkdir(parents=True)
        dst.write_text("moved file")
        entry = UndoEntry(
            file_name="test.txt",
            source_path=src,
            destination_path=dst,
            action_type=ActionType.MOVE,
            rule_name="TestRule",
        )
        self.repo.undo_pop.return_value = entry
        self.executor.rollback.return_value = ClassificationResult(status=ClassificationStatus.SUCCESS)
        callback = MagicMock()
        self.manager.set_result_callback(callback)
        self.manager.undo()
        callback.assert_called_once()

    def test_redo_delegates(self) -> None:
        entry = UndoEntry(file_name="test.txt")
        self.repo.redo_pop.return_value = entry
        self.manager.redo()
        self.repo.redo_pop.assert_called_once()

    def test_redo_empty(self) -> None:
        self.repo.redo_pop.return_value = None
        assert self.manager.redo() is None
