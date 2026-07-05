from pathlib import Path
from unittest.mock import MagicMock, create_autospec

from zorma.core.models.classification import ClassificationResult, ClassificationStatus
from zorma.core.models.file_event import FileEvent, FileEventType
from zorma.core.models.rule import ActionType, ConditionType, Rule, RuleAction
from zorma.core.models.filter_config import FilterConfig
from zorma.adapters.persistence.zorma_repository import ZormaRepository
from zorma.adapters.watcher.watchdog_watcher import WatchdogFileWatcher
from zorma.core.services.action_executor import ActionExecutor
from zorma.core.services.rule_evaluator import RuleEvaluator
from zorma.core.services.watcher_service import WatcherService


class TestWatcherService:
    def setup_method(self) -> None:
        self.watcher = create_autospec(WatchdogFileWatcher)
        self.repo = create_autospec(ZormaRepository, instance=True)
        self.evaluator = create_autospec(RuleEvaluator)
        self.executor = create_autospec(ActionExecutor)
        self.history = create_autospec(ZormaRepository, instance=True)
        self.service = WatcherService(self.watcher, self.repo, self.evaluator, self.executor, self.history)

    def test_start_monitoring(self) -> None:
        paths = [Path("/watch")]
        self.service.start_monitoring(paths)
        self.watcher.update_filter.assert_called_once_with(None)
        self.watcher.start.assert_called_once()

    def test_start_monitoring_with_filter(self) -> None:
        paths = [Path("/watch")]
        cfg = FilterConfig(include_extensions=[".txt"])
        self.service.start_monitoring(paths, cfg)
        self.watcher.update_filter.assert_called_once_with(cfg)
        self.watcher.start.assert_called_once()

    def test_stop_monitoring(self) -> None:
        self.service.stop_monitoring()
        self.watcher.stop.assert_called_once()

    def test_classify_no_rules(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        self.repo.get_all_rules.return_value = []
        self.evaluator.evaluate_all.return_value = []
        result = self.service._classify(f)
        assert result.status == ClassificationStatus.NO_RULE

    def test_classify_no_match(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        rule = Rule(condition_type=ConditionType.EXTENSION, condition_value=".pdf")
        self.repo.get_all_rules.return_value = [rule]
        self.evaluator.evaluate_all.return_value = []
        result = self.service._classify(f)
        assert result.status == ClassificationStatus.NO_RULE

    def test_classify_match_no_action(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        rule = Rule(condition_type=ConditionType.EXTENSION, condition_value=".txt")
        self.repo.get_all_rules.return_value = [rule]
        self.evaluator.evaluate_all.return_value = [rule]
        self.repo.get_actions_for_rule.return_value = []
        result = self.service._classify(f)
        assert result.status == ClassificationStatus.NO_RULE

    def test_classify_success(self, tmp_path: Path) -> None:
        src = tmp_path / "test.txt"
        src.write_text("hello")
        dest = tmp_path / "moved.txt"
        rule = Rule(condition_type=ConditionType.EXTENSION, condition_value=".txt")
        action = RuleAction(action_type=ActionType.MOVE, target_folder=str(tmp_path))
        self.repo.get_all_rules.return_value = [rule]
        self.evaluator.evaluate_all.return_value = [rule]
        self.repo.get_actions_for_rule.return_value = [action]
        exec_result = ClassificationResult(
            file_name="test.txt",
            source_path=src,
            destination_path=dest,
            rule_applied=rule,
            action_applied=action,
            status=ClassificationStatus.SUCCESS,
        )
        self.executor.execute.return_value = exec_result
        result = self.service._classify(src)
        assert result.status == ClassificationStatus.SUCCESS
        assert result.destination_path == dest
        self.executor.execute.assert_called_once_with(action, src, False)

    def test_classify_file_not_found(self, tmp_path: Path) -> None:
        f = tmp_path / "nonexistent.txt"
        result = self.service._classify(f)
        assert result.status == ClassificationStatus.FILTERED_OUT

    def test_on_event_triggers_callback(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        self.repo.get_all_rules.return_value = []
        callback = MagicMock()
        self.service.set_result_callback(callback)
        result = self.service._on_event(FileEvent(src_path=f, event_type=FileEventType.CREATED))
        callback.assert_called_once_with(result)

    def test_initial_scan(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.pdf"
        f1.write_text("a")
        f2.write_text("b")
        self.repo.get_all_rules.return_value = []
        self.evaluator.evaluate_all.return_value = []
        results = self.service._initial_scan([tmp_path])
        assert len(results) == 2

    def test_initial_scan_with_filter(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.pdf"
        f1.write_text("a")
        f2.write_text("b")
        cfg = FilterConfig(include_extensions=[".txt"])
        self.repo.get_all_rules.return_value = []
        self.evaluator.evaluate_all.return_value = []
        results = self.service._initial_scan([tmp_path], cfg)
        assert len(results) == 1
        assert results[0].file_name == "a.txt"

    def test_preview_no_rules(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        self.repo.get_all_rules.return_value = []
        self.evaluator.evaluate_all.return_value = []
        result = self.service.preview(f)
        assert result.status == ClassificationStatus.NO_RULE

    def test_preview_no_conflict(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        rule = Rule(condition_type=ConditionType.EXTENSION, condition_value=".txt")
        action = RuleAction(action_type=ActionType.MOVE, target_folder=str(tmp_path))
        self.repo.get_all_rules.return_value = [rule]
        self.evaluator.evaluate_all.return_value = [rule]
        self.repo.get_actions_for_rule.return_value = [action]
        self.executor.check_conflict.return_value = (False, tmp_path / "test.txt")
        result = self.service.preview(f)
        assert result.status == ClassificationStatus.SUCCESS
        assert result.destination_path == tmp_path / "test.txt"

    def test_preview_with_conflict(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        dest_file = tmp_path / "test.txt"
        dest_file.write_text("existing")
        rule = Rule(condition_type=ConditionType.EXTENSION, condition_value=".txt")
        action = RuleAction(action_type=ActionType.MOVE, target_folder=str(tmp_path))
        self.repo.get_all_rules.return_value = [rule]
        self.evaluator.evaluate_all.return_value = [rule]
        self.repo.get_actions_for_rule.return_value = [action]
        self.executor.check_conflict.return_value = (True, tmp_path / "test.txt")
        result = self.service.preview(f)
        assert result.status == ClassificationStatus.CONFLICT

    def test_preview_all(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.pdf"
        f1.write_text("a")
        f2.write_text("b")
        self.repo.get_all_rules.return_value = []
        self.evaluator.evaluate_all.return_value = []
        results = self.service.preview_all([tmp_path])
        assert len(results) == 2

    def test_preview_all_with_filter(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.pdf"
        f1.write_text("a")
        f2.write_text("b")
        cfg = FilterConfig(include_extensions=[".txt"])
        self.repo.get_all_rules.return_value = []
        self.evaluator.evaluate_all.return_value = []
        results = self.service.preview_all([tmp_path], cfg)
        assert len(results) == 1
        assert results[0].file_name == "a.txt"

    def test_set_undo_manager(self) -> None:
        from zorma.core.services.undo_manager import UndoManager

        manager = MagicMock(spec=UndoManager)
        self.service.set_undo_manager(manager)
        assert self.service.get_undo_manager() is manager

    def test_classify_picks_first_matching_rule(self, tmp_path: Path) -> None:
        f = tmp_path / "test.mp4"
        f.write_text("hello")
        rule1 = Rule(name="Videos", condition_type=ConditionType.EXTENSION, condition_value=".mp4")
        rule2 = Rule(name="All", condition_type=ConditionType.EXTENSION, condition_value="*")
        self.repo.get_all_rules.return_value = [rule1, rule2]
        self.evaluator.evaluate_all.return_value = [rule1, rule2]
        action = RuleAction(action_type=ActionType.MOVE, target_folder=str(tmp_path))
        self.repo.get_actions_for_rule.return_value = [action]
        exec_result = ClassificationResult(
            file_name="test.mp4",
            source_path=f,
            destination_path=tmp_path / "test.mp4",
            rule_applied=rule1,
            action_applied=action,
            status=ClassificationStatus.SUCCESS,
        )
        self.executor.execute.return_value = exec_result
        result = self.service._classify(f)
        assert result.rule_applied is rule1

    def test_on_event_skips_directories(self, tmp_path: Path) -> None:
        d = tmp_path / "subdir"
        d.mkdir()
        self.repo.get_all_rules.return_value = []
        self.evaluator.evaluate_all.return_value = []
        result = self.service._on_event(FileEvent(src_path=d, event_type=FileEventType.CREATED, is_directory=True))
        assert result.status == ClassificationStatus.FILTERED_OUT
