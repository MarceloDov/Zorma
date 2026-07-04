from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.rule import Rule, RuleAction, RuleGroup


class RuleRepository(ABC):
    """Interfaz para el repositorio de reglas."""

    @abstractmethod
    def get_all(self) -> list[Rule]:
        """
        Obtiene todas las reglas.

        Returns:
            Lista de todas las reglas.
        """
        ...

    @abstractmethod
    def get_by_id(self, rule_id: str) -> Rule | None:
        """
        Obtiene una regla por su ID.

        Args:
            rule_id: ID de la regla.

        Returns:
            La regla encontrada o None.
        """
        ...

    @abstractmethod
    def get_by_group(self, group_id: str) -> list[Rule]:
        """
        Obtiene reglas por grupo.

        Args:
            group_id: ID del grupo.

        Returns:
            Lista de reglas en el grupo.
        """
        ...

    @abstractmethod
    def save(self, rule: Rule) -> None:
        """
        Guarda una regla.

        Args:
            rule: La regla a guardar.
        """
        ...

    @abstractmethod
    def delete(self, rule_id: str) -> None:
        """
        Elimina una regla por su ID.

        Args:
            rule_id: ID de la regla a eliminar.
        """
        ...

    @abstractmethod
    def get_groups(self) -> list[RuleGroup]:
        """
        Obtiene todos los grupos de reglas.

        Returns:
            Lista de grupos de reglas.
        """
        ...

    @abstractmethod
    def save_group(self, group: RuleGroup) -> None:
        """
        Guarda un grupo de reglas.

        Args:
            group: El grupo a guardar.
        """
        ...

    @abstractmethod
    def get_actions_for_rule(self, rule_id: str) -> list[RuleAction]:
        """
        Obtiene acciones para una regla.

        Args:
            rule_id: ID de la regla.

        Returns:
            Lista de acciones para la regla.
        """
        ...

    @abstractmethod
    def save_action(self, action: RuleAction) -> None:
        """
        Guarda una acción.

        Args:
            action: La acción a guardar.
        """
        ...

    @abstractmethod
    def delete_group(self, group_id: str) -> None:
        """
        Elimina un grupo de reglas.

        Args:
            group_id: ID del grupo a eliminar.
        """
        ...
