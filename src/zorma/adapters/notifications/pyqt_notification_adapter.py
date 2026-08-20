"""
Adaptador de notificaciones para PyQt.
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QSystemTrayIcon

from ...core.models.enums import UrgenciaNotificacion


class PyQtNotificationAdapter(QObject):
    """
    Implementación del servicio de notificaciones utilizando PyQt6 QSystemTrayIcon.
    """

    _notification_signal = pyqtSignal(str, str, int, int)

    _tray_icon: QSystemTrayIcon | None
    _enabled: bool

    def __init__(self, tray_icon: QSystemTrayIcon | None = None) -> None:
        """
        Inicializa el adaptador con un icono de bandeja opcional.
        """
        super().__init__()
        self._tray_icon = tray_icon
        self._enabled = True
        self._notification_signal.connect(self._mostrar_mensaje)

    def establecer_icono_bandeja(self, tray_icon: QSystemTrayIcon) -> None:
        """
        Establece o actualiza el icono de la bandeja del sistema.
        """
        self._tray_icon = tray_icon

    def notificar(
        self,
        title: str,
        message: str,
        urgency: UrgenciaNotificacion = UrgenciaNotificacion.NORMAL,
    ) -> None:
        """
        Envía una notificación al sistema.
        """
        if not self._enabled or self._tray_icon is None:
            return

        icon_map = {
            UrgenciaNotificacion.BAJA: QSystemTrayIcon.MessageIcon.Information.value,
            UrgenciaNotificacion.NORMAL: QSystemTrayIcon.MessageIcon.Information.value,
            UrgenciaNotificacion.CRITICA: QSystemTrayIcon.MessageIcon.Critical.value,
        }
        duration = 3000 if urgency == UrgenciaNotificacion.BAJA else 5000
        icon_val = icon_map.get(urgency, QSystemTrayIcon.MessageIcon.Information.value)
        self._notification_signal.emit(title, message, icon_val, duration)

    def _mostrar_mensaje(self, title: str, message: str, icon_val: int, duration: int) -> None:
        if self._tray_icon:
            self._tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon(icon_val), duration)

    def configurar(self, enabled: bool) -> None:
        """
        Configura el estado de las notificaciones.

        Args:
            enabled: Habilita o deshabilita las notificaciones.
        """
        self._enabled = enabled
