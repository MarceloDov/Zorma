from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

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

from ..shared.styles import COLORS, btn_secondary


class HistoryView(QWidget):
    def __init__(self, data_dir: Optional[Path] = None) -> None:
        super().__init__()
        self._data_dir = data_dir or Path.home() / ".zorma"
        self._log_file = self._data_dir / "history.jsonl"
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        header_row = QHBoxLayout()
        header = QLabel("Historial de Clasificación")
        header.setStyleSheet(f"color: {COLORS['text_bright']}; font-size: 26px; font-weight: 700;")
        header_row.addWidget(header)

        refresh_btn = QPushButton("⟳ Actualizar")
        refresh_btn.setStyleSheet(btn_secondary())
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self._load_history)
        header_row.addStretch()
        header_row.addWidget(refresh_btn)
        layout.addLayout(header_row)

        info = QLabel("Revise todos los movimientos de archivos y resultados de clasificación.")
        info.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 13px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        self._table = QTableWidget(0, 6)
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
        self._table.setStyleSheet(f"""
            QTableWidget {{
                alternate-background-color: {COLORS["bg2"]};
            }}
        """)
        layout.addWidget(self._table, 1)

        self._empty_label = QLabel(
            "No hay historial disponible aún.\n"
            "Inicie el monitor para registrar clasificaciones."
        )
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 14px; padding: 40px;"
        )
        self._empty_label.setWordWrap(True)
        layout.addWidget(self._empty_label)

        self._load_history()

    def _load_history(self) -> None:
        self._table.setRowCount(0)

        if not self._log_file.exists():
            self._table.hide()
            self._empty_label.show()
            return

        entries: List[Dict[str, Any]] = []
        with self._log_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        if not entries:
            self._table.hide()
            self._empty_label.show()
            return

        self._table.show()
        self._empty_label.hide()

        for entry in reversed(entries):
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
