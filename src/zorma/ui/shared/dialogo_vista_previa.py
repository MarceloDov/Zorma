from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.models.enums import EstadoClasificacion
from ...core.models.resultado_clasificacion import ResultadoClasificacion
from ..shared.styles import COLORS, SPACING


def _formatear_tamanio(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024**2:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024**3:
        return f"{size_bytes / (1024**2):.1f} MB"
    return f"{size_bytes / (1024**3):.1f} GB"


class DialogoVistaPrevia(QDialog):
    def __init__(
        self,
        results: list[ResultadoClasificacion],
        watch_path: Path,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._results = results
        self._watch_path = watch_path
        self._row_checks: list[QCheckBox] = []
        self._row_combos: list[QComboBox | None] = []
        self.setWindowTitle("Vista Previa — Modo Activo")
        self.setMinimumSize(950, 600)
        self.setModal(True)
        self._configurar_ui()

    def _configurar_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING["2xl"], SPACING["2xl"], SPACING["2xl"], SPACING["2xl"])
        layout.setSpacing(SPACING["md"])

        header = QLabel(f"Escaneando: {self._watch_path.name}")
        header.setObjectName("preview_header")
        layout.addWidget(header)

        matched = sum(
            1
            for r in self._results
            if r.estado in (EstadoClasificacion.EXITO, EstadoClasificacion.CONFLICTO)
        )
        no_rule = sum(1 for r in self._results if r.estado == EstadoClasificacion.SIN_REGLA)
        conflicts = sum(1 for r in self._results if r.estado == EstadoClasificacion.CONFLICTO)
        filtered = sum(1 for r in self._results if r.estado == EstadoClasificacion.FILTRADO)

        stats_parts = [f"{len(self._results)} archivos encontrados"]
        if matched:
            stats_parts.append(f"{matched} coinciden reglas")
        if no_rule:
            stats_parts.append(f"{no_rule} sin regla")
        if conflicts:
            stats_parts.append(f"{conflicts} conflicto(s)")
        if filtered:
            stats_parts.append(f"{filtered} filtrados")

        summary = QLabel("  |  ".join(stats_parts))
        summary.setObjectName("preview_summary")
        layout.addWidget(summary)

        select_row = QHBoxLayout()
        select_row.setSpacing(SPACING["sm"])

        self._select_all_btn = QPushButton("Seleccionar Todo")
        self._select_all_btn.setProperty("class", "secondary")
        self._select_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._select_all_btn.clicked.connect(self._seleccionar_todo)
        select_row.addWidget(self._select_all_btn)

        self._deselect_all_btn = QPushButton("Deseleccionar Todo")
        self._deselect_all_btn.setProperty("class", "secondary")
        self._deselect_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._deselect_all_btn.clicked.connect(self._deseleccionar_todo)
        select_row.addWidget(self._deselect_all_btn)

        self._select_matched_btn = QPushButton("Seleccionar Solo Coincidentes")
        self._select_matched_btn.setProperty("class", "secondary")
        self._select_matched_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._select_matched_btn.clicked.connect(self._seleccionar_coincidentes)
        select_row.addWidget(self._select_matched_btn)

        select_row.addStretch()

        self._selection_count = QLabel("")
        self._selection_count.setObjectName("preview_selection_count")
        select_row.addWidget(self._selection_count)
        layout.addLayout(select_row)

        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(
            ["", "Archivo", "Regla", "Acción", "Destino", "Tamaño", "Resolución"]
        )
        hdr = self._table.horizontalHeader()
        if hdr is not None:
            hdr.setStretchLastSection(False)
            hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
            hdr.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(0, 36)
        self._table.setColumnWidth(2, 140)
        self._table.setColumnWidth(3, 90)
        self._table.setColumnWidth(5, 80)
        self._table.setColumnWidth(6, 120)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        vhdr = self._table.verticalHeader()
        if vhdr is not None:
            vhdr.setDefaultSectionSize(38)
        layout.addWidget(self._table, 1)

        self._poblar()
        self._actualizar_contador_seleccion()

        if conflicts:
            warn = QLabel(f"⚠ {conflicts} conflicto(s) detectados — use la columna Resolución")
            warn.setObjectName("preview_warning")
            layout.addWidget(warn)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self._apply_btn = QPushButton("✓ Aplicar Seleccionados")
        self._apply_btn.setProperty("class", "primary")
        self._apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_btn.clicked.connect(self.accept)
        btn_row.addWidget(self._apply_btn)

        layout.addLayout(btn_row)

    def _poblar(self) -> None:
        for r in self._results:
            row = self._table.rowCount()
            self._table.insertRow(row)

            cb = QCheckBox()
            is_actionable = r.estado in (
                EstadoClasificacion.EXITO,
                EstadoClasificacion.CONFLICTO,
            )
            cb.setChecked(is_actionable)
            cb.setStyleSheet("QCheckBox::indicator { width: 16px; height: 16px; }")
            cb.toggled.connect(self._actualizar_contador_seleccion)
            self._row_checks.append(cb)

            cb_widget = QWidget()
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self._table.setCellWidget(row, 0, cb_widget)

            file_item = QTableWidgetItem(r.nombre_archivo)
            self._table.setItem(row, 1, file_item)

            rule_name = r.regla_aplicada.nombre if r.regla_aplicada else "—"
            self._table.setItem(row, 2, QTableWidgetItem(rule_name))

            action_text = r.accion_aplicada.tipo_accion.value if r.accion_aplicada else "—"
            self._table.setItem(row, 3, QTableWidgetItem(action_text))

            dest = str(r.ruta_destino) if r.ruta_destino else "—"
            self._table.setItem(row, 4, QTableWidgetItem(dest))

            try:
                if r.ruta_origen is not None:
                    size_str = _formatear_tamanio(r.ruta_origen.stat().st_size)
                else:
                    size_str = "—"
            except OSError:
                size_str = "—"
            self._table.setItem(row, 5, QTableWidgetItem(size_str))

            if r.estado == EstadoClasificacion.CONFLICTO:
                combo = QComboBox()
                combo.addItems(["Sobrescribir", "Omitir"])
                combo.setCurrentIndex(1)
                combo.currentIndexChanged.connect(
                    lambda idx, r_idx=row: self._al_cambiar_resolucion(r_idx, idx)
                )
                self._table.setCellWidget(row, 6, combo)
                self._row_combos.append(combo)
                for col in range(1, 7):
                    item = self._table.item(row, col)
                    if item is not None:
                        item.setBackground(QColor(COLORS["error"] + "40"))
            else:
                self._table.setItem(row, 6, QTableWidgetItem("—"))
                self._row_combos.append(None)

    def _al_cambiar_resolucion(self, row: int, index: int) -> None:
        if row < len(self._row_checks):
            cb = self._row_checks[row]
            cb.blockSignals(True)
            cb.setChecked(index == 0)
            cb.blockSignals(False)
            self._actualizar_contador_seleccion()

    def _seleccionar_todo(self) -> None:
        for i, cb in enumerate(self._row_checks):
            if self._row_combos[i] is not None:
                self._row_combos[i].blockSignals(True)
                self._row_combos[i].setCurrentIndex(0)
                self._row_combos[i].blockSignals(False)
            cb.setChecked(True)

    def _deseleccionar_todo(self) -> None:
        for cb in self._row_checks:
            cb.setChecked(False)

    def _seleccionar_coincidentes(self) -> None:
        for i, r in enumerate(self._results):
            is_actionable = r.estado in (
                EstadoClasificacion.EXITO,
                EstadoClasificacion.CONFLICTO,
            )
            should_check = r.estado != EstadoClasificacion.CONFLICTO and is_actionable
            if self._row_combos[i] is not None:
                self._row_combos[i].blockSignals(True)
                self._row_combos[i].setCurrentIndex(0 if should_check else 1)
                self._row_combos[i].blockSignals(False)
            self._row_checks[i].setChecked(is_actionable)

    def _actualizar_contador_seleccion(self) -> None:
        count = sum(1 for cb in self._row_checks if cb.isChecked())
        self._selection_count.setText(f"{count} seleccionados")

    def obtener_resultados_seleccionados(self) -> list[ResultadoClasificacion]:
        selected = []
        for r, cb, combo in zip(self._results, self._row_checks, self._row_combos):
            if cb.isChecked():
                if combo is not None:
                    r.sobrescribir = combo.currentIndex() == 0
                selected.append(r)
        return selected
