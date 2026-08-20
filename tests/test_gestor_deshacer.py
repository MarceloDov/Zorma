from pathlib import Path
from unittest.mock import MagicMock, create_autospec

from zorma.adapters.persistence.zorma_repository import ZormaRepository
from zorma.core.models.enums import EstadoClasificacion, TipoAccion
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
        self.manager.registrar(result)
        self.repo.limpiar_rehacer.assert_called_once()
        self.repo.apilar_deshacer.assert_called_once()

    def test_record_non_success_ignored(self) -> None:
        result = self._make_result(EstadoClasificacion.ERROR)
        self.manager.registrar(result)
        self.repo.apilar_deshacer.assert_not_called()

    def test_can_undo(self) -> None:
        self.repo.tamanio_deshacer.return_value = 1
        assert self.manager.puede_deshacer()
        self.repo.tamanio_deshacer.return_value = 0
        assert not self.manager.puede_deshacer()

    def test_can_redo(self) -> None:
        self.repo.tamanio_rehacer.return_value = 1
        assert self.manager.puede_rehacer()
        self.repo.tamanio_rehacer.return_value = 0
        assert not self.manager.puede_rehacer()

    def test_undo_returns_none_when_empty(self) -> None:
        self.repo.desapilar_deshacer.return_value = None
        assert self.manager.deshacer() is None

    def test_undo_move_success(self, tmp_path: Path) -> None:
        orig = tmp_path / "orig" / "test.txt"
        orig.parent.mkdir(parents=True)
        dst = tmp_path / "dst" / "test.txt"
        dst.parent.mkdir(parents=True)
        dst.write_text("moved file")
        entry = PilaDeshacer(
            tipo_operacion=TipoAccion.MOVER,
            _ruta_origen=orig,
            _ruta_destino=dst,
        )
        self.repo.desapilar_deshacer.return_value = entry

        result = self.manager.deshacer()
        assert result is not None
        assert result.estado == EstadoClasificacion.EXITO
        self.repo.marcar_deshacer_revertido.assert_called_once_with(entry.id)
        self.repo.apilar_rehacer.assert_called_once()

    def test_undo_empty_stack(self) -> None:
        self.repo.desapilar_deshacer.return_value = None
        result = self.manager.deshacer()
        assert result is None

    def test_undo_callback_called(self, tmp_path: Path) -> None:
        orig = tmp_path / "orig" / "test.txt"
        orig.parent.mkdir(parents=True)
        dst = tmp_path / "dst" / "test.txt"
        dst.parent.mkdir(parents=True)
        dst.write_text("moved file")
        entry = PilaDeshacer(
            tipo_operacion=TipoAccion.MOVER,
            _ruta_origen=orig,
            _ruta_destino=dst,
        )
        self.repo.desapilar_deshacer.return_value = entry
        callback = MagicMock()
        self.manager.establecer_callback_resultado(callback)
        self.manager.deshacer()
        callback.assert_called_once()

    def test_redo_delegates(self) -> None:
        entry = PilaDeshacer()
        self.repo.desapilar_rehacer.return_value = entry
        self.manager.rehacer()
        self.repo.desapilar_rehacer.assert_called_once()

    def test_redo_empty(self) -> None:
        self.repo.desapilar_rehacer.return_value = None
        assert self.manager.rehacer() is None
