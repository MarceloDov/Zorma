from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...adapters.persistence.zorma_repository import ZormaRepository
from ..shared.styles import SPACING
from ..shared.widgets import EmptyState

PAGE_SIZE = 100


class HistoryView(QWidget):
    def __init__(self, data_dir: Path | None = None, repo: ZormaRepository | None = None) -> None:
        super().__init__()
        self._data_dir = data_dir or Path.home() / ".zorma"
        self._repo = repo
        self._all_entries: list[dict] = []
        self._visible_count = 0
        self._configurar_ui()

    def _configurar_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING["3xl"], SPACING["2xl"], SPACING["3xl"], SPACING["2xl"])
        layout.setSpacing(SPACING["xl"])

        header_row = QHBoxLayout()
        header = QLabel("Historial de Clasificación")
        header.setObjectName("history_header")
        header_row.addWidget(header)

        refresh_btn = QPushButton("⟳ Actualizar")
        refresh_btn.setProperty("class", "secondary")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setAccessibleName("Actualizar historial")
        refresh_btn.clicked.connect(self._cargar_historial)
        header_row.addStretch()
        header_row.addWidget(refresh_btn)
        layout.addLayout(header_row)

        info = QLabel("Revise todos los movimientos de archivos y resultados de clasificación.")
        info.setObjectName("history_info")
        info.setWordWrap(True)
        layout.addWidget(info)

        self._table = QTableWidget(0, 6)
        self._table.setObjectName("history_table")
        self._table.setHorizontalHeaderLabels(["Archivo", "Regla", "Acción", "Estado", "Hora", "Origen"])
        hdr = self._table.horizontalHeader()
        if hdr is not None:
            hdr.setStretchLastSection(True)
        self._table.setColumnWidth(0, 220)
        self._table.setColumnWidth(1, 160)
        self._table.setColumnWidth(2, 80)
        self._table.setColumnWidth(3, 100)
        self._table.setColumnWidth(4, 120)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table, 1)

        self._load_more_btn = QPushButton("Cargar más…")
        self._load_more_btn.setProperty("class", "secondary")
        self._load_more_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._load_more_btn.setAccessibleName("Cargar más registros")
        self._load_more_btn.clicked.connect(self._cargar_mas)
        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(self._load_more_btn)
        button_row.addStretch()
        button_layout = QVBoxLayout()
        button_layout.addLayout(button_row)
        layout.addLayout(button_layout)

        self._empty_state = EmptyState(
            icon="📋",
            title="Sin historial aún",
            description="Inicie el monitor para empezar a registrar clasificaciones de archivos.",
        )
        layout.addWidget(self._empty_state)

        self._cargar_historial()

    def _cargar_historial(self) -> None:
        self._table.setRowCount(0)
        self._visible_count = 0

        if self._repo is None:
            self._table.hide()
            self._load_more_btn.hide()
            self._empty_state.show()
            return

        results = self._repo.obtener_historial()
        if not results:
            self._table.hide()
            self._load_more_btn.hide()
            self._empty_state.show()
            return

        self._all_entries = []
        for r in reversed(results):
            self._all_entries.append({
                "file_name": r.nombre_archivo,
                "source_path": str(r.ruta_origen) if r.ruta_origen else "",
                "destination_path": str(r.ruta_destino) if r.ruta_destino else "",
                "rule_name": r.regla_aplicada.nombre if r.regla_aplicada else "",
                "action_applied": r.accion_aplicada.tipo_accion.value if r.accion_aplicada else "",
                "status": r.estado.value,
                "error_message": r.mensaje_error,
                "timestamp": r.marca_tiempo.isoformat(),
            })

        self._table.show()
        self._empty_state.hide()
        self._cargar_mas()

    def _cargar_mas(self) -> None:
        start = self._visible_count
        batch = list(reversed(self._all_entries))[start:start + PAGE_SIZE]
        if not batch:
            self._load_more_btn.hide()
            return

        for entry in batch:
            row = self._table.rowCount()
            self._table.insertRow(row)

            self._table.setItem(row, 0, QTableWidgetItem(entry.get("file_name", "")))
            rule_name = entry.get("rule_name", "")
            if not rule_name and "rule_applied" in entry:
                r = entry["rule_applied"]
                rule_name = r.get("name", "") if isinstance(r, dict) else str(r)
            self._table.setItem(row, 1, QTableWidgetItem(rule_name))

            action = entry.get("action_applied", "")
            if isinstance(action, dict):
                action = action.get("action_type", "")
            self._table.setItem(row, 2, QTableWidgetItem(str(action)))

            status = entry.get("status", entry.get("event_type", ""))
            self._table.setItem(row, 3, QTableWidgetItem(str(status)))

            ts = entry.get("timestamp", "")
            if ts:
                try:
                    ts = datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError):
                    pass
            self._table.setItem(row, 4, QTableWidgetItem(str(ts)))

            src = entry.get("source_path", "")
            self._table.setItem(row, 5, QTableWidgetItem(str(src)))

        self._visible_count += len(batch)
        remaining = len(self._all_entries) - self._visible_count
        self._load_more_btn.setText(f"Cargar más… ({remaining} restantes)" if remaining > 0 else "Sin más registros")
        self._load_more_btn.setVisible(remaining > 0)
