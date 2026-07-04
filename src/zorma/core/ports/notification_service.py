from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum


class NotificationUrgency(str, Enum):
    """Niveles de urgencia para las notificaciones."""
    LOW = "low"
    NORMAL = "normal"
    CRITICAL = "critical"


class NotificationService(ABC):
    """Interfaz para el servicio de notificaciones."""

    @abstractmethod
    def notify(
        self,
        title: str,
        message: str,
        urgency: NotificationUrgency = NotificationUrgency.NORMAL,
    ) -> None:
        """
        Envía una notificación.

        Args:
            title: Título de la notificación.
            message: Mensaje de la notificación.
            urgency: Nivel de urgencia de la notificación.
        """
        ...

    @abstractmethod
    def configure(self, enabled: bool, sound: bool) -> None:
        """
        Configura el servicio de notificaciones.

        Args:
            enabled: Si las notificaciones están habilitadas.
            sound: Si el sonido está habilitado.
        """
        ...
