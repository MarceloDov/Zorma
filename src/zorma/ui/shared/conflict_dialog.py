from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import Qt
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

from ...core.models.classification import ClassificationResult
from ..shared.styles import BORDER_RADIUS, COLORS, FONT_SIZES, SPACING, btn_primary, btn_secondary, hex_to_rgba


class ConflictDialog(QDialog):
    def __init__(
        self,
        conflicts: List[ClassificationResult],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._conflicts = conflicts
        self._overwrite_all = False
        self._skip_all = False
        self.setWindowTitle("Conflictos Detectados")
        self.setMinimumSize(640, 450)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING["2xl"], SPACING["2xl"], SPACING["2xl"], SPACING["2xl"])
        layout.setSpacing(SPACING["md"])

        header_widget = QWidget()
        header_widget.setObjectName("conflict_header")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(SPACING["lg"], SPACING["md"], SPACING["lg"], SPACING["md"])

        icon_label = QLabel("⚠")
        icon_label.setObjectName("conflict_icon")
        header_layout.addWidget(icon_label)

        header_text = QLabel(f"{len(self._conflicts)} conflicto(s) de destino")
        header_text.setObjectName("conflict_text")
        header_layout.addWidget(header_text)
        header_layout.addStretch()
        layout.addWidget(header_widget)

        desc = QLabel("El archivo de destino ya existe. Elija cómo proceder:")
        desc.setObjectName("conflict_desc")
        layout.addWidget(desc)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Archivo", "Destino", "Acción"])
        hdr = self._table.horizontalHeader()
        if hdr is not None:
            hdr.setStretchLastSection(True)
            hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(0, 220)
        self._table.setColumnWidth(2, 100)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        vhdr = self._table.verticalHeader()
        if vhdr is not None:
            vhdr.setDefaultSectionSize(36)
        layout.addWidget(self._table, 1)

        self._populate()

        self._overwrite_cb = QCheckBox("Sobrescribir todo")
        self._overwrite_cb.toggled.connect(self._on_overwrite_toggle)
        layout.addWidget(self._overwrite_cb)

        self._skip_cb = QCheckBox("Omitir todos los conflictos")
        self._skip_cb.toggled.connect(self._on_skip_toggle)
        layout.addWidget(self._skip_cb)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self._apply_btn = QPushButton("Aplicar seleccionados")
        self._apply_btn.setProperty("class", "primary")
        self._apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_btn.clicked.connect(self.accept)
        btn_row.addWidget(self._apply_btn)

        layout.addLayout(btn_row)

    def _populate(self) -> None:
        for c in self._conflicts:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(c.file_name))
            dest = str(c.destination_path) if c.destination_path else "—"
            self._table.setItem(row, 1, QTableWidgetItem(dest))
            action_text = c.action_applied.action_type.value if c.action_applied else "—"
            self._table.setItem(row, 2, QTableWidgetItem(action_text))

    def _on_overwrite_toggle(self, checked: bool) -> None:
        if checked:
            self._skip_cb.blockSignals(True)
            self._skip_cb.setChecked(False)
            self._skip_cb.blockSignals(False)

    def _on_skip_toggle(self, checked: bool) -> None:
        if checked:
            self._overwrite_cb.blockSignals(True)
            self._overwrite_cb.setChecked(False)
            self._overwrite_cb.blockSignals(False)

    def should_overwrite(self) -> bool:
        return self._overwrite_cb.isChecked()

    def should_skip_all(self) -> bool:
        return self._skip_cb.isChecked()
