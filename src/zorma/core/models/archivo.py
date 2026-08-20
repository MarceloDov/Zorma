from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from .extension import Extension
from .nombre import Nombre


@dataclass
class Archivo(Nombre, Extension):
    _ruta_completa: Path = field(default_factory=Path)
    _tamanio_bytes: int = 0
    _fecha_creacion: datetime = field(default_factory=lambda: datetime.now(UTC))
    _fecha_modificacion: datetime = field(default_factory=lambda: datetime.now(UTC))
    _es_oculto: bool = False

    def __post_init__(self):
        # Inicializar Nombre y Extension desde la ruta si no se proporcionaron
        if not self._nombre:
            self._nombre = self._ruta_completa.stem
        if not self._extension:
            self._extension = self._ruta_completa.suffix.lower()

    def obtener_ruta_completa(self) -> str:
        return str(self._ruta_completa)

    def obtener_tamanio(self) -> int:
        return self._tamanio_bytes

    def obtener_tamanio_legible(self) -> str:
        # TODO: Implementar formato humano
        return f"{self._tamanio_bytes} bytes"

    def existe(self) -> bool:
        return self._ruta_completa.exists()
