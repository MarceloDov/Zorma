from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from watchdog.events import FileSystemEvent, PatternMatchingEventHandler
from watchdog.observers import Observer

from ...core.models.enums import TipoEvento
from ...core.models.evento_archivo import EventoArchivo

if TYPE_CHECKING:
    from collections.abc import Callable

    from ...core.models.filter_config import FilterConfig

logger = logging.getLogger(__name__)

DEBOUNCE_DELAY = 0.3


class DebounceCallback:
    def __init__(self, callback: Callable[[EventoArchivo], None], delay: float = DEBOUNCE_DELAY) -> None:
        self._callback = callback
        self._delay = delay
        self._timers: dict[Path, threading.Timer] = {}
        self._events: dict[Path, EventoArchivo] = {}
        self._lock = threading.Lock()

    def __call__(self, event: EventoArchivo) -> None:
        with self._lock:
            self._events[event.src_path] = event
            old = self._timers.pop(event.src_path, None)
            if old is not None:
                old.cancel()
            timer = threading.Timer(self._delay, self._disparar, args=[event.src_path])
            timer.daemon = True
            self._timers[event.src_path] = timer
            timer.start()

    def _disparar(self, src_path: Path) -> None:
        with self._lock:
            self._timers.pop(src_path, None)
            event = self._events.pop(src_path, None)
        if event is not None:
            try:
                self._callback(event)
            except Exception:
                logger.exception("Error en callback debounceado para %s", src_path)

    def vaciar_todo(self) -> None:
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
    def __init__(
        self,
        callback: Callable[[EventoArchivo], None],
        filter_config: FilterConfig | None = None,
        ignore_patterns: list[str] | None = None,
    ) -> None:
        super().__init__(ignore_directories=False, ignore_patterns=ignore_patterns, case_sensitive=False)
        self.callback = callback
        self.filter_config = filter_config

    def on_created(self, event: FileSystemEvent) -> None:
        self._despachar(event, TipoEvento.CREADO)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._despachar(event, TipoEvento.MODIFICADO)

    def on_moved(self, event: FileSystemEvent) -> None:
        self._despachar(event, TipoEvento.MOVIDO)

    def on_deleted(self, event: FileSystemEvent) -> None:
        self._despachar(event, TipoEvento.ELIMINADO)

    def _despachar(self, event: FileSystemEvent, event_type: TipoEvento) -> None:
        if event.is_directory:
            return
        src = Path(str(event.src_path))

        if self.filter_config and not self.filter_config.coincide(src):
            return
        dest: Path | None = None
        if event_type == TipoEvento.MOVIDO and hasattr(event, "dest_path"):
            dest = Path(str(event.dest_path))
        fe = EventoArchivo(tipo_evento=event_type, src_path=src, dest_path=dest)
        try:
            self.callback(fe)
        except Exception:
            logger.exception("Error processing file event: %s", src)


class WatchdogFileWatcher:
    def __init__(self) -> None:
        self._observer: Observer | None = None # type: ignore
        self._handlers: list[ZormaEventHandler] = []
        self._filter_config: FilterConfig | None = None
        self._debounced: DebounceCallback | None = None

    def iniciar(
        self, paths: list[Path], callback: Callable[[EventoArchivo], None], excluded_patterns: list[str] | None = None
    ) -> None:
        if self._observer is not None:
            self.detener()

        self._observer = Observer()
        self._handlers = []
        self._debounced = DebounceCallback(callback)

        handler = ZormaEventHandler(self._debounced, self._filter_config, ignore_patterns=excluded_patterns)
        self._handlers.append(handler)
        for p in paths:
            resolved = p.resolve()
            if resolved.is_dir():
                self._observer.schedule(handler, str(resolved), recursive=True)
                logger.info("Watching directory: %s", resolved)
        self._observer.start()

    def detener(self) -> None:
        if self._debounced is not None:
            self._debounced.vaciar_todo()
            self._debounced = None
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None

    def esta_activo(self) -> bool:
        return self._observer is not None and self._observer.is_alive()

    def actualizar_filtro(self, filter_config: FilterConfig | None) -> None:
        self._filter_config = filter_config
        for handler in self._handlers:
            handler.filter_config = filter_config
