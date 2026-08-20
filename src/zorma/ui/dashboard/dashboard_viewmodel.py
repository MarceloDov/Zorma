from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from ...adapters.persistence.zorma_repository import ZormaRepository
from ...core.models.enums import EstadoClasificacion
from ...core.models.resultado_clasificacion import ResultadoClasificacion
from ...core.services.gestor_deshacer import GestorDeshacer
from ...core.services.servicio_clasificacion import ServicioClasificacion
from ..shared.styles import COLORS


class ScanWorker(QThread):
    """Worker para realizar escaneos de archivos en segundo plano."""
    scan_finished = pyqtSignal(list)

    def __init__(
        self,
        watcher_service: ServicioClasificacion,
        paths: list[Path],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._watcher_service = watcher_service
        self._paths = paths
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        results = self._watcher_service.previsualizar_todos(self._paths)
        if not self._cancelled:
            self.scan_finished.emit(results)


class ClassifyWorker(QThread):
    """Worker para realizar la clasificación de archivos en segundo plano."""
    progress = pyqtSignal(int, int)
    file_done = pyqtSignal(object)
    classify_finished = pyqtSignal(int, int)

    def __init__(
        self,
        watcher_service: ServicioClasificacion,
        results: list[ResultadoClasificacion],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._watcher_service = watcher_service
        self._results = results
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        total = len(self._results)
        success_count = 0
        error_count = 0
        for i, r in enumerate(self._results):
            if self._cancelled:
                break
            self.progress.emit(i + 1, total)
            if self._watcher_service is None or r.ruta_origen is None:
                continue
            actual = self._watcher_service.clasificar(r.ruta_origen, overwrite=r.sobrescribir)
            self.file_done.emit(actual)
            if actual.estado == EstadoClasificacion.EXITO:
                success_count += 1
            else:
                error_count += 1
        self.classify_finished.emit(success_count, error_count)


class DashboardViewModel(QObject):
    """ViewModel del Dashboard. Gestiona estado, workers, settings, undo y watcher."""

    watch_path_changed = pyqtSignal(object)
    classifying_changed = pyqtSignal(bool)
    counters_changed = pyqtSignal(int, int)
    undo_redo_changed = pyqtSignal(bool, bool)
    onboarding_changed = pyqtSignal(bool)
    progress_changed = pyqtSignal(int, int)
    status_text = pyqtSignal(str, str)
    result_added = pyqtSignal(object)
    watcher_status = pyqtSignal(str, str)
    show_toast = pyqtSignal(str, str)

    def __init__(
        self,
        data_dir: Path,
        repo: ZormaRepository | None = None,
        gestor_deshacer: GestorDeshacer | None = None,
        watcher_service: ServicioClasificacion | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._data_dir = data_dir
        self._repo = repo
        self._gestor_deshacer = gestor_deshacer
        self._watcher_service = watcher_service
        self._watch_path: Path | None = None
        self._total_classified = 0
        self._total_errors = 0
        self._classifying = False
        self._watcher_running = False
        self._auto_classify = False
        self._scan_worker: ScanWorker | None = None
        self._classify_worker: ClassifyWorker | None = None
        self._load_settings()

    # --- Settings ---

    def _load_settings(self) -> None:
        config_file = self._data_dir / "app_config.json"
        if not config_file.exists():
            return
        try:
            config: dict[str, Any] = json.loads(config_file.read_text(encoding="utf-8"))
            watch_path_str = config.get("watch_path", "")
            if watch_path_str:
                p = Path(watch_path_str)
                if p.is_dir():
                    self._watch_path = p
                    self.watch_path_changed.emit(p)
                    self._auto_classify = config.get("auto_classify", False)
            self._emit_ui_state()
        except (OSError, json.JSONDecodeError):
            pass

    def _save_settings(self) -> None:
        config_file = self._data_dir / "app_config.json"
        try:
            config: dict[str, Any] = {}
            if config_file.exists():
                config = json.loads(config_file.read_text(encoding="utf-8"))
            config["watch_path"] = str(self._watch_path) if self._watch_path else ""
            config["auto_classify"] = self._auto_classify
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_file.write_text(json.dumps(config, indent=2, default=str), encoding="utf-8")
        except OSError:
            pass

    # --- Watch path ---

    def set_watch_path(self, path: Path | None) -> None:
        self._watch_path = path
        self.watch_path_changed.emit(path)
        self._emit_ui_state()
        self._save_settings()

    def get_watch_path(self) -> Path | None:
        return self._watch_path

    def get_auto_classify(self) -> bool:
        return self._auto_classify

    # --- Classification ---

    def set_watcher_service(self, service: ServicioClasificacion) -> None:
        self._watcher_service = service
        self._load_history()

    def get_watcher_service(self) -> ServicioClasificacion | None:
        return self._watcher_service

    def run_scan(self) -> None:
        if self._watcher_service is None or self._watch_path is None:
            return
        self._classifying = True
        self.classifying_changed.emit(True)
        self.status_text.emit("Escaneando archivos...", COLORS["primary"])
        self.progress_changed.emit(0, 0)

        self._scan_worker = ScanWorker(self._watcher_service, [self._watch_path])
        self._scan_worker.scan_finished.connect(self._on_scan_finished)
        self._scan_worker.start()

    def _on_scan_finished(self, results: list[ResultadoClasificacion]) -> None:
        self._classifying = False
        self.classifying_changed.emit(False)

        if not results:
            self.status_text.emit("", "")
            self.progress_changed.emit(0, 100)
            self.show_toast.emit("Sin archivos en la carpeta", COLORS["text_muted"])
            return

        self.status_text.emit("", "")
        self.progress_changed.emit(0, 100)
        self.scan_finished_for_preview.emit(results)

    scan_finished_for_preview = pyqtSignal(list)

    def start_classify(self, results: list[ResultadoClasificacion]) -> None:
        if self._watcher_service is None:
            return
        self._classifying = True
        self.classifying_changed.emit(True)
        self.status_text.emit("Clasificando...", COLORS["primary"])
        self.progress_changed.emit(0, 100)

        self._classify_worker = ClassifyWorker(self._watcher_service, results)
        self._classify_worker.progress.connect(self._on_classify_progress)
        self._classify_worker.file_done.connect(self._on_classify_file_done)
        self._classify_worker.classify_finished.connect(self._on_classify_finished)
        self._classify_worker.start()

    def _on_classify_progress(self, current: int, total: int) -> None:
        self.progress_changed.emit(current, total)
        self.status_text.emit(f"Clasificando {current} de {total}", COLORS["primary"])

    def _on_classify_file_done(self, result: object) -> None:
        if isinstance(result, ResultadoClasificacion):
            self._add_result(result)

    def _on_classify_finished(self, success_count: int, error_count: int) -> None:
        self._classifying = False
        self.classifying_changed.emit(False)
        self._classify_worker = None
        self.status_text.emit("", "")
        self.progress_changed.emit(0, 100)
        self._emit_ui_state()
        self.show_toast.emit(
            f"✓ {success_count} clasificados, {error_count} errores",
            COLORS["success"] if error_count == 0 else COLORS["warning"],
        )

    def cancel_operation(self) -> None:
        if self._classify_worker is not None and self._classify_worker.isRunning():
            self._classify_worker.cancel()
            self._classify_worker.wait(3000)
            self._classify_worker = None
            self._classifying = False
            self.classifying_changed.emit(False)
            self.status_text.emit("", "")
            self.progress_changed.emit(0, 100)
            self.show_toast.emit("Clasificación cancelada", COLORS["warning"])
            return

        if self._scan_worker is not None and self._scan_worker.isRunning():
            self._scan_worker.cancel()
            self._scan_worker.wait(3000)
            self._scan_worker = None
            self._classifying = False
            self.classifying_changed.emit(False)
            self.status_text.emit("", "")
            self.progress_changed.emit(0, 100)
            self.show_toast.emit("Escaneo cancelado", COLORS["warning"])
            return

    # --- Watcher ---

    def start_watcher(self) -> None:
        if self._watcher_service is None or self._watch_path is None:
            return
        self._watcher_service.set_result_callback(self._on_result)
        self._watcher_service.start_monitoring([self._watch_path])
        self._watcher_running = True
        self.watcher_status.emit("● Monitor activo", COLORS["success"])

    def stop_watcher(self) -> None:
        if self._watcher_service is None:
            return
        self._watcher_service.stop_monitoring()
        self._watcher_running = False
        self.watcher_status.emit("● Monitor detenido", COLORS["error"])

    def set_auto_classify(self, enabled: bool) -> None:
        self._auto_classify = enabled
        if enabled:
            self.start_watcher()
        else:
            self.stop_watcher()
        self._emit_ui_state()
        self._save_settings()

    # --- History ---

    def _load_history(self) -> None:
        if self._watcher_service is None:
            return
        results = self._watcher_service.get_history()
        self._total_classified = 0
        self._total_errors = 0
        for result in results:
            self._add_result(result)

    def _add_result(self, result: ResultadoClasificacion) -> None:
        if result.estado == EstadoClasificacion.EXITO:
            self._total_classified += 1
        elif result.estado == EstadoClasificacion.ERROR:
            self._total_errors += 1
        self.counters_changed.emit(self._total_classified, self._total_errors)
        self.result_added.emit(result)
        self._emit_ui_state()

    def _on_result(self, result: ResultadoClasificacion) -> None:
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self._add_result(result))

    # --- Undo / Redo ---

    def can_undo(self) -> bool:
        return self._gestor_deshacer is not None and self._gestor_deshacer.can_undo()

    def can_redo(self) -> bool:
        return self._gestor_deshacer is not None and self._gestor_deshacer.can_redo()

    def get_undoable_count(self) -> int:
        if self._gestor_deshacer is None:
            return 0
        return len([e for e in self._gestor_deshacer.get_undoable() if not e.revertido])

    def undo_file(self, result: ResultadoClasificacion) -> None:
        if self._gestor_deshacer is None or result.ruta_origen is None:
            return
        undone = self._gestor_deshacer.undo_by_source_path(result.ruta_origen)
        if undone is not None and undone.estado == EstadoClasificacion.EXITO:
            self._total_classified = max(0, self._total_classified - 1)
            self.counters_changed.emit(self._total_classified, self._total_errors)
            self._emit_ui_state()

    def undo_all(self) -> int:
        if self._gestor_deshacer is None:
            return 0
        undone_count = 0
        while self._gestor_deshacer.can_undo():
            result = self._gestor_deshacer.undo()
            if result is not None and result.estado == EstadoClasificacion.EXITO:
                self._total_classified = max(0, self._total_classified - 1)
                undone_count += 1
        self.counters_changed.emit(self._total_classified, self._total_errors)
        self._emit_ui_state()
        return undone_count

    def redo_all(self) -> int:
        if self._gestor_deshacer is None:
            return 0
        redone_count = 0
        while self._gestor_deshacer.can_redo():
            result = self._gestor_deshacer.redo()
            if result is not None and result.estado == EstadoClasificacion.EXITO:
                self._total_classified += 1
                redone_count += 1
        self.counters_changed.emit(self._total_classified, self._total_errors)
        self._emit_ui_state()
        return redone_count

    # --- UI state helpers ---

    def _emit_ui_state(self) -> None:
        show_onboarding = self._total_classified == 0 and self._watch_path is None
        self.onboarding_changed.emit(show_onboarding)
        can_undo = self.can_undo()
        can_redo = self.can_redo()
        self.undo_redo_changed.emit(can_undo, can_redo)

    def get_rules_count(self) -> str:
        if self._repo is None:
            return "0"
        return str(len(self._repo.get_all_rules()))

    @property
    def is_classifying(self) -> bool:
        return self._classifying
