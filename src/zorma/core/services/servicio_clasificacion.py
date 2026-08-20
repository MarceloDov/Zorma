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
    from ...adapters.watcher.vigilante_watchdog import VigilanteArchivosWatchdog
    from ..models.accion_regla import AccionRegla
    from ..models.configuracion_filtro import ConfiguracionFiltro
    from ..models.evento_archivo import EventoArchivo
    from ..models.regla import Regla

logger = logging.getLogger(__name__)


class ServicioClasificacion:
    def __init__(
        self,
        watcher: VigilanteArchivosWatchdog,
        repo: ZormaRepository,
    ) -> None:
        self._watcher = watcher
        self._repo = repo
        self._result_callback: Callable[[ResultadoClasificacion], None] | None = None

    def establecer_callback_resultado(self, callback: Callable[[ResultadoClasificacion], None]) -> None:
        self._result_callback = callback

    def obtener_historial(self) -> list[ResultadoClasificacion]:
        return self._repo.obtener_historial()

    def iniciar_monitoreo(
        self,
        paths: list[Path],
        filter_config: ConfiguracionFiltro | None = None,
    ) -> None:
        self._watcher.actualizar_filtro(filter_config)
        excluded_patterns = ["Archivos *"]
        self._watcher.iniciar(paths, self._al_evento, excluded_patterns=excluded_patterns)
        self._escaneo_inicial(paths, filter_config)
        logger.info("Watcher started on %d path(s)", len(paths))

    def detener_monitoreo(self) -> None:
        self._watcher.detener()
        logger.info("Watcher stopped")

    def _al_evento(self, event: EventoArchivo) -> None:
        if event.src_path.is_dir():
            result = ResultadoClasificacion(
                estado=EstadoClasificacion.FILTRADO,
                mensaje_error="Directory event ignored",
            )
        else:
            result = self._clasificar(event.src_path)
            self._repo.agregar_historial(result)
        if self._result_callback:
            self._result_callback(result)

    def clasificar(self, file_path: Path, overwrite: bool = False) -> ResultadoClasificacion:
        result = self._clasificar(file_path, overwrite)
        self._repo.agregar_historial(result)
        return result

    _SKIP_DIRS = {"node_modules", ".git", "__pycache__", "venv", ".venv", "dist", "build", ".tox", ".mypy_cache"}

    @staticmethod
    def _iterar_archivos(
        paths: list[Path], filter_config: ConfiguracionFiltro | None = None
    ) -> Generator[Path, None, None]:
        for base in paths:
            if not base.is_dir():
                continue
            for fpath in base.rglob("*"):
                if not fpath.is_file():
                    continue
                if any(part in ServicioClasificacion._SKIP_DIRS for part in fpath.parts):
                    continue
                if filter_config and not filter_config.coincide(fpath):
                    continue
                yield fpath

    def _buscar_accion(self, file_path: Path) -> tuple[Regla, AccionRegla] | None:
        if not file_path.exists():
            return None
        reglas = self._repo.obtener_todas_las_reglas()
        archivo = Archivo(_ruta_completa=file_path)
        for regla in reglas:
            if regla.evaluar(archivo):
                acciones = self._repo.obtener_acciones_de_regla(regla.id)
                if acciones:
                    return regla, acciones[0]
        return None

    def _clasificar(self, file_path: Path, overwrite: bool = False) -> ResultadoClasificacion:
        match = self._buscar_accion(file_path)
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
        match = self._buscar_accion(file_path)
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
        filter_config: ConfiguracionFiltro | None = None,
    ) -> list[ResultadoClasificacion]:
        results: list[ResultadoClasificacion] = []
        for fpath in self._iterar_archivos(paths, filter_config):
            result = self.previsualizar(fpath)
            results.append(result)
        return results

    def _escaneo_inicial(
        self,
        paths: list[Path],
        filter_config: ConfiguracionFiltro | None = None,
    ) -> list[ResultadoClasificacion]:
        results: list[ResultadoClasificacion] = []
        for fpath in self._iterar_archivos(paths, filter_config):
            result = self.previsualizar(fpath)
            if self._result_callback:
                self._result_callback(result)
            results.append(result)
        logger.info("Initial scan complete: %d files processed", len(results))
        return results
