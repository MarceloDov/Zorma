"""
Adaptador de notificaciones para PyQt.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import QSystemTrayIcon

from ...core.models.notification_urgency import NotificationUrgency


from PyQt6.QtCore import QObject, pyqtSignal

class PyQtNotificationAdapter(QObject):
    """
    Implementación del servicio de notificaciones utilizando PyQt6 QSystemTrayIcon.
    """
    _notification_signal = pyqtSignal(str, str, int, int)
    
    _tray_icon: Optional[QSystemTrayIcon]
    _enabled: bool
    _sound: bool

    def __init__(self, tray_icon: Optional[QSystemTrayIcon] = None) -> None:
        """
        Inicializa el adaptador con un icono de bandeja opcional.
        """
        super().__init__()
        self._tray_icon = tray_icon
        self._enabled = True
        self._sound = True
        self._notification_signal.connect(self._show_message)

    def set_tray_icon(self, tray_icon: QSystemTrayIcon) -> None:
        """
        Establece o actualiza el icono de la bandeja del sistema.
        """
        self._tray_icon = tray_icon

    def notify(
        self,
        title: str,
        message: str,
        urgency: NotificationUrgency = NotificationUrgency.NORMAL,
    ) -> None:
        """
        Envía una notificación al sistema.
        """
        if not self._enabled or self._tray_icon is None:
            return

        icon_map = {
            NotificationUrgency.LOW: QSystemTrayIcon.MessageIcon.Information.value,
            NotificationUrgency.NORMAL: QSystemTrayIcon.MessageIcon.Information.value,
            NotificationUrgency.CRITICAL: QSystemTrayIcon.MessageIcon.Critical.value,
        }
        duration = 3000 if urgency == NotificationUrgency.LOW else 5000
        icon_val = icon_map.get(urgency, QSystemTrayIcon.MessageIcon.Information.value)
        self._notification_signal.emit(title, message, icon_val, duration)

    def _show_message(self, title: str, message: str, icon_val: int, duration: int) -> None:
        if self._tray_icon:
            self._tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon(icon_val), duration)

    def configure(self, enabled: bool, sound: bool) -> None:
        """
        Configura el estado de las notificaciones.

        Args:
            enabled: Habilita o deshabilita las notificaciones.
            sound: Habilita o deshabilita el sonido de las notificaciones.
        """
        self._enabled = enabled
        self._sound = sound
