from __future__ import annotations

import json
import logging
from collections.abc import Callable, Generator
from pathlib import Path

from ..models.classification import ClassificationResult, ClassificationStatus
from ..models.file_event import FileEvent
from ..models.rule import Rule, RuleAction
from ..ports.file_watcher import FileWatcher, FilterConfig
from ..ports.rule_repository import RuleRepository
from .action_executor import ActionExecutor
from .rule_evaluator import RuleEvaluator
from .undo_manager import UndoManager

logger = logging.getLogger(__name__)


def _log_classification(data_dir: Path, result: ClassificationResult) -> None:
    log_file = data_dir / "history.jsonl"
    entry = {
        "file_name": result.file_name,
        "source_path": str(result.source_path),
        "destination_path": str(result.destination_path) if result.destination_path else None,
        "rule_name": result.rule_applied.name if result.rule_applied else None,
        "action_applied": result.action_applied.action_type.value if result.action_applied else None,
        "status": result.status,
        "error_message": result.error_message,
        "timestamp": result.timestamp.isoformat(),
    }
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except OSError:
        logger.exception("Failed to write classification log")


class WatcherService:
    """Servicio encargado de monitorear cambios en archivos y clasificarlos."""
    def __init__(
        self,
        watcher: FileWatcher,
        repo: RuleRepository,
        evaluator: RuleEvaluator,
        executor: ActionExecutor,
        data_dir: Path | None = None,
    ) -> None:
        self._watcher = watcher
        self._repo = repo
        self._evaluator = evaluator
        self._executor = executor
        self._data_dir = data_dir
        self._undo_manager: UndoManager | None = None
        self._result_callback: Callable[[ClassificationResult], None] | None = None

    def set_undo_manager(self, manager: UndoManager) -> None:
        """Asigna el gestor de deshacer operaciones."""
        self._undo_manager = manager

    def get_undo_manager(self) -> UndoManager | None:
        """Retorna el gestor de deshacer operaciones."""
        return self._undo_manager

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

    def _on_event(self, event: FileEvent) -> None:
        """Manejador de eventos de archivo."""
        if event.is_directory:
            result = ClassificationResult(
                file_name=event.src_path.name,
                source_path=event.src_path,
                status=ClassificationStatus.FILTERED_OUT,
                error_message="Directory event ignored",
            )
            return
        result = self._classify(event.src_path)
        self._post_process_result(result)
        if self._result_callback:
            self._result_callback(result)

    def classify(self, file_path: Path) -> ClassificationResult:
        """Clasifica un archivo dado de forma manual."""
        result = self._classify(file_path)
        self._post_process_result(result)
        return result

    def _post_process_result(self, result: ClassificationResult) -> None:
        """Procesa el resultado: registra en log y en el gestor de deshacer."""
        if self._data_dir is not None:
            _log_classification(self._data_dir, result)
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
        rules = self._repo.get_all()
        matched = self._evaluator.evaluate_all(file_path, rules)
        if not matched:
            return None
        best = matched[0]
        actions = self._repo.get_actions_for_rule(best.id)
        if not actions:
            return None
        return best, actions[0]

    def _classify(self, file_path: Path) -> ClassificationResult:
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
        exec_result = self._executor.execute(action, file_path)
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
        """Realiza un escaneo inicial de las rutas configuradas."""
        results: list[ClassificationResult] = []
        for fpath in self._iter_files(paths, filter_config):
            result = self._classify(fpath)
            self._post_process_result(result)
            if self._result_callback:
                self._result_callback(result)
            results.append(result)
        logger.info("Initial scan complete: %d files processed", len(results))
        return results
