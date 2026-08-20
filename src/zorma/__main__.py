from __future__ import annotations

import logging
import sys

from PyQt6.QtWidgets import QApplication

from .adapters.persistence.zorma_repository import ZormaRepository
from .adapters.watcher.watchdog_watcher import WatchdogFileWatcher
from .config.settings import APP_NAME, DATA_DIR, UNDO_STACK_LIMIT
from .core.services.gestor_deshacer import GestorDeshacer
from .core.services.servicio_clasificacion import ServicioClasificacion
from .ui.main_window import MainWindow
from .ui.shared.styles import construir_qss


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyleSheet(construir_qss())

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    repo = ZormaRepository(DATA_DIR, undo_limit=UNDO_STACK_LIMIT)
    if not repo.obtener_grupos():
        repo.crear_reglas_predeterminadas()

    gestor_deshacer = GestorDeshacer(repo)

    watcher_service = ServicioClasificacion(
        watcher=WatchdogFileWatcher(),
        repo=repo,
    )

    window = MainWindow(
        data_dir=DATA_DIR,
        watcher_service=watcher_service,
        rule_repository=repo,
        gestor_deshacer=gestor_deshacer,
    )
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
