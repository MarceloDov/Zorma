from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QPropertyAnimation, Qt
from PyQt6.QtGui import QAction, QCloseEvent, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from ..adapters.notifications.pyqt_notification_adapter import PyQtNotificationAdapter
from ..adapters.persistence.zorma_repository import ZormaRepository
from ..config.settings import APP_NAME, ICONS_DIR
from ..core.services.undo_manager import UndoManager
from ..core.services.watcher_service import WatcherService
from .dashboard.dashboard_view import DashboardView
from .history.history_view import HistoryView
from .rules.rules_view import RulesView
from .settings.settings_view import SettingsView
from .shared.styles import COLORS, build_qss, set_theme
from .shared.toast import show_toast
from .shared.widgets import SidebarButton


class MainWindow(QMainWindow):
    def __init__(
        self,
        data_dir: Optional[Path] = None,
        watcher_service: Optional[WatcherService] = None,
        rule_repository: Optional[ZormaRepository] = None,
        undo_manager: Optional[UndoManager] = None,
    ) -> None:
        super().__init__()
        self._data_dir = data_dir or Path.home() / ".zorma"
        self._watcher_service = watcher_service
        self._rule_repository = rule_repository
        self._undo_manager = undo_manager
        self._status_label: Optional[QLabel] = None
        self._tray_icon: Optional[QSystemTrayIcon] = None
        self._dashboard_view: Optional[DashboardView] = None
        self._settings_view: Optional[SettingsView] = None
        self._theme_btn: Optional[QPushButton] = None
        self._nav_anim: Optional[QPropertyAnimation] = None

        self._theme = self._rule_repository.get_theme() if self._rule_repository else "dark"
        if self._theme == "light":
            set_theme("light")
            app = QApplication.instance()
            if app is not None:
                app.setStyleSheet(build_qss())

        self._setup_ui()
        self._setup_shortcuts()
        self._setup_tray()
        icon_path = ICONS_DIR / "app_icon.svg"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

    def _setup_ui(self) -> None:
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
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setObjectName("sidebar")
        return sidebar

    def _create_logo(self) -> QLabel:
        logo = QLabel(APP_NAME)
        logo.setObjectName("logo")
        return logo

    def _create_nav_items(self, layout: QVBoxLayout) -> None:
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
        self._status_label = QLabel("● Monitor detenido")
        self._status_label.setObjectName("status_label")
        return self._status_label

    def _init_views(self) -> None:
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
        content = QFrame()
        content.setObjectName("content")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        top_bar = QFrame()
        top_bar.setFixedHeight(36)
        top_bar.setObjectName("top_bar")
        bar_layout = QHBoxLayout(top_bar)
        bar_layout.setContentsMargins(0, 0, 8, 0)
        bar_layout.addStretch()

        self._theme_btn = QPushButton("☀" if self._theme == "light" else "☾")
        self._theme_btn.setFixedSize(30, 30)
        self._theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._theme_btn.setToolTip("Cambiar tema claro/oscuro")
        self._theme_btn.setAccessibleName("Cambiar tema")
        self._theme_btn.setObjectName("theme_btn")
        self._theme_btn.clicked.connect(self._toggle_theme)
        bar_layout.addWidget(self._theme_btn)
        content_layout.addWidget(top_bar)

        content_layout.addWidget(self._nav_stack, 1)
        return content

    def _setup_shortcuts(self) -> None:
        if self._undo_manager is not None:
            QShortcut(QKeySequence.StandardKey.Undo, self, self._undo_shortcut)
            QShortcut(QKeySequence.StandardKey.Redo, self, self._redo_shortcut)

        QShortcut(QKeySequence("Ctrl+N"), self, self._new_rule_shortcut)
        QShortcut(QKeySequence(QKeySequence.StandardKey.Close), self, self._ctrl_w_shortcut)
        QShortcut(QKeySequence("F5"), self, self._refresh_shortcut)

        for i in range(4):
            QShortcut(QKeySequence(f"Ctrl+{i+1}"), self, lambda checked, idx=i: self._navigate(idx))

    def _undo_shortcut(self) -> None:
        if self._undo_manager is not None:
            result = self._undo_manager.undo()
            if result is not None:
                show_toast("↩ Archivo restaurado exitosamente", COLORS["success"])

    def _redo_shortcut(self) -> None:
        if self._undo_manager is not None:
            result = self._undo_manager.redo()
            if result is not None:
                show_toast("↪ Archivo reclasificado exitosamente", COLORS["success"])

    def _new_rule_shortcut(self) -> None:
        self._navigate(1)
        self._rules_view._new_rule()

    def _ctrl_w_shortcut(self) -> None:
        self.close()

    def _refresh_shortcut(self) -> None:
        idx = self._nav_stack.currentIndex()
        if idx == 0:
            self._dashboard_view.run_scan()
        elif idx == 1:
            self._rules_view._load_rules()

    def _setup_tray(self) -> None:
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
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_visibility()

    def closeEvent(self, event: QCloseEvent | None) -> None:
        if event is None:
            return
        if self._tray_icon is not None and self._tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            event.accept()

    def _navigate(self, index: int) -> None:
        if self._nav_stack.currentIndex() == index:
            return

        for i, btn in enumerate(self._nav_buttons):
            btn.set_active(i == index)

        widget = self._nav_stack.widget(index)
        if widget is not None:
            old_effect = widget.graphicsEffect()
            if old_effect is not None:
                widget.setGraphicsEffect(None)
            effect = QGraphicsOpacityEffect(widget)
            effect.setOpacity(0.0)
            widget.setGraphicsEffect(effect)

            self._nav_stack.setCurrentIndex(index)
            
            # Ensure the widget is active and visible
            widget.show()
            widget.raise_()
            widget.update()

            self._nav_anim = QPropertyAnimation(effect, b"opacity")
            self._nav_anim.setDuration(150)
            self._nav_anim.setStartValue(0.0)
            self._nav_anim.setEndValue(1.0)
            self._nav_anim.start()

    def _on_watcher_status(self, text: str, color: str) -> None:
        if self._status_label is not None:
            self._status_label.setText(text)
            self._status_label.setStyleSheet(f"color: {color};")

    def _on_theme_changed(self, theme: str) -> None:
        if self._theme_btn is not None:
            self._theme_btn.setText("☀" if theme == "light" else "☾")

    def _toggle_theme(self) -> None:
        new = "light" if self._theme == "dark" else "dark"
        self._theme = new
        set_theme(new)
        
        # Actualización global: volvemos a aplicar QSS
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_qss())
            
        if self._rule_repository:
            self._rule_repository.set_theme(new)
        self._on_theme_changed(new)
        
        # Refrescar UI si es necesario (ej. pollish)
        self.style().unpolish(self)
        self.style().polish(self)

