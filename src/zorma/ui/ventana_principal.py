from __future__ import annotations

from pathlib import Path

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

from ..adapters.notifications.adaptador_notificacion_pyqt import AdaptadorNotificacionPyQt
from ..adapters.persistence.zorma_repository import ZormaRepository
from ..config.settings import APP_NAME, ICONS_DIR
from ..core.services.gestor_deshacer import GestorDeshacer
from ..core.services.servicio_clasificacion import ServicioClasificacion
from .dashboard.vista_inicio import VistaInicio
from .history.vista_historial import VistaHistorial
from .rules.vista_reglas import VistaReglas
from .settings.vista_configuracion import VistaConfiguracion
from .shared.aviso import mostrar_aviso
from .shared.styles import COLORS, construir_qss, establecer_tema
from .shared.widgets import BotonBarraLateral


class VentanaPrincipal(QMainWindow):
    def __init__(
        self,
        data_dir: Path | None = None,
        watcher_service: ServicioClasificacion | None = None,
        rule_repository: ZormaRepository | None = None,
        gestor_deshacer: GestorDeshacer | None = None,
    ) -> None:
        super().__init__()
        self._data_dir = data_dir or Path.home() / ".zorma"
        self._watcher_service = watcher_service
        self._rule_repository = rule_repository
        self._gestor_deshacer = gestor_deshacer
        self._status_label: QLabel | None = None
        self._tray_icon: QSystemTrayIcon | None = None
        self._dashboard_view: VistaInicio | None = None
        self._settings_view: VistaConfiguracion | None = None
        self._theme_btn: QPushButton | None = None
        self._nav_anim: QPropertyAnimation | None = None

        self._theme = self._rule_repository.obtener_tema() if self._rule_repository else "dark"
        if self._theme == "light":
            establecer_tema("light")
            app = QApplication.instance()
            if app is not None:
                app.setStyleSheet(construir_qss())

        self._configurar_ui()
        self._configurar_atajos()
        self._configurar_bandeja()
        icon_path = ICONS_DIR / "app_icon.svg"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

    def _configurar_ui(self) -> None:
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1024, 680)
        self.resize(1280, 800)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._construir_barra_lateral())
        layout.addWidget(self._construir_contenido(), 1)

    def _construir_barra_lateral(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 20, 12, 20)
        sidebar_layout.setSpacing(4)

        logo = QLabel(APP_NAME)
        logo.setObjectName("logo")
        sidebar_layout.addWidget(logo)

        self._inicializar_vistas()
        self._nav_buttons: list[BotonBarraLateral] = []
        self._nav_stack = QStackedWidget()
        self._nav_stack.addWidget(self._dashboard_view)
        self._nav_stack.addWidget(self._rules_view)
        self._nav_stack.addWidget(self._history_view)
        self._nav_stack.addWidget(self._settings_view)

        self._crear_items_navegacion(sidebar_layout)

        sidebar_layout.addStretch()

        self._status_label = QLabel("● Monitor detenido")
        self._status_label.setObjectName("status_label")
        sidebar_layout.addWidget(self._status_label)

        self._nav_buttons[0].establecer_activo(True)

        return sidebar

    def _crear_items_navegacion(self, layout: QVBoxLayout) -> None:
        nav_items = [
            ("Inicio", "dashboard.svg"),
            ("Reglas", "rules.svg"),
            ("Historial", "history.svg"),
            ("Configuración", "settings.svg"),
        ]

        for i, (label, icon_name) in enumerate(nav_items):
            icon_path = ICONS_DIR / icon_name
            btn = BotonBarraLateral(label, icon_path)
            btn.clicked.connect(lambda checked, idx=i: self._navegar(idx))
            self._nav_buttons.append(btn)
            layout.addWidget(btn)

    def _inicializar_vistas(self) -> None:
        self._rules_view = VistaReglas(self._data_dir, self._rule_repository)

        self._dashboard_view = VistaInicio(self._data_dir, self._rule_repository, self._gestor_deshacer)
        if self._watcher_service is not None:
            self._dashboard_view.establecer_servicio_vigilancia(self._watcher_service)
        self._dashboard_view.watcher_status_changed.connect(self._al_estado_vigilancia)
        self._dashboard_view.navigate_requested.connect(self._navegar)

        self._settings_view = VistaConfiguracion(self._data_dir)
        self._history_view = VistaHistorial(self._data_dir, self._rule_repository)

    def _construir_contenido(self) -> QFrame:
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
        self._theme_btn.clicked.connect(self._alternar_tema)
        bar_layout.addWidget(self._theme_btn)
        content_layout.addWidget(top_bar)

        content_layout.addWidget(self._nav_stack, 1)
        return content

    def _configurar_atajos(self) -> None:
        if self._gestor_deshacer is not None:
            QShortcut(QKeySequence.StandardKey.Undo, self, self._atajo_deshacer)
            QShortcut(QKeySequence.StandardKey.Redo, self, self._atajo_rehacer)

        QShortcut(QKeySequence("Ctrl+N"), self, self._atajo_nueva_regla)
        QShortcut(QKeySequence(QKeySequence.StandardKey.Close), self, self._atajo_ctrl_w)
        QShortcut(QKeySequence("F5"), self, self._atajo_refrescar)

        for i in range(4):
            QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self, lambda checked, idx=i: self._navegar(idx))

    def _atajo_deshacer(self) -> None:
        if self._gestor_deshacer is not None:
            result = self._gestor_deshacer.deshacer()
            if result is not None:
                mostrar_aviso("↩ Archivo restaurado exitosamente", COLORS["success"])

    def _atajo_rehacer(self) -> None:
        if self._gestor_deshacer is not None:
            result = self._gestor_deshacer.rehacer()
            if result is not None:
                mostrar_aviso("↪ Archivo reclasificado exitosamente", COLORS["success"])

    def _atajo_nueva_regla(self) -> None:
        self._navegar(1)
        self._rules_view._nueva_regla()

    def _atajo_ctrl_w(self) -> None:
        self.close()

    def _atajo_refrescar(self) -> None:
        idx = self._nav_stack.currentIndex()
        if idx == 0:
            self._dashboard_view.ejecutar_escaneo()
        elif idx == 1:
            self._rules_view._cargar_reglas()

    def _configurar_bandeja(self) -> None:
        self._tray_icon = QSystemTrayIcon(self)
        self._tray_icon.setToolTip(APP_NAME)
        icon_path = ICONS_DIR / "tray_icon.svg"
        if icon_path.exists():
            self._tray_icon.setIcon(QIcon(str(icon_path)))

        tray_menu = QMenu(self)

        show_action = QAction("Mostrar/Ocultar", self)
        show_action.triggered.connect(self._alternar_visibilidad)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        quit_action = QAction("Salir", self)
        app = QApplication.instance()
        if app:
            quit_action.triggered.connect(app.quit)
        tray_menu.addAction(quit_action)

        self._tray_icon.setContextMenu(tray_menu)
        self._tray_icon.activated.connect(self._al_activar_bandeja)

        if self._settings_view is not None:
            adapter = AdaptadorNotificacionPyQt(self._tray_icon)
            self._settings_view.establecer_servicio_notificacion(adapter)

        self._tray_icon.show()

    def _alternar_visibilidad(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def _al_activar_bandeja(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._alternar_visibilidad()

    def closeEvent(self, event: QCloseEvent | None) -> None:  # noqa: N802 (override de Qt)
        if event is None:
            return
        if self._tray_icon is not None and self._tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            event.accept()

    def _navegar(self, index: int) -> None:
        if self._nav_stack.currentIndex() == index:
            return

        for i, btn in enumerate(self._nav_buttons):
            btn.establecer_activo(i == index)

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

    def _al_estado_vigilancia(self, text: str, color: str) -> None:
        if self._status_label is not None:
            self._status_label.setText(text)
            self._status_label.setStyleSheet(f"color: {color};")

    def _alternar_tema(self) -> None:
        new = "light" if self._theme == "dark" else "dark"
        self._theme = new
        establecer_tema(new)

        # Actualización global: volvemos a aplicar QSS
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(construir_qss())

        if self._rule_repository:
            self._rule_repository.establecer_tema(new)
        if self._theme_btn is not None:
            self._theme_btn.setText("☀" if new == "light" else "☾")

        # Refrescar UI si es necesario (ej. pollish)
        self.style().unpolish(self)
        self.style().polish(self)
