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

    def cancelar(self) -> None:
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

    def cancelar(self) -> None:
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
        self._cargar_configuracion()

    # --- Settings ---

    def _cargar_configuracion(self) -> None:
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
            self._emitir_estado_ui()
        except (OSError, json.JSONDecodeError):
            pass

    def _guardar_configuracion(self) -> None:
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

    def establecer_ruta_vigilancia(self, path: Path | None) -> None:
        self._watch_path = path
        self.watch_path_changed.emit(path)
        self._emitir_estado_ui()
        self._guardar_configuracion()

    def obtener_ruta_vigilancia(self) -> Path | None:
        return self._watch_path

    def obtener_auto_clasificar(self) -> bool:
        return self._auto_classify

    # --- Classification ---

    def establecer_servicio_vigilancia(self, service: ServicioClasificacion) -> None:
        self._watcher_service = service
        self._cargar_historial()

    def obtener_servicio_vigilancia(self) -> ServicioClasificacion | None:
        return self._watcher_service

    def ejecutar_escaneo(self) -> None:
        if self._watcher_service is None or self._watch_path is None:
            return
        self._classifying = True
        self.classifying_changed.emit(True)
        self.status_text.emit("Escaneando archivos...", COLORS["primary"])
        self.progress_changed.emit(0, 0)

        self._scan_worker = ScanWorker(self._watcher_service, [self._watch_path])
        self._scan_worker.scan_finished.connect(self._al_finalizar_escaneo)
        self._scan_worker.start()

    def _al_finalizar_escaneo(self, results: list[ResultadoClasificacion]) -> None:
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

    def iniciar_clasificacion(self, results: list[ResultadoClasificacion]) -> None:
        if self._watcher_service is None:
            return
        self._classifying = True
        self.classifying_changed.emit(True)
        self.status_text.emit("Clasificando...", COLORS["primary"])
        self.progress_changed.emit(0, 100)

        self._classify_worker = ClassifyWorker(self._watcher_service, results)
        self._classify_worker.progress.connect(self._al_progreso_clasificacion)
        self._classify_worker.file_done.connect(self._al_archivo_clasificado)
        self._classify_worker.classify_finished.connect(self._al_finalizar_clasificacion)
        self._classify_worker.start()

    def _al_progreso_clasificacion(self, current: int, total: int) -> None:
        self.progress_changed.emit(current, total)
        self.status_text.emit(f"Clasificando {current} de {total}", COLORS["primary"])

    def _al_archivo_clasificado(self, result: object) -> None:
        if isinstance(result, ResultadoClasificacion):
            self._agregar_resultado(result)

    def _al_finalizar_clasificacion(self, success_count: int, error_count: int) -> None:
        self._classifying = False
        self.classifying_changed.emit(False)
        self._classify_worker = None
        self.status_text.emit("", "")
        self.progress_changed.emit(0, 100)
        self._emitir_estado_ui()
        self.show_toast.emit(
            f"✓ {success_count} clasificados, {error_count} errores",
            COLORS["success"] if error_count == 0 else COLORS["warning"],
        )

    def cancelar_operacion(self) -> None:
        if self._classify_worker is not None and self._classify_worker.isRunning():
            self._classify_worker.cancelar()
            self._classify_worker.wait(3000)
            self._classify_worker = None
            self._classifying = False
            self.classifying_changed.emit(False)
            self.status_text.emit("", "")
            self.progress_changed.emit(0, 100)
            self.show_toast.emit("Clasificación cancelada", COLORS["warning"])
            return

        if self._scan_worker is not None and self._scan_worker.isRunning():
            self._scan_worker.cancelar()
            self._scan_worker.wait(3000)
            self._scan_worker = None
            self._classifying = False
            self.classifying_changed.emit(False)
            self.status_text.emit("", "")
            self.progress_changed.emit(0, 100)
            self.show_toast.emit("Escaneo cancelado", COLORS["warning"])
            return

    # --- Watcher ---

    def iniciar_vigilancia(self) -> None:
        if self._watcher_service is None or self._watch_path is None:
            return
        self._watcher_service.establecer_callback_resultado(self._al_resultado)
        self._watcher_service.iniciar_monitoreo([self._watch_path])
        self._watcher_running = True
        self.watcher_status.emit("● Monitor activo", COLORS["success"])

    def detener_vigilancia(self) -> None:
        if self._watcher_service is None:
            return
        self._watcher_service.detener_monitoreo()
        self._watcher_running = False
        self.watcher_status.emit("● Monitor detenido", COLORS["error"])

    def establecer_auto_clasificar(self, enabled: bool) -> None:
        self._auto_classify = enabled
        if enabled:
            self.iniciar_vigilancia()
        else:
            self.detener_vigilancia()
        self._emitir_estado_ui()
        self._guardar_configuracion()

    # --- History ---

    def _cargar_historial(self) -> None:
        if self._watcher_service is None:
            return
        results = self._watcher_service.obtener_historial()
        self._total_classified = 0
        self._total_errors = 0
        for result in results:
            self._agregar_resultado(result)

    def _agregar_resultado(self, result: ResultadoClasificacion) -> None:
        if result.estado == EstadoClasificacion.EXITO:
            self._total_classified += 1
        elif result.estado == EstadoClasificacion.ERROR:
            self._total_errors += 1
        self.counters_changed.emit(self._total_classified, self._total_errors)
        self.result_added.emit(result)
        self._emitir_estado_ui()

    def _al_resultado(self, result: ResultadoClasificacion) -> None:
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self._agregar_resultado(result))

    # --- Undo / Redo ---

    def puede_deshacer(self) -> bool:
        return self._gestor_deshacer is not None and self._gestor_deshacer.puede_deshacer()

    def puede_rehacer(self) -> bool:
        return self._gestor_deshacer is not None and self._gestor_deshacer.puede_rehacer()

    def obtener_cantidad_deshacibles(self) -> int:
        if self._gestor_deshacer is None:
            return 0
        return len([e for e in self._gestor_deshacer.obtener_pila_deshacer() if not e.revertido])

    def deshacer_archivo(self, result: ResultadoClasificacion) -> None:
        if self._gestor_deshacer is None or result.ruta_origen is None:
            return
        undone = self._gestor_deshacer.deshacer_por_ruta_origen(result.ruta_origen)
        if undone is not None and undone.estado == EstadoClasificacion.EXITO:
            self._total_classified = max(0, self._total_classified - 1)
            self.counters_changed.emit(self._total_classified, self._total_errors)
            self._emitir_estado_ui()

    def deshacer_todo(self) -> int:
        if self._gestor_deshacer is None:
            return 0
        undone_count = 0
        while self._gestor_deshacer.puede_deshacer():
            result = self._gestor_deshacer.deshacer()
            if result is not None and result.estado == EstadoClasificacion.EXITO:
                self._total_classified = max(0, self._total_classified - 1)
                undone_count += 1
        self.counters_changed.emit(self._total_classified, self._total_errors)
        self._emitir_estado_ui()
        return undone_count

    def rehacer_todo(self) -> int:
        if self._gestor_deshacer is None:
            return 0
        redone_count = 0
        while self._gestor_deshacer.puede_rehacer():
            result = self._gestor_deshacer.rehacer()
            if result is not None and result.estado == EstadoClasificacion.EXITO:
                self._total_classified += 1
                redone_count += 1
        self.counters_changed.emit(self._total_classified, self._total_errors)
        self._emitir_estado_ui()
        return redone_count

    # --- UI state helpers ---

    def _emitir_estado_ui(self) -> None:
        show_onboarding = self._total_classified == 0 and self._watch_path is None
        self.onboarding_changed.emit(show_onboarding)
        can_undo = self.puede_deshacer()
        can_redo = self.puede_rehacer()
        self.undo_redo_changed.emit(can_undo, can_redo)

    def obtener_cantidad_reglas(self) -> str:
        if self._repo is None:
            return "0"
        return str(len(self._repo.obtener_todas_las_reglas()))

    @property
    def esta_clasificando(self) -> bool:
        return self._classifying
