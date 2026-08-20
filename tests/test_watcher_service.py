from pathlib import Path
from unittest.mock import MagicMock, create_autospec

from zorma.adapters.persistence.zorma_repository import ZormaRepository
from zorma.adapters.watcher.vigilante_watchdog import VigilanteArchivosWatchdog
from zorma.core.models.accion_regla import AccionRegla
from zorma.core.models.configuracion_filtro import ConfiguracionFiltro
from zorma.core.models.enums import EstadoClasificacion, TipoAccion, TipoCondicion, TipoEvento
from zorma.core.models.evento_archivo import EventoArchivo
from zorma.core.models.regla import Regla
from zorma.core.services.servicio_clasificacion import ServicioClasificacion


class TestWatcherService:
    def setup_method(self) -> None:
        self.watcher = create_autospec(VigilanteArchivosWatchdog)
        self.repo = create_autospec(ZormaRepository, instance=True)
        self.service = ServicioClasificacion(self.watcher, self.repo)

    def test_start_monitoring(self) -> None:
        paths = [Path("/watch")]
        self.service.iniciar_monitoreo(paths)
        self.watcher.actualizar_filtro.assert_called_once_with(None)
        self.watcher.iniciar.assert_called_once()

    def test_start_monitoring_with_filter(self) -> None:
        paths = [Path("/watch")]
        cfg = ConfiguracionFiltro(include_extensions=[".txt"])
        self.service.iniciar_monitoreo(paths, cfg)
        self.watcher.actualizar_filtro.assert_called_once_with(cfg)
        self.watcher.iniciar.assert_called_once()

    def test_stop_monitoring(self) -> None:
        self.service.detener_monitoreo()
        self.watcher.detener.assert_called_once()

    def test_classify_no_rules(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        self.repo.obtener_todas_las_reglas.return_value = []
        result = self.service._clasificar(f)
        assert result.estado == EstadoClasificacion.SIN_REGLA

    def test_classify_no_match(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        rule = Regla(tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".pdf")
        self.repo.obtener_todas_las_reglas.return_value = [rule]
        result = self.service._clasificar(f)
        assert result.estado == EstadoClasificacion.SIN_REGLA

    def test_classify_match_no_action(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        rule = Regla(tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".txt")
        self.repo.obtener_todas_las_reglas.return_value = [rule]
        self.repo.obtener_acciones_de_regla.return_value = []
        result = self.service._clasificar(f)
        assert result.estado == EstadoClasificacion.SIN_REGLA

    def test_classify_success(self, tmp_path: Path) -> None:
        src = tmp_path / "test.txt"
        src.write_text("hello")
        rule = Regla(tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".txt")
        action = AccionRegla(tipo_accion=TipoAccion.MOVER, carpeta_destino=str(tmp_path / "dest"))
        self.repo.obtener_todas_las_reglas.return_value = [rule]
        self.repo.obtener_acciones_de_regla.return_value = [action]
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
        self.repo.obtener_todas_las_reglas.return_value = []
        callback = MagicMock()
        self.service.establecer_callback_resultado(callback)
        event = EventoArchivo(src_path=f, tipo_evento=TipoEvento.CREADO)
        self.service._al_evento(event)
        callback.assert_called_once()

    def test_initial_scan(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.pdf"
        f1.write_text("a")
        f2.write_text("b")
        self.repo.obtener_todas_las_reglas.return_value = []
        results = self.service._escaneo_inicial([tmp_path])
        assert len(results) == 2

    def test_initial_scan_with_filter(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.pdf"
        f1.write_text("a")
        f2.write_text("b")
        cfg = ConfiguracionFiltro(include_extensions=[".txt"])
        self.repo.obtener_todas_las_reglas.return_value = []
        results = self.service._escaneo_inicial([tmp_path], cfg)
        assert len(results) == 1
        assert results[0].nombre_archivo == "a.txt"

    def test_preview_no_rules(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        self.repo.obtener_todas_las_reglas.return_value = []
        result = self.service.previsualizar(f)
        assert result.estado == EstadoClasificacion.SIN_REGLA

    def test_preview_no_conflict(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        rule = Regla(tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".txt")
        action = AccionRegla(tipo_accion=TipoAccion.MOVER, carpeta_destino=str(tmp_path / "dest"))
        self.repo.obtener_todas_las_reglas.return_value = [rule]
        self.repo.obtener_acciones_de_regla.return_value = [action]
        result = self.service.previsualizar(f)
        assert result.estado == EstadoClasificacion.EXITO

    def test_preview_with_conflict(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        dest_file = tmp_path / "test.txt"
        dest_file.write_text("existing")
        rule = Regla(tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".txt")
        action = AccionRegla(tipo_accion=TipoAccion.MOVER, carpeta_destino=str(tmp_path))
        self.repo.obtener_todas_las_reglas.return_value = [rule]
        self.repo.obtener_acciones_de_regla.return_value = [action]
        result = self.service.previsualizar(f)
        assert result.estado == EstadoClasificacion.CONFLICTO

    def test_preview_all(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.pdf"
        f1.write_text("a")
        f2.write_text("b")
        self.repo.obtener_todas_las_reglas.return_value = []
        results = self.service.previsualizar_todos([tmp_path])
        assert len(results) == 2

    def test_preview_all_with_filter(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.pdf"
        f1.write_text("a")
        f2.write_text("b")
        cfg = ConfiguracionFiltro(include_extensions=[".txt"])
        self.repo.obtener_todas_las_reglas.return_value = []
        results = self.service.previsualizar_todos([tmp_path], cfg)
        assert len(results) == 1
        assert results[0].nombre_archivo == "a.txt"

    def test_classify_picks_first_matching_rule(self, tmp_path: Path) -> None:
        f = tmp_path / "test.mp4"
        f.write_text("hello")
        rule1 = Regla(nombre="Videos", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".mp4")
        rule2 = Regla(nombre="All", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion="*")
        self.repo.obtener_todas_las_reglas.return_value = [rule1, rule2]
        action = AccionRegla(tipo_accion=TipoAccion.MOVER, carpeta_destino=str(tmp_path))
        self.repo.obtener_acciones_de_regla.side_effect = lambda rid: [action]
        result = self.service._clasificar(f)
        assert result.regla_aplicada is rule1

    def test_on_event_skips_directories(self, tmp_path: Path) -> None:
        d = tmp_path / "subdir"
        d.mkdir()
        self.repo.obtener_todas_las_reglas.return_value = []
        callback = MagicMock()
        self.service.establecer_callback_resultado(callback)
        event = EventoArchivo(src_path=d, tipo_evento=TipoEvento.CREADO)
        self.service._al_evento(event)
        callback.assert_called_once()
        result = callback.call_args[0][0]
        assert result.estado == EstadoClasificacion.FILTRADO
