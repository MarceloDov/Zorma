from pathlib import Path
from unittest.mock import MagicMock, create_autospec

from zorma.adapters.persistence.zorma_repository import ZormaRepository
from zorma.core.models.enums import EstadoClasificacion, TipoOperacion
from zorma.core.models.pila_deshacer import PilaDeshacer
from zorma.core.models.resultado_clasificacion import ResultadoClasificacion
from zorma.core.services.gestor_deshacer import GestorDeshacer


class TestGestorDeshacer:
    def setup_method(self) -> None:
        self.repo = create_autospec(ZormaRepository, instance=True)
        self.manager = GestorDeshacer(self.repo)

    def _make_result(self, estado: EstadoClasificacion = EstadoClasificacion.EXITO) -> ResultadoClasificacion:
        return ResultadoClasificacion(
            nombre_archivo="test.txt",
            ruta_origen=Path("/orig/test.txt"),
            ruta_destino=Path("/dest/test.txt"),
            estado=estado,
        )

    def test_record_success(self) -> None:
        result = self._make_result()
        self.manager.record(result)
        self.repo.redo_clear.assert_called_once()
        self.repo.undo_push.assert_called_once()

    def test_record_non_success_ignored(self) -> None:
        result = self._make_result(EstadoClasificacion.ERROR)
        self.manager.record(result)
        self.repo.undo_push.assert_not_called()

    def test_can_undo(self) -> None:
        self.repo.undo_size.return_value = 1
        assert self.manager.can_undo()
        self.repo.undo_size.return_value = 0
        assert not self.manager.can_undo()

    def test_can_redo(self) -> None:
        self.repo.redo_size.return_value = 1
        assert self.manager.can_redo()
        self.repo.redo_size.return_value = 0
        assert not self.manager.can_redo()

    def test_undo_returns_none_when_empty(self) -> None:
        self.repo.undo_pop.return_value = None
        assert self.manager.undo() is None

    def test_undo_move_success(self, tmp_path: Path) -> None:
        orig = tmp_path / "orig" / "test.txt"
        orig.parent.mkdir(parents=True)
        dst = tmp_path / "dst" / "test.txt"
        dst.parent.mkdir(parents=True)
        dst.write_text("moved file")
        entry = PilaDeshacer(
            tipo_operacion=TipoOperacion.MOVER,
            _ruta_origen=orig,
            _ruta_destino=dst,
        )
        self.repo.undo_pop.return_value = entry

        result = self.manager.undo()
        assert result is not None
        assert result.estado == EstadoClasificacion.EXITO
        self.repo.undo_mark_reverted.assert_called_once_with(entry.id)
        self.repo.redo_push.assert_called_once()

    def test_undo_empty_stack(self) -> None:
        self.repo.undo_pop.return_value = None
        result = self.manager.undo()
        assert result is None

    def test_undo_callback_called(self, tmp_path: Path) -> None:
        orig = tmp_path / "orig" / "test.txt"
        orig.parent.mkdir(parents=True)
        dst = tmp_path / "dst" / "test.txt"
        dst.parent.mkdir(parents=True)
        dst.write_text("moved file")
        entry = PilaDeshacer(
            tipo_operacion=TipoOperacion.MOVER,
            _ruta_origen=orig,
            _ruta_destino=dst,
        )
        self.repo.undo_pop.return_value = entry
        callback = MagicMock()
        self.manager.set_result_callback(callback)
        self.manager.undo()
        callback.assert_called_once()

    def test_redo_delegates(self) -> None:
        entry = PilaDeshacer()
        self.repo.redo_pop.return_value = entry
        self.manager.redo()
        self.repo.redo_pop.assert_called_once()

    def test_redo_empty(self) -> None:
        self.repo.redo_pop.return_value = None
        assert self.manager.redo() is None
