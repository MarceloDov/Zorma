from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from ...adapters.persistence.zorma_repository import ZormaRepository
from ...core.models.accion_regla import AccionRegla
from ...core.models.regla import Regla
from ..shared.styles import COLORS


class RulesViewModel(QObject):
    rules_changed = pyqtSignal(list)
    toast_requested = pyqtSignal(str, str)

    def __init__(self, repo: ZormaRepository | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._repo = repo
        self._rules_list: list[Regla] = []

    def establecer_repositorio(self, repo: ZormaRepository) -> None:
        self._repo = repo
        self.cargar_reglas()

    def cargar_reglas(self) -> None:
        if self._repo is None:
            return
        self._rules_list = self._repo.obtener_todas_las_reglas()
        self.rules_changed.emit(self._rules_list)

    def obtener_reglas(self) -> list[Regla]:
        return self._rules_list

    def buscar_regla_por_id(self, rule_id: str) -> Regla | None:
        for r in self._rules_list:
            if r.id == rule_id:
                return r
        return None

    def obtener_acciones_de_regla(self, rule_id: str) -> list[AccionRegla]:
        if self._repo is None:
            return []
        return self._repo.obtener_acciones_de_regla(rule_id)

    def crear_regla(self, rule: Regla, action: AccionRegla | None) -> None:
        if self._repo is None:
            return
        self._repo.guardar_regla(rule)
        if action is not None:
            action.id_regla = rule.id
            self._repo.guardar_accion(action)
        self.cargar_reglas()
        self.toast_requested.emit(f"✓ Regla '{rule.nombre}' creada", COLORS["success"])

    def actualizar_regla(self, rule: Regla, action: AccionRegla | None) -> None:
        if self._repo is None:
            return
        self._repo.guardar_regla(rule)
        if action is not None:
            action.id_regla = rule.id
            self._repo.guardar_accion(action)
        self.cargar_reglas()
        self.toast_requested.emit(f"✓ Regla '{rule.nombre}' actualizada", COLORS["success"])

    def eliminar_regla(self, rule_id: str, rule_name: str) -> None:
        if self._repo is None:
            return
        self._repo.eliminar_regla(rule_id)
        self.cargar_reglas()
        self.toast_requested.emit(f"🗑 Regla '{rule_name}' eliminada", COLORS["warning"])

    def reordenar_reglas(self, ordered_pairs: list[tuple[str, int]]) -> None:
        if self._repo is None:
            return
        for rule_id, row in ordered_pairs:
            rule = self.buscar_regla_por_id(rule_id)
            if rule is not None:
                rule.prioridad = row * 10
                self._repo.guardar_regla(rule)
        self.cargar_reglas()
        self.toast_requested.emit("✓ Orden de reglas actualizado", COLORS["success"])
