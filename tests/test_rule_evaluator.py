from pathlib import Path

import pytest

from zorma.core.models.rule import ConditionType, Rule
from zorma.core.services.rule_evaluator import RuleEvaluator


class TestRuleEvaluator:
    """
    Clase de pruebas para `RuleEvaluator`.
    Verifica la evaluación correcta de diversas condiciones de reglas (extensiones, tamaños, fechas, nombres) sobre los archivos.
    """
    def setup_method(self) -> None:
        """Configura el evaluador antes de cada prueba, inicializando una instancia de RuleEvaluator."""
        self.evaluator = RuleEvaluator()

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
        """
        Prueba que el filtrado por extensión funcione correctamente con varios formatos y casos (insensibilidad a mayúsculas, múltiples valores).
        Escenario: Se evalúan diferentes extensiones de archivo contra reglas de tipo EXTENSION.
        """
        rule = Rule(condition_type=ConditionType.EXTENSION, condition_value=condition_value)
        assert self.evaluator.evaluate(tmp_files.get(filename, tmp_files["video.mp4"]), rule) is expected

    def test_disabled_rule(self, tmp_files: dict[str, Path]) -> None:
        """
        Prueba que una regla deshabilitada no sea evaluada.
        Escenario: Una regla configurada como `enabled=False` debe retornar `False` independientemente de si el archivo coincide.
        """
        rule = Rule(condition_type=ConditionType.EXTENSION, condition_value=".mp4", enabled=False)
        assert self.evaluator.evaluate(tmp_files["video.mp4"], rule) is False

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
    def test_size_matching(
        self, tmp_files: dict[str, Path], condition_value: str, expected: bool
    ) -> None:
        """
        Prueba que el filtrado por tamaño de archivo funcione con varias condiciones de comparación (mayor que, menor que).
        Escenario: Se evalúa el tamaño de un archivo contra reglas de tipo SIZE con diversas condiciones.
        """
        rule = Rule(condition_type=ConditionType.SIZE, condition_value=condition_value)
        assert self.evaluator.evaluate(tmp_files["video.mp4"], rule) is expected

    def test_size_exact(self, tmp_files: dict[str, Path]) -> None:
        """
        Prueba que el filtrado por tamaño exacto funcione.
        Escenario: Se crea una regla de tamaño exacto coincidente con el archivo real, y debe ser evaluada como `True`.
        """
        rule = Rule(
            condition_type=ConditionType.SIZE,
            condition_value=f"=={tmp_files['video.mp4'].stat().st_size}",
        )
        assert self.evaluator.evaluate(tmp_files["video.mp4"], rule) is True

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
    def test_date_matching(
        self, tmp_files: dict[str, Path], condition_value: str, expected: bool
    ) -> None:
        """
        Prueba que el filtrado por fecha del archivo funcione con varias condiciones temporales.
        Escenario: Se evalúa la fecha de creación/modificación del archivo contra reglas de tipo DATE.
        """
        rule = Rule(condition_type=ConditionType.DATE, condition_value=condition_value)
        assert self.evaluator.evaluate(tmp_files["video.mp4"], rule) is expected

    def test_date_newer_than_minutes(self, tmp_files: dict[str, Path]) -> None:
        """
        Prueba que el filtrado por fecha basada en minutos funcione.
        Escenario: Se evalúa si el archivo fue creado/modificado hace menos de X minutos.
        """
        rule = Rule(condition_type=ConditionType.DATE, condition_value="<60 minutes")
        assert self.evaluator.evaluate(tmp_files["video.mp4"], rule) is True

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
        """
        Prueba que el filtrado por nombre de archivo usando patrones (wildcards) funcione.
        Escenario: Se verifica la coincidencia del nombre del archivo contra reglas de tipo NAME.
        """
        rule = Rule(condition_type=ConditionType.NAME, condition_value=condition_value)
        assert self.evaluator.evaluate(tmp_files[filename], rule) is expected

    def test_evaluate_all_multiple_matches(
        self, tmp_files: dict[str, Path], sample_rules: list[Rule]
    ) -> None:
        """
        Prueba que la evaluación de todas las reglas retorne el conjunto de reglas que coinciden con el archivo.
        Escenario: Se aplican múltiples reglas y se comprueba que solo las reglas coincidentes se devuelvan en el resultado.
        """
        matched = self.evaluator.evaluate_all(tmp_files["video.mp4"], sample_rules)
        names = [r.name for r in matched]
        assert "Videos" in names
        assert "Grandes (>100MB)" not in names

    def test_evaluate_all_no_match(self, sample_rules: list[Rule]) -> None:
        """
        Prueba que no se retornen reglas si no hay coincidencias con ningún archivo.
        Escenario: Se intenta evaluar reglas sobre una ruta inexistente, esperando una lista vacía como resultado.
        """
        fake = Path("/nonexistent/file.xyz")
        matched = self.evaluator.evaluate_all(fake, sample_rules)
        assert len(matched) == 0

    def test_invalid_condition_type(self, tmp_files: dict[str, Path]) -> None:
        """
        Prueba que una condición desconocida sea evaluada como False.
        Escenario: Se usa un tipo de condición no soportada, esperando un manejo seguro y resultado negativo.
        """
        rule = Rule(condition_type="unknown", condition_value="x")  # type: ignore[arg-type]
        assert self.evaluator.evaluate(tmp_files["video.mp4"], rule) is False

    @pytest.mark.parametrize(
        "condition_value",
        [
            "",
            " ",
            ".,.",
        ],
    )
    def test_edge_case_extension_values(self, tmp_files: dict[str, Path], condition_value: str) -> None:
        """
        Prueba casos borde en el filtrado por extensión (valores vacíos, malformados).
        Escenario: Se evalúan reglas con valores de condición mal formados, esperando que la evaluación sea negativa.
        """
        rule = Rule(condition_type=ConditionType.EXTENSION, condition_value=condition_value)
        assert self.evaluator.evaluate(tmp_files["video.mp4"], rule) is False

    def test_file_without_extension(self, tmp_path: Path) -> None:
        """
        Prueba que el filtrado por extensión funcione correctamente para archivos sin extensión.
        Escenario: Un archivo sin extensión no debe coincidir con una regla de extensión común.
        """
        f = tmp_path / "README"
        f.write_text("hello")
        rule = Rule(condition_type=ConditionType.EXTENSION, condition_value=".txt,.md")
        assert self.evaluator.evaluate(f, rule) is False

    def test_file_with_only_extension(self, tmp_path: Path) -> None:
        """
        Prueba que el filtrado por extensión funcione para archivos cuyo nombre es solo una extensión (ej. .hidden.bak).
        Escenario: Se verifica que se detecte correctamente la extensión de archivos con nombres atípicos.
        """
        f = tmp_path / ".hidden.bak"
        f.write_text("content")
        rule = Rule(condition_type=ConditionType.EXTENSION, condition_value=".bak")
        assert self.evaluator.evaluate(f, rule) is True
