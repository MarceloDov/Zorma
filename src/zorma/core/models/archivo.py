from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class Archivo:
    _ruta_completa: Path = field(default_factory=Path)
    _nombre: str = ""
    _extension: str = ""
    _tamanio_bytes: int = 0
    _fecha_creacion: datetime = field(default_factory=lambda: datetime.now(UTC))
    _fecha_modificacion: datetime = field(default_factory=lambda: datetime.now(UTC))
    _es_oculto: bool = False

    def __post_init__(self):
        if not self._nombre:
            self._nombre = self._ruta_completa.stem
        if not self._extension:
            self._extension = self._ruta_completa.suffix.lower()

    def obtener_nombre(self) -> str:
        return self._nombre

    def establecer_nombre(self, nombre: str) -> None:
        self._nombre = nombre

    def validar_nombre(self) -> bool:
        # TODO: Implementar validación real
        return len(self._nombre) > 0 and len(self._nombre) <= 255

    def obtener_extension(self) -> str:
        return self._extension.lower()

    def establecer_extension(self, extension: str) -> None:
        self._extension = extension.lower()

    def es_extension_valida(self) -> bool:
        return self._extension.startswith(".") or self._extension == ""

    def normalizar(self) -> str:
        ext = self._extension.lower()
        if ext and not ext.startswith("."):
            ext = "." + ext
        self._extension = ext
        return ext

    def obtener_ruta_completa(self) -> str:
        return str(self._ruta_completa)

    def obtener_tamanio(self) -> int:
        return self._tamanio_bytes

    def obtener_tamanio_legible(self) -> str:
        # TODO: Implementar formato humano
        return f"{self._tamanio_bytes} bytes"

    def existe(self) -> bool:
        return self._ruta_completa.exists()
