from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.models.classification import ClassificationResult, ClassificationStatus
from ...core.ports.rule_repository import RuleRepository
from ...core.services.undo_manager import UndoManager
from ...core.services.watcher_service import WatcherService
from ..shared.conflict_dialog import ConflictDialog
from ..shared.preview_dialog import PreviewDialog
from ..shared.styles import (
    COLORS,
    FONT_SIZES,
    SPACING,
    btn_error,
    btn_secondary,
)
from ..shared.toast import show_toast
from ..shared.widgets import Card, TimelineFeed


class ScanWorker(QThread):
    """Worker para realizar escaneos de archivos en segundo plano."""

    scan_finished = pyqtSignal(list)

    def __init__(
        self,
        watcher_service: WatcherService,
        paths: List[Path],
        parent: Optional[QWidget] = None,
    ) -> None:
        """Inicializa el worker de escaneo.

        Args:
            watcher_service: Servicio de monitorización.
            paths: Lista de rutas a escanear.
            parent: Widget padre.
        """
        super().__init__(parent)
        self._watcher_service = watcher_service
        self._paths = paths

    def run(self) -> None:
        """Ejecuta el escaneo."""
        results = self._watcher_service.preview_all(self._paths)
        self.scan_finished.emit(results)


class ClassifyWorker(QThread):
    """Worker para realizar la clasificación de archivos en segundo plano."""

    progress = pyqtSignal(int, int)
    file_done = pyqtSignal(object)
    classify_finished = pyqtSignal(int, int)

    def __init__(
        self,
        watcher_service: WatcherService,
        results: List[ClassificationResult],
        should_overwrite: bool,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Inicializa el worker de clasificación.

        Args:
            watcher_service: Servicio de monitorización.
            results: Resultados de la clasificación.
            should_overwrite: Indica si se deben sobrescribir archivos existentes.
            parent: Widget padre.
        """
        super().__init__(parent)
        self._watcher_service = watcher_service
        self._results = results
        self._should_overwrite = should_overwrite
        self._cancelled = False

    def cancel(self) -> None:
        """Cancela la operación de clasificación."""
        self._cancelled = True

    def run(self) -> None:
        """Ejecuta la clasificación."""
        total = len(self._results)
        success_count = 0
        error_count = 0
        for i, r in enumerate(self._results):
            if self._cancelled:
                break
            self.progress.emit(i + 1, total)
            
            if self._watcher_service is None or r.source_path is None:
                continue

            if r.status == ClassificationStatus.CONFLICT:
                if self._should_overwrite:
                    actual = self._watcher_service.classify(r.source_path)
                    self.file_done.emit(actual)
                    if actual.status == ClassificationStatus.SUCCESS:
                        success_count += 1
                    else:
                        error_count += 1
                continue
            
            actual = self._watcher_service.classify(r.source_path)
            self.file_done.emit(actual)
            if actual.status == ClassificationStatus.SUCCESS:
                success_count += 1
            else:
                error_count += 1
        self.classify_finished.emit(success_count, error_count)


class DashboardView(QWidget):
    watcher_status_changed = pyqtSignal(str, str)
    folder_selected = pyqtSignal(Path)

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        repo: Optional[RuleRepository] = None,
        undo_manager: Optional[UndoManager] = None,
    ) -> None:
        super().__init__()
        self._data_dir = data_dir or Path.home() / ".zorma"
        self._repo = repo
        self._undo_manager = undo_manager
        self._watcher_service: Optional[WatcherService] = None
        self._watcher_running = False
        self._watch_path: Optional[Path] = None
        self._classifying = False
        self._total_classified = 0
        self._total_errors = 0
        self._scan_worker: Optional[ScanWorker] = None
        self._classify_worker: Optional[ClassifyWorker] = None
        self._setup_ui()

    def set_watcher_service(self, service: WatcherService) -> None:
        self._watcher_service = service

    def _setup_ui(self) -> None:
        """Configura la interfaz de usuario del dashboard."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING["3xl"], SPACING["xl"], SPACING["3xl"], SPACING["xl"])
        layout.setSpacing(SPACING["lg"])

        layout.addWidget(self._create_header())
        layout.addLayout(self._create_cards())
        layout.addLayout(self._create_folder_selection())
        layout.addLayout(self._create_control_panel())
        layout.addLayout(self._create_progress_area())
        layout.addLayout(self._create_timeline_area())

    def _create_header(self) -> QLabel:
        """Crea el label del encabezado.

        Returns:
            QLabel: Label del encabezado.
        """
        header = QLabel("Inicio")
        header.setStyleSheet(
            f"color: {COLORS['text_bright']}; font-size: {FONT_SIZES['2xl']}; font-weight: 800;"
        )
        return header

    def _create_cards(self) -> QHBoxLayout:
        """Crea el layout de las tarjetas de estadísticas.

        Returns:
            QHBoxLayout: Layout con las tarjetas.
        """
        rules_count = str(len(self._repo.get_all())) if self._repo else "0"
        self._card_total = Card("Clasificados", "0", COLORS["primary"])
        self._card_rules = Card("Reglas Activas", rules_count, COLORS["success"])
        self._card_errors = Card("Errores", "0", COLORS["error"])

        cards = QHBoxLayout()
        cards.setSpacing(16)
        cards.addWidget(self._card_total, 1)
        cards.addWidget(self._card_rules, 1)
        cards.addWidget(self._card_errors, 1)
        return cards

    def _create_folder_selection(self) -> QHBoxLayout:
        """Crea el layout de selección de carpeta.

        Returns:
            QHBoxLayout: Layout con botón y label de carpeta.
        """
        folder_row = QHBoxLayout()
        folder_row.setSpacing(SPACING["md"])

        self._folder_btn = QPushButton("📁 Seleccionar Carpeta")
        self._folder_btn.setStyleSheet(btn_secondary())
        self._folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._folder_btn.clicked.connect(self._pick_folder)
        folder_row.addWidget(self._folder_btn)

        self._folder_label = QLabel("Sin carpeta seleccionada")
        self._folder_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: {FONT_SIZES['base']};"
        )
        folder_row.addWidget(self._folder_label)
        folder_row.addStretch()
        return folder_row

    def _create_control_panel(self) -> QHBoxLayout:
        """Crea el layout del panel de control.

        Returns:
            QHBoxLayout: Layout con checkbox y botón de acción.
        """
        control_row = QHBoxLayout()
        control_row.setSpacing(SPACING["md"])

        self._auto_checkbox = QCheckBox("Clasificación automática (Segundo plano)")
        self._auto_checkbox.setEnabled(False)
        self._auto_checkbox.toggled.connect(self._on_auto_toggled)
        control_row.addWidget(self._auto_checkbox)

        self._action_btn = QPushButton("⏸ Seleccione una carpeta para iniciar")
        self._action_btn.setObjectName("action_btn")
        self._action_btn.setEnabled(False)
        self._action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._action_btn.clicked.connect(self._on_action_clicked)
        control_row.addWidget(self._action_btn)

        control_row.addStretch()
        return control_row

    def _create_progress_area(self) -> QHBoxLayout:
        """Crea el layout del área de progreso.

        Returns:
            QHBoxLayout: Layout con barra de progreso y botón de cancelar.
        """
        progress_row = QHBoxLayout()
        progress_row.setSpacing(SPACING["md"])

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.hide()
        progress_row.addWidget(self._progress, 1)

        self._cancel_btn = QPushButton("✕ Cancelar")
        self._cancel_btn.setStyleSheet(btn_error())
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.clicked.connect(self._cancel_operation)
        self._cancel_btn.hide()
        progress_row.addWidget(self._cancel_btn)
        return progress_row

    def _create_timeline_area(self) -> QVBoxLayout:
        """Crea el layout del área de actividad reciente.

        Returns:
            QVBoxLayout: Layout con encabezado de línea de tiempo y feed.
        """
        layout = QVBoxLayout()
        timeline_header_row = QHBoxLayout()
        timeline_header = QLabel("Actividad Reciente")
        timeline_header.setStyleSheet(
            f"color: {COLORS['text_bright']}; font-size: {FONT_SIZES['lg']}; font-weight: 700;"
        )
        timeline_header_row.addWidget(timeline_header)

        self._undo_btn = QPushButton("↩ Deshacer todo")
        self._undo_btn.setStyleSheet(btn_secondary())
        self._undo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._undo_btn.hide()
        self._undo_btn.clicked.connect(self._on_undo_all)
        timeline_header_row.addStretch()
        timeline_header_row.addWidget(self._undo_btn)
        layout.addLayout(timeline_header_row)

        self._timeline = TimelineFeed()
        self._timeline.undo_requested.connect(self._on_undo_file)
        layout.addWidget(self._timeline, 1)
        return layout

    def _update_action_btn(self) -> None:
        if self._classifying:
            self._action_btn.setText("⟳ Clasificando...")
            self._action_btn.setEnabled(False)
            self._action_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['bg2']};
                    color: {COLORS['text_muted']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 8px;
                    padding: 10px 22px;
                    font-weight: 600;
                    font-size: {FONT_SIZES['base']};
                }}
            """)
            return

        if self._watch_path is None:
            self._action_btn.setText("⏸ Seleccione una carpeta para iniciar")
            self._action_btn.setEnabled(False)
            self._action_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['bg2']};
                    color: {COLORS['text_muted']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 8px;
                    padding: 10px 22px;
                    font-weight: 600;
                    font-size: {FONT_SIZES['base']};
                }}
            """)
        elif self._auto_checkbox.isChecked():
            self._action_btn.setText(f"🟢 Monitoreando {self._watch_path.name}...")
            self._action_btn.setEnabled(False)
            self._action_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['bg2']};
                    color: {COLORS['success']};
                    border: 1px solid {COLORS['success']};
                    border-radius: 8px;
                    padding: 10px 22px;
                    font-weight: 600;
                    font-size: {FONT_SIZES['base']};
                }}
            """)
        else:
            self._action_btn.setText("⚡ Clasificar contenido actual")
            self._action_btn.setEnabled(True)
            self._action_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['primary']};
                    color: {COLORS['bg']};
                    border: none;
                    border-radius: 8px;
                    padding: 10px 22px;
                    font-weight: 700;
                    font-size: {FONT_SIZES['base']};
                }}
                QPushButton:hover {{
                    background-color: {COLORS['primary_hover']};
                }}
                QPushButton:pressed {{
                    background-color: #6a8fd8;
                }}
            """)

    def _pick_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta a monitorear")
        if folder:
            self._watch_path = Path(folder)
            self._folder_label.setText(str(self._watch_path))
            self._auto_checkbox.setEnabled(True)
            self._update_action_btn()
            self.folder_selected.emit(self._watch_path)

    def _on_auto_toggled(self, checked: bool) -> None:
        if checked:
            self._start_watcher()
        else:
            self._stop_watcher()
        self._update_action_btn()

    def _on_action_clicked(self) -> None:
        if self._classifying:
            return
        if self._watch_path is None or self._watcher_service is None:
            return
        if not self._auto_checkbox.isChecked():
            self._run_scan()

    def _run_scan(self) -> None:
        if self._watcher_service is None or self._watch_path is None:
            return
        self._classifying = True
        self._update_action_btn()
        self._cancel_btn.show()

        self._scan_worker = ScanWorker(self._watcher_service, [self._watch_path])
        self._scan_worker.scan_finished.connect(self._on_scan_finished)
        self._scan_worker.start()

    def _cancel_operation(self) -> None:
        if self._classify_worker is not None and self._classify_worker.isRunning():
            self._classify_worker.cancel()
            self._classify_worker.wait(3000)
            self._classify_worker = None
            self._progress.hide()
            self._cancel_btn.hide()
            self._classifying = False
            self._update_action_btn()
            show_toast("Clasificación cancelada", COLORS["warning"])
            return

        if self._scan_worker is not None and self._scan_worker.isRunning():
            self._scan_worker.terminate()
            self._scan_worker.wait(3000)
            self._scan_worker = None
            self._progress.hide()
            self._cancel_btn.hide()
            self._classifying = False
            self._update_action_btn()
            show_toast("Escaneo cancelado", COLORS["warning"])
            return

    def _on_scan_finished(self, results: list[ClassificationResult]) -> None:
        self._cancel_btn.hide()
        self._classifying = False
        self._update_action_btn()

        if not results:
            show_toast("Sin archivos en la carpeta", COLORS["text_muted"])
            return

        conflict_results = [r for r in results if r.status == ClassificationStatus.CONFLICT]
        should_overwrite = False
        if conflict_results:
            conflict_dialog = ConflictDialog(conflict_results, self)
            if conflict_dialog.exec() != QDialog.DialogCode.Accepted:
                return
            if conflict_dialog.should_skip_all():
                return
            should_overwrite = conflict_dialog.should_overwrite()

        if self._watch_path is None:
            return

        preview_dialog = PreviewDialog(results, self._watch_path, self)
        if preview_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        selected = preview_dialog.get_selected_results()
        if not selected:
            show_toast("Ningún archivo seleccionado", COLORS["text_muted"])
            return

        self._classifying = True
        self._update_action_btn()
        self._progress.setValue(0)
        self._progress.show()
        self._cancel_btn.show()

        if self._watcher_service is None:
            return
            
        self._classify_worker = ClassifyWorker(
            self._watcher_service, selected, should_overwrite
        )
        self._classify_worker.progress.connect(self._on_classify_progress)
        self._classify_worker.file_done.connect(self._on_classify_file_done)
        self._classify_worker.classify_finished.connect(self._on_classify_finished)
        self._classify_worker.start()

    def _on_classify_progress(self, current: int, total: int) -> None:
        if total > 0:
            self._progress.setMaximum(total)
            self._progress.setValue(current)

    def _on_classify_file_done(self, result: object) -> None:
        if isinstance(result, ClassificationResult):
            self._add_result(result)

    def _on_classify_finished(self, success_count: int, error_count: int) -> None:
        self._progress.hide()
        self._cancel_btn.hide()
        self._classifying = False
        self._update_action_btn()
        self._classify_worker = None
        self._update_undo_btn()
        show_toast(
            f"✓ {success_count} clasificados, {error_count} errores",
            COLORS["success"] if error_count == 0 else COLORS["warning"],
        )

    def _update_undo_btn(self) -> None:
        visible = self._undo_manager is not None and self._undo_manager.can_undo()
        self._undo_btn.setVisible(visible)

    def _on_undo_file(self, result: ClassificationResult) -> None:
        if self._undo_manager is None or result.source_path is None:
            return
        undone = self._undo_manager.undo_by_source_path(result.source_path)
        if undone is not None and undone.status == ClassificationStatus.SUCCESS:
            self._total_classified = max(0, self._total_classified - 1)
            self._card_total.update_value(str(self._total_classified))
            self._update_undo_btn()

    def _on_undo_all(self) -> None:
        if self._undo_manager is None:
            return
        count = 0
        while self._undo_manager.can_undo():
            result = self._undo_manager.undo()
            if result is not None and result.status == ClassificationStatus.SUCCESS:
                self._total_classified = max(0, self._total_classified - 1)
                count += 1
        self._card_total.update_value(str(self._total_classified))
        self._timeline.clear()
        self._update_undo_btn()
        if count > 0:
            msg = f"↩ {count} movimiento{'s' if count != 1 else ''} revertido{'s' if count != 1 else ''}"
            show_toast(msg, COLORS["warning"])

    def _start_watcher(self) -> None:
        if self._watcher_service is None or self._watch_path is None:
            return
        self._watcher_service.set_result_callback(self._on_result)
        self._watcher_service.start_monitoring([self._watch_path])
        self._watcher_running = True
        self.watcher_status_changed.emit("● Monitor activo", COLORS["success"])

    def _stop_watcher(self) -> None:
        if self._watcher_service is None:
            return
        self._watcher_service.stop_monitoring()
        self._watcher_running = False
        self.watcher_status_changed.emit("● Monitor detenido", COLORS["error"])

    def _on_result(self, result: ClassificationResult) -> None:
        QTimer.singleShot(0, lambda: self._add_result(result))

    def _add_result(self, result: ClassificationResult) -> None:
        if result.status == ClassificationStatus.SUCCESS:
            self._total_classified += 1
        elif result.status == ClassificationStatus.ERROR:
            self._total_errors += 1

        self._card_total.update_value(str(self._total_classified))
        self._card_errors.update_value(str(self._total_errors))

        can_undo = (
            self._undo_manager is not None
            and self._undo_manager.can_undo()
        )
        self._timeline.add_result(result, can_undo)
        self._update_undo_btn()
