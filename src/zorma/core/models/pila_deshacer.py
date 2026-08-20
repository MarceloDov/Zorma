from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .enums import TipoOperacion

logger = logging.getLogger(__name__)


@dataclass
class PilaDeshacer:
    id: str = field(default_factory=lambda: uuid4().hex)
    id_registro: str = ""
    tipo_operacion: TipoOperacion = TipoOperacion.MOVER
    estado_serializado: dict[str, Any] = field(default_factory=dict)
    marca_tiempo: datetime = field(default_factory=lambda: datetime.now(UTC))
    revertido: bool = False

    _ruta_origen: Path = field(default_factory=Path)
    _ruta_destino: Path = field(default_factory=Path)

    def revertir(self) -> bool:
        if self.revertido:
            return False
        src = self._ruta_destino
        dst = self._ruta_origen
        if not src.exists():
            logger.warning("Cannot undo: file not found: %s", src)
            return False
        try:
            if self.tipo_operacion in (TipoOperacion.MOVER, TipoOperacion.RENOMBRAR):
                shutil.move(str(src), str(dst))
            elif self.tipo_operacion == TipoOperacion.COPIAR:
                src.unlink()
            self.revertido = True
            return True
        except OSError as e:
            logger.error("Error reverting %s: %s", src, e)
            return False


