from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from .enums import EstadoClasificacion, TipoAccion
from .resultado_clasificacion import ResultadoClasificacion

if TYPE_CHECKING:
    from .archivo import Archivo

logger = logging.getLogger(__name__)


@dataclass
class AccionRegla:
    id: str = field(default_factory=lambda: uuid4().hex)
    id_regla: str = ""
    tipo_accion: TipoAccion = TipoAccion.MOVER
    carpeta_destino: str = ""
    patron_renombre: str = ""
    creado_en: datetime = field(default_factory=lambda: datetime.now(UTC))

    def ejecutar(self, archivo: Archivo, sobrescribir: bool = False) -> ResultadoClasificacion:
        file = archivo._ruta_completa
        dest_str = str(self._resolver_destino(file)) if file.exists() else "(not found)"
        logger.info("%s %s → %s", self.tipo_accion.value, file, dest_str)
        result = ResultadoClasificacion(
            nombre_archivo=file.name,
            ruta_origen=file,
        )
        try:
            if not file.exists():
                result.estado = EstadoClasificacion.ERROR
                result.mensaje_error = f"Source file not found: {file}"
                return result

            dest = self._resolver_destino(file)
            result.ruta_destino = dest
            if dest.exists():
                if sobrescribir:
                    dest.unlink()
                else:
                    result.estado = EstadoClasificacion.OMITIDO
                    result.mensaje_error = f"Destination exists: {dest}"
                    return result

            if self.tipo_accion in (TipoAccion.MOVER, TipoAccion.COPIAR):
                dest.parent.mkdir(parents=True, exist_ok=True)
                if self.tipo_accion == TipoAccion.MOVER:
                    shutil.move(str(file), str(dest))
                else:
                    shutil.copy2(str(file), str(dest))
            else:
                file.rename(dest)

            result.aplicada = True
            result.estado = EstadoClasificacion.EXITO

        except PermissionError as e:
            logger.warning("Permission denied %s: %s", file, e)
            result.estado = EstadoClasificacion.ERROR
            result.mensaje_error = f"PERMISSION_DENIED: {e}"
        except OSError as e:
            logger.error("OSError %d on %s: %s", e.errno, file, e)
            result.estado = EstadoClasificacion.ERROR
            result.mensaje_error = f"DISK_FULL: {e}" if e.errno == 28 else f"OS_ERROR: {e}"
        return result

    def verificar_conflicto(self, archivo: Archivo) -> bool:
        file = archivo._ruta_completa
        dest = self._resolver_destino(file)
        if dest.exists():
            logger.info("conflict %s → %s", file, dest)
            return True
        return False

    def revertir(self, archivo: Archivo, origen: Path) -> ResultadoClasificacion:
        file = archivo._ruta_completa
        logger.info("rollback %s → %s", file, origen)
        result = ResultadoClasificacion()
        try:
            if not file.exists():
                result.estado = EstadoClasificacion.ERROR
                result.mensaje_error = f"File to rollback not found: {file}"
                return result
            if self.tipo_accion == TipoAccion.MOVER:
                shutil.move(str(file), str(origen))
            elif self.tipo_accion == TipoAccion.COPIAR:
                file.unlink()
            elif self.tipo_accion == TipoAccion.RENOMBRAR:
                file.rename(origen)
            result.aplicada = True
            result.estado = EstadoClasificacion.EXITO
        except OSError as e:
            result.estado = EstadoClasificacion.ERROR
            result.mensaje_error = str(e)
        return result

    def _resolver_destino(self, file: Path) -> Path:
        if self.tipo_accion == TipoAccion.RENOMBRAR:
            new_name = self._aplicar_patron_renombre(file)
            return file.parent / new_name
        return self._construir_ruta_destino(file)

    def _construir_ruta_destino(self, file: Path) -> Path:
        target_str = self.carpeta_destino
        if not target_str:
            raise ValueError("Target folder cannot be empty")

        ext_str = file.suffix.lower() if file.suffix else "varios"
        target_str = target_str.replace("{ext}", ext_str)
        raw = Path(target_str)

        if ".." in raw.parts:
            raise ValueError(f"Path traversal detected in target folder: {target_str}")

        if raw.is_absolute():
            target = raw.resolve()
        else:
            target = (file.parent / raw).resolve()

        if not target.is_absolute():
            raise ValueError("Invalid target path: must be absolute")

        return target / file.name

    def _aplicar_patron_renombre(self, file: Path) -> str:
        pattern = self.patron_renombre or file.stem
        ext = file.suffix.lower()
        new_name = pattern.replace("{name}", file.stem).replace("{ext}", ext)
        if not new_name.endswith(ext):
            new_name = f"{new_name}{ext}"
        return new_name
