from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from ...core.models.file_event import FileEvent, FileEventType
from ...core.ports.file_watcher import FileWatcher, FilterConfig

logger = logging.getLogger(__name__)


class ZormaEventHandler(FileSystemEventHandler):
    """
    Manejador de eventos de archivos para Watchdog que despacha eventos a un callback.
    """
    def __init__(self, callback: Callable[[FileEvent], None], filter_config: FilterConfig | None = None) -> None:
        """
        Inicializa el manejador.

        :param callback: Función a llamar cuando ocurre un evento de archivo.
        :param filter_config: Configuración de filtros opcional.
        """
        super().__init__()
        self.callback = callback
        self.filter_config = filter_config

    def on_created(self, event: FileSystemEvent) -> None:
        """
        Manejador para el evento de creación.
        """
        self._dispatch(event, FileEventType.CREATED)

    def on_modified(self, event: FileSystemEvent) -> None:
        """
        Manejador para el evento de modificación.
        """
        self._dispatch(event, FileEventType.MODIFIED)

    def on_moved(self, event: FileSystemEvent) -> None:
        """
        Manejador para el evento de movimiento.
        """
        self._dispatch(event, FileEventType.MOVED)

    def on_deleted(self, event: FileSystemEvent) -> None:
        """
        Manejador para el evento de eliminación.
        """
        self._dispatch(event, FileEventType.DELETED)

    def _dispatch(self, event: FileSystemEvent, event_type: FileEventType) -> None:
        """
        Despacha el evento al callback configurado.

        :param event: Evento original de Watchdog.
        :param event_type: Tipo de evento de Zorma.
        """
        if event.is_directory:
            return
        src = Path(str(event.src_path))
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

    def start(self, paths: list[Path], callback: Callable[[FileEvent], None]) -> None:
        """
        Inicia la observación de los directorios especificados.

        :param paths: Lista de rutas a observar.
        :param callback: Función a llamar cuando ocurre un evento.
        """
        handler = ZormaEventHandler(callback, self._filter_config)
        self._handlers.append(handler)
        for p in paths:
            resolved = p.resolve()
            if resolved.is_dir():
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

