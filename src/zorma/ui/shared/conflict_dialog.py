from __future__ import annotations

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

from ...core.models.resultado_clasificacion import ResultadoClasificacion
from ..shared.styles import SPACING


class ConflictDialog(QDialog):
    def __init__(
        self,
        conflicts: list[ResultadoClasificacion],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._conflicts = conflicts
        self._overwrite_all = False
        self._skip_all = False
        self.setWindowTitle("Conflictos Detectados")
        self.setMinimumSize(640, 450)
        self.setModal(True)
        self._configurar_ui()

    def _configurar_ui(self) -> None:
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

        self._poblar()

        self._overwrite_cb = QCheckBox("Sobrescribir todo")
        self._overwrite_cb.toggled.connect(self._al_alternar_sobrescribir)
        layout.addWidget(self._overwrite_cb)

        self._skip_cb = QCheckBox("Omitir todos los conflictos")
        self._skip_cb.toggled.connect(self._al_alternar_omitir)
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

    def _poblar(self) -> None:
        for c in self._conflicts:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(c.nombre_archivo))
            dest = str(c.ruta_destino) if c.ruta_destino else "—"
            self._table.setItem(row, 1, QTableWidgetItem(dest))
            action_text = c.accion_aplicada.tipo_accion.value if c.accion_aplicada else "—"
            self._table.setItem(row, 2, QTableWidgetItem(action_text))

    def _al_alternar_sobrescribir(self, checked: bool) -> None:
        if checked:
            self._skip_cb.blockSignals(True)
            self._skip_cb.setChecked(False)
            self._skip_cb.blockSignals(False)

    def _al_alternar_omitir(self, checked: bool) -> None:
        if checked:
            self._overwrite_cb.blockSignals(True)
            self._overwrite_cb.setChecked(False)
            self._overwrite_cb.blockSignals(False)

    def debe_sobrescribir(self) -> bool:
        return self._overwrite_cb.isChecked()

    def debe_omitir_todo(self) -> bool:
        return self._skip_cb.isChecked()
