from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.models.rule import ActionType, ConditionType, Rule, RuleAction
from ..shared.styles import COLORS, btn_primary, btn_secondary


class RuleDialog(QDialog):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        rule: Optional[Rule] = None,
        action: Optional[RuleAction] = None,
    ) -> None:
        super().__init__(parent)
        self._rule = rule
        self._action = action
        self._editing = rule is not None

        self.result_rule: Optional[Rule] = None
        self.result_action: Optional[RuleAction] = None

        self.setWindowTitle("Editar Regla" if self._editing else "Nueva Regla")
        self.setMinimumWidth(520)
        self.setModal(True)
        self._setup_ui()
        self._load_data()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        header = QLabel("Editar Regla" if self._editing else "Nueva Regla")
        header.setStyleSheet(f"color: {COLORS['text_bright']}; font-size: 20px; font-weight: 700;")
        layout.addWidget(header)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("ej. Videos, Documentos, Archivos Grandes...")
        form.addRow("Name:", self._name_input)

        self._enabled_check = QCheckBox("Enabled")
        self._enabled_check.setChecked(True)
        form.addRow("", self._enabled_check)

        self._condition_type = QComboBox()
        for ct in ConditionType:
            self._condition_type.addItem(ct.value.capitalize(), ct)
        self._condition_type.currentIndexChanged.connect(self._on_condition_type_changed)
        form.addRow("Condition Type:", self._condition_type)

        self._condition_value = QLineEdit()
        self._condition_value.setPlaceholderText(".mp4,.mkv,.avi")
        form.addRow("Condition Value:", self._condition_value)

        self._condition_hint = QLabel("Extensiones separadas por coma, ej. .mp4,.mkv,.avi")
        self._condition_hint.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        form.addRow("", self._condition_hint)

        self._action_type = QComboBox()
        for at in ActionType:
            self._action_type.addItem(at.value.capitalize(), at)
        self._action_type.currentIndexChanged.connect(self._on_action_type_changed)
        form.addRow("Action Type:", self._action_type)

        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)
        self._target_folder = QLineEdit()
        self._target_folder.setPlaceholderText(str(Path.home() / "Videos"))
        folder_row.addWidget(self._target_folder, 1)
        browse_btn = QPushButton("Examinar...")
        browse_btn.setStyleSheet(btn_secondary().replace("padding: 10px 22px;", "padding: 8px 16px;"))
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.clicked.connect(self._browse_folder)
        folder_row.addWidget(browse_btn)
        form.addRow("Target Folder:", folder_row)

        self._target_hint = QLabel("Usa {ext} para crear carpetas automáticas por extensión, ej. C:\\Documentos\\{ext}")
        self._target_hint.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        form.addRow("", self._target_hint)

        self._rename_pattern = QLineEdit()
        self._rename_pattern.setPlaceholderText("{name}_backup{ext}")
        form.addRow("Rename Pattern:", self._rename_pattern)

        layout.addLayout(form)
        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setStyleSheet(btn_secondary())
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Guardar Regla")
        save_btn.setStyleSheet(btn_primary())
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)

        self._update_hints()

    def _on_condition_type_changed(self) -> None:
        self._update_hints()

    def _on_action_type_changed(self) -> None:
        is_rename = self._action_type.currentData() == ActionType.RENAME
        self._rename_pattern.setVisible(is_rename)
        parent = self._rename_pattern.parent()
        if parent is not None:
            labels = parent.findChildren(QLabel)
            if labels:
                labels[-1].setVisible(is_rename)

    def _update_hints(self) -> None:
        ct = self._condition_type.currentData()
        hints = {
            ConditionType.EXTENSION: "Extensiones separadas por coma, ej. .mp4,.mkv,.avi",
            ConditionType.SIZE: 'ej. >100 MB, <1 GB, ==512 KB, >=10 MB',
            ConditionType.DATE: 'ej. <7 días, >30 días, <1 hora',
            ConditionType.NAME: 'ej. report (contiene) o report_* (glob)',
        }
        self._condition_hint.setText(hints.get(ct, ""))
        self._condition_value.setPlaceholderText({
            ConditionType.EXTENSION: ".mp4,.mkv,.avi",
            ConditionType.SIZE: ">100 MB",
            ConditionType.DATE: "<7 días",
            ConditionType.NAME: "report",
        }.get(ct, ""))

    def _browse_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta destino")
        if folder:
            self._target_folder.setText(folder)

    def _load_data(self) -> None:
        if self._rule is not None:
            self._name_input.setText(self._rule.name)
            self._enabled_check.setChecked(self._rule.enabled)
            idx = self._condition_type.findData(self._rule.condition_type)
            if idx >= 0:
                self._condition_type.setCurrentIndex(idx)
            self._condition_value.setText(self._rule.condition_value)

        if self._action is not None:
            idx = self._action_type.findData(self._action.action_type)
            if idx >= 0:
                self._action_type.setCurrentIndex(idx)
            self._target_folder.setText(self._action.target_folder)
            self._rename_pattern.setText(self._action.rename_pattern)

        self._on_action_type_changed()

    def _save(self) -> None:
        name = self._name_input.text().strip()
        if not name:
            self._name_input.setFocus()
            return

        self.result_rule = Rule(
            id=self._rule.id if self._rule else "",
            group_id=self._rule.group_id if self._rule else "",
            name=name,
            enabled=self._enabled_check.isChecked(),
            condition_type=self._condition_type.currentData(),
            condition_value=self._condition_value.text().strip(),
        )

        is_rename = self._action_type.currentData() == ActionType.RENAME
        self.result_action = RuleAction(
            id=self._action.id if self._action else "",
            rule_id=self.result_rule.id,
            action_type=self._action_type.currentData(),
            target_folder=self._target_folder.text().strip(),
            rename_pattern=self._rename_pattern.text().strip() if is_rename else "",
        )

        self.accept()
