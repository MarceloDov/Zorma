from pathlib import Path

from zorma.adapters.persistence.zorma_repository import ZormaRepository
from zorma.core.models.rule import ActionType, ConditionType, Rule, RuleAction, RuleGroup


class TestZormaRepository:
    def test_save_and_get_rule(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        rule = Rule(name="Test", condition_type=ConditionType.EXTENSION, condition_value=".txt")
        repo.save_rule(rule)
        retrieved = repo.get_rule_by_id(rule.id)
        assert retrieved is not None
        assert retrieved.name == "Test"
        assert retrieved.condition_type == ConditionType.EXTENSION

    def test_get_all_rules(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        repo.save_rule(Rule(name="R1", condition_type=ConditionType.EXTENSION, condition_value=".txt"))
        repo.save_rule(Rule(name="R2", condition_type=ConditionType.SIZE, condition_value=">10 MB"))
        rules = repo.get_all_rules()
        assert len(rules) == 2

    def test_get_rule_by_id_not_found(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        assert repo.get_rule_by_id("nonexistent") is None

    def test_delete_rule(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        rule = Rule(name="ToDelete", condition_type=ConditionType.EXTENSION, condition_value=".tmp")
        repo.save_rule(rule)
        assert repo.get_rule_by_id(rule.id) is not None
        repo.delete_rule(rule.id)
        assert repo.get_rule_by_id(rule.id) is None

    def test_save_and_get_group(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        group = RuleGroup(name="Test Group", priority=1)
        repo.save_group(group)
        groups = repo.get_groups()
        assert len(groups) == 1
        assert groups[0].name == "Test Group"

    def test_get_rules_by_group(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        group = RuleGroup(name="G1")
        repo.save_group(group)
        r1 = Rule(name="R1", group_id=group.id, condition_type=ConditionType.EXTENSION, condition_value=".txt")
        r2 = Rule(name="R2", group_id="other", condition_type=ConditionType.EXTENSION, condition_value=".pdf")
        repo.save_rule(r1)
        repo.save_rule(r2)
        rules = repo.get_rules_by_group(group.id)
        assert len(rules) == 1
        assert rules[0].name == "R1"

    def test_save_and_get_action(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        rule = Rule(name="Test", condition_type=ConditionType.EXTENSION, condition_value=".txt")
        repo.save_rule(rule)
        action = RuleAction(rule_id=rule.id, action_type=ActionType.MOVE, target_folder="/tmp/dest")
        repo.save_action(action)
        actions = repo.get_actions_for_rule(rule.id)
        assert len(actions) == 1
        assert actions[0].action_type == ActionType.MOVE
        assert actions[0].target_folder == "/tmp/dest"

    def test_persistence_across_instances(self, tmp_path: Path) -> None:
        repo1 = ZormaRepository(tmp_path)
        rule = Rule(name="Persistent", condition_type=ConditionType.EXTENSION, condition_value=".csv")
        repo1.save_rule(rule)

        repo2 = ZormaRepository(tmp_path)
        retrieved = repo2.get_rule_by_id(rule.id)
        assert retrieved is not None
        assert retrieved.name == "Persistent"

    def test_create_default_rules(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        assert len(repo.get_groups()) == 0
        repo.create_default_rules()
        groups = repo.get_groups()
        assert len(groups) == 1
        assert groups[0].is_default is True
        rules = repo.get_all_rules()
        assert len(rules) == 1
        for rule in rules:
            assert rule.condition_type == ConditionType.EXTENSION

    def test_create_default_rules_use_ext_template(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        repo.create_default_rules()
        rules = repo.get_all_rules()
        assert len(rules) == 1
        rule = rules[0]
        assert rule.condition_value == "*"
        actions = repo.get_actions_for_rule(rule.id)
        assert len(actions) == 1
        assert "{ext}" in actions[0].target_folder

    def test_delete_group_cascades(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        repo.create_default_rules()
        group = repo.get_groups()[0]
        repo.delete_group(group.id)
        assert len(repo.get_groups()) == 0
        assert len(repo.get_all_rules()) == 0

    def test_theme_persistence(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        assert repo.get_theme() == "dark"
        repo.set_theme("light")
        assert repo.get_theme() == "light"
        repo2 = ZormaRepository(tmp_path)
        assert repo2.get_theme() == "light"

    def test_undo_redo(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path, undo_limit=3)
        from zorma.core.models.undo_entry import UndoEntry
        e1 = UndoEntry(file_name="a.txt")
        e2 = UndoEntry(file_name="b.txt")
        repo.undo_push(e1)
        repo.undo_push(e2)
        assert repo.undo_size() == 2
        assert repo.undo_peek().file_name == "b.txt"
        popped = repo.undo_pop()
        assert popped.file_name == "b.txt"
        assert repo.undo_size() == 1
        repo.redo_push(e2)
        assert repo.redo_size() == 1
        assert repo.redo_pop().file_name == "b.txt"

    def test_history(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        from zorma.core.models.classification import ClassificationResult, ClassificationStatus
        r = ClassificationResult(file_name="f.txt", status=ClassificationStatus.SUCCESS)
        repo.add_history(r)
        entries = repo.get_history()
        assert len(entries) == 1
        assert entries[0].file_name == "f.txt"
