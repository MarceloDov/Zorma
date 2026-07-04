from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path


class FileEventType(str, Enum):
    """Define los tipos de eventos de archivo soportados."""
    CREATED = "created"
    MODIFIED = "modified"
    MOVED = "moved"
    DELETED = "deleted"


@dataclass
class FileEvent:
    """Representa un evento ocurrido sobre un archivo en el sistema de archivos."""
    src_path: Path
    event_type: FileEventType
    timestamp: datetime = field(default_factory=datetime.now)
    is_directory: bool = False
    dest_path: Path | None = None

    @property
    def file_name(self) -> str:
        """Retorna el nombre del archivo asociado al evento."""
        return self.src_path.name

    @property
    def extension(self) -> str:
        """Retorna la extensión del archivo en minúsculas."""
        return self.src_path.suffix.lower()

    @property
    def size(self) -> int:
        """Retorna el tamaño del archivo en bytes."""
        try:
            return self.src_path.stat().st_size
        except OSError:
            return 0
