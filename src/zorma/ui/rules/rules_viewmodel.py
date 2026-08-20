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

    def set_repository(self, repo: ZormaRepository) -> None:
        self._repo = repo
        self.load_rules()

    def load_rules(self) -> None:
        if self._repo is None:
            return
        self._rules_list = self._repo.get_all_rules()
        self.rules_changed.emit(self._rules_list)

    def get_rules(self) -> list[Regla]:
        return self._rules_list

    def find_rule_by_id(self, rule_id: str) -> Regla | None:
        for r in self._rules_list:
            if r.id == rule_id:
                return r
        return None

    def get_actions_for_rule(self, rule_id: str) -> list[AccionRegla]:
        if self._repo is None:
            return []
        return self._repo.get_actions_for_rule(rule_id)

    def create_rule(self, rule: Regla, action: AccionRegla | None) -> None:
        if self._repo is None:
            return
        self._repo.save_rule(rule)
        if action is not None:
            action.id_regla = rule.id
            self._repo.save_action(action)
        self.load_rules()
        self.toast_requested.emit(f"✓ Regla '{rule.nombre}' creada", COLORS["success"])

    def update_rule(self, rule: Regla, action: AccionRegla | None) -> None:
        if self._repo is None:
            return
        self._repo.save_rule(rule)
        if action is not None:
            action.id_regla = rule.id
            self._repo.save_action(action)
        self.load_rules()
        self.toast_requested.emit(f"✓ Regla '{rule.nombre}' actualizada", COLORS["success"])

    def delete_rule(self, rule_id: str, rule_name: str) -> None:
        if self._repo is None:
            return
        self._repo.delete_rule(rule_id)
        self.load_rules()
        self.toast_requested.emit(f"🗑 Regla '{rule_name}' eliminada", COLORS["warning"])

    def reorder_rules(self, ordered_pairs: list[tuple[str, int]]) -> None:
        if self._repo is None:
            return
        for rule_id, row in ordered_pairs:
            rule = self.find_rule_by_id(rule_id)
            if rule is not None:
                rule.prioridad = row * 10
                self._repo.save_rule(rule)
        self.load_rules()
        self.toast_requested.emit("✓ Orden de reglas actualizado", COLORS["success"])
