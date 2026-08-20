from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, create_autospec

import pytest
from PyQt6.QtWidgets import QTableWidget

from zorma.adapters.persistence.zorma_repository import ZormaRepository
from zorma.core.models.accion_regla import AccionRegla
from zorma.core.models.enums import TipoAccion, TipoCondicion
from zorma.core.models.regla import Regla
from zorma.ui.rules.vista_reglas import VistaReglas
from zorma.ui.shared.widgets import EstadoVacio


@pytest.fixture
def repo() -> MagicMock:
    return create_autospec(ZormaRepository, instance=True)


@pytest.fixture
def sample_rule() -> Regla:
    return Regla(nombre="Videos", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".mp4", prioridad=0)


@pytest.fixture
def sample_action() -> AccionRegla:
    return AccionRegla(tipo_accion=TipoAccion.MOVER, carpeta_destino="/videos")


class TestRulesView:
    def test_shows_empty_state_when_no_rules(self, qtbot, repo: MagicMock):
        repo.obtener_todas_las_reglas.return_value = []
        view = VistaReglas(Path("/tmp"), repo)
        qtbot.addWidget(view)
        view.show()
        empty = view.findChild(EstadoVacio)
        assert empty is not None
        assert empty.isVisible()

    def test_shows_table_when_rules_exist(self, qtbot, repo: MagicMock, sample_rule: Regla, sample_action: AccionRegla):
        repo.obtener_todas_las_reglas.return_value = [sample_rule]
        repo.obtener_acciones_de_regla.return_value = [sample_action]
        view = VistaReglas(Path("/tmp"), repo)
        qtbot.addWidget(view)
        view.show()
        table = view.findChild(QTableWidget)
        assert table is not None
        assert table.rowCount() == 1

    def test_table_contains_rule_name(self, qtbot, repo: MagicMock, sample_rule: Regla, sample_action: AccionRegla):
        repo.obtener_todas_las_reglas.return_value = [sample_rule]
        repo.obtener_acciones_de_regla.return_value = [sample_action]
        view = VistaReglas(Path("/tmp"), repo)
        qtbot.addWidget(view)
        view.show()
        table = view.findChild(QTableWidget)
        item = table.item(0, 1)
        assert item is not None
        assert item.text() == "Videos"

    def test_add_button_creates_rule(self, qtbot, repo: MagicMock, sample_rule: Regla, sample_action: AccionRegla):
        repo.obtener_todas_las_reglas.return_value = []
        view = VistaReglas(Path("/tmp"), repo)
        qtbot.addWidget(view)
        view.show()
        # Click new rule button
        repo.obtener_todas_las_reglas.return_value = [sample_rule]
        repo.obtener_acciones_de_regla.return_value = [sample_action]
        # Simulate creating a rule
        view._vm.crear_regla(sample_rule, sample_action)
        qtbot.wait(50)
        table = view.findChild(QTableWidget)
        assert table.rowCount() == 1

    def test_delete_button_removes_rule(self, qtbot, repo: MagicMock, sample_rule: Regla, sample_action: AccionRegla):
        repo.obtener_todas_las_reglas.return_value = [sample_rule]
        repo.obtener_acciones_de_regla.return_value = [sample_action]
        view = VistaReglas(Path("/tmp"), repo)
        qtbot.addWidget(view)
        view.show()
        table = view.findChild(QTableWidget)
        assert table.rowCount() == 1
        # Select the row
        table.selectRow(0)
        repo.obtener_todas_las_reglas.return_value = []
        view._vm.eliminar_regla(sample_rule.id, sample_rule.nombre)
        qtbot.wait(50)
        assert table.rowCount() == 0

    def test_set_repository_loads_rules(self, qtbot, repo: MagicMock, sample_rule: Regla, sample_action: AccionRegla):
        view = VistaReglas(Path("/tmp"))
        qtbot.addWidget(view)
        view.show()
        repo.obtener_todas_las_reglas.return_value = [sample_rule]
        repo.obtener_acciones_de_regla.return_value = [sample_action]
        view.establecer_repositorio(repo)
        qtbot.wait(50)
        table = view.findChild(QTableWidget)
        assert table.rowCount() == 1
