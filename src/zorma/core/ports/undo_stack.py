from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from ..models.rule import ActionType


@dataclass
class UndoEntry:
    """
    Entrada para el historial de acciones deshacer.

    Atributos:
        id: ID único de la entrada.
        file_name: Nombre del archivo.
        source_path: Ruta de origen.
        destination_path: Ruta de destino.
        action_type: Tipo de acción.
        rule_name: Nombre de la regla.
        timestamp: Marca de tiempo.
        reverted: Indica si la acción ha sido revertida.
    """
    id: str = field(default_factory=lambda: uuid4().hex)
    file_name: str = ""
    source_path: Path = field(default_factory=Path)
    destination_path: Path = field(default_factory=Path)
    action_type: ActionType = ActionType.MOVE
    rule_name: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    reverted: bool = False


class UndoStack(ABC):
    """Interfaz para la pila de acciones deshacer."""

    @abstractmethod
    def push(self, entry: UndoEntry) -> None:
        """
        Agrega una entrada a la pila.

        Args:
            entry: La entrada a agregar.
        """
        ...

    @abstractmethod
    def pop(self) -> UndoEntry | None:
        """
        Extrae la última entrada de la pila.

        Returns:
            La última entrada o None si la pila está vacía.
        """
        ...

    @abstractmethod
    def peek(self) -> UndoEntry | None:
        """
        Obtiene la última entrada de la pila sin extraerla.

        Returns:
            La última entrada o None si la pila está vacía.
        """
        ...

    @abstractmethod
    def size(self) -> int:
        """
        Obtiene el tamaño de la pila.

        Returns:
            El tamaño de la pila.
        """
        ...

    @abstractmethod
    def clear(self) -> None:
        """Limpia la pila."""
        ...

    @abstractmethod
    def get_all(self) -> list[UndoEntry]:
        """
        Obtiene todas las entradas.

        Returns:
            Lista de todas las entradas.
        """
        ...

    @abstractmethod
    def mark_reverted(self, entry_id: str) -> None:
        """
        Marca una entrada como revertida.

        Args:
            entry_id: ID de la entrada a marcar.
        """
        ...

    @abstractmethod
    def remove_by_id(self, entry_id: str) -> UndoEntry | None:
        """
        Elimina una entrada por su ID.

        Args:
            entry_id: ID de la entrada a eliminar.

        Returns:
            La entrada eliminada o None.
        """
        ...
