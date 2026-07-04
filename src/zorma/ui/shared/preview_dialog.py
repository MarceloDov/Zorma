from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
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

from ...core.models.classification import ClassificationResult, ClassificationStatus
from ..shared.styles import COLORS, FONT_SIZES, SPACING, btn_primary, btn_secondary, btn_small


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024**2:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024**3:
        return f"{size_bytes / (1024**2):.1f} MB"
    return f"{size_bytes / (1024**3):.1f} GB"


class PreviewDialog(QDialog):
    def __init__(
        self,
        results: List[ClassificationResult],
        watch_path: Path,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._results = results
        self._watch_path = watch_path
        self._row_checks: List[QCheckBox] = []
        self.setWindowTitle("Vista Previa — Modo Activo")
        self.setMinimumSize(850, 600)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING["2xl"], SPACING["2xl"], SPACING["2xl"], SPACING["2xl"])
        layout.setSpacing(SPACING["md"])

        header = QLabel(f"Escaneando: {self._watch_path.name}")
        header.setStyleSheet(
            f"color: {COLORS['text_bright']}; font-size: {FONT_SIZES['lg']}; font-weight: 700;"
        )
        layout.addWidget(header)

        matched = sum(
            1
            for r in self._results
            if r.status in (ClassificationStatus.SUCCESS, ClassificationStatus.CONFLICT)
        )
        no_rule = sum(1 for r in self._results if r.status == ClassificationStatus.NO_RULE)
        conflicts = sum(1 for r in self._results if r.status == ClassificationStatus.CONFLICT)
        filtered = sum(1 for r in self._results if r.status == ClassificationStatus.FILTERED_OUT)

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
        summary.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: {FONT_SIZES['base']};")
        layout.addWidget(summary)

        select_row = QHBoxLayout()
        select_row.setSpacing(SPACING["sm"])

        self._select_all_btn = QPushButton("Seleccionar Todo")
        self._select_all_btn.setStyleSheet(btn_small("secondary"))
        self._select_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._select_all_btn.clicked.connect(self._select_all)
        select_row.addWidget(self._select_all_btn)

        self._deselect_all_btn = QPushButton("Deseleccionar Todo")
        self._deselect_all_btn.setStyleSheet(btn_small("secondary"))
        self._deselect_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._deselect_all_btn.clicked.connect(self._deselect_all)
        select_row.addWidget(self._deselect_all_btn)

        self._select_matched_btn = QPushButton("Seleccionar Solo Coincidentes")
        self._select_matched_btn.setStyleSheet(btn_small("secondary"))
        self._select_matched_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._select_matched_btn.clicked.connect(self._select_matched)
        select_row.addWidget(self._select_matched_btn)

        select_row.addStretch()

        self._selection_count = QLabel("")
        self._selection_count.setStyleSheet(
            f"color: {COLORS['primary']}; font-size: {FONT_SIZES['sm']}; font-weight: 700;"
        )
        select_row.addWidget(self._selection_count)
        layout.addLayout(select_row)

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ["", "Archivo", "Regla", "Acción", "Destino", "Tamaño"]
        )
        hdr = self._table.horizontalHeader()
        if hdr is not None:
            hdr.setStretchLastSection(False)
            hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(0, 36)
        self._table.setColumnWidth(2, 140)
        self._table.setColumnWidth(3, 90)
        self._table.setColumnWidth(5, 80)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        vhdr = self._table.verticalHeader()
        if vhdr is not None:
            vhdr.setDefaultSectionSize(38)
        layout.addWidget(self._table, 1)

        self._populate()
        self._update_selection_count()

        if conflicts:
            warn = QLabel(f"⚠ {conflicts} conflicto(s) detectados — resaltados en rojo")
            warn.setStyleSheet(f"color: {COLORS['warning']}; font-size: 12px; font-weight: 600;")
            layout.addWidget(warn)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setStyleSheet(btn_secondary())
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self._apply_btn = QPushButton("✓ Aplicar Seleccionados")
        self._apply_btn.setStyleSheet(btn_primary())
        self._apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_btn.clicked.connect(self.accept)
        btn_row.addWidget(self._apply_btn)

        layout.addLayout(btn_row)

    def _populate(self) -> None:
        for r in self._results:
            row = self._table.rowCount()
            self._table.insertRow(row)

            cb = QCheckBox()
            is_actionable = r.status in (
                ClassificationStatus.SUCCESS,
                ClassificationStatus.CONFLICT,
            )
            cb.setChecked(is_actionable)
            cb.setStyleSheet("QCheckBox::indicator { width: 16px; height: 16px; }")
            cb.toggled.connect(self._update_selection_count)
            self._row_checks.append(cb)

            cb_widget = QWidget()
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self._table.setCellWidget(row, 0, cb_widget)

            file_item = QTableWidgetItem(r.file_name)
            self._table.setItem(row, 1, file_item)

            rule_name = r.rule_applied.name if r.rule_applied else "—"
            self._table.setItem(row, 2, QTableWidgetItem(rule_name))

            action_text = r.action_applied.action_type.value if r.action_applied else "—"
            self._table.setItem(row, 3, QTableWidgetItem(action_text))

            dest = str(r.destination_path) if r.destination_path else "—"
            self._table.setItem(row, 4, QTableWidgetItem(dest))

            try:
                if r.source_path is not None:
                    size_str = _format_size(r.source_path.stat().st_size)
                else:
                    size_str = "—"
            except OSError:
                size_str = "—"
            self._table.setItem(row, 5, QTableWidgetItem(size_str))

            if r.status == ClassificationStatus.CONFLICT:
                for col in range(1, 6):
                    item = self._table.item(row, col)
                    if item is not None:
                        item.setBackground(QColor(COLORS["error"] + "40"))

    def _select_all(self) -> None:
        for cb in self._row_checks:
            cb.setChecked(True)

    def _deselect_all(self) -> None:
        for cb in self._row_checks:
            cb.setChecked(False)

    def _select_matched(self) -> None:
        for i, r in enumerate(self._results):
            is_actionable = r.status in (
                ClassificationStatus.SUCCESS,
                ClassificationStatus.CONFLICT,
            )
            self._row_checks[i].setChecked(is_actionable)

    def _update_selection_count(self) -> None:
        count = sum(1 for cb in self._row_checks if cb.isChecked())
        self._selection_count.setText(f"{count} seleccionados")

    def get_selected_results(self) -> List[ClassificationResult]:
        return [r for r, cb in zip(self._results, self._row_checks) if cb.isChecked()]
