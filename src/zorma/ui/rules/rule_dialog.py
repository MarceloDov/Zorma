from __future__ import annotations

import re
from pathlib import Path

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

from ...core.models.accion_regla import AccionRegla
from ...core.models.enums import TipoAccion, TipoCondicion
from ...core.models.regla import Regla

CONDITION_LABELS = {
    TipoCondicion.EXTENSION: "Extensión",
    TipoCondicion.TAMANIO: "Tamaño",
    TipoCondicion.FECHA: "Fecha",
    TipoCondicion.NOMBRE: "Nombre",
}

ACTION_LABELS = {
    TipoAccion.MOVER: "Mover",
    TipoAccion.COPIAR: "Copiar",
    TipoAccion.RENOMBRAR: "Renombrar",
}


class RuleDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        rule: Regla | None = None,
        action: AccionRegla | None = None,
    ) -> None:
        super().__init__(parent)
        self._rule = rule
        self._action = action
        self._editing = rule is not None

        self.result_rule: Regla | None = None
        self.result_action: AccionRegla | None = None

        self.setWindowTitle("Editar Regla" if self._editing else "Nueva Regla")
        self.setMinimumWidth(520)
        self.setModal(True)
        self._configurar_ui()
        self._cargar_datos()

    def _configurar_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        header = QLabel("Editar Regla" if self._editing else "Nueva Regla")
        header.setObjectName("rule_header")
        layout.addWidget(header)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("ej. Videos, Documentos, Archivos Grandes...")
        self._name_input.setAccessibleName("Nombre de la regla")
        form.addRow("Nombre:", self._name_input)

        self._enabled_check = QCheckBox("Habilitada")
        self._enabled_check.setChecked(True)
        form.addRow("", self._enabled_check)

        self._condition_type = QComboBox()
        for ct in TipoCondicion:
            self._condition_type.addItem(CONDITION_LABELS[ct], ct)
        self._condition_type.setAccessibleName("Tipo de condición")
        self._condition_type.currentIndexChanged.connect(self._al_cambiar_tipo_condicion)
        form.addRow("Tipo de condición:", self._condition_type)

        self._condition_value = QLineEdit()
        self._condition_value.setPlaceholderText(".mp4,.mkv,.avi")
        self._condition_value.setAccessibleName("Valor de condición")
        form.addRow("Valor de condición:", self._condition_value)

        self._condition_hint = QLabel("Extensiones separadas por coma, ej. .mp4,.mkv,.avi")
        self._condition_hint.setObjectName("hint_label")
        form.addRow("", self._condition_hint)

        self._action_type = QComboBox()
        for at in TipoAccion:
            self._action_type.addItem(ACTION_LABELS[at], at)
        self._action_type.currentIndexChanged.connect(self._al_cambiar_tipo_accion)
        form.addRow("Tipo de acción:", self._action_type)

        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)
        self._target_folder = QLineEdit()
        self._target_folder.setPlaceholderText(str(Path.home() / "Videos"))
        self._target_folder.setAccessibleName("Carpeta destino")
        folder_row.addWidget(self._target_folder, 1)
        browse_btn = QPushButton("Examinar...")
        browse_btn.setObjectName("browse_btn")
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.clicked.connect(self._explorar_carpeta)
        folder_row.addWidget(browse_btn)
        form.addRow("Carpeta destino:", folder_row)

        self._target_hint = QLabel("Usa {ext} para crear carpetas automáticas por extensión, ej. C:\\Documentos\\{ext} → Documentos\\.txt")
        self._target_hint.setObjectName("hint_label")
        form.addRow("", self._target_hint)

        self._rename_pattern = QLineEdit()
        self._rename_pattern.setPlaceholderText("{name}_backup{ext}")
        self._rename_pattern.setAccessibleName("Patrón de renombrado")
        self._rename_pattern.textChanged.connect(self._validar)
        form.addRow("Patrón de renombrado:", self._rename_pattern)

        self._error_label = QLabel("")
        self._error_label.setObjectName("error_label")
        layout.addWidget(self._error_label)

        self._name_input.textChanged.connect(self._validar)
        self._target_folder.textChanged.connect(self._validar)

        layout.addLayout(form)
        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self._save_btn = QPushButton("Guardar Regla")
        self._save_btn.setProperty("class", "primary")
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.clicked.connect(self._guardar)
        btn_row.addWidget(self._save_btn)

        layout.addLayout(btn_row)

        self._validar()
        self._actualizar_sugerencias()

    _SIZE_RE = re.compile(r"(<=?|>=?|==?)\s*(\d+)\s*(KB|MB|GB)?$", re.IGNORECASE)
    _DATE_RE = re.compile(r"(<|>|==?)\s*(\d+)\s*(days|hours|minutes|días|dias|horas|minutos)?$", re.IGNORECASE)

    def _validar(self) -> None:
        name = self._name_input.text().strip()
        target = self._target_folder.text().strip()
        cond_val = self._condition_value.text().strip()
        cond_type = self._condition_type.currentData()
        action_type = self._action_type.currentData()

        errors: list[str] = []

        if not name:
            errors.append("El nombre de la regla es obligatorio.")

        if not cond_val:
            errors.append("El valor de la condición no puede estar vacío.")
        elif cond_type == TipoCondicion.EXTENSION:
            parts = [e.strip() for e in cond_val.split(",")]
            if not parts or not any(parts):
                errors.append("Indique al menos una extensión, ej. .mp4,.mkv")
        elif cond_type == TipoCondicion.TAMANIO:
            if not self._SIZE_RE.match(cond_val):
                errors.append("Formato inválido. Ej: >100 MB, <=1 GB, ==512 KB")
        elif cond_type == TipoCondicion.FECHA:
            if not self._DATE_RE.match(cond_val):
                errors.append("Formato inválido. Ej: <7 días, >30 días, <1 hora")
        elif cond_type == TipoCondicion.NOMBRE:
            if not cond_val:
                errors.append("El valor del nombre no puede estar vacío.")

        is_move_copy = action_type in (TipoAccion.MOVER, TipoAccion.COPIAR)
        is_rename = action_type == TipoAccion.RENOMBRAR
        if is_move_copy and not target:
            errors.append("La carpeta destino es obligatoria para mover o copiar.")
        if is_rename:
            pattern = self._rename_pattern.text().strip()
            if not pattern:
                errors.append("El patrón de renombrado no puede estar vacío.")
            elif "{name}" not in pattern and "{ext}" not in pattern:
                errors.append('El patrón debe incluir {name} y/o {ext}, ej. "{name}_backup{ext}"')

        self._error_label.setText("\n".join(errors))
        self._save_btn.setEnabled(not errors)

    def _al_cambiar_tipo_condicion(self) -> None:

        self._actualizar_sugerencias()

    def _al_cambiar_tipo_accion(self) -> None:
        is_rename = self._action_type.currentData() == TipoAccion.RENOMBRAR
        self._rename_pattern.setVisible(is_rename)
        parent = self._rename_pattern.parent()
        if parent is not None:
            labels = parent.findChildren(QLabel)
            if labels:
                labels[-1].setVisible(is_rename)

    def _actualizar_sugerencias(self) -> None:
        ct = self._condition_type.currentData()
        hints = {
            TipoCondicion.EXTENSION: "Extensiones separadas por coma, ej. .mp4,.mkv,.avi",
            TipoCondicion.TAMANIO: 'ej. >100 MB, <1 GB, ==512 KB, >=10 MB',
            TipoCondicion.FECHA: 'ej. <7 días, >30 días, <1 hora',
            TipoCondicion.NOMBRE: 'ej. report (contiene) o report_* (glob)',
        }
        self._condition_hint.setText(hints.get(ct, ""))
        self._condition_value.setPlaceholderText({
            TipoCondicion.EXTENSION: ".mp4,.mkv,.avi",
            TipoCondicion.TAMANIO: ">100 MB",
            TipoCondicion.FECHA: "<7 días",
            TipoCondicion.NOMBRE: "report",
        }.get(ct, ""))

    def _explorar_carpeta(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta destino")
        if folder:
            self._target_folder.setText(folder)

    def _cargar_datos(self) -> None:
        if self._rule is not None:
            self._name_input.setText(self._rule.nombre)
            self._enabled_check.setChecked(self._rule.habilitada)
            idx = self._condition_type.findData(self._rule.tipo_condicion)
            if idx >= 0:
                self._condition_type.setCurrentIndex(idx)
            self._condition_value.setText(self._rule.valor_condicion)

        if self._action is not None:
            idx = self._action_type.findData(self._action.tipo_accion)
            if idx >= 0:
                self._action_type.setCurrentIndex(idx)
            self._target_folder.setText(self._action.carpeta_destino)
            self._rename_pattern.setText(self._action.patron_renombre)

        self._al_cambiar_tipo_accion()

    def _guardar(self) -> None:
        name = self._name_input.text().strip()
        if not name:
            self._name_input.setFocus()
            return

        self.result_rule = Regla(
            id=self._rule.id if self._rule else "",
            id_grupo=self._rule.id_grupo if self._rule else "",
            nombre=name,
            habilitada=self._enabled_check.isChecked(),
            tipo_condicion=self._condition_type.currentData(),
            valor_condicion=self._condition_value.text().strip(),
        )

        is_rename = self._action_type.currentData() == TipoAccion.RENOMBRAR
        self.result_action = AccionRegla(
            id=self._action.id if self._action else "",
            id_regla=self.result_rule.id,
            tipo_accion=self._action_type.currentData(),
            carpeta_destino=self._target_folder.text().strip(),
            patron_renombre=self._rename_pattern.text().strip() if is_rename else "",
        )

        self.accept()
