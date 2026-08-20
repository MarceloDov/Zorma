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
from ..shared.toast import show_toast
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
        self._setup_ui()
        self._connect_vm()
        self._apply_vm_state()

    def set_watcher_service(self, service: ServicioClasificacion) -> None:
        self._watcher_service = service
        self._vm.set_watcher_service(service)

    def run_scan(self) -> None:
        self._vm.run_scan()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING["3xl"], SPACING["xl"], SPACING["3xl"], SPACING["xl"])
        layout.setSpacing(SPACING["lg"])

        layout.addWidget(self._create_header())

        self._onboarding = OnboardingWidget()
        self._onboarding.folder_requested.connect(self._pick_folder)
        self._onboarding.rules_requested.connect(lambda: self.navigate_requested.emit(1))
        self._onboarding.start_requested.connect(self._on_action_clicked)
        layout.addWidget(self._onboarding)

        layout.addLayout(self._create_cards())
        layout.addLayout(self._create_folder_selection())
        layout.addLayout(self._create_control_panel())
        layout.addLayout(self._create_progress_area())
        layout.addLayout(self._create_timeline_area())

    def _create_header(self) -> QLabel:
        header = QLabel("Inicio")
        header.setObjectName("header")
        return header

    def _create_cards(self) -> QHBoxLayout:
        rules_count = self._vm.get_rules_count()
        self._card_total = Card("Clasificados", "0", "primary")
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

    def _create_folder_selection(self) -> QHBoxLayout:
        folder_row = QHBoxLayout()
        folder_row.setSpacing(SPACING["md"])

        self._folder_btn = QPushButton("📁 Seleccionar Carpeta")
        self._folder_btn.setObjectName("folder_btn")
        self._folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._folder_btn.setAccessibleName("Seleccionar carpeta")
        self._folder_btn.clicked.connect(self._pick_folder)
        folder_row.addWidget(self._folder_btn)

        self._folder_label = QLabel("Sin carpeta seleccionada")
        self._folder_label.setObjectName("folder_label")
        folder_row.addWidget(self._folder_label)
        folder_row.addStretch()
        return folder_row

    def _create_control_panel(self) -> QHBoxLayout:
        control_row = QHBoxLayout()
        control_row.setSpacing(SPACING["md"])

        self._auto_checkbox = QCheckBox("Clasificación automática (Segundo plano)")
        self._auto_checkbox.setEnabled(False)
        self._auto_checkbox.toggled.connect(self._on_auto_toggled)
        control_row.addWidget(self._auto_checkbox)

        self._action_btn = QPushButton("⏸ Seleccione una carpeta para iniciar")
        self._action_btn.setObjectName("action_btn")
        self._action_btn.setProperty("state", "inactive")
        self._action_btn.setEnabled(False)
        self._action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._action_btn.setAccessibleName("Acción de clasificación")
        self._action_btn.clicked.connect(self._on_action_clicked)
        control_row.addWidget(self._action_btn)

        control_row.addStretch()
        return control_row

    def _create_progress_area(self) -> QHBoxLayout:
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
        self._cancel_btn.clicked.connect(self._vm.cancel_operation)
        self._cancel_btn.hide()
        progress_row.addWidget(self._cancel_btn)
        return progress_row

    def _create_timeline_area(self) -> QVBoxLayout:
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
        self._undo_btn.clicked.connect(self._on_undo_all)

        self._redo_btn = QPushButton("↪ Rehacer todo")
        self._redo_btn.setObjectName("redo_btn")
        self._redo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._redo_btn.setAccessibleName("Rehacer todo")
        self._redo_btn.hide()
        self._redo_btn.clicked.connect(self._on_redo_all)

        timeline_header_row.addStretch()
        timeline_header_row.addWidget(self._redo_btn)
        timeline_header_row.addWidget(self._undo_btn)
        layout.addLayout(timeline_header_row)

        self._timeline = TimelineFeed()
        self._timeline.undo_requested.connect(self._on_undo_file)
        layout.addWidget(self._timeline, 1)
        return layout

    def _connect_vm(self) -> None:
        self._vm.watch_path_changed.connect(self._on_watch_path_changed)
        self._vm.classifying_changed.connect(self._on_classifying_changed)
        self._vm.counters_changed.connect(self._on_counters_changed)
        self._vm.undo_redo_changed.connect(self._on_undo_redo_changed)
        self._vm.onboarding_changed.connect(self._on_onboarding_changed)
        self._vm.progress_changed.connect(self._on_progress_changed)
        self._vm.status_text.connect(self._on_status_text)
        self._vm.result_added.connect(self._on_vm_result_added)
        self._vm.watcher_status.connect(self._on_vm_watcher_status)
        self._vm.show_toast.connect(self._on_vm_show_toast)
        self._vm.scan_finished_for_preview.connect(self._on_scan_results_for_preview)

    def _apply_vm_state(self) -> None:
        wp = self._vm.get_watch_path()
        if wp is not None:
            self._folder_label.setText(str(wp))
            self._auto_checkbox.setEnabled(True)
            if self._vm.get_auto_classify():
                self._auto_checkbox.setChecked(True)
        self._update_action_btn()

    # --- VM signal handlers ---

    def _on_watch_path_changed(self, path: object) -> None:
        if isinstance(path, Path):
            self._folder_label.setText(str(path))
            self._auto_checkbox.setEnabled(True)
        else:
            self._folder_label.setText("Sin carpeta seleccionada")
            self._auto_checkbox.setEnabled(False)
            self._auto_checkbox.setChecked(False)
        self._update_action_btn()

    def _on_classifying_changed(self, classifying: bool) -> None:
        self._cancel_btn.setVisible(classifying)
        self._update_action_btn()

    def _on_counters_changed(self, classified: int, errors: int) -> None:
        self._card_total.update_value(str(classified))
        self._card_errors.update_value(str(errors))

    def _on_undo_redo_changed(self, can_undo: bool, can_redo: bool) -> None:
        if self._vm._gestor_deshacer is None:
            self._undo_btn.setVisible(False)
            self._redo_btn.setVisible(False)
            return
        if can_undo:
            count = self._vm.get_undoable_count()
            self._undo_btn.setText(f"↩ Deshacer ({count})")
        self._undo_btn.setVisible(can_undo)
        self._redo_btn.setVisible(can_redo)

    def _on_onboarding_changed(self, show: bool) -> None:
        self._onboarding.setVisible(show)
        self._card_total.setVisible(not show)
        self._card_rules.setVisible(not show)
        self._card_errors.setVisible(not show)

    def _on_progress_changed(self, current: int, total: int) -> None:
        if total == 0:
            self._progress.setRange(0, 0)
            self._progress.setValue(0)
        else:
            self._progress.setRange(0, total)
            self._progress.setValue(current)
        self._progress.setVisible(total > 0 or current == 0)

    def _on_status_text(self, text: str, color: str) -> None:
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

    def _on_vm_result_added(self, result: object) -> None:
        from ...core.models.resultado_clasificacion import ResultadoClasificacion
        if isinstance(result, ResultadoClasificacion):
            can_undo = self._vm.can_undo()
            self._timeline.add_result(result, can_undo)

    def _on_vm_watcher_status(self, text: str, color: str) -> None:
        self.watcher_status_changed.emit(text, color)

    def _on_vm_show_toast(self, message: str, color: str) -> None:
        show_toast(message, color)

    def _on_scan_results_for_preview(self, results: list) -> None:
        self._scan_pending_results = results
        watch_path = self._vm.get_watch_path()
        if watch_path is None:
            return

        dlg = PreviewDialog(results, watch_path, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        selected = dlg.get_selected_results()
        if not selected:
            show_toast("Ningún archivo seleccionado", COLORS["text_muted"])
            return
        self._vm.start_classify(selected)

    # --- User actions ---

    def _pick_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta a monitorear")
        if folder:
            p = Path(folder)
            self._vm.set_watch_path(p)
            self.folder_selected.emit(p)

    def _on_auto_toggled(self, checked: bool) -> None:
        self._vm.set_auto_classify(checked)
        self._update_action_btn()

    def _on_action_clicked(self) -> None:
        if self._vm.is_classifying:
            return
        if self._vm.get_watch_path() is None or self._vm.get_watcher_service() is None:
            return
        if not self._auto_checkbox.isChecked():
            self._vm.run_scan()

    def _on_undo_file(self, result: object) -> None:
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
        self._vm.undo_file(result)

    def _on_undo_all(self) -> None:
        count = self._vm.get_undoable_count()
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
        undone = self._vm.undo_all()
        self._timeline.clear()
        if undone > 0:
            msg = f"↩ {undone} movimiento{'s' if undone != 1 else ''} revertido{'s' if undone != 1 else ''}"
            show_toast(msg, COLORS["warning"])

    def _on_redo_all(self) -> None:
        reply = QMessageBox.question(
            self,
            "Confirmar rehacer",
            "¿Re-aplicar los últimos movimientos deshechos?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        redone = self._vm.redo_all()
        if redone > 0:
            msg = f"↪ {redone} movimiento{'s' if redone != 1 else ''} re-aplicado{'s' if redone != 1 else ''}"
            show_toast(msg, COLORS["primary"])

    def _update_action_btn(self) -> None:
        if self._vm.is_classifying:
            self._action_btn.setText("⟳ Clasificando...")
            self._action_btn.setEnabled(False)
            self._action_btn.setProperty("state", "inactive")

        else:
            watch_path = self._vm.get_watch_path()
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
