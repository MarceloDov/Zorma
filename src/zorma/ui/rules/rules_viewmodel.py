from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from ...adapters.persistence.zorma_repository import ZormaRepository
from ...core.models.rule import Rule, RuleAction
from ..shared.styles import COLORS


class RulesViewModel(QObject):
    rules_changed = pyqtSignal(list)
    toast_requested = pyqtSignal(str, str)

    def __init__(self, repo: Optional[ZormaRepository] = None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._repo = repo
        self._rules_list: List[Rule] = []

    def set_repository(self, repo: ZormaRepository) -> None:
        self._repo = repo
        self.load_rules()

    def load_rules(self) -> None:
        if self._repo is None:
            return
        self._rules_list = self._repo.get_all_rules()
        self.rules_changed.emit(self._rules_list)

    def get_rules(self) -> List[Rule]:
        return self._rules_list

    def find_rule_by_id(self, rule_id: str) -> Optional[Rule]:
        for r in self._rules_list:
            if r.id == rule_id:
                return r
        return None

    def get_actions_for_rule(self, rule_id: str) -> List[RuleAction]:
        if self._repo is None:
            return []
        return self._repo.get_actions_for_rule(rule_id)

    def create_rule(self, rule: Rule, action: Optional[RuleAction]) -> None:
        if self._repo is None:
            return
        self._repo.save_rule(rule)
        if action is not None:
            action.rule_id = rule.id
            self._repo.save_action(action)
        self.load_rules()
        self.toast_requested.emit(f"✓ Regla '{rule.name}' creada", COLORS["success"])

    def update_rule(self, rule: Rule, action: Optional[RuleAction]) -> None:
        if self._repo is None:
            return
        self._repo.save_rule(rule)
        if action is not None:
            action.rule_id = rule.id
            self._repo.save_action(action)
        self.load_rules()
        self.toast_requested.emit(f"✓ Regla '{rule.name}' actualizada", COLORS["success"])

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
                rule.priority = row * 10
                self._repo.save_rule(rule)
        self.load_rules()
        self.toast_requested.emit("✓ Orden de reglas actualizado", COLORS["success"])
