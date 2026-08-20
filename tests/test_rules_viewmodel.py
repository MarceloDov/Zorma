from __future__ import annotations

from unittest.mock import MagicMock, create_autospec

import pytest

from zorma.adapters.persistence.zorma_repository import ZormaRepository
from zorma.core.models.accion_regla import AccionRegla
from zorma.core.models.enums import TipoAccion, TipoCondicion
from zorma.core.models.regla import Regla
from zorma.ui.rules.reglas_viewmodel import ReglasViewModel


@pytest.fixture
def repo() -> MagicMock:
    return create_autospec(ZormaRepository, instance=True)


@pytest.fixture
def vm(repo: MagicMock) -> ReglasViewModel:
    return ReglasViewModel(repo)


class TestRulesViewModel:
    def test_load_rules_emits_rules_changed(self, vm: ReglasViewModel, repo: MagicMock):
        rules = [Regla(nombre="Videos", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".mp4")]
        repo.obtener_todas_las_reglas.return_value = rules
        emitted = []
        vm.rules_changed.connect(lambda r: emitted.append(r))
        vm.cargar_reglas()
        assert len(emitted) == 1
        assert emitted[0] == rules

    def test_load_rules_noop_when_no_repo(self):
        vm = ReglasViewModel(None)
        emitted = []
        vm.rules_changed.connect(lambda r: emitted.append(r))
        vm.cargar_reglas()
        assert len(emitted) == 0

    def test_find_rule_by_id(self, vm: ReglasViewModel, repo: MagicMock):
        rule = Regla(nombre="Test", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".txt")
        repo.obtener_todas_las_reglas.return_value = [rule]
        vm.cargar_reglas()
        found = vm.buscar_regla_por_id(rule.id)
        assert found is rule

    def test_find_rule_by_id_not_found(self, vm: ReglasViewModel, repo: MagicMock):
        repo.obtener_todas_las_reglas.return_value = []
        vm.cargar_reglas()
        assert vm.buscar_regla_por_id("nonexistent") is None

    def test_create_rule_saves_and_reloads(self, vm: ReglasViewModel, repo: MagicMock):
        rule = Regla(nombre="New", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".mp3")
        action = AccionRegla(tipo_accion=TipoAccion.MOVER, carpeta_destino="/music")
        repo.obtener_todas_las_reglas.return_value = [rule]
        vm.crear_regla(rule, action)
        repo.guardar_regla.assert_called_once_with(rule)
        repo.guardar_accion.assert_called_once_with(action)
        assert action.id_regla == rule.id

    def test_create_rule_without_action(self, vm: ReglasViewModel, repo: MagicMock):
        rule = Regla(nombre="New", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".mp3")
        repo.obtener_todas_las_reglas.return_value = [rule]
        vm.crear_regla(rule, None)
        repo.guardar_regla.assert_called_once()
        repo.guardar_accion.assert_not_called()

    def test_update_rule_saves(self, vm: ReglasViewModel, repo: MagicMock):
        rule = Regla(nombre="Old", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".txt")
        action = AccionRegla(tipo_accion=TipoAccion.MOVER, carpeta_destino="/docs")
        repo.obtener_todas_las_reglas.return_value = [rule]
        vm.actualizar_regla(rule, action)
        repo.guardar_regla.assert_called_once_with(rule)
        repo.guardar_accion.assert_called_once()

    def test_delete_rule_deletes_and_reloads(self, vm: ReglasViewModel, repo: MagicMock):
        rule = Regla(nombre="DeleteMe", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".zip")
        repo.obtener_todas_las_reglas.return_value = [rule]
        vm.cargar_reglas()
        repo.obtener_todas_las_reglas.return_value = []
        vm.eliminar_regla(rule.id, rule.nombre)
        repo.eliminar_regla.assert_called_once_with(rule.id)

    def test_reorder_rules_saves_priorities(self, vm: ReglasViewModel, repo: MagicMock):
        r1 = Regla(nombre="A", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".txt", prioridad=0)
        r2 = Regla(nombre="B", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".pdf", prioridad=10)
        repo.obtener_todas_las_reglas.return_value = [r1, r2]
        vm.cargar_reglas()
        vm.reordenar_reglas([(r2.id, 0), (r1.id, 1)])
        assert r2.prioridad == 0
        assert r1.prioridad == 10
        assert repo.guardar_regla.call_count >= 2

    def test_get_actions_for_rule(self, vm: ReglasViewModel, repo: MagicMock):
        rule = Regla(nombre="Test", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".txt")
        action = AccionRegla(tipo_accion=TipoAccion.MOVER, carpeta_destino="/dest")
        repo.obtener_acciones_de_regla.return_value = [action]
        result = vm.obtener_acciones_de_regla(rule.id)
        assert result == [action]
        repo.obtener_acciones_de_regla.assert_called_once_with(rule.id)

    def test_toast_emitted_on_create(self, vm: ReglasViewModel, repo: MagicMock):
        rule = Regla(nombre="New", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".txt")
        repo.obtener_todas_las_reglas.return_value = [rule]
        emitted = []
        vm.toast_requested.connect(lambda msg, color: emitted.append(msg))
        vm.crear_regla(rule, None)
        assert len(emitted) == 1
        assert "creada" in emitted[0]

    def test_toast_emitted_on_delete(self, vm: ReglasViewModel, repo: MagicMock):
        rule = Regla(nombre="Del", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".txt")
        repo.obtener_todas_las_reglas.return_value = []
        emitted = []
        vm.toast_requested.connect(lambda msg, color: emitted.append(msg))
        vm.eliminar_regla(rule.id, rule.nombre)
        assert len(emitted) == 1
        assert "eliminada" in emitted[0]

    def test_set_repository_loads_rules(self, vm: ReglasViewModel, repo: MagicMock):
        rules = [Regla(nombre="A", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".txt")]
        repo.obtener_todas_las_reglas.return_value = rules
        emitted = []
        vm.rules_changed.connect(lambda r: emitted.append(r))
        vm.establecer_repositorio(repo)
        assert len(emitted) == 1
        assert emitted[0] == rules

    def test_reorder_noop_without_repo(self):
        vm = ReglasViewModel(None)
        vm.reordenar_reglas([("id", 0)])
