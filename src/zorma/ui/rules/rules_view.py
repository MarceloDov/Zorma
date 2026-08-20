from __future__ import annotations

from pathlib import Path

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

from ...adapters.persistence.zorma_repository import ZormaRepository
from ...core.models.accion_regla import AccionRegla
from ...core.models.enums import TipoAccion, TipoCondicion
from ...core.models.regla import Regla
from ..shared.styles import SPACING
from ..shared.toast import mostrar_toast
from ..shared.widgets import EmptyState
from .rule_dialog import RuleDialog
from .rules_viewmodel import RulesViewModel


class RulesView(QWidget):
    def __init__(self, data_dir: Path | None = None, repo: ZormaRepository | None = None) -> None:
        super().__init__()
        self._vm = RulesViewModel(repo)
        self._configurar_ui()
        self._conectar_vm()
        if repo is not None:
            self._vm.cargar_reglas()

    def establecer_repositorio(self, repo: ZormaRepository) -> None:
        self._vm.establecer_repositorio(repo)

    def _conectar_vm(self) -> None:
        self._vm.rules_changed.connect(self._al_cambiar_reglas)
        self._vm.toast_requested.connect(mostrar_toast)

    def _cargar_reglas(self) -> None:
        self._vm.cargar_reglas()

    def _al_cambiar_reglas(self, rules: list[Regla]) -> None:
        self._table.setRowCount(0)
        if not rules:
            self._table.hide()
            self._empty_state.show()
        else:
            self._table.show()
            self._empty_state.hide()
            for i, rule in enumerate(rules):
                actions = self._vm.obtener_acciones_de_regla(rule.id)
                action = actions[0] if actions else None
                self._agregar_fila_regla(i, rule, action)

    def _configurar_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING["3xl"], SPACING["xl"], SPACING["3xl"], SPACING["xl"])
        layout.setSpacing(SPACING["lg"])

        layout.addLayout(self._crear_encabezado())
        layout.addWidget(self._crear_descripcion())
        layout.addWidget(self._crear_tabla(), 1)
        layout.addWidget(self._crear_etiqueta_vacia())

    def _crear_encabezado(self) -> QHBoxLayout:
        header_row = QHBoxLayout()
        header = QLabel("Reglas de Clasificación")
        header.setObjectName("rules_header")
        header_row.addWidget(header)

        self._add_btn = QPushButton("+ Nueva Regla")
        self._add_btn.setObjectName("add_btn")
        self._add_btn.setProperty("class", "primary")
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.setAccessibleName("Nueva regla")
        self._add_btn.clicked.connect(self._nueva_regla)
        header_row.addStretch()
        header_row.addWidget(self._add_btn)

        self._delete_btn = QPushButton("Eliminar Seleccionada")
        self._delete_btn.setObjectName("delete_btn")
        self._delete_btn.setProperty("class", "error")
        self._delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._delete_btn.setAccessibleName("Eliminar regla seleccionada")
        self._delete_btn.clicked.connect(self._eliminar_seleccionada)
        header_row.addWidget(self._delete_btn)
        return header_row

    def _crear_descripcion(self) -> QLabel:
        info = QLabel(
            "Defina reglas para organizar sus archivos automáticamente "
            "por extensión, tamaño, fecha o nombre."
        )
        info.setObjectName("rules_description")
        info.setWordWrap(True)
        return info

    def _crear_tabla(self) -> QTableWidget:
        self._table = QTableWidget(0, 7)
        self._table.setObjectName("rules_table")
        self._table.setHorizontalHeaderLabels(["#", "Nombre", "Tipo", "Condición", "Acción", "Destino", "Estado"])
        hdr = self._table.horizontalHeader()
        if hdr is not None:
            hdr.setStretchLastSection(True)
            hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(0, 36)
        self._table.setColumnWidth(2, 100)
        self._table.setColumnWidth(3, 150)
        self._table.setColumnWidth(4, 100)
        self._table.setColumnWidth(6, 80)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.doubleClicked.connect(self._editar_seleccionada)
        return self._table

    def _crear_etiqueta_vacia(self) -> EmptyState:
        self._empty_state = EmptyState(
            icon="📝",
            title="Sin reglas definidas",
            description="Cree su primera regla para empezar a clasificar archivos automáticamente.",
            button_text="+ Primera regla",
        )
        self._empty_state.establecer_callback_boton(self._nueva_regla)
        return self._empty_state

    def _agregar_fila_regla(self, row: int, rule: Regla, action: AccionRegla | None) -> None:
        self._table.insertRow(row)

        num_item = QTableWidgetItem(str(row + 1))
        num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        num_item.setData(Qt.ItemDataRole.UserRole, rule.id)
        self._table.setItem(row, 0, num_item)

        self._table.setItem(row, 1, QTableWidgetItem(rule.nombre))

        type_labels = {
            TipoCondicion.EXTENSION: "Extensión",
            TipoCondicion.TAMANIO: "Tamaño",
            TipoCondicion.FECHA: "Fecha",
            TipoCondicion.NOMBRE: "Nombre",
        }
        self._table.setItem(row, 2, QTableWidgetItem(type_labels.get(rule.tipo_condicion, "")))

        self._table.setItem(row, 3, QTableWidgetItem(rule.valor_condicion))

        action_text = ""
        target = ""
        if action:
            action_labels = {
                TipoAccion.MOVER: "Mover",
                TipoAccion.COPIAR: "Copiar",
                TipoAccion.RENOMBRAR: "Renombrar",
            }
            action_text = action_labels.get(action.tipo_accion, "")
            target = action.carpeta_destino
        self._table.setItem(row, 4, QTableWidgetItem(action_text))
        self._table.setItem(row, 5, QTableWidgetItem(target))
        self._table.setItem(row, 6, QTableWidgetItem("Activa" if rule.habilitada else "Desactivada"))

    def _nueva_regla(self) -> None:
        dlg = RuleDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_rule is not None:
            self._vm.crear_regla(dlg.result_rule, dlg.result_action)

    def _editar_seleccionada(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            return
        item = self._table.item(row, 0)
        if item is None:
            return
        rule_id = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(rule_id, str):
            return
        rule = self._vm.buscar_regla_por_id(rule_id)
        if rule is None:
            return
        actions = self._vm.obtener_acciones_de_regla(rule.id)
        action = actions[0] if actions else None

        dlg = RuleDialog(self, rule=rule, action=action)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_rule is not None:
            edited = dlg.result_rule
            edited.id = rule.id
            self._vm.actualizar_regla(edited, dlg.result_action)

    def _eliminar_seleccionada(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            return
        item = self._table.item(row, 0)
        if item is None:
            return
        rule_id = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(rule_id, str):
            return
        rule = self._vm.buscar_regla_por_id(rule_id)
        if rule is None:
            return

        confirm = QMessageBox.question(
            self,
            "Eliminar Regla",
            f'¿Eliminar la regla "{rule.nombre}"?\nEsta acción no se puede deshacer.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self._vm.eliminar_regla(rule_id, rule.nombre)


