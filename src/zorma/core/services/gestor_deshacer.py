from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from ..models.enums import EstadoClasificacion, TipoOperacion
from ..models.pila_deshacer import PilaDeshacer
from ..models.resultado_clasificacion import ResultadoClasificacion

if TYPE_CHECKING:
    from collections.abc import Callable

    from ...adapters.persistence.zorma_repository import ZormaRepository

logger = logging.getLogger(__name__)


class GestorDeshacer:
    def __init__(self, repo: ZormaRepository) -> None:
        self._repo = repo
        self._result_callback: Callable[[ResultadoClasificacion], None] | None = None

    def set_result_callback(self, callback: Callable[[ResultadoClasificacion], None]) -> None:
        self._result_callback = callback

    def record(self, result: ResultadoClasificacion) -> None:
        if result.estado != EstadoClasificacion.EXITO:
            return
        self._repo.redo_clear()
        entry = PilaDeshacer(
            tipo_operacion=TipoOperacion.MOVER,
            _ruta_origen=result.ruta_origen or Path(),
            _ruta_destino=result.ruta_destino or Path(),
        )
        self._repo.undo_push(entry)

    def undo(self) -> ResultadoClasificacion | None:
        entry = self._repo.undo_pop()
        if entry is None:
            return None
        if entry.revertido:
            return None
        success = entry.revertir()
        result = ResultadoClasificacion(
            nombre_archivo=entry._ruta_origen.name,
            ruta_origen=entry._ruta_destino,
            ruta_destino=entry._ruta_origen,
            estado=EstadoClasificacion.EXITO if success else EstadoClasificacion.ERROR,
        )
        if success:
            self._repo.redo_push(entry)
            self._repo.undo_mark_reverted(entry.id)
            if self._result_callback:
                self._result_callback(result)
        return result

    def undo_by_source_path(self, source_path: Path) -> ResultadoClasificacion | None:
        for entry in self._repo.undo_get_all():
            if entry._ruta_origen == source_path and not entry.revertido:
                removed = self._repo.undo_remove_by_id(entry.id)
                if removed is not None:
                    success = removed.revertir()
                    result = ResultadoClasificacion(
                        nombre_archivo=removed._ruta_origen.name,
                        ruta_origen=removed._ruta_destino,
                        ruta_destino=removed._ruta_origen,
                        estado=EstadoClasificacion.EXITO if success else EstadoClasificacion.ERROR,
                    )
                    if success:
                        self._repo.redo_push(removed)
                        self._repo.undo_mark_reverted(removed.id)
                        if self._result_callback:
                            self._result_callback(result)
                    return result
        return None

    def redo(self) -> ResultadoClasificacion | None:
        entry = self._repo.redo_pop()
        if entry is None:
            return None
        src = entry._ruta_origen
        dest = entry._ruta_destino
        if not src.exists():
            logger.warning("Cannot redo: source file not found: %s", src)
            return None
        result = ResultadoClasificacion(
            nombre_archivo=src.name,
            ruta_origen=src,
            ruta_destino=dest,
        )
        try:
            if dest.exists():
                logger.warning("Cannot redo: destination exists: %s", dest)
                result.estado = EstadoClasificacion.OMITIDO
                return result
            if entry.tipo_operacion in (TipoOperacion.MOVER, TipoOperacion.COPIAR):
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dest))
            elif entry.tipo_operacion == TipoOperacion.RENOMBRAR:
                src.rename(dest)
            result.estado = EstadoClasificacion.EXITO
            entry.revertido = False
            self._repo.undo_push(entry)
            if self._result_callback:
                self._result_callback(result)
        except OSError as e:
            result.estado = EstadoClasificacion.ERROR
            result.mensaje_error = str(e)
        return result

    def get_undoable(self) -> list[PilaDeshacer]:
        return self._repo.undo_get_all()

    def can_undo(self) -> bool:
        return self._repo.undo_size() > 0

    def can_redo(self) -> bool:
        return self._repo.redo_size() > 0
