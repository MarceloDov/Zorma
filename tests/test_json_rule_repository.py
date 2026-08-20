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
        repo.guardar_regla(rule)
        retrieved = repo.obtener_regla_por_id(rule.id)
        assert retrieved is not None
        assert retrieved.nombre == "Test"
        assert retrieved.tipo_condicion == TipoCondicion.EXTENSION

    def test_get_all_rules(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        repo.guardar_regla(Regla(nombre="R1", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".txt"))
        repo.guardar_regla(Regla(nombre="R2", tipo_condicion=TipoCondicion.TAMANIO, valor_condicion=">10 MB"))
        rules = repo.obtener_todas_las_reglas()
        assert len(rules) == 2

    def test_get_rule_by_id_not_found(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        assert repo.obtener_regla_por_id("nonexistent") is None

    def test_delete_rule(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        rule = Regla(nombre="ToDelete", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".tmp")
        repo.guardar_regla(rule)
        assert repo.obtener_regla_por_id(rule.id) is not None
        repo.eliminar_regla(rule.id)
        assert repo.obtener_regla_por_id(rule.id) is None

    def test_save_and_get_group(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        group = GrupoRegla(nombre="Test Group", prioridad=1)
        repo.guardar_grupo(group)
        groups = repo.obtener_grupos()
        assert len(groups) == 1
        assert groups[0].nombre == "Test Group"

    def test_get_rules_by_group(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        group = GrupoRegla(nombre="G1")
        repo.guardar_grupo(group)
        r1 = Regla(nombre="R1", id_grupo=group.id, tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".txt")
        r2 = Regla(nombre="R2", id_grupo="other", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".pdf")
        repo.guardar_regla(r1)
        repo.guardar_regla(r2)
        rules = repo.obtener_reglas_por_grupo(group.id)
        assert len(rules) == 1
        assert rules[0].nombre == "R1"

    def test_save_and_get_action(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        rule = Regla(nombre="Test", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".txt")
        repo.guardar_regla(rule)
        action = AccionRegla(id_regla=rule.id, tipo_accion=TipoAccion.MOVER, carpeta_destino="/tmp/dest")
        repo.guardar_accion(action)
        actions = repo.obtener_acciones_de_regla(rule.id)
        assert len(actions) == 1
        assert actions[0].tipo_accion == TipoAccion.MOVER
        assert actions[0].carpeta_destino == "/tmp/dest"

    def test_persistence_across_instances(self, tmp_path: Path) -> None:
        repo1 = ZormaRepository(tmp_path)
        rule = Regla(nombre="Persistent", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".csv")
        repo1.guardar_regla(rule)

        repo2 = ZormaRepository(tmp_path)
        retrieved = repo2.obtener_regla_por_id(rule.id)
        assert retrieved is not None
        assert retrieved.nombre == "Persistent"

    def test_create_default_rules(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        assert len(repo.obtener_grupos()) == 0
        repo.crear_reglas_predeterminadas()
        groups = repo.obtener_grupos()
        assert len(groups) == 1
        assert groups[0].es_predeterminado is True
        rules = repo.obtener_todas_las_reglas()
        assert len(rules) == 1
        for rule in rules:
            assert rule.tipo_condicion == TipoCondicion.EXTENSION

    def test_create_default_rules_use_ext_template(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        repo.crear_reglas_predeterminadas()
        rules = repo.obtener_todas_las_reglas()
        assert len(rules) == 1
        rule = rules[0]
        assert rule.valor_condicion == "*"
        actions = repo.obtener_acciones_de_regla(rule.id)
        assert len(actions) == 1
        assert "{ext}" in actions[0].carpeta_destino

    def test_delete_group_cascades(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        repo.crear_reglas_predeterminadas()
        group = repo.obtener_grupos()[0]
        repo.eliminar_grupo(group.id)
        assert len(repo.obtener_grupos()) == 0
        assert len(repo.obtener_todas_las_reglas()) == 0

    def test_theme_persistence(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        assert repo.obtener_tema() == "dark"
        repo.establecer_tema("light")
        assert repo.obtener_tema() == "light"
        repo2 = ZormaRepository(tmp_path)
        assert repo2.obtener_tema() == "light"

    def test_undo_redo(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path, undo_limit=3)
        e1 = PilaDeshacer()
        e2 = PilaDeshacer()
        repo.apilar_deshacer(e1)
        repo.apilar_deshacer(e2)
        assert repo.tamanio_deshacer() == 2
        assert repo.ver_tope_deshacer().id == e2.id
        popped = repo.desapilar_deshacer()
        assert popped.id == e2.id
        assert repo.tamanio_deshacer() == 1
        repo.apilar_rehacer(e2)
        assert repo.tamanio_rehacer() == 1
        assert repo.desapilar_rehacer().id == e2.id

    def test_history(self, tmp_path: Path) -> None:
        repo = ZormaRepository(tmp_path)
        r = ResultadoClasificacion(nombre_archivo="f.txt", estado=EstadoClasificacion.EXITO)
        repo.agregar_historial(r)
        entries = repo.obtener_historial()
        assert len(entries) == 1
        assert entries[0].nombre_archivo == "f.txt"
