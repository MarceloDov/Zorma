from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...adapters.persistence.zorma_repository import ZormaRepository
from ...core.services.gestor_deshacer import GestorDeshacer
from ...core.services.servicio_clasificacion import ServicioClasificacion
from ..shared.preview_dialog import PreviewDialog
from ..shared.styles import COLORS, SPACING
from ..shared.toast import mostrar_toast
from ..shared.widgets import Card, OnboardingWidget, TimelineFeed
from .dashboard_viewmodel import DashboardViewModel


class DashboardView(QWidget):
    watcher_status_changed = pyqtSignal(str, str)
    folder_selected = pyqtSignal(Path)
    navigate_requested = pyqtSignal(int)

    def __init__(
        self,
        data_dir: Path | None = None,
        repo: ZormaRepository | None = None,
        gestor_deshacer: GestorDeshacer | None = None,
    ) -> None:
        super().__init__()
        data_dir_resolved = data_dir or Path.home() / ".zorma"
        self._vm = DashboardViewModel(data_dir_resolved, repo, gestor_deshacer)
        self._watcher_service: ServicioClasificacion | None = None
        self._scan_pending_results: list = []
        self._configurar_ui()
        self._conectar_vm()
        self._aplicar_estado_vm()

    def establecer_servicio_vigilancia(self, service: ServicioClasificacion) -> None:
        self._watcher_service = service
        self._vm.establecer_servicio_vigilancia(service)

    def ejecutar_escaneo(self) -> None:
        self._vm.ejecutar_escaneo()

    def _configurar_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING["3xl"], SPACING["xl"], SPACING["3xl"], SPACING["xl"])
        layout.setSpacing(SPACING["lg"])

        layout.addWidget(self._crear_encabezado())

        self._onboarding = OnboardingWidget()
        self._onboarding.folder_requested.connect(self._elegir_carpeta)
        self._onboarding.rules_requested.connect(lambda: self.navigate_requested.emit(1))
        self._onboarding.start_requested.connect(self._al_clic_accion)
        layout.addWidget(self._onboarding)

        layout.addLayout(self._crear_tarjetas())
        layout.addLayout(self._crear_seleccion_carpeta())
        layout.addLayout(self._crear_panel_control())
        layout.addLayout(self._crear_area_progreso())
        layout.addLayout(self._crear_area_linea_tiempo())

    def _crear_encabezado(self) -> QLabel:
        header = QLabel("Inicio")
        header.setObjectName("header")
        return header

    def _crear_tarjetas(self) -> QHBoxLayout:
        rules_count = self._vm.obtener_cantidad_reglas()
        self._card_total = Card("Clasificados", "0", "brand")
        self._card_total.setObjectName("card_total")
        self._card_rules = Card("Reglas Activas", rules_count, "success")
        self._card_rules.setObjectName("card_rules")
        self._card_errors = Card("Errores", "0", "error")
        self._card_errors.setObjectName("card_errors")

        cards = QHBoxLayout()
        cards.setSpacing(16)
        cards.addWidget(self._card_total, 1)
        cards.addWidget(self._card_rules, 1)
        cards.addWidget(self._card_errors, 1)
        return cards

    def _crear_seleccion_carpeta(self) -> QHBoxLayout:
        folder_row = QHBoxLayout()
        folder_row.setSpacing(SPACING["md"])

        self._folder_btn = QPushButton("📁 Seleccionar Carpeta")
        self._folder_btn.setObjectName("folder_btn")
        self._folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._folder_btn.setAccessibleName("Seleccionar carpeta")
        self._folder_btn.clicked.connect(self._elegir_carpeta)
        folder_row.addWidget(self._folder_btn)

        self._folder_label = QLabel("Sin carpeta seleccionada")
        self._folder_label.setObjectName("folder_label")
        folder_row.addWidget(self._folder_label)
        folder_row.addStretch()
        return folder_row

    def _crear_panel_control(self) -> QHBoxLayout:
        control_row = QHBoxLayout()
        control_row.setSpacing(SPACING["md"])

        self._auto_checkbox = QCheckBox("Clasificación automática (Segundo plano)")
        self._auto_checkbox.setEnabled(False)
        self._auto_checkbox.toggled.connect(self._al_alternar_auto)
        control_row.addWidget(self._auto_checkbox)

        self._action_btn = QPushButton("⏸ Seleccione una carpeta para iniciar")
        self._action_btn.setObjectName("action_btn")
        self._action_btn.setProperty("state", "inactive")
        self._action_btn.setEnabled(False)
        self._action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._action_btn.setAccessibleName("Acción de clasificación")
        self._action_btn.clicked.connect(self._al_clic_accion)
        control_row.addWidget(self._action_btn)

        control_row.addStretch()
        return control_row

    def _crear_area_progreso(self) -> QHBoxLayout:
        progress_row = QHBoxLayout()
        progress_row.setSpacing(SPACING["md"])

        self._status_label = QLabel("")
        self._status_label.setObjectName("status_label")
        self._status_label.hide()
        progress_row.addWidget(self._status_label)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.hide()
        progress_row.addWidget(self._progress, 1)

        self._cancel_btn = QPushButton("✕ Cancelar")
        self._cancel_btn.setObjectName("cancel_btn")
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.setAccessibleName("Cancelar clasificación")
        self._cancel_btn.clicked.connect(self._vm.cancelar_operacion)
        self._cancel_btn.hide()
        progress_row.addWidget(self._cancel_btn)
        return progress_row

    def _crear_area_linea_tiempo(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        timeline_header_row = QHBoxLayout()
        timeline_header = QLabel("Actividad Reciente")
        timeline_header.setObjectName("timeline_header")
        timeline_header_row.addWidget(timeline_header)

        self._undo_btn = QPushButton("↩ Deshacer")
        self._undo_btn.setObjectName("undo_btn")
        self._undo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._undo_btn.setAccessibleName("Deshacer todo")
        self._undo_btn.hide()
        self._undo_btn.clicked.connect(self._al_deshacer_todo)

        self._redo_btn = QPushButton("↪ Rehacer todo")
        self._redo_btn.setObjectName("redo_btn")
        self._redo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._redo_btn.setAccessibleName("Rehacer todo")
        self._redo_btn.hide()
        self._redo_btn.clicked.connect(self._al_rehacer_todo)

        timeline_header_row.addStretch()
        timeline_header_row.addWidget(self._redo_btn)
        timeline_header_row.addWidget(self._undo_btn)
        layout.addLayout(timeline_header_row)

        self._timeline = TimelineFeed()
        self._timeline.undo_requested.connect(self._al_deshacer_archivo)
        layout.addWidget(self._timeline, 1)
        return layout

    def _conectar_vm(self) -> None:
        self._vm.watch_path_changed.connect(self._al_cambiar_ruta_vigilancia)
        self._vm.classifying_changed.connect(self._al_cambiar_clasificando)
        self._vm.counters_changed.connect(self._al_cambiar_contadores)
        self._vm.undo_redo_changed.connect(self._al_cambiar_deshacer_rehacer)
        self._vm.onboarding_changed.connect(self._al_cambiar_onboarding)
        self._vm.progress_changed.connect(self._al_cambiar_progreso)
        self._vm.status_text.connect(self._al_cambiar_texto_estado)
        self._vm.result_added.connect(self._al_agregar_resultado_vm)
        self._vm.watcher_status.connect(self._al_estado_vigilancia_vm)
        self._vm.show_toast.connect(self._al_mostrar_toast_vm)
        self._vm.scan_finished_for_preview.connect(self._al_resultados_escaneo_preview)

    def _aplicar_estado_vm(self) -> None:
        wp = self._vm.obtener_ruta_vigilancia()
        if wp is not None:
            self._folder_label.setText(str(wp))
            self._auto_checkbox.setEnabled(True)
            if self._vm.obtener_auto_clasificar():
                self._auto_checkbox.setChecked(True)
        self._actualizar_boton_accion()

    # --- VM signal handlers ---

    def _al_cambiar_ruta_vigilancia(self, path: object) -> None:
        if isinstance(path, Path):
            self._folder_label.setText(str(path))
            self._auto_checkbox.setEnabled(True)
        else:
            self._folder_label.setText("Sin carpeta seleccionada")
            self._auto_checkbox.setEnabled(False)
            self._auto_checkbox.setChecked(False)
        self._actualizar_boton_accion()

    def _al_cambiar_clasificando(self, classifying: bool) -> None:
        self._cancel_btn.setVisible(classifying)
        self._actualizar_boton_accion()

    def _al_cambiar_contadores(self, classified: int, errors: int) -> None:
        self._card_total.actualizar_valor(str(classified))
        self._card_errors.actualizar_valor(str(errors))

    def _al_cambiar_deshacer_rehacer(self, can_undo: bool, can_redo: bool) -> None:
        if self._vm._gestor_deshacer is None:
            self._undo_btn.setVisible(False)
            self._redo_btn.setVisible(False)
            return
        if can_undo:
            count = self._vm.obtener_cantidad_deshacibles()
            self._undo_btn.setText(f"↩ Deshacer ({count})")
        self._undo_btn.setVisible(can_undo)
        self._redo_btn.setVisible(can_redo)

    def _al_cambiar_onboarding(self, show: bool) -> None:
        self._onboarding.setVisible(show)
        self._card_total.setVisible(not show)
        self._card_rules.setVisible(not show)
        self._card_errors.setVisible(not show)

    def _al_cambiar_progreso(self, current: int, total: int) -> None:
        if total == 0:
            self._progress.setRange(0, 0)
            self._progress.setValue(0)
        else:
            self._progress.setRange(0, total)
            self._progress.setValue(current)
        self._progress.setVisible(total > 0 or current == 0)

    def _al_cambiar_texto_estado(self, text: str, color: str) -> None:
        if text:
            # Mapear colores a niveles dinámicos
            level = "primary"
            if color == COLORS["error"]:
                level = "error"
            elif color == COLORS["success"]:
                level = "success"
            elif color == COLORS["warning"]:
                level = "warning"

            self._status_label.setText(text)
            self._status_label.setProperty("level", level)
            self._status_label.style().unpolish(self._status_label)
            self._status_label.style().polish(self._status_label)
            self._status_label.show()
        else:
            self._status_label.hide()

    def _al_agregar_resultado_vm(self, result: object) -> None:
        from ...core.models.resultado_clasificacion import ResultadoClasificacion
        if isinstance(result, ResultadoClasificacion):
            can_undo = self._vm.puede_deshacer()
            self._timeline.agregar_resultado(result, can_undo)

    def _al_estado_vigilancia_vm(self, text: str, color: str) -> None:
        self.watcher_status_changed.emit(text, color)

    def _al_mostrar_toast_vm(self, message: str, color: str) -> None:
        mostrar_toast(message, color)

    def _al_resultados_escaneo_preview(self, results: list) -> None:
        self._scan_pending_results = results
        watch_path = self._vm.obtener_ruta_vigilancia()
        if watch_path is None:
            return

        dlg = PreviewDialog(results, watch_path, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        selected = dlg.obtener_resultados_seleccionados()
        if not selected:
            mostrar_toast("Ningún archivo seleccionado", COLORS["text_muted"])
            return
        self._vm.iniciar_clasificacion(selected)

    # --- User actions ---

    def _elegir_carpeta(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta a monitorear")
        if folder:
            p = Path(folder)
            self._vm.establecer_ruta_vigilancia(p)
            self.folder_selected.emit(p)

    def _al_alternar_auto(self, checked: bool) -> None:
        self._vm.establecer_auto_clasificar(checked)
        self._actualizar_boton_accion()

    def _al_clic_accion(self) -> None:
        if self._vm.esta_clasificando:
            return
        if self._vm.obtener_ruta_vigilancia() is None or self._vm.obtener_servicio_vigilancia() is None:
            return
        if not self._auto_checkbox.isChecked():
            self._vm.ejecutar_escaneo()

    def _al_deshacer_archivo(self, result: object) -> None:
        from ...core.models.resultado_clasificacion import ResultadoClasificacion
        if not isinstance(result, ResultadoClasificacion):
            return
        reply = QMessageBox.question(
            self,
            "Confirmar deshacer",
            f"¿Revertir el movimiento de '{result.nombre_archivo}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._vm.deshacer_archivo(result)

    def _al_deshacer_todo(self) -> None:
        count = self._vm.obtener_cantidad_deshacibles()
        if count == 0:
            return
        reply = QMessageBox.question(
            self,
            "Confirmar deshacer todo",
            f"¿Revertir los últimos {count} movimiento{'s' if count != 1 else ''}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        undone = self._vm.deshacer_todo()
        self._timeline.limpiar()
        if undone > 0:
            msg = f"↩ {undone} movimiento{'s' if undone != 1 else ''} revertido{'s' if undone != 1 else ''}"
            mostrar_toast(msg, COLORS["warning"])

    def _al_rehacer_todo(self) -> None:
        reply = QMessageBox.question(
            self,
            "Confirmar rehacer",
            "¿Re-aplicar los últimos movimientos deshechos?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        redone = self._vm.rehacer_todo()
        if redone > 0:
            msg = f"↪ {redone} movimiento{'s' if redone != 1 else ''} re-aplicado{'s' if redone != 1 else ''}"
            mostrar_toast(msg, COLORS["primary"])

    def _actualizar_boton_accion(self) -> None:
        if self._vm.esta_clasificando:
            self._action_btn.setText("⟳ Clasificando...")
            self._action_btn.setEnabled(False)
            self._action_btn.setProperty("state", "inactive")

        else:
            watch_path = self._vm.obtener_ruta_vigilancia()
            if watch_path is None:
                self._action_btn.setText("⏸ Seleccione una carpeta para iniciar")
                self._action_btn.setEnabled(False)
                self._action_btn.setProperty("state", "inactive")
            elif self._auto_checkbox.isChecked():
                self._action_btn.setText(f"🟢 Monitoreando {watch_path.name}...")
                self._action_btn.setEnabled(False)
                self._action_btn.setProperty("state", "monitoring")
            else:
                self._action_btn.setText("⚡ Clasificar contenido actual")
                self._action_btn.setEnabled(True)
                self._action_btn.setProperty("state", "active")

        self._action_btn.style().unpolish(self._action_btn)
        self._action_btn.style().polish(self._action_btn)
