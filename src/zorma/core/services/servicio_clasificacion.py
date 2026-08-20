from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..models.archivo import Archivo
from ..models.enums import EstadoClasificacion
from ..models.resultado_clasificacion import ResultadoClasificacion

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from pathlib import Path

    from ...adapters.persistence.zorma_repository import ZormaRepository
    from ...adapters.watcher.watchdog_watcher import WatchdogFileWatcher
    from ..models.accion_regla import AccionRegla
    from ..models.evento_archivo import EventoArchivo
    from ..models.filter_config import FilterConfig
    from ..models.regla import Regla

logger = logging.getLogger(__name__)


class ServicioClasificacion:
    def __init__(
        self,
        watcher: WatchdogFileWatcher,
        repo: ZormaRepository,
        history: ZormaRepository,
    ) -> None:
        self._watcher = watcher
        self._repo = repo
        self._history = history
        self._result_callback: Callable[[ResultadoClasificacion], None] | None = None

    def set_result_callback(self, callback: Callable[[ResultadoClasificacion], None]) -> None:
        self._result_callback = callback

    def get_history(self) -> list[ResultadoClasificacion]:
        return self._history.get_history()

    def start_monitoring(
        self,
        paths: list[Path],
        filter_config: FilterConfig | None = None,
    ) -> None:
        self._watcher.update_filter(filter_config)
        excluded_patterns = ["Archivos *"]
        self._watcher.start(paths, self._on_event, excluded_patterns=excluded_patterns)
        self._initial_scan(paths, filter_config)
        logger.info("Watcher started on %d path(s)", len(paths))

    def stop_monitoring(self) -> None:
        self._watcher.stop()
        logger.info("Watcher stopped")

    def _on_event(self, event: EventoArchivo) -> None:
        if event.src_path.is_dir():
            result = ResultadoClasificacion(
                estado=EstadoClasificacion.FILTRADO,
                mensaje_error="Directory event ignored",
            )
        else:
            result = self._clasificar(event.src_path)
            self._history.add_history(result)
        if self._result_callback:
            self._result_callback(result)

    def clasificar(self, file_path: Path, overwrite: bool = False) -> ResultadoClasificacion:
        result = self._clasificar(file_path, overwrite)
        self._history.add_history(result)
        return result

    _SKIP_DIRS = {"node_modules", ".git", "__pycache__", "venv", ".venv", "dist", "build", ".tox", ".mypy_cache"}

    @staticmethod
    def _iter_files(paths: list[Path], filter_config: FilterConfig | None = None) -> Generator[Path, None, None]:
        for base in paths:
            if not base.is_dir():
                continue
            for fpath in base.rglob("*"):
                if not fpath.is_file():
                    continue
                if any(part in ServicioClasificacion._SKIP_DIRS for part in fpath.parts):
                    continue
                if filter_config and not filter_config.matches(fpath):
                    continue
                yield fpath

    def _find_action(self, file_path: Path) -> tuple[Regla, AccionRegla] | None:
        if not file_path.exists():
            return None
        reglas = self._repo.get_all_rules()
        archivo = Archivo(_ruta_completa=file_path)
        for regla in reglas:
            if regla.evaluar(archivo):
                acciones = self._repo.get_actions_for_rule(regla.id)
                if acciones:
                    return regla, acciones[0]
        return None

    def _clasificar(self, file_path: Path, overwrite: bool = False) -> ResultadoClasificacion:
        match = self._find_action(file_path)
        archivo = Archivo(_ruta_completa=file_path)
        if match is None:
            return ResultadoClasificacion(
                nombre_archivo=file_path.name,
                ruta_origen=file_path,
                estado=EstadoClasificacion.FILTRADO if not file_path.exists() else EstadoClasificacion.SIN_REGLA,
            )
        regla, accion = match
        result = accion.ejecutar(archivo, overwrite)
        result.regla_aplicada = regla
        result.accion_aplicada = accion
        return result

    def previsualizar(self, file_path: Path) -> ResultadoClasificacion:
        match = self._find_action(file_path)
        archivo = Archivo(_ruta_completa=file_path)
        if match is None:
            return ResultadoClasificacion(
                nombre_archivo=file_path.name,
                ruta_origen=file_path,
                estado=EstadoClasificacion.FILTRADO if not file_path.exists() else EstadoClasificacion.SIN_REGLA,
            )
        _, accion = match
        has_conflict = accion.verificar_conflicto(archivo)
        return ResultadoClasificacion(
            nombre_archivo=file_path.name,
            ruta_origen=file_path,
            accion_aplicada=accion,
            estado=EstadoClasificacion.CONFLICTO if has_conflict else EstadoClasificacion.EXITO,
        )

    def previsualizar_todos(
        self,
        paths: list[Path],
        filter_config: FilterConfig | None = None,
    ) -> list[ResultadoClasificacion]:
        results: list[ResultadoClasificacion] = []
        for fpath in self._iter_files(paths, filter_config):
            result = self.previsualizar(fpath)
            results.append(result)
        return results

    def _initial_scan(
        self,
        paths: list[Path],
        filter_config: FilterConfig | None = None,
    ) -> list[ResultadoClasificacion]:
        results: list[ResultadoClasificacion] = []
        for fpath in self._iter_files(paths, filter_config):
            result = self.previsualizar(fpath)
            if self._result_callback:
                self._result_callback(result)
            results.append(result)
        logger.info("Initial scan complete: %d files processed", len(results))
        return results
