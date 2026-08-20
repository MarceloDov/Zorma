from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from .archivo import Archivo
from .enums import TipoEvento


@dataclass
class EventoArchivo:
    tipo_evento: TipoEvento
    src_path: Path
    dest_path: Path | None = None
    marca_tiempo: datetime = field(default_factory=lambda: datetime.now(UTC))

    def obtener_archivo(self) -> Archivo:
        return Archivo(_ruta_completa=self.src_path)


