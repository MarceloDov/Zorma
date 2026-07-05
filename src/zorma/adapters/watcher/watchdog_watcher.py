from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from watchdog.events import FileSystemEvent, PatternMatchingEventHandler
from watchdog.observers import Observer

from ...core.models.file_event import FileEvent, FileEventType
from ...core.ports.file_watcher import FileWatcher, FilterConfig

logger = logging.getLogger(__name__)


class ZormaEventHandler(PatternMatchingEventHandler):
    """
    Manejador de eventos de archivos para Watchdog que despacha eventos a un callback.
    """
    def __init__(
        self, 
        callback: Callable[[FileEvent], None], 
        filter_config: FilterConfig | None = None,
        ignore_patterns: list[str] | None = None
    ) -> None:
        """
        Inicializa el manejador.

        :param callback: Función a llamar cuando ocurre un evento de archivo.
        :param filter_config: Configuración de filtros opcional.
        :param ignore_patterns: Patrones de archivos/carpetas a ignorar.
        """
        super().__init__(ignore_directories=False, ignore_patterns=ignore_patterns, case_sensitive=False)
        self.callback = callback
        self.filter_config = filter_config

    def on_created(self, event: FileSystemEvent) -> None:
        self._dispatch(event, FileEventType.CREATED)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._dispatch(event, FileEventType.MODIFIED)

    def on_moved(self, event: FileSystemEvent) -> None:
        self._dispatch(event, FileEventType.MOVED)

    def on_deleted(self, event: FileSystemEvent) -> None:
        self._dispatch(event, FileEventType.DELETED)

    def _dispatch(self, event: FileSystemEvent, event_type: FileEventType) -> None:
        if event.is_directory:
            return
        src = Path(str(event.src_path))
        
        # Filtro de seguridad adicional para rutas recursivas
        if any(part.startswith("Archivos ") for part in src.parts):
            return

        if self.filter_config and not self.filter_config.matches(src):
            return
        dest: Path | None = None
        if event_type == FileEventType.MOVED and hasattr(event, "dest_path"):
            dest = Path(str(event.dest_path))
        fe = FileEvent(src_path=src, event_type=event_type, dest_path=dest)
        try:
            self.callback(fe)
        except Exception:
            logger.exception("Error processing file event: %s", src)


class WatchdogFileWatcher(FileWatcher):
    """
    Implementación de FileWatcher utilizando Watchdog.
    """
    def __init__(self) -> None:
        """
        Inicializa el observador Watchdog.
        """
        self._observer = Observer()
        self._handlers: list[ZormaEventHandler] = []
        self._filter_config: FilterConfig | None = None

    def start(
        self, 
        paths: list[Path], 
        callback: Callable[[FileEvent], None], 
        excluded_patterns: list[str] | None = None
    ) -> None:
        """
        Inicia la observación de los directorios especificados.

        :param paths: Lista de rutas a observar.
        :param callback: Función a llamar cuando ocurre un evento.
        :param excluded_patterns: Lista de patrones de archivos/carpetas a excluir.
        """
        # Usar PatternMatchingEventHandler para manejar exclusiones
        handler = ZormaEventHandler(callback, self._filter_config, ignore_patterns=excluded_patterns)
        self._handlers.append(handler)
        for p in paths:
            resolved = p.resolve()
            if resolved.is_dir():
                # Nota: Cuando usamos PatternMatchingEventHandler, no necesitamos 
                # filtrar explícitamente en el manejador, pero mantenemos el 
                # filtro de seguridad por precaución.
                self._observer.schedule(handler, str(resolved), recursive=True)
                logger.info("Watching directory: %s", resolved)
        self._observer.start()

    def stop(self) -> None:
        """
        Detiene la observación.
        """
        self._observer.stop()
        self._observer.join(timeout=5)

    def is_alive(self) -> bool:
        """
        Retorna True si el observador está activo.

        :return: True si está activo, False en caso contrario.
        """
        return self._observer.is_alive()

    def update_filter(self, filter_config: FilterConfig | None) -> None:
        """
        Actualiza la configuración de filtros.

        :param filter_config: Nueva configuración de filtros.
        """
        self._filter_config = filter_config
        for handler in self._handlers:
            handler.filter_config = filter_config

