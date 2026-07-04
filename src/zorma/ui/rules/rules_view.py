from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.models.rule import ActionType, ConditionType, Rule, RuleAction
from ...core.ports.rule_repository import RuleRepository
from ..shared.styles import COLORS, FONT_SIZES, SPACING, btn_error, btn_primary
from ..shared.toast import show_toast
from .rule_dialog import RuleDialog


class RulesView(QWidget):
    def __init__(self, data_dir: Optional[Path] = None, repo: Optional[RuleRepository] = None) -> None:
        super().__init__()
        self._data_dir = data_dir
        self._repo = repo
        self._rules_list: List[Rule] = []
        self._setup_ui()

    def set_repository(self, repo: RuleRepository) -> None:
        self._repo = repo
        self._load_rules()

    def _setup_ui(self) -> None:
        """Configura la interfaz de usuario de las reglas."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING["3xl"], SPACING["xl"], SPACING["3xl"], SPACING["xl"])
        layout.setSpacing(SPACING["lg"])

        layout.addLayout(self._create_header())
        layout.addWidget(self._create_description())
        layout.addWidget(self._create_table(), 1)
        layout.addWidget(self._create_empty_label())

    def _create_header(self) -> QHBoxLayout:
        """Crea el layout del encabezado.

        Returns:
            QHBoxLayout: Layout con título y botones.
        """
        header_row = QHBoxLayout()
        header = QLabel("Reglas de Clasificación")
        header.setStyleSheet(f"color: {COLORS['text_bright']}; font-size: {FONT_SIZES['2xl']}; font-weight: 700;")
        header_row.addWidget(header)

        self._add_btn = QPushButton("+ Nueva Regla")
        self._add_btn.setStyleSheet(btn_primary())
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.clicked.connect(self._new_rule)
        header_row.addStretch()
        header_row.addWidget(self._add_btn)

        self._delete_btn = QPushButton("Eliminar Seleccionada")
        self._delete_btn.setStyleSheet(btn_error())
        self._delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._delete_btn.clicked.connect(self._delete_selected)
        header_row.addWidget(self._delete_btn)
        return header_row

    def _create_description(self) -> QLabel:
        """Crea el label de descripción.

        Returns:
            QLabel: Label con la descripción.
        """
        info = QLabel(
            "Defina reglas para organizar sus archivos automáticamente "
            "por extensión, tamaño, fecha o nombre."
        )
        info.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: {FONT_SIZES['base']};")
        info.setWordWrap(True)
        return info

    def _create_table(self) -> QTableWidget:
        """Crea la tabla de reglas.

        Returns:
            QTableWidget: Tabla configurada.
        """
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(["Nombre", "Tipo", "Condición", "Acción", "Destino", "Estado"])
        hdr = self._table.horizontalHeader()
        if hdr is not None:
            hdr.setStretchLastSection(True)
            hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(1, 100)
        self._table.setColumnWidth(2, 150)
        self._table.setColumnWidth(3, 100)
        self._table.setColumnWidth(5, 80)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(f"""
            QTableWidget {{
                alternate-background-color: {COLORS["bg2"]};
            }}
        """)
        self._table.doubleClicked.connect(self._edit_selected)
        return self._table

    def _create_empty_label(self) -> QLabel:
        """Crea el label para cuando no hay reglas.

        Returns:
            QLabel: Label de estado vacío.
        """
        self._empty_label = QLabel("Sin reglas definidas.\nHaga clic en '+ Nueva Regla' para crear una.")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: {FONT_SIZES['md']}; padding: {SPACING['3xl']};"
        )
        self._empty_label.setWordWrap(True)
        return self._empty_label

    def _load_rules(self) -> None:
        if self._repo is None:
            return
        self._rules_list = self._repo.get_all()
        self._table.setRowCount(0)

        if not self._rules_list:
            self._table.hide()
            self._empty_label.show()
        else:
            self._table.show()
            self._empty_label.hide()
            for rule in self._rules_list:
                actions = self._repo.get_actions_for_rule(rule.id)
                action = actions[0] if actions else None
                self._add_rule_row(rule, action)

    def _add_rule_row(self, rule: Rule, action: Optional[RuleAction]) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)

        self._table.setItem(row, 0, QTableWidgetItem(rule.name))

        type_labels = {
            ConditionType.EXTENSION: "Extensión",
            ConditionType.SIZE: "Tamaño",
            ConditionType.DATE: "Fecha",
            ConditionType.NAME: "Nombre",
        }
        self._table.setItem(row, 1, QTableWidgetItem(type_labels.get(rule.condition_type, "")))

        self._table.setItem(row, 2, QTableWidgetItem(rule.condition_value))

        action_text = ""
        target = ""
        if action:
            action_labels = {
                ActionType.MOVE: "Mover",
                ActionType.COPY: "Copiar",
                ActionType.RENAME: "Renombrar",
            }
            action_text = action_labels.get(action.action_type, "")
            target = action.target_folder
        self._table.setItem(row, 3, QTableWidgetItem(action_text))
        self._table.setItem(row, 4, QTableWidgetItem(target))
        self._table.setItem(row, 5, QTableWidgetItem("Activa" if rule.enabled else "Desactivada"))

        item = self._table.item(row, 0)
        if item is not None:
            item.setData(Qt.ItemDataRole.UserRole, rule.id)

    def _find_rule_by_id(self, rule_id: str) -> Optional[Rule]:
        for r in self._rules_list:
            if r.id == rule_id:
                return r
        return None

    def _new_rule(self) -> None:
        if self._repo is None:
            return
        dlg = RuleDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_rule is not None:
            rule = dlg.result_rule
            action = dlg.result_action
            self._repo.save(rule)
            if action is not None:
                action.rule_id = rule.id
                self._repo.save_action(action)
            self._load_rules()
            show_toast(f"✓ Regla '{rule.name}' creada", COLORS["success"])

    def _edit_selected(self) -> None:
        if self._repo is None:
            return
        row = self._table.currentRow()
        if row < 0:
            return
        item = self._table.item(row, 0)
        if item is None:
            return
        rule_id = item.data(Qt.ItemDataRole.UserRole)
        rule = self._find_rule_by_id(rule_id)
        if rule is None:
            return
        actions = self._repo.get_actions_for_rule(rule.id)
        action = actions[0] if actions else None

        dlg = RuleDialog(self, rule=rule, action=action)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_rule is not None:
            edited = dlg.result_rule
            edited.id = rule.id
            self._repo.save(edited)
            if dlg.result_action is not None:
                dlg.result_action.rule_id = rule.id
                self._repo.save_action(dlg.result_action)
            self._load_rules()
            show_toast(f"✓ Regla '{rule.name}' actualizada", COLORS["success"])

    def _delete_selected(self) -> None:
        if self._repo is None:
            return
        row = self._table.currentRow()
        if row < 0:
            return
        item = self._table.item(row, 0)
        if item is None:
            return
        rule_id = item.data(Qt.ItemDataRole.UserRole)
        rule = self._find_rule_by_id(rule_id)
        if rule is None:
            return

        confirm = QMessageBox.question(
            self,
            "Eliminar Regla",
            f'¿Eliminar la regla "{rule.name}"?\nEsta acción no se puede deshacer.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self._repo.delete(rule_id)
            self._load_rules()
            show_toast(f"🗑 Regla '{rule.name}' eliminada", COLORS["warning"])
