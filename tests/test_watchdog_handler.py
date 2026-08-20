from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from watchdog.events import DirCreatedEvent, FileDeletedEvent, FileModifiedEvent, FileMovedEvent

from zorma.adapters.watcher.vigilante_watchdog import ManejadorEventosZorma
from zorma.core.models.configuracion_filtro import ConfiguracionFiltro

if TYPE_CHECKING:
    from zorma.core.models.evento_archivo import EventoArchivo


class TestZormaEventHandler:
    def test_on_created(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        callback = MagicMock()
        handler = ManejadorEventosZorma(callback)
        handler.on_created(FileModifiedEvent(str(f)))
        callback.assert_called_once()
        event: EventoArchivo = callback.call_args[0][0]
        assert event.tipo_evento.value == "created"
        assert event.src_path == f

    def test_on_modified(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        callback = MagicMock()
        handler = ManejadorEventosZorma(callback)
        handler.on_modified(FileModifiedEvent(str(f)))
        callback.assert_called_once()

    def test_on_moved(self, tmp_path: Path) -> None:
        src = tmp_path / "test.txt"
        dst = tmp_path / "renamed.txt"
        src.write_text("hello")
        callback = MagicMock()
        handler = ManejadorEventosZorma(callback)
        handler.on_moved(FileMovedEvent(str(src), str(dst)))
        callback.assert_called_once()
        event: EventoArchivo = callback.call_args[0][0]
        assert event.tipo_evento.value == "moved"
        assert event.dest_path == dst

    def test_on_deleted(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        callback = MagicMock()
        handler = ManejadorEventosZorma(callback)
        handler.on_deleted(FileDeletedEvent(str(f)))
        callback.assert_called_once()

    def test_ignores_directory_events(self, tmp_path: Path) -> None:
        d = tmp_path / "subdir"
        d.mkdir()
        callback = MagicMock()
        handler = ManejadorEventosZorma(callback)
        handler.on_created(DirCreatedEvent(str(d)))
        callback.assert_not_called()

    def test_filter_excludes_file(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        callback = MagicMock()
        cfg = ConfiguracionFiltro(include_extensions=[".pdf"])
        handler = ManejadorEventosZorma(callback, cfg)
        handler.on_created(FileModifiedEvent(str(f)))
        callback.assert_not_called()

    def test_filter_includes_file(self, tmp_path: Path) -> None:
        f = tmp_path / "test.pdf"
        f.write_text("hello")
        callback = MagicMock()
        cfg = ConfiguracionFiltro(include_extensions=[".pdf"])
        handler = ManejadorEventosZorma(callback, cfg)
        handler.on_modified(FileModifiedEvent(str(f)))
        callback.assert_called_once()
