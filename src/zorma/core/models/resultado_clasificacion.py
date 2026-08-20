from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from .enums import EstadoClasificacion

if TYPE_CHECKING:
    from pathlib import Path

    from .accion_regla import AccionRegla
    from .regla import Regla


@dataclass
class ResultadoClasificacion:
    aplicada: bool = False
    regla_aplicada: Regla | None = None
    accion_aplicada: AccionRegla | None = None
    estado: EstadoClasificacion = EstadoClasificacion.SIN_REGLA
    mensaje_error: str = ""
    marca_tiempo: datetime = field(default_factory=lambda: datetime.now(UTC))
    nombre_archivo: str = ""
    ruta_origen: Path | None = None
    ruta_destino: Path | None = None
    sobrescribir: bool = False


