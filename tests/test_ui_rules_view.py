from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, create_autospec

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTableWidget, QPushButton

from zorma.core.models.rule import ActionType, ConditionType, Rule, RuleAction
from zorma.adapters.persistence.zorma_repository import ZormaRepository
from zorma.ui.rules.rules_view import RulesView
from zorma.ui.shared.widgets import EmptyState


@pytest.fixture
def repo() -> MagicMock:
    return create_autospec(ZormaRepository, instance=True)


@pytest.fixture
def sample_rule() -> Rule:
    return Rule(name="Videos", condition_type=ConditionType.EXTENSION, condition_value=".mp4", priority=0)


@pytest.fixture
def sample_action() -> RuleAction:
    return RuleAction(action_type=ActionType.MOVE, target_folder="/videos")


class TestRulesView:
    def test_shows_empty_state_when_no_rules(self, qtbot, repo: MagicMock):
        repo.get_all_rules.return_value = []
        view = RulesView(Path("/tmp"), repo)
        qtbot.addWidget(view)
        view.show()
        empty = view.findChild(EmptyState)
        assert empty is not None
        assert empty.isVisible()

    def test_shows_table_when_rules_exist(self, qtbot, repo: MagicMock, sample_rule: Rule, sample_action: RuleAction):
        repo.get_all_rules.return_value = [sample_rule]
        repo.get_actions_for_rule.return_value = [sample_action]
        view = RulesView(Path("/tmp"), repo)
        qtbot.addWidget(view)
        view.show()
        table = view.findChild(QTableWidget)
        assert table is not None
        assert table.rowCount() == 1

    def test_table_contains_rule_name(self, qtbot, repo: MagicMock, sample_rule: Rule, sample_action: RuleAction):
        repo.get_all_rules.return_value = [sample_rule]
        repo.get_actions_for_rule.return_value = [sample_action]
        view = RulesView(Path("/tmp"), repo)
        qtbot.addWidget(view)
        view.show()
        table = view.findChild(QTableWidget)
        item = table.item(0, 1)
        assert item is not None
        assert item.text() == "Videos"

    def test_add_button_creates_rule(self, qtbot, repo: MagicMock, sample_rule: Rule, sample_action: RuleAction):
        repo.get_all_rules.return_value = []
        view = RulesView(Path("/tmp"), repo)
        qtbot.addWidget(view)
        view.show()
        # Click new rule button
        repo.get_all_rules.return_value = [sample_rule]
        repo.get_actions_for_rule.return_value = [sample_action]
        # Simulate creating a rule
        view._vm.create_rule(sample_rule, sample_action)
        qtbot.wait(50)
        table = view.findChild(QTableWidget)
        assert table.rowCount() == 1

    def test_delete_button_removes_rule(self, qtbot, repo: MagicMock, sample_rule: Rule, sample_action: RuleAction):
        repo.get_all_rules.return_value = [sample_rule]
        repo.get_actions_for_rule.return_value = [sample_action]
        view = RulesView(Path("/tmp"), repo)
        qtbot.addWidget(view)
        view.show()
        table = view.findChild(QTableWidget)
        assert table.rowCount() == 1
        # Select the row
        table.selectRow(0)
        repo.get_all_rules.return_value = []
        view._vm.delete_rule(sample_rule.id, sample_rule.name)
        qtbot.wait(50)
        assert table.rowCount() == 0

    def test_reorder_rules_returns_pairs(self, qtbot, repo: MagicMock, sample_rule: Rule, sample_action: RuleAction):
        r2 = Rule(name="Images", condition_type=ConditionType.EXTENSION, condition_value=".jpg", priority=10)
        repo.get_all_rules.return_value = [sample_rule, r2]
        repo.get_actions_for_rule.return_value = [sample_action]
        view = RulesView(Path("/tmp"), repo)
        qtbot.addWidget(view)
        view.show()
        pairs = view._reorder_rules()
        assert len(pairs) == 2
        assert pairs[0][0] == sample_rule.id
        assert pairs[0][1] == 0
        assert pairs[1][0] == r2.id
        assert pairs[1][1] == 1

    def test_set_repository_loads_rules(self, qtbot, repo: MagicMock, sample_rule: Rule, sample_action: RuleAction):
        view = RulesView(Path("/tmp"))
        qtbot.addWidget(view)
        view.show()
        repo.get_all_rules.return_value = [sample_rule]
        repo.get_actions_for_rule.return_value = [sample_action]
        view.set_repository(repo)
        qtbot.wait(50)
        table = view.findChild(QTableWidget)
        assert table.rowCount() == 1
