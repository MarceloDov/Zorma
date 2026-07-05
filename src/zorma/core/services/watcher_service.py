from __future__ import annotations

import logging
from collections.abc import Callable, Generator
from pathlib import Path

from ...adapters.persistence.zorma_repository import ZormaRepository
from ..models.classification import ClassificationResult, ClassificationStatus
from ..models.file_event import FileEvent
from ..models.filter_config import FilterConfig
from ..models.rule import Rule, RuleAction
from ...adapters.watcher.watchdog_watcher import WatchdogFileWatcher
from .action_executor import ActionExecutor
from .rule_evaluator import RuleEvaluator
from .undo_manager import UndoManager

logger = logging.getLogger(__name__)


class WatcherService:
    """Servicio encargado de monitorear cambios en archivos y clasificarlos."""
    def __init__(
        self,
        watcher: WatchdogFileWatcher,
        repo: ZormaRepository,
        evaluator: RuleEvaluator,
        executor: ActionExecutor,
        history: ZormaRepository,
    ) -> None:
        self._watcher = watcher
        self._repo = repo
        self._evaluator = evaluator
        self._executor = executor
        self._history = history
        self._undo_manager: UndoManager | None = None
        self._result_callback: Callable[[ClassificationResult], None] | None = None

    def set_undo_manager(self, manager: UndoManager) -> None:
        """Asigna el gestor de deshacer operaciones."""
        self._undo_manager = manager

    def get_undo_manager(self) -> UndoManager | None:
        """Retorna el gestor de deshacer operaciones."""
        return self._undo_manager

    def get_history(self) -> list[ClassificationResult]:
        """Retorna el historial de clasificaciones."""
        return self._history.get_history()

    def set_result_callback(self, callback: Callable[[ClassificationResult], None]) -> None:
        """Asigna una función callback para el resultado de la clasificación."""
        self._result_callback = callback

    def start_monitoring(
        self,
        paths: list[Path],
        filter_config: FilterConfig | None = None,
    ) -> None:
        """Inicia el monitoreo de las rutas especificadas."""
        self._watcher.update_filter(filter_config)

        # Obtener patrones de exclusión de las reglas
        excluded_patterns = ["Archivos *"]

        self._watcher.start(paths, self._on_event, excluded_patterns=excluded_patterns)
        self._initial_scan(paths, filter_config)
        logger.info("Watcher started on %d path(s)", len(paths))

    def stop_monitoring(self) -> None:
        """Detiene el monitoreo."""
        self._watcher.stop()
        logger.info("Watcher stopped")

    def _on_event(self, event: FileEvent) -> ClassificationResult | None:
        """Manejador de eventos de archivo."""
        if event.is_directory:
            result = ClassificationResult(
                file_name=event.src_path.name,
                source_path=event.src_path,
                status=ClassificationStatus.FILTERED_OUT,
                error_message="Directory event ignored",
            )
            return result
        result = self._classify(event.src_path)
        self._post_process_result(result)
        if self._result_callback:
            self._result_callback(result)
        return result

    def classify(self, file_path: Path, overwrite: bool = False) -> ClassificationResult:
        """Clasifica un archivo dado de forma manual."""
        result = self._classify(file_path, overwrite)
        self._post_process_result(result)
        return result

    def _post_process_result(self, result: ClassificationResult) -> None:
        """Procesa el resultado: registra en log y en el gestor de deshacer."""
        self._history.add_history(result)
        if self._undo_manager is not None:
            self._undo_manager.record(result)

    @staticmethod
    def _iter_files(paths: list[Path], filter_config: FilterConfig | None = None) -> Generator[Path, None, None]:
        """Itera sobre archivos en las rutas dadas, aplicando filtros."""
        for base in paths:
            if not base.is_dir():
                continue
            for fpath in base.rglob("*"):
                if not fpath.is_file():
                    continue
                if filter_config and not filter_config.matches(fpath):
                    continue
                yield fpath

    def _find_action(self, file_path: Path) -> tuple[Rule, RuleAction] | None:
        """Busca la mejor acción para un archivo dado."""
        if not file_path.exists():
            return None
        rules = self._repo.get_all_rules()
        matched = self._evaluator.evaluate_all(file_path, rules)
        if not matched:
            return None
        best = matched[0]
        actions = self._repo.get_actions_for_rule(best.id)
        if not actions:
            return None
        return best, actions[0]

    def _classify(self, file_path: Path, overwrite: bool = False) -> ClassificationResult:
        """Clasifica internamente un archivo."""
        match = self._find_action(file_path)
        result = ClassificationResult(
            file_name=file_path.name,
            source_path=file_path,
        )
        if match is None:
            result.status = ClassificationStatus.FILTERED_OUT if not file_path.exists() else ClassificationStatus.NO_RULE
            return result
        rule, action = match
        result.rule_applied = rule
        result.action_applied = action
        exec_result = self._executor.execute(action, file_path, overwrite)
        result.status = exec_result.status
        result.destination_path = exec_result.destination_path
        result.error_message = exec_result.error_message
        return result

    def preview(self, file_path: Path) -> ClassificationResult:
        """Genera una vista previa de la clasificación de un archivo."""
        match = self._find_action(file_path)
        result = ClassificationResult(
            file_name=file_path.name,
            source_path=file_path,
        )
        if match is None:
            result.status = ClassificationStatus.FILTERED_OUT if not file_path.exists() else ClassificationStatus.NO_RULE
            return result
        _, action = match
        result.action_applied = action
        has_conflict, dest = self._executor.check_conflict(action, file_path)
        result.destination_path = dest
        result.status = ClassificationStatus.CONFLICT if has_conflict else ClassificationStatus.SUCCESS
        return result

    def preview_all(
        self,
        paths: list[Path],
        filter_config: FilterConfig | None = None,
    ) -> list[ClassificationResult]:
        """Genera una vista previa de clasificación para todos los archivos en las rutas dadas."""
        results: list[ClassificationResult] = []
        for fpath in self._iter_files(paths, filter_config):
            result = self.preview(fpath)
            results.append(result)
        return results

    def _initial_scan(
        self,
        paths: list[Path],
        filter_config: FilterConfig | None = None,
    ) -> list[ClassificationResult]:
        """Realiza un escaneo inicial de las rutas configuradas (solo vista previa)."""
        results: list[ClassificationResult] = []
        for fpath in self._iter_files(paths, filter_config):
            result = self.preview(fpath)
            if self._result_callback:
                self._result_callback(result)
            results.append(result)
        logger.info("Initial scan complete: %d files processed", len(results))
        return results
