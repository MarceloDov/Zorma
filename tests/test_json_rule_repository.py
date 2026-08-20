from pathlib import Path

from zorma.adapters.persistence.zorma_repository import ZormaRepository
from zorma.core.models.accion_regla import AccionRegla
from zorma.core.models.enums import EstadoClasificacion, TipoAccion, TipoCondicion
from zorma.core.models.grupo_regla import GrupoRegla
from zorma.core.models.pila_deshacer import PilaDeshacer
from zorma.core.models.regla import Regla
from zorma.core.models.resultado_clasificacion import ResultadoClasificacion


class TestZormaRepository:
    def test_save_and_get_rule(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        rule = Regla(nombre="Test", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".txt")
        repo.save_rule(rule)
        retrieved = repo.get_rule_by_id(rule.id)
        assert retrieved is not None
        assert retrieved.nombre == "Test"
        assert retrieved.tipo_condicion == TipoCondicion.EXTENSION

    def test_get_all_rules(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        repo.save_rule(Regla(nombre="R1", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".txt"))
        repo.save_rule(Regla(nombre="R2", tipo_condicion=TipoCondicion.TAMANIO, valor_condicion=">10 MB"))
        rules = repo.get_all_rules()
        assert len(rules) == 2

    def test_get_rule_by_id_not_found(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        assert repo.get_rule_by_id("nonexistent") is None

    def test_delete_rule(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        rule = Regla(nombre="ToDelete", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".tmp")
        repo.save_rule(rule)
        assert repo.get_rule_by_id(rule.id) is not None
        repo.delete_rule(rule.id)
        assert repo.get_rule_by_id(rule.id) is None

    def test_save_and_get_group(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        group = GrupoRegla(nombre="Test Group", prioridad=1)
        repo.save_group(group)
        groups = repo.get_groups()
        assert len(groups) == 1
        assert groups[0].nombre == "Test Group"

    def test_get_rules_by_group(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        group = GrupoRegla(nombre="G1")
        repo.save_group(group)
        r1 = Regla(nombre="R1", id_grupo=group.id, tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".txt")
        r2 = Regla(nombre="R2", id_grupo="other", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".pdf")
        repo.save_rule(r1)
        repo.save_rule(r2)
        rules = repo.get_rules_by_group(group.id)
        assert len(rules) == 1
        assert rules[0].nombre == "R1"

    def test_save_and_get_action(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        rule = Regla(nombre="Test", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".txt")
        repo.save_rule(rule)
        action = AccionRegla(id_regla=rule.id, tipo_accion=TipoAccion.MOVER, carpeta_destino="/tmp/dest")
        repo.save_action(action)
        actions = repo.get_actions_for_rule(rule.id)
        assert len(actions) == 1
        assert actions[0].tipo_accion == TipoAccion.MOVER
        assert actions[0].carpeta_destino == "/tmp/dest"

    def test_persistence_across_instances(self, tmp_path: Path) -> None:
        repo1 = ZormaRepository(tmp_path)
        rule = Regla(nombre="Persistent", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".csv")
        repo1.save_rule(rule)

        repo2 = ZormaRepository(tmp_path)
        retrieved = repo2.get_rule_by_id(rule.id)
        assert retrieved is not None
        assert retrieved.nombre == "Persistent"

    def test_create_default_rules(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        assert len(repo.get_groups()) == 0
        repo.create_default_rules()
        groups = repo.get_groups()
        assert len(groups) == 1
        assert groups[0].es_predeterminado is True
        rules = repo.get_all_rules()
        assert len(rules) == 1
        for rule in rules:
            assert rule.tipo_condicion == TipoCondicion.EXTENSION

    def test_create_default_rules_use_ext_template(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        repo.create_default_rules()
        rules = repo.get_all_rules()
        assert len(rules) == 1
        rule = rules[0]
        assert rule.valor_condicion == "*"
        actions = repo.get_actions_for_rule(rule.id)
        assert len(actions) == 1
        assert "{ext}" in actions[0].carpeta_destino

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
        e1 = PilaDeshacer()
        e2 = PilaDeshacer()
        repo.undo_push(e1)
        repo.undo_push(e2)
        assert repo.undo_size() == 2
        assert repo.undo_peek().id == e2.id
        popped = repo.undo_pop()
        assert popped.id == e2.id
        assert repo.undo_size() == 1
        repo.redo_push(e2)
        assert repo.redo_size() == 1
        assert repo.redo_pop().id == e2.id

    def test_history(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        r = ResultadoClasificacion(nombre_archivo="f.txt", estado=EstadoClasificacion.EXITO)
        repo.add_history(r)
        entries = repo.get_history()
        assert len(entries) == 1
        assert entries[0].nombre_archivo == "f.txt"
