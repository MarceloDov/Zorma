from pathlib import Path
from unittest.mock import MagicMock, create_autospec

from zorma.adapters.persistence.zorma_repository import ZormaRepository
from zorma.adapters.watcher.watchdog_watcher import WatchdogFileWatcher
from zorma.core.models.accion_regla import AccionRegla
from zorma.core.models.enums import EstadoClasificacion, TipoAccion, TipoCondicion, TipoEvento
from zorma.core.models.evento_archivo import EventoArchivo
from zorma.core.models.filter_config import FilterConfig
from zorma.core.models.regla import Regla
from zorma.core.services.servicio_clasificacion import ServicioClasificacion


class TestWatcherService:
    def setup_method(self) -> None:
        self.watcher = create_autospec(WatchdogFileWatcher)
        self.repo = create_autospec(ZormaRepository, instance=True)
        self.history = create_autospec(ZormaRepository, instance=True)
        self.service = ServicioClasificacion(self.watcher, self.repo, self.history)

    def test_start_monitoring(self) -> None:
        paths = [Path("/watch")]
        self.service.start_monitoring(paths)
        self.watcher.update_filter.assert_called_once_with(None)
        self.watcher.start.assert_called_once()

    def test_start_monitoring_with_filter(self) -> None:
        paths = [Path("/watch")]
        cfg = FilterConfig(include_extensions=[".txt"])
        self.service.start_monitoring(paths, cfg)
        self.watcher.update_filter.assert_called_once_with(cfg)
        self.watcher.start.assert_called_once()

    def test_stop_monitoring(self) -> None:
        self.service.stop_monitoring()
        self.watcher.stop.assert_called_once()

    def test_classify_no_rules(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        self.repo.get_all_rules.return_value = []
        result = self.service._clasificar(f)
        assert result.estado == EstadoClasificacion.SIN_REGLA

    def test_classify_no_match(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        rule = Regla(tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".pdf")
        self.repo.get_all_rules.return_value = [rule]
        result = self.service._clasificar(f)
        assert result.estado == EstadoClasificacion.SIN_REGLA

    def test_classify_match_no_action(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        rule = Regla(tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".txt")
        self.repo.get_all_rules.return_value = [rule]
        self.repo.get_actions_for_rule.return_value = []
        result = self.service._clasificar(f)
        assert result.estado == EstadoClasificacion.SIN_REGLA

    def test_classify_success(self, tmp_path: Path) -> None:
        src = tmp_path / "test.txt"
        src.write_text("hello")
        rule = Regla(tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".txt")
        action = AccionRegla(tipo_accion=TipoAccion.MOVER, carpeta_destino=str(tmp_path / "dest"))
        self.repo.get_all_rules.return_value = [rule]
        self.repo.get_actions_for_rule.return_value = [action]
        result = self.service._clasificar(src)
        assert result.estado == EstadoClasificacion.EXITO
        assert result.ruta_destino == tmp_path / "dest" / "test.txt"

    def test_classify_file_not_found(self, tmp_path: Path) -> None:
        f = tmp_path / "nonexistent.txt"
        result = self.service._clasificar(f)
        assert result.estado == EstadoClasificacion.FILTRADO

    def test_on_event_triggers_callback(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        self.repo.get_all_rules.return_value = []
        callback = MagicMock()
        self.service.set_result_callback(callback)
        event = EventoArchivo(src_path=f, tipo_evento=TipoEvento.CREADO)
        self.service._on_event(event)
        callback.assert_called_once()

    def test_initial_scan(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.pdf"
        f1.write_text("a")
        f2.write_text("b")
        self.repo.get_all_rules.return_value = []
        results = self.service._initial_scan([tmp_path])
        assert len(results) == 2

    def test_initial_scan_with_filter(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.pdf"
        f1.write_text("a")
        f2.write_text("b")
        cfg = FilterConfig(include_extensions=[".txt"])
        self.repo.get_all_rules.return_value = []
        results = self.service._initial_scan([tmp_path], cfg)
        assert len(results) == 1
        assert results[0].nombre_archivo == "a.txt"

    def test_preview_no_rules(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        self.repo.get_all_rules.return_value = []
        result = self.service.previsualizar(f)
        assert result.estado == EstadoClasificacion.SIN_REGLA

    def test_preview_no_conflict(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        rule = Regla(tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".txt")
        action = AccionRegla(tipo_accion=TipoAccion.MOVER, carpeta_destino=str(tmp_path / "dest"))
        self.repo.get_all_rules.return_value = [rule]
        self.repo.get_actions_for_rule.return_value = [action]
        result = self.service.previsualizar(f)
        assert result.estado == EstadoClasificacion.EXITO

    def test_preview_with_conflict(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        dest_file = tmp_path / "test.txt"
        dest_file.write_text("existing")
        rule = Regla(tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".txt")
        action = AccionRegla(tipo_accion=TipoAccion.MOVER, carpeta_destino=str(tmp_path))
        self.repo.get_all_rules.return_value = [rule]
        self.repo.get_actions_for_rule.return_value = [action]
        result = self.service.previsualizar(f)
        assert result.estado == EstadoClasificacion.CONFLICTO

    def test_preview_all(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.pdf"
        f1.write_text("a")
        f2.write_text("b")
        self.repo.get_all_rules.return_value = []
        results = self.service.previsualizar_todos([tmp_path])
        assert len(results) == 2

    def test_preview_all_with_filter(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.pdf"
        f1.write_text("a")
        f2.write_text("b")
        cfg = FilterConfig(include_extensions=[".txt"])
        self.repo.get_all_rules.return_value = []
        results = self.service.previsualizar_todos([tmp_path], cfg)
        assert len(results) == 1
        assert results[0].nombre_archivo == "a.txt"

    def test_classify_picks_first_matching_rule(self, tmp_path: Path) -> None:
        f = tmp_path / "test.mp4"
        f.write_text("hello")
        rule1 = Regla(nombre="Videos", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".mp4")
        rule2 = Regla(nombre="All", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion="*")
        self.repo.get_all_rules.return_value = [rule1, rule2]
        action = AccionRegla(tipo_accion=TipoAccion.MOVER, carpeta_destino=str(tmp_path))
        self.repo.get_actions_for_rule.side_effect = lambda rid: [action]
        result = self.service._clasificar(f)
        assert result.regla_aplicada is rule1

    def test_on_event_skips_directories(self, tmp_path: Path) -> None:
        d = tmp_path / "subdir"
        d.mkdir()
        self.repo.get_all_rules.return_value = []
        callback = MagicMock()
        self.service.set_result_callback(callback)
        event = EventoArchivo(src_path=d, tipo_evento=TipoEvento.CREADO)
        self.service._on_event(event)
        callback.assert_called_once()
        result = callback.call_args[0][0]
        assert result.estado == EstadoClasificacion.FILTRADO
