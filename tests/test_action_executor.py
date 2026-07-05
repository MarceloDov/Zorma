from pathlib import Path

import pytest

from zorma.core.models.classification import ClassificationStatus
from zorma.core.models.rule import ActionType, RuleAction
from zorma.core.services.action_executor import ActionExecutor


class TestActionExecutor:
    """
    Clase de pruebas para ActionExecutor.
    Se encarga de verificar la ejecución de acciones de archivos (mover, copiar, renombrar), incluyendo el manejo de conflictos, la creación dinámica de carpetas y la reversión (rollback) de acciones.
    """
    def setup_method(self) -> None:
        """Configura el ejecutor antes de cada prueba, inicializando una instancia limpia de ActionExecutor."""
        self.executor = ActionExecutor()

    @pytest.mark.parametrize("action_type", [ActionType.MOVE, ActionType.COPY])
    def test_move_copy_success(self, tmp_path: Path, action_type: ActionType) -> None:
        """
        Prueba que la ejecución de acciones de mover y copiar archivos funciona correctamente cuando el destino no existe.
        Escenario: Un archivo origen existe y el directorio destino es válido y no contiene conflictos, por lo que la acción debe completarse exitosamente.
        """
        src = tmp_path / "test.txt"
        src.write_text("hello")
        dest_dir = tmp_path / "destination"
        action = RuleAction(action_type=action_type, target_folder=str(dest_dir))
        result = self.executor.execute(action, src)
        assert result.status == ClassificationStatus.SUCCESS
        assert result.destination_path is not None
        assert result.destination_path.exists()
        if action_type == ActionType.MOVE:
            assert not src.exists()
        else:
            assert src.exists()

    def test_rename_success(self, tmp_path: Path) -> None:
        """
        Prueba que la acción de renombrar un archivo funciona correctamente.
        Escenario: Un archivo existente se renombra aplicando un patrón, verificando que el archivo destino se cree y el origen desaparezca.
        """
        src = tmp_path / "test.txt"
        src.write_text("hello")
        action = RuleAction(action_type=ActionType.RENAME, rename_pattern="{name}_backup{ext}")
        result = self.executor.execute(action, src)
        assert result.status == ClassificationStatus.SUCCESS
        assert result.destination_path is not None
        assert result.destination_path.name == "test_backup.txt"
        assert not src.exists()

    def test_rename_no_double_extension(self, tmp_path: Path) -> None:
        """
        Prueba que la acción de renombrar no duplique las extensiones de archivo.
        Escenario: Al renombrar un archivo, se debe reemplazar el nombre base correctamente sin concatenar extensiones innecesariamente.
        """
        src = tmp_path / "report.txt"
        src.write_text("hello")
        action = RuleAction(action_type=ActionType.RENAME, rename_pattern="{name}_backup{ext}")
        result = self.executor.execute(action, src)
        assert result.status == ClassificationStatus.SUCCESS
        assert result.destination_path is not None
        assert result.destination_path.name == "report_backup.txt"
        assert result.destination_path.suffix == ".txt"

    def test_move_destination_exists(self, tmp_path: Path) -> None:
        """
        Prueba que mover un archivo resulta en estado SKIPPED si el destino ya contiene un archivo con el mismo nombre.
        Escenario: Conflicto de nombres al intentar mover un archivo a una carpeta donde ya existe un archivo idéntico o con el mismo nombre.
        """
        src = tmp_path / "test.txt"
        src.write_text("hello")
        dest_dir = tmp_path / "destination"
        dest_dir.mkdir()
        (dest_dir / "test.txt").write_text("existing")
        action = RuleAction(action_type=ActionType.MOVE, target_folder=str(dest_dir))
        result = self.executor.execute(action, src)
        assert result.status == ClassificationStatus.SKIPPED

    def test_source_not_found(self, tmp_path: Path) -> None:
        """
        Prueba que se reporte un error si el archivo de origen no existe.
        Escenario: El archivo de origen especificado para mover no está presente en el sistema de archivos.
        """
        src = tmp_path / "nonexistent.txt"
        action = RuleAction(action_type=ActionType.MOVE, target_folder=str(tmp_path))
        result = self.executor.execute(action, src)
        assert result.status == ClassificationStatus.ERROR

    def test_rollback_move(self, tmp_path: Path) -> None:
        """
        Prueba que la función de reversión (rollback) mueve el archivo correctamente de vuelta al origen.
        Escenario: Se requiere revertir una acción exitosa de mover un archivo.
        """
        src = tmp_path / "test.txt"
        src.write_text("hello")
        dest_dir = tmp_path / "destination"
        dest_dir.mkdir()
        dest = dest_dir / "test.txt"
        dest.write_text("hello")
        action = RuleAction(action_type=ActionType.MOVE, target_folder=str(dest_dir))
        result = self.executor.rollback(action, dest, src)
        assert result.status == ClassificationStatus.SUCCESS
        assert src.exists()
        assert not dest.exists()

    def test_rollback_file_not_found(self, tmp_path: Path) -> None:
        """
        Prueba que la reversión (rollback) falle si el archivo de destino no existe.
        Escenario: Se intenta revertir el movimiento de un archivo que ya no está presente en la ubicación de destino.
        """
        src = tmp_path / "original.txt"
        dest = tmp_path / "nonexistent.txt"
        action = RuleAction(action_type=ActionType.MOVE, target_folder=str(tmp_path))
        result = self.executor.rollback(action, dest, src)
        assert result.status == ClassificationStatus.ERROR

    @pytest.mark.parametrize("exists", [True, False])
    def test_check_conflict(self, tmp_path: Path, exists: bool) -> None:
        """
        Prueba que check_conflict detecte correctamente si un archivo ya existe en el directorio destino.
        Escenario: Se verifica la existencia de un conflicto basándose en si un archivo con el mismo nombre está presente en el destino.
        """
        src = tmp_path / "test.txt"
        src.write_text("hello")
        dest_dir = tmp_path / "destination"
        dest_dir.mkdir()
        if exists:
            (dest_dir / "test.txt").write_text("existing")
        action = RuleAction(action_type=ActionType.MOVE, target_folder=str(dest_dir))
        has_conflict, dest = self.executor.check_conflict(action, src)
        assert has_conflict is exists

    def test_build_dest_path_with_ext_template(self, tmp_path: Path) -> None:
        """
        Prueba la creación dinámica de carpetas de destino utilizando plantillas con la extensión del archivo.
        Escenario: La carpeta destino contiene la plantilla '{ext}', que debe sustituirse por la extensión real del archivo origen.
        """
        src = tmp_path / "notas.txt"
        src.write_text("hello")
        dest_dir = str(tmp_path / "Archivos {ext}")
        action = RuleAction(action_type=ActionType.MOVE, target_folder=dest_dir)
        result = self.executor.execute(action, src)
        assert result.status == ClassificationStatus.SUCCESS
        assert result.destination_path is not None
        assert "Archivos .txt" in str(result.destination_path.parent)
        assert result.destination_path.name == "notas.txt"

    @pytest.mark.parametrize(
        "filename,template_str,expected_folder",
        [
            ("foto.jpg", "Imagenes {ext}", "Imagenes .jpg"),
            ("doc.pdf", "Documentos {ext}", "Documentos .pdf"),
            ("video.mp4", "Videos {ext}", "Videos .mp4"),
        ],
    )
    def test_build_dest_path_with_ext_template_multiple(
        self, tmp_path: Path, filename: str, template_str: str, expected_folder: str
    ) -> None:
        """
        Prueba la creación dinámica de múltiples carpetas basadas en diferentes extensiones de archivo.
        Escenario: Varios archivos con distintas extensiones se mueven a carpetas creadas dinámicamente según su tipo.
        """
        src = tmp_path / filename
        src.write_text("data")
        dest_dir = str(tmp_path / template_str)
        action = RuleAction(action_type=ActionType.MOVE, target_folder=dest_dir)
        result = self.executor.execute(action, src)
        assert result.status == ClassificationStatus.SUCCESS
        assert result.destination_path is not None
        assert result.destination_path.parent == tmp_path / expected_folder

    def test_file_with_no_extension(self, tmp_path: Path) -> None:
        """
        Prueba que el manejo de archivos sin extensión funcione correctamente.
        Escenario: Un archivo sin extensión se mueve correctamente a la carpeta destino sin errores de formato.
        """
        src = tmp_path / "README"
        src.write_text("hello")
        dest_dir = tmp_path / "destination"
        action = RuleAction(action_type=ActionType.MOVE, target_folder=str(dest_dir))
        result = self.executor.execute(action, src)
        assert result.status == ClassificationStatus.SUCCESS
        assert (dest_dir / "README").exists()

    def test_nested_directory_creation(self, tmp_path: Path) -> None:
        """
        Prueba que la creación de directorios anidados funcione correctamente al mover archivos.
        Escenario: Se especifica una ruta de destino con múltiples niveles de subcarpetas que deben crearse automáticamente.
        """
        src = tmp_path / "doc.txt"
        src.write_text("hello")
        dest_dir = tmp_path / "a" / "b" / "c"
        action = RuleAction(action_type=ActionType.MOVE, target_folder=str(dest_dir))
        result = self.executor.execute(action, src)
        assert result.status == ClassificationStatus.SUCCESS
        assert (dest_dir / "doc.txt").exists()
        assert not src.exists()
