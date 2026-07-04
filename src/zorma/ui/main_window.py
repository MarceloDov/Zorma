from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtGui import QAction, QCloseEvent, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from ..adapters.notifications.pyqt_notification_adapter import PyQtNotificationAdapter
from ..config.settings import APP_NAME, ICONS_DIR
from ..core.ports.rule_repository import RuleRepository
from ..core.services.undo_manager import UndoManager
from ..core.services.watcher_service import WatcherService
from .dashboard.dashboard_view import DashboardView
from .history.history_view import HistoryView
from .rules.rules_view import RulesView
from .settings.settings_view import SettingsView
from .shared.styles import COLORS
from .shared.toast import show_toast
from .shared.widgets import SidebarButton


class MainWindow(QMainWindow):
    """Ventana principal de la aplicación Zorma."""

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        watcher_service: Optional[WatcherService] = None,
        rule_repository: Optional[RuleRepository] = None,
        undo_manager: Optional[UndoManager] = None,
    ) -> None:
        """Inicializa la ventana principal.

        Args:
            data_dir: Directorio de datos.
            watcher_service: Servicio de monitorización.
            rule_repository: Repositorio de reglas.
            undo_manager: Gestor de deshacer.
        """
        super().__init__()
        self._data_dir = data_dir or Path.home() / ".zorma"
        self._watcher_service = watcher_service
        self._rule_repository = rule_repository
        self._undo_manager = undo_manager
        self._status_label: Optional[QLabel] = None
        self._tray_icon: Optional[QSystemTrayIcon] = None
        self._dashboard_view: Optional[DashboardView] = None
        self._settings_view: Optional[SettingsView] = None
        self._setup_ui()
        self._setup_shortcuts()
        self._setup_tray()
        icon_path = ICONS_DIR / "app_icon.svg"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

    def _setup_ui(self) -> None:
        """Configura la interfaz de usuario principal."""
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1024, 680)
        self.resize(1280, 800)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_sidebar())
        layout.addWidget(self._build_content(), 1)

    def _build_sidebar(self) -> QFrame:
        """Construye la barra lateral de la aplicación.

        Returns:
            QFrame: El frame de la barra lateral.
        """
        sidebar = self._create_sidebar_frame()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 20, 12, 20)
        sidebar_layout.setSpacing(4)

        sidebar_layout.addWidget(self._create_logo())

        self._init_views()
        self._nav_buttons: list[SidebarButton] = []
        self._nav_stack = QStackedWidget()
        self._nav_stack.addWidget(self._dashboard_view)
        self._nav_stack.addWidget(self._rules_view)
        self._nav_stack.addWidget(self._history_view)
        self._nav_stack.addWidget(self._settings_view)

        self._create_nav_items(sidebar_layout)

        sidebar_layout.addStretch()
        sidebar_layout.addWidget(self._create_status_label())

        self._nav_buttons[0].set_active(True)

        return sidebar

    def _create_sidebar_frame(self) -> QFrame:
        """Crea el frame base para la barra lateral.

        Returns:
            QFrame: Frame configurado para la barra lateral.
        """
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet(
            f"background-color: {COLORS['sidebar']}; border-right: 1px solid {COLORS['border']};"
        )
        return sidebar

    def _create_logo(self) -> QLabel:
        """Crea el label del logo.

        Returns:
            QLabel: Label con el nombre de la aplicación.
        """
        logo = QLabel(APP_NAME)
        logo.setStyleSheet(
            f"color: {COLORS['text_bright']}; font-size: 22px; font-weight: 800; padding: 0 12px 20px 12px;"
        )
        return logo

    def _create_nav_items(self, layout: QVBoxLayout) -> None:
        """Crea y añade los botones de navegación al layout.

        Args:
            layout: Layout donde añadir los botones.
        """
        nav_items = [
            ("Inicio", "dashboard.svg"),
            ("Reglas", "rules.svg"),
            ("Historial", "history.svg"),
            ("Configuración", "settings.svg"),
        ]

        for i, (label, icon_name) in enumerate(nav_items):
            icon_path = ICONS_DIR / icon_name
            btn = SidebarButton(label, icon_path)
            btn.clicked.connect(lambda checked, idx=i: self._navigate(idx))
            self._nav_buttons.append(btn)
            layout.addWidget(btn)

    def _create_status_label(self) -> QLabel:
        """Crea el label de estado.

        Returns:
            QLabel: Label de estado configurado.
        """
        self._status_label = QLabel("● Monitor detenido")
        self._status_label.setStyleSheet(
            f"color: {COLORS['error']}; font-size: 12px; font-weight: 600; padding: 12px;"
        )
        return self._status_label

    def _init_views(self) -> None:
        """Inicializa las vistas de la aplicación."""
        self._rules_view = RulesView(self._data_dir, self._rule_repository)

        self._dashboard_view = DashboardView(
            self._data_dir, self._rule_repository, self._undo_manager
        )
        if self._watcher_service is not None:
            self._dashboard_view.set_watcher_service(self._watcher_service)
        self._dashboard_view.watcher_status_changed.connect(self._on_watcher_status)

        self._settings_view = SettingsView(self._data_dir)
        self._history_view = HistoryView(self._data_dir)

    def _build_content(self) -> QFrame:
        """Construye el área de contenido principal.

        Returns:
            QFrame: El frame del contenido.
        """
        content = QFrame()
        content.setStyleSheet(f"background-color: {COLORS['bg']};")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(self._nav_stack)
        return content

    def _setup_shortcuts(self) -> None:
        """Configura los atajos de teclado."""
        if self._undo_manager is not None:
            QShortcut(QKeySequence.StandardKey.Undo, self, self._undo_shortcut)

    def _undo_shortcut(self) -> None:
        """Manejador para el atajo de deshacer."""
        if self._undo_manager is not None:
            result = self._undo_manager.undo()
            if result is not None:
                show_toast("↩ Archivo restaurado exitosamente", COLORS["success"])

    def _setup_tray(self) -> None:
        """Configura el icono de la bandeja del sistema."""
        self._tray_icon = QSystemTrayIcon(self)
        self._tray_icon.setToolTip(APP_NAME)
        icon_path = ICONS_DIR / "tray_icon.svg"
        if icon_path.exists():
            self._tray_icon.setIcon(QIcon(str(icon_path)))

        tray_menu = QMenu(self)

        show_action = QAction("Mostrar/Ocultar", self)
        show_action.triggered.connect(self._toggle_visibility)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        quit_action = QAction("Salir", self)
        app = QApplication.instance()
        if app:
            quit_action.triggered.connect(app.quit)
        tray_menu.addAction(quit_action)

        self._tray_icon.setContextMenu(tray_menu)
        self._tray_icon.activated.connect(self._on_tray_activated)

        if self._settings_view is not None:
            adapter = PyQtNotificationAdapter(self._tray_icon)
            self._settings_view.set_notification_service(adapter)

        self._tray_icon.show()

    def _toggle_visibility(self) -> None:
        """Alterna la visibilidad de la ventana."""
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def _on_tray_activated(self, reason: int) -> None:
        """Manejador para la activación del icono de la bandeja.

        Args:
            reason: Motivo de la activación.
        """
        if reason == 3:
            self._toggle_visibility()

    def closeEvent(self, event: QCloseEvent | None) -> None:
        """Maneja el evento de cierre de la ventana.

        Args:
            event: El evento de cierre.
        """
        if event is None:
            return
        if self._tray_icon is not None and self._tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            event.accept()

    def _navigate(self, index: int) -> None:
        """Navega a la vista especificada.

        Args:
            index: Índice de la vista a mostrar.
        """
        for i, btn in enumerate(self._nav_buttons):
            btn.set_active(i == index)
        self._nav_stack.setCurrentIndex(index)

    def _on_watcher_status(self, text: str, color: str) -> None:
        """Actualiza el estado del monitor.

        Args:
            text: Texto del estado.
            color: Color del estado.
        """
        if self._status_label is not None:
            self._status_label.setText(text)
            self._status_label.setStyleSheet(
                f"color: {color}; font-size: 12px; font-weight: 600; padding: 12px;"
            )
