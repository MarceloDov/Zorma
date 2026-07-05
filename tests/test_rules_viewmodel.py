from __future__ import annotations

from unittest.mock import MagicMock, create_autospec

import pytest

from zorma.adapters.persistence.zorma_repository import ZormaRepository
from zorma.core.models.rule import ActionType, ConditionType, Rule, RuleAction
from zorma.ui.rules.rules_viewmodel import RulesViewModel


@pytest.fixture
def repo() -> MagicMock:
    return create_autospec(ZormaRepository, instance=True)


@pytest.fixture
def vm(repo: MagicMock) -> RulesViewModel:
    return RulesViewModel(repo)


class TestRulesViewModel:
    def test_load_rules_emits_rules_changed(self, vm: RulesViewModel, repo: MagicMock):
        rules = [Rule(name="Videos", condition_type=ConditionType.EXTENSION, condition_value=".mp4")]
        repo.get_all_rules.return_value = rules
        emitted = []
        vm.rules_changed.connect(lambda r: emitted.append(r))
        vm.load_rules()
        assert len(emitted) == 1
        assert emitted[0] == rules

    def test_load_rules_noop_when_no_repo(self):
        vm = RulesViewModel(None)
        emitted = []
        vm.rules_changed.connect(lambda r: emitted.append(r))
        vm.load_rules()
        assert len(emitted) == 0

    def test_find_rule_by_id(self, vm: RulesViewModel, repo: MagicMock):
        rule = Rule(name="Test", condition_type=ConditionType.EXTENSION, condition_value=".txt")
        repo.get_all_rules.return_value = [rule]
        vm.load_rules()
        found = vm.find_rule_by_id(rule.id)
        assert found is rule

    def test_find_rule_by_id_not_found(self, vm: RulesViewModel, repo: MagicMock):
        repo.get_all_rules.return_value = []
        vm.load_rules()
        assert vm.find_rule_by_id("nonexistent") is None

    def test_create_rule_saves_and_reloads(self, vm: RulesViewModel, repo: MagicMock):
        rule = Rule(name="New", condition_type=ConditionType.EXTENSION, condition_value=".mp3")
        action = RuleAction(action_type=ActionType.MOVE, target_folder="/music")
        repo.get_all_rules.return_value = [rule]
        vm.create_rule(rule, action)
        repo.save_rule.assert_called_once_with(rule)
        repo.save_action.assert_called_once_with(action)
        assert action.rule_id == rule.id

    def test_create_rule_without_action(self, vm: RulesViewModel, repo: MagicMock):
        rule = Rule(name="New", condition_type=ConditionType.EXTENSION, condition_value=".mp3")
        repo.get_all_rules.return_value = [rule]
        vm.create_rule(rule, None)
        repo.save_rule.assert_called_once()
        repo.save_action.assert_not_called()

    def test_update_rule_saves(self, vm: RulesViewModel, repo: MagicMock):
        rule = Rule(name="Old", condition_type=ConditionType.EXTENSION, condition_value=".txt")
        action = RuleAction(action_type=ActionType.MOVE, target_folder="/docs")
        repo.get_all_rules.return_value = [rule]
        vm.update_rule(rule, action)
        repo.save_rule.assert_called_once_with(rule)
        repo.save_action.assert_called_once()

    def test_delete_rule_deletes_and_reloads(self, vm: RulesViewModel, repo: MagicMock):
        rule = Rule(name="DeleteMe", condition_type=ConditionType.EXTENSION, condition_value=".zip")
        repo.get_all_rules.return_value = [rule]
        vm.load_rules()
        repo.get_all_rules.return_value = []
        vm.delete_rule(rule.id, rule.name)
        repo.delete_rule.assert_called_once_with(rule.id)

    def test_reorder_rules_saves_priorities(self, vm: RulesViewModel, repo: MagicMock):
        r1 = Rule(name="A", condition_type=ConditionType.EXTENSION, condition_value=".txt", priority=0)
        r2 = Rule(name="B", condition_type=ConditionType.EXTENSION, condition_value=".pdf", priority=10)
        repo.get_all_rules.return_value = [r1, r2]
        vm.load_rules()
        vm.reorder_rules([(r2.id, 0), (r1.id, 1)])
        assert r2.priority == 0
        assert r1.priority == 10
        assert repo.save_rule.call_count >= 2

    def test_get_actions_for_rule(self, vm: RulesViewModel, repo: MagicMock):
        rule = Rule(name="Test", condition_type=ConditionType.EXTENSION, condition_value=".txt")
        action = RuleAction(action_type=ActionType.MOVE, target_folder="/dest")
        repo.get_actions_for_rule.return_value = [action]
        result = vm.get_actions_for_rule(rule.id)
        assert result == [action]
        repo.get_actions_for_rule.assert_called_once_with(rule.id)

    def test_toast_emitted_on_create(self, vm: RulesViewModel, repo: MagicMock):
        rule = Rule(name="New", condition_type=ConditionType.EXTENSION, condition_value=".txt")
        repo.get_all_rules.return_value = [rule]
        emitted = []
        vm.toast_requested.connect(lambda msg, color: emitted.append(msg))
        vm.create_rule(rule, None)
        assert len(emitted) == 1
        assert "creada" in emitted[0]

    def test_toast_emitted_on_delete(self, vm: RulesViewModel, repo: MagicMock):
        rule = Rule(name="Del", condition_type=ConditionType.EXTENSION, condition_value=".txt")
        repo.get_all_rules.return_value = []
        emitted = []
        vm.toast_requested.connect(lambda msg, color: emitted.append(msg))
        vm.delete_rule(rule.id, rule.name)
        assert len(emitted) == 1
        assert "eliminada" in emitted[0]

    def test_set_repository_loads_rules(self, vm: RulesViewModel, repo: MagicMock):
        rules = [Rule(name="A", condition_type=ConditionType.EXTENSION, condition_value=".txt")]
        repo.get_all_rules.return_value = rules
        emitted = []
        vm.rules_changed.connect(lambda r: emitted.append(r))
        vm.set_repository(repo)
        assert len(emitted) == 1
        assert emitted[0] == rules

    def test_reorder_noop_without_repo(self):
        vm = RulesViewModel(None)
        vm.reorder_rules([("id", 0)])
