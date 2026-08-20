from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, create_autospec

import pytest

from zorma.adapters.persistence.zorma_repository import ZormaRepository
from zorma.core.services.gestor_deshacer import GestorDeshacer
from zorma.ui.dashboard.dashboard_viewmodel import DashboardViewModel


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    return tmp_path / ".zorma"


@pytest.fixture(autouse=True)
def _no_existing_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Prevent the real ~/.zorma config from being loaded."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)


@pytest.fixture
def repo() -> MagicMock:
    return create_autospec(ZormaRepository, instance=True)


@pytest.fixture
def undo_manager() -> MagicMock:
    return create_autospec(GestorDeshacer)


@pytest.fixture
def vm(data_dir: Path, repo: MagicMock) -> DashboardViewModel:
    return DashboardViewModel(data_dir, repo)


class TestDashboardViewModel:
    def test_init_creates_no_signals(self, vm: DashboardViewModel):
        assert vm.obtener_ruta_vigilancia() is None
        assert not vm.esta_clasificando

    def test_set_watch_path_emits_signal(self, vm: DashboardViewModel):
        p = Path("/tmp/test")
        emitted = []
        vm.watch_path_changed.connect(lambda x: emitted.append(x))
        vm.establecer_ruta_vigilancia(p)
        assert len(emitted) == 1
        assert emitted[0] == p

    def test_set_watch_path_none(self, vm: DashboardViewModel):
        vm.establecer_ruta_vigilancia(None)
        assert vm.obtener_ruta_vigilancia() is None

    def test_get_rules_count(self, vm: DashboardViewModel, repo: MagicMock):
        repo.obtener_todas_las_reglas.return_value = [MagicMock(), MagicMock()]
        assert vm.obtener_cantidad_reglas() == "2"

    def test_get_rules_count_zero(self, vm: DashboardViewModel, repo: MagicMock):
        repo.obtener_todas_las_reglas.return_value = []
        assert vm.obtener_cantidad_reglas() == "0"

    def test_get_rules_count_no_repo(self):
        vm = DashboardViewModel(Path("/tmp"))
        assert vm.obtener_cantidad_reglas() == "0"

    def test_watch_path_persisted(self, data_dir: Path, repo: MagicMock):
        watch_dir = data_dir / "watch"
        watch_dir.mkdir(parents=True)
        config_file = data_dir / "app_config.json"
        config_file.write_text(json.dumps({"watch_path": str(watch_dir), "auto_classify": True}))
        vm = DashboardViewModel(data_dir, repo)
        assert vm.obtener_ruta_vigilancia() == watch_dir
        assert vm.obtener_auto_clasificar()

    def test_persist_watch_path(self, data_dir: Path, repo: MagicMock):
        saved_dir = data_dir / "saved"
        vm = DashboardViewModel(data_dir, repo)
        vm.establecer_ruta_vigilancia(saved_dir)
        config_file = data_dir / "app_config.json"
        assert config_file.exists()
        config = json.loads(config_file.read_text(encoding="utf-8"))
        assert config["watch_path"] == str(saved_dir)

    def test_auto_classify_default_false(self, vm: DashboardViewModel):
        assert not vm.obtener_auto_clasificar()

    def test_counters_start_at_zero(self, vm: DashboardViewModel):
        emitted = []
        vm.counters_changed.connect(lambda c, e: emitted.append((c, e)))
        assert len(emitted) == 0

    def test_undo_redo_state_no_manager(self, vm: DashboardViewModel):
        assert not vm.puede_deshacer()
        assert not vm.puede_rehacer()
        assert vm.obtener_cantidad_deshacibles() == 0

    def test_onboarding_signal_after_path_change(self, data_dir: Path, repo: MagicMock):
        vm = DashboardViewModel(data_dir, repo)
        emitted = []
        vm.onboarding_changed.connect(lambda x: emitted.append(x))
        vm.establecer_ruta_vigilancia(data_dir / "watch")
        assert len(emitted) == 1
