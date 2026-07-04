from __future__ import annotations

import logging
import sys

from PyQt6.QtWidgets import QApplication

from .adapters.persistence.json_rule_repository import JsonRuleRepository
from .adapters.persistence.json_undo_stack import JsonUndoStack
from .adapters.watcher.watchdog_watcher import WatchdogFileWatcher
from .config.settings import APP_NAME, DATA_DIR, UNDO_FILE, UNDO_STACK_LIMIT
from .core.services.action_executor import ActionExecutor
from .core.services.rule_evaluator import RuleEvaluator
from .core.services.undo_manager import UndoManager
from .core.services.watcher_service import WatcherService
from .ui.main_window import MainWindow
from .ui.shared.styles import DARK_THEME


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyleSheet(DARK_THEME)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    repo = JsonRuleRepository(DATA_DIR)
    if not repo.get_groups():
        repo.create_default_rules()

    executor = ActionExecutor()
    undo_stack = JsonUndoStack(UNDO_FILE, UNDO_STACK_LIMIT)
    undo_manager = UndoManager(undo_stack, executor)

    watcher_service = WatcherService(
        watcher=WatchdogFileWatcher(),
        repo=repo,
        evaluator=RuleEvaluator(),
        executor=executor,
        data_dir=DATA_DIR,
    )
    watcher_service.set_undo_manager(undo_manager)

    window = MainWindow(
        data_dir=DATA_DIR,
        watcher_service=watcher_service,
        rule_repository=repo,
        undo_manager=undo_manager,
    )
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
