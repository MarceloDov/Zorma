from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from ..models.file_event import FileEvent


@dataclass
class FilterConfig:
    """
    Configuración para filtrar archivos.

    Atributos:
        include_extensions: Conjunto de extensiones a incluir.
        exclude_extensions: Conjunto de extensiones a excluir.
        max_size: Tamaño máximo permitido.
        min_size: Tamaño mínimo permitido.
        include_hidden: Si incluir archivos ocultos.
        exclude_dirs: Lista de directorios a excluir.
    """
    include_extensions: set[str] | None = None
    exclude_extensions: set[str] | None = None
    max_size: int | None = None
    min_size: int | None = None
    include_hidden: bool = False
    exclude_dirs: list[str] = field(default_factory=list)

    def matches(self, file_path: Path) -> bool:
        """
        Verifica si el archivo cumple con la configuración de filtro.

        Args:
            file_path: Ruta del archivo a verificar.

        Returns:
            True si el archivo cumple los criterios, False en caso contrario.
        """
        if not self.include_hidden:
            if file_path.name.startswith("."):
                return False
        suffix = file_path.suffix.lower()
        if self.include_extensions is not None:
            if suffix not in self.include_extensions:
                return False
        if self.exclude_extensions is not None:
            if suffix in self.exclude_extensions:
                return False
        if self.min_size is not None or self.max_size is not None:
            try:
                sz = file_path.stat().st_size
                if self.min_size is not None and sz < self.min_size:
                    return False
                if self.max_size is not None and sz > self.max_size:
                    return False
            except OSError:
                return False
        if self.exclude_dirs:
            # Convertimos a minúsculas para comparación insensible a mayúsculas
            exclude_dirs_lower = [d.lower() for d in self.exclude_dirs]
            for part in file_path.parts:
                if part.lower() in exclude_dirs_lower:
                    return False
        return True


class FileWatcher(ABC):
    """Interfaz para el observador de archivos."""

    @abstractmethod
    def start(self, paths: list[Path], callback: Callable[[FileEvent], None], excluded_patterns: list[str] | None = None) -> None:
        """
        Inicia el observador de archivos.

        Args:
            paths: Lista de rutas a observar.
            callback: Función de devolución de llamada para eventos de archivo.
            excluded_patterns: Lista de patrones de archivos/carpetas a excluir.
        """
        ...

    @abstractmethod
    def stop(self) -> None:
        """Detiene el observador de archivos."""
        ...

    @abstractmethod
    def is_alive(self) -> bool:
        """
        Verifica si el observador está activo.

        Returns:
            True si el observador está activo, False en caso contrario.
        """
        ...

    @abstractmethod
    def update_filter(self, filter_config: FilterConfig | None) -> None:
        """
        Actualiza la configuración de filtro.

        Args:
            filter_config: Nueva configuración de filtro.
        """
        ...
