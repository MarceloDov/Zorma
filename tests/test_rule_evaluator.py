from pathlib import Path

import pytest

from zorma.core.models.archivo import Archivo
from zorma.core.models.enums import TipoCondicion
from zorma.core.models.regla import Regla


def _archivo(path: Path) -> Archivo:
    return Archivo(_ruta_completa=path)


class TestRuleEvaluator:
    @pytest.mark.parametrize(
        "condition_value,filename,expected",
        [
            (".mp4,.mkv,.avi", "video.mp4", True),
            (".MP4,.AVI", "video.mp4", True),
            ("mp4,mkv", "video.mp4", True),
            (".pdf,.doc", "video.mp4", False),
            ("*", "video.mp4", True),
            (".txt", "archive.tar.gz", False),
        ],
    )
    def test_extension_matching(
        self, tmp_files: dict[str, Path], condition_value: str, filename: str, expected: bool
    ) -> None:
        rule = Regla(tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=condition_value)
        assert rule.evaluar(_archivo(tmp_files.get(filename, tmp_files["video.mp4"]))) is expected

    def test_disabled_rule(self, tmp_files: dict[str, Path]) -> None:
        rule = Regla(tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".mp4", habilitada=False)
        assert rule.evaluar(_archivo(tmp_files["video.mp4"])) is False

    @pytest.mark.parametrize(
        "condition_value,expected",
        [
            (">0 KB", True),
            ("<1 GB", True),
            (">1 GB", False),
            ("==100", False),
            ("<0 KB", False),
            ("invalid", False),
        ],
    )
    def test_size_matching(self, tmp_files: dict[str, Path], condition_value: str, expected: bool) -> None:
        rule = Regla(tipo_condicion=TipoCondicion.TAMANIO, valor_condicion=condition_value)
        assert rule.evaluar(_archivo(tmp_files["video.mp4"])) is expected

    def test_size_exact(self, tmp_files: dict[str, Path]) -> None:
        rule = Regla(
            tipo_condicion=TipoCondicion.TAMANIO,
            valor_condicion=f"=={tmp_files['video.mp4'].stat().st_size}",
        )
        assert rule.evaluar(_archivo(tmp_files["video.mp4"])) is True

    @pytest.mark.parametrize(
        "condition_value,expected",
        [
            (">100 years", False),
            ("<1 days", True),
            ("<1 hours", True),
            ("<0 hours", False),
            ("invalid", False),
        ],
    )
    def test_date_matching(self, tmp_files: dict[str, Path], condition_value: str, expected: bool) -> None:
        rule = Regla(tipo_condicion=TipoCondicion.FECHA, valor_condicion=condition_value)
        assert rule.evaluar(_archivo(tmp_files["video.mp4"])) is expected

    def test_date_newer_than_minutes(self, tmp_files: dict[str, Path]) -> None:
        rule = Regla(tipo_condicion=TipoCondicion.FECHA, valor_condicion="<60 minutes")
        assert rule.evaluar(_archivo(tmp_files["video.mp4"])) is True

    @pytest.mark.parametrize(
        "condition_value,filename,expected",
        [
            ("reporte", "reporte_final.xlsx", True),
            ("reporte", "video.mp4", False),
            ("reporte_*", "reporte_final.xlsx", True),
            ("*final*", "reporte_final.xlsx", True),
        ],
    )
    def test_name_matching(
        self, tmp_files: dict[str, Path], condition_value: str, filename: str, expected: bool
    ) -> None:
        rule = Regla(tipo_condicion=TipoCondicion.NOMBRE, valor_condicion=condition_value)
        assert rule.evaluar(_archivo(tmp_files[filename])) is expected

    def test_evaluate_all_multiple_matches(self, tmp_files: dict[str, Path], sample_rules: list[Regla]) -> None:
        matched = [r for r in sample_rules if r.evaluar(_archivo(tmp_files["video.mp4"]))]
        names = [r.nombre for r in matched]
        assert "Videos" in names
        assert "Grandes (>100MB)" not in names

    def test_evaluate_all_no_match(self, sample_rules: list[Regla]) -> None:
        fake = Path("/nonexistent/file.xyz")
        archivo = _archivo(fake)
        matched = [r for r in sample_rules if r.evaluar(archivo)]
        assert len(matched) == 0

    def test_invalid_condition_type(self, tmp_files: dict[str, Path]) -> None:
        rule = Regla(tipo_condicion="unknown", valor_condicion="x")  # type: ignore[arg-type]
        assert rule.evaluar(_archivo(tmp_files["video.mp4"])) is False

    @pytest.mark.parametrize(
        "condition_value",
        [
            "",
            " ",
            ".,.",
        ],
    )
    def test_edge_case_extension_values(self, tmp_files: dict[str, Path], condition_value: str) -> None:
        rule = Regla(tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=condition_value)
        assert rule.evaluar(_archivo(tmp_files["video.mp4"])) is False

    def test_file_without_extension(self, tmp_path: Path) -> None:
        f = tmp_path / "README"
        f.write_text("hello")
        rule = Regla(tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".txt,.md")
        assert rule.evaluar(_archivo(f)) is False

    def test_file_with_only_extension(self, tmp_path: Path) -> None:
        f = tmp_path / ".hidden.bak"
        f.write_text("content")
        rule = Regla(tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".bak")
        assert rule.evaluar(_archivo(f)) is True
