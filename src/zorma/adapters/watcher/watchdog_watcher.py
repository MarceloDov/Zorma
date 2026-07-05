from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from pathlib import Path

from watchdog.events import FileSystemEvent, PatternMatchingEventHandler
from watchdog.observers import Observer

from ...core.models.file_event import FileEvent, FileEventType
from ...core.models.filter_config import FilterConfig
logger = logging.getLogger(__name__)

DEBOUNCE_DELAY = 0.3


class DebounceCallback:
    """Envuelve un callback para debouncear eventos rápidos sucesivos del mismo archivo.

    Acumula eventos por src_path y reinicia el temporizador cada vez que llega
    uno nuevo para la misma ruta. Solo el último evento se entrega tras
    DEBOUNCE_DELAY segundos de silencio.
    """
    def __init__(self, callback: Callable[[FileEvent], None], delay: float = DEBOUNCE_DELAY) -> None:
        self._callback = callback
        self._delay = delay
        self._timers: dict[Path, threading.Timer] = {}
        self._events: dict[Path, FileEvent] = {}
        self._lock = threading.Lock()

    def __call__(self, event: FileEvent) -> None:
        with self._lock:
            self._events[event.src_path] = event
            old = self._timers.pop(event.src_path, None)
            if old is not None:
                old.cancel()
            timer = threading.Timer(self._delay, self._fire, args=[event.src_path])
            timer.daemon = True
            self._timers[event.src_path] = timer
            timer.start()

    def _fire(self, src_path: Path) -> None:
        with self._lock:
            self._timers.pop(src_path, None)
            event = self._events.pop(src_path, None)
        if event is not None:
            try:
                self._callback(event)
            except Exception:
                logger.exception("Error en callback debounceado para %s", src_path)

    def flush_all(self) -> None:
        """Procesa inmediatamente todos los eventos pendientes y cancela temporizadores."""
        with self._lock:
            timers = dict(self._timers)
            events = dict(self._events)
            self._timers.clear()
            self._events.clear()
        for timer in timers.values():
            timer.cancel()
        for event in events.values():
            try:
                self._callback(event)
            except Exception:
                logger.exception("Error al vaciar evento debounceado")


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


class WatchdogFileWatcher:
    """
    Implementación de FileWatcher utilizando Watchdog.
    """
    def __init__(self) -> None:
        """
        Inicializa el observador Watchdog.
        """
        self._observer: Observer | None = None
        self._handlers: list[ZormaEventHandler] = []
        self._filter_config: FilterConfig | None = None
        self._debounced: DebounceCallback | None = None

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
        # Limpiar observador previo si existe
        if self._observer is not None:
            self.stop()

        self._observer = Observer()
        self._handlers = [] # Limpiar handlers
        self._debounced = DebounceCallback(callback)

        # Usar PatternMatchingEventHandler para manejar exclusiones
        handler = ZormaEventHandler(self._debounced, self._filter_config, ignore_patterns=excluded_patterns)
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
        if self._debounced is not None:
            self._debounced.flush_all()
            self._debounced = None
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None

    def is_alive(self) -> bool:
        """
        Retorna True si el observador está activo.

        :return: True si está activo, False en caso contrario.
        """
        return self._observer is not None and self._observer.is_alive()

    def update_filter(self, filter_config: FilterConfig | None) -> None:
        """
        Actualiza la configuración de filtros.

        :param filter_config: Nueva configuración de filtros.
        """
        self._filter_config = filter_config
        for handler in self._handlers:
            handler.filter_config = filter_config

