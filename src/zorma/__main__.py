from __future__ import annotations

import logging
import sys

from PyQt6.QtWidgets import QApplication

from .adapters.persistence.zorma_repository import ZormaRepository
from .adapters.watcher.watchdog_watcher import WatchdogFileWatcher
from .config.settings import APP_NAME, DATA_DIR, UNDO_STACK_LIMIT
from .core.services.action_executor import ActionExecutor
from .core.services.rule_evaluator import RuleEvaluator
from .core.services.undo_manager import UndoManager
from .core.services.watcher_service import WatcherService
from .ui.main_window import MainWindow
from .ui.shared.styles import build_qss


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyleSheet(build_qss())

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    repo = ZormaRepository(DATA_DIR, undo_limit=UNDO_STACK_LIMIT)
    if not repo.get_groups():
        repo.create_default_rules()

    executor = ActionExecutor()
    undo_manager = UndoManager(repo, executor)
    history = repo

    watcher_service = WatcherService(
        watcher=WatchdogFileWatcher(),
        repo=repo,
        evaluator=RuleEvaluator(),
        executor=executor,
        history=history,
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
