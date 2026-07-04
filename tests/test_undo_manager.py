from pathlib import Path
from unittest.mock import MagicMock, create_autospec

from zorma.core.models.classification import ClassificationResult, ClassificationStatus
from zorma.core.models.rule import ActionType, Rule, RuleAction
from zorma.core.ports.undo_stack import UndoStack
from zorma.core.services.action_executor import ActionExecutor
from zorma.core.services.undo_manager import UndoManager


class TestUndoManager:
    """
    Clase de pruebas para `UndoManager`.
    Verifica la gestión correcta de operaciones de deshacer, incluyendo el registro de resultados, la validación de capacidad de deshacer y la ejecución de la lógica de reversión (rollback).
    """
    def setup_method(self) -> None:
        """Configura el gestor antes de cada prueba, inicializando mocks para UndoStack y ActionExecutor."""
        self.stack = create_autospec(UndoStack)
        self.executor = create_autospec(ActionExecutor)
        self.manager = UndoManager(self.stack, self.executor)

    def _make_result(self, status: ClassificationStatus = ClassificationStatus.SUCCESS) -> ClassificationResult:
        """Helper para crear un resultado de clasificación dummy utilizado en pruebas."""
        rule = Rule(name="TestRule")
        action = RuleAction(action_type=ActionType.MOVE, target_folder="/tmp")
        return ClassificationResult(
            file_name="test.txt",
            source_path=Path("/src/test.txt"),
            destination_path=Path("/dst/test.txt"),
            rule_applied=rule,
            action_applied=action,
            status=status,
        )

    def test_record_success(self) -> None:
        """
        Prueba que un resultado exitoso sea registrado en la pila de deshacer.
        Escenario: Una operación exitosa debe activar el push en `UndoStack`.
        """
        result = self._make_result()
        self.manager.record(result)
        self.stack.push.assert_called_once()

    def test_record_non_success_ignored(self) -> None:
        """
        Prueba que un resultado no exitoso no sea registrado.
        Escenario: Si el estado es distinto de SUCCESS (ej. ERROR), no debe registrarse en `UndoStack`.
        """
        result = self._make_result(status=ClassificationStatus.ERROR)
        self.manager.record(result)
        self.stack.not_called()

    def test_can_undo(self) -> None:
        """
        Prueba que se pueda deshacer cuando hay elementos en la pila.
        Escenario: La pila reporta tamaño > 0, por lo que `can_undo()` debe ser `True`.
        """
        self.stack.size.return_value = 3
        assert self.manager.can_undo() is True

    def test_cannot_undo(self) -> None:
        """
        Prueba que no se pueda deshacer cuando la pila está vacía.
        Escenario: La pila reporta tamaño 0, por lo que `can_undo()` debe ser `False`.
        """
        self.stack.size.return_value = 0
        assert self.manager.can_undo() is False

    def test_undo_move_success(self, tmp_path: Path) -> None:
        """
        Prueba que la operación de deshacer una acción de movimiento funcione correctamente.
        Escenario: Se obtiene un elemento de la pila, se ejecuta el rollback del ejecutor y se marca como revertido.
        """
        from zorma.core.ports.undo_stack import UndoEntry

        src = tmp_path / "src" / "test.txt"
        dst = tmp_path / "dst" / "test.txt"
        dst.parent.mkdir(parents=True)
        dst.write_text("moved file")
        entry = UndoEntry(
            file_name="test.txt",
            source_path=src,
            destination_path=dst,
            action_type=ActionType.MOVE,
            rule_name="TestRule",
        )
        self.stack.pop.return_value = entry
        rollback_result = ClassificationResult(status=ClassificationStatus.SUCCESS)
        self.executor.rollback.return_value = rollback_result

        result = self.manager.undo()
        assert result is not None
        assert result.status == ClassificationStatus.SUCCESS
        self.stack.mark_reverted.assert_called_once_with(entry.id)

    def test_undo_empty_stack(self) -> None:
        """
        Prueba que la operación de deshacer retorne None si la pila está vacía.
        Escenario: Se llama a `undo()` sin elementos en la pila, esperando un valor nulo.
        """
        self.stack.pop.return_value = None
        result = self.manager.undo()
        assert result is None

    def test_undo_callback_called(self, tmp_path: Path) -> None:
        """
        Prueba que el callback registrado sea ejecutado tras una operación de deshacer exitosa.
        Escenario: Un callback configurado en `UndoManager` debe ser invocado al finalizar `undo()`.
        """
        from zorma.core.ports.undo_stack import UndoEntry

        src = tmp_path / "src" / "test.txt"
        dst = tmp_path / "dst" / "test.txt"
        dst.parent.mkdir(parents=True)
        dst.write_text("moved file")
        entry = UndoEntry(
            file_name="test.txt",
            source_path=src,
            destination_path=dst,
            action_type=ActionType.MOVE,
        )
        self.stack.pop.return_value = entry
        rollback_result = ClassificationResult(status=ClassificationStatus.SUCCESS)
        self.executor.rollback.return_value = rollback_result

        callback = MagicMock()
        self.manager.set_result_callback(callback)
        self.manager.undo()
        callback.assert_called_once()

    def test_get_undoable(self) -> None:
        """
        Prueba la obtención de todas las entradas disponibles para deshacer.
        Escenario: Verifica que `get_undoable()` recupere correctamente todas las entradas desde `UndoStack`.
        """
        entries = [MagicMock(), MagicMock()]
        self.stack.get_all.return_value = entries
        result = self.manager.get_undoable()
        assert result == entries
