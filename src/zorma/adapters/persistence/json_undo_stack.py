from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ...core.models.rule import ActionType
from ...core.ports.undo_stack import UndoEntry, UndoStack


class JsonUndoStack(UndoStack):
    """
    Pila de deshacer (undo stack) que persiste en un archivo JSON.
    """
    def __init__(self, file_path: Path, max_size: int = 1000) -> None:
        """
        Inicializa la pila de deshacer.

        :param file_path: Ruta del archivo JSON donde persistir la pila.
        :param max_size: Tamaño máximo de la pila.
        """
        self._file_path = file_path
        self._max_size = max_size
        self._stack: list[UndoEntry] = []
        self._load()

    def push(self, entry: UndoEntry) -> None:
        """
        Añade una entrada a la pila.

        :param entry: Entrada a añadir.
        """
        self._stack.append(entry)
        if len(self._stack) > self._max_size:
            self._stack.pop(0)
        self._save()

    def pop(self) -> UndoEntry | None:
        """
        Elimina y retorna la última entrada de la pila.

        :return: Entrada eliminada o None si la pila está vacía.
        """
        if not self._stack:
            return None
        entry = self._stack.pop()
        self._save()
        return entry

    def peek(self) -> UndoEntry | None:
        """
        Retorna la última entrada de la pila sin eliminarla.

        :return: Última entrada o None si la pila está vacía.
        """
        return self._stack[-1] if self._stack else None

    def size(self) -> int:
        """
        Retorna el tamaño actual de la pila.

        :return: Tamaño de la pila.
        """
        return len(self._stack)

    def clear(self) -> None:
        """
        Limpia toda la pila.
        """
        self._stack.clear()
        self._save()

    def get_all(self) -> list[UndoEntry]:
        """
        Retorna todas las entradas de la pila en orden inverso (más reciente primero).

        :return: Lista de entradas.
        """
        return list(reversed(self._stack))

    def mark_reverted(self, entry_id: str) -> None:
        """
        Marca una entrada como revertida.

        :param entry_id: ID de la entrada a marcar.
        """
        for entry in self._stack:
            if entry.id == entry_id:
                entry.reverted = True
                self._save()
                return

    def remove_by_id(self, entry_id: str) -> UndoEntry | None:
        """
        Elimina y retorna una entrada específica por ID.

        :param entry_id: ID de la entrada a eliminar.
        :return: Entrada eliminada o None si no existe.
        """
        for i, entry in enumerate(self._stack):
            if entry.id == entry_id:
                removed = self._stack.pop(i)
                self._save()
                return removed
        return None

    def _serialize(self, entry: UndoEntry) -> dict[str, Any]:
        """
        Serializa una entrada de deshacer a un diccionario.

        :param entry: Entrada a serializar.
        :return: Diccionario serializado.
        """
        return {
            "id": entry.id,
            "file_name": entry.file_name,
            "source_path": str(entry.source_path),
            "destination_path": str(entry.destination_path),
            "action_type": entry.action_type.value,
            "rule_name": entry.rule_name,
            "timestamp": entry.timestamp.isoformat(),
            "reverted": entry.reverted,
        }

    def _deserialize(self, d: dict[str, Any]) -> UndoEntry:
        """
        Deserializa un diccionario a una entrada de deshacer.

        :param d: Diccionario con los datos.
        :return: Entrada de deshacer deserializada.
        """
        return UndoEntry(
            id=d["id"],
            file_name=d.get("file_name", ""),
            source_path=Path(d.get("source_path", "")),
            destination_path=Path(d.get("destination_path", "")),
            action_type=ActionType(d.get("action_type", ActionType.MOVE.value)),
            rule_name=d.get("rule_name", ""),
            timestamp=datetime.fromisoformat(d["timestamp"]) if "timestamp" in d else datetime.now(),
            reverted=d.get("reverted", False),
        )

    def _save(self) -> None:
        """
        Guarda el estado actual de la pila en el archivo JSON.
        """
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        data = [self._serialize(e) for e in self._stack]
        self._file_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def _load(self) -> None:
        """
        Carga el estado de la pila desde el archivo JSON.
        """
        if not self._file_path.exists():
            return
        try:
            data = json.loads(self._file_path.read_text(encoding="utf-8"))
            self._stack = [self._deserialize(d) for d in data]
        except (json.JSONDecodeError, KeyError):
            self._stack = []
