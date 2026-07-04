from pathlib import Path

from zorma.adapters.persistence.json_rule_repository import JsonRuleRepository
from zorma.core.models.rule import ActionType, ConditionType, Rule, RuleAction, RuleGroup


class TestJsonRuleRepository:
    """
    Clase de pruebas para `JsonRuleRepository`.
    Verifica la persistencia de reglas, grupos de reglas y acciones en archivos JSON, asegurando la integridad, recuperación, actualización y eliminación de datos.
    """
    def test_save_and_get_rule(self, tmp_path: Path) -> None:
        """
        Prueba que una regla pueda ser guardada y recuperada correctamente por su ID.
        Escenario: Se crea una regla nueva, se persiste en el repositorio y luego se recupera verificando que sus atributos coincidan.
        """
        repo = JsonRuleRepository(tmp_path)
        rule = Rule(name="Test", condition_type=ConditionType.EXTENSION, condition_value=".txt")
        repo.save(rule)
        retrieved = repo.get_by_id(rule.id)
        assert retrieved is not None
        assert retrieved.name == "Test"
        assert retrieved.condition_type == ConditionType.EXTENSION

    def test_get_all(self, tmp_path: Path) -> None:
        """
        Prueba la recuperación de todas las reglas almacenadas.
        Escenario: Se guardan múltiples reglas y se verifica que `get_all()` devuelva la cantidad total correcta.
        """
        repo = JsonRuleRepository(tmp_path)
        repo.save(Rule(name="R1", condition_type=ConditionType.EXTENSION, condition_value=".txt"))
        repo.save(Rule(name="R2", condition_type=ConditionType.SIZE, condition_value=">10 MB"))
        rules = repo.get_all()
        assert len(rules) == 2

    def test_get_by_id_not_found(self, tmp_path: Path) -> None:
        """
        Prueba que se retorne None si se busca una regla con un ID inexistente.
        Escenario: Se intenta consultar una regla usando un identificador arbitrario que no ha sido guardado previamente.
        """
        repo = JsonRuleRepository(tmp_path)
        assert repo.get_by_id("nonexistent") is None

    def test_delete_rule(self, tmp_path: Path) -> None:
        """
        Prueba la eliminación de una regla existente.
        Escenario: Una regla guardada se elimina del repositorio y se confirma que ya no es posible recuperarla.
        """
        repo = JsonRuleRepository(tmp_path)
        rule = Rule(name="ToDelete", condition_type=ConditionType.EXTENSION, condition_value=".tmp")
        repo.save(rule)
        assert repo.get_by_id(rule.id) is not None
        repo.delete(rule.id)
        assert repo.get_by_id(rule.id) is None

    def test_save_and_get_group(self, tmp_path: Path) -> None:
        """
        Prueba que un grupo de reglas pueda ser guardado y recuperado.
        Escenario: Se crea un `RuleGroup`, se guarda y se verifica que aparezca en la lista de grupos recuperados.
        """
        repo = JsonRuleRepository(tmp_path)
        group = RuleGroup(name="Test Group", priority=1)
        repo.save_group(group)
        groups = repo.get_groups()
        assert len(groups) == 1
        assert groups[0].name == "Test Group"

    def test_get_by_group(self, tmp_path: Path) -> None:
        """
        Prueba la recuperación de reglas filtradas por su grupo.
        Escenario: Se crean reglas asociadas a diferentes grupos, verificando que la consulta por `group_id` retorne solo las correctas.
        """
        repo = JsonRuleRepository(tmp_path)
        group = RuleGroup(name="G1")
        repo.save_group(group)
        r1 = Rule(name="R1", group_id=group.id, condition_type=ConditionType.EXTENSION, condition_value=".txt")
        r2 = Rule(name="R2", group_id="other", condition_type=ConditionType.EXTENSION, condition_value=".pdf")
        repo.save(r1)
        repo.save(r2)
        rules = repo.get_by_group(group.id)
        assert len(rules) == 1
        assert rules[0].name == "R1"

    def test_save_and_get_action(self, tmp_path: Path) -> None:
        """
        Prueba el guardado y recuperación de acciones asociadas a una regla.
        Escenario: Se asocia una `RuleAction` a una regla, se guarda y se verifica que la acción se recupere correctamente al consultar por el ID de la regla.
        """
        repo = JsonRuleRepository(tmp_path)
        rule = Rule(name="Test", condition_type=ConditionType.EXTENSION, condition_value=".txt")
        repo.save(rule)
        action = RuleAction(rule_id=rule.id, action_type=ActionType.MOVE, target_folder="/tmp/dest")
        repo.save_action(action)
        actions = repo.get_actions_for_rule(rule.id)
        assert len(actions) == 1
        assert actions[0].action_type == ActionType.MOVE
        assert actions[0].target_folder == "/tmp/dest"

    def test_persistence_across_instances(self, tmp_path: Path) -> None:
        """
        Prueba que los datos persistan al instanciar un nuevo repositorio apuntando a la misma ruta.
        Escenario: Se guarda una regla en un repositorio, luego se crea uno nuevo apuntando a la misma ruta y se verifica la recuperación del dato.
        """
        repo1 = JsonRuleRepository(tmp_path)
        rule = Rule(name="Persistent", condition_type=ConditionType.EXTENSION, condition_value=".csv")
        repo1.save(rule)

        repo2 = JsonRuleRepository(tmp_path)
        retrieved = repo2.get_by_id(rule.id)
        assert retrieved is not None
        assert retrieved.name == "Persistent"

    def test_create_default_rules(self, tmp_path: Path) -> None:
        """
        Prueba la creación automática de reglas por defecto.
        Escenario: Se invoca la creación de reglas predeterminadas y se verifica que se generen los grupos y reglas iniciales.
        """
        repo = JsonRuleRepository(tmp_path)
        assert len(repo.get_groups()) == 0
        repo.create_default_rules()
        groups = repo.get_groups()
        assert len(groups) == 1
        assert groups[0].is_default is True
        rules = repo.get_all()
        assert len(rules) == 1
        for rule in rules:
            assert rule.condition_type == ConditionType.EXTENSION

    def test_create_default_rules_use_ext_template(self, tmp_path: Path) -> None:
        """
        Prueba que las reglas por defecto utilicen la plantilla de extensión correctamente.
        Escenario: Verifica que la acción generada por defecto contenga la plantilla '{ext}' en la carpeta de destino.
        """
        repo = JsonRuleRepository(tmp_path)
        repo.create_default_rules()
        rules = repo.get_all()
        assert len(rules) == 1
        rule = rules[0]
        assert rule.condition_value == "*"
        actions = repo.get_actions_for_rule(rule.id)
        assert len(actions) == 1
        assert "{ext}" in actions[0].target_folder

    def test_delete_group_cascades(self, tmp_path: Path) -> None:
        """
        Prueba que al eliminar un grupo, las reglas asociadas también se eliminen.
        Escenario: Se crea un grupo con reglas, se elimina el grupo y se confirma que las reglas asociadas ya no existen.
        """
        repo = JsonRuleRepository(tmp_path)
        repo.create_default_rules()
        group = repo.get_groups()[0]
        rules_before = repo.get_all()
        repo.delete_group(group.id)
        assert len(repo.get_groups()) == 0
        assert len(repo.get_all()) == 0
