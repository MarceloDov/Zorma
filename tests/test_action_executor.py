from pathlib import Path

import pytest

from zorma.core.models.accion_regla import AccionRegla
from zorma.core.models.archivo import Archivo
from zorma.core.models.enums import EstadoClasificacion, TipoAccion


def _archivo(path: Path) -> Archivo:
    return Archivo(_ruta_completa=path)


class TestActionExecutor:
    @pytest.mark.parametrize("tipo_accion", [TipoAccion.MOVER, TipoAccion.COPIAR])
    def test_move_copy_success(self, tmp_path: Path, tipo_accion: TipoAccion) -> None:
        src = tmp_path / "test.txt"
        src.write_text("hello")
        dest_dir = tmp_path / "destination"
        action = AccionRegla(tipo_accion=tipo_accion, carpeta_destino=str(dest_dir))
        result = action.ejecutar(_archivo(src))
        assert result.estado == EstadoClasificacion.EXITO
        assert result.ruta_destino is not None
        assert result.ruta_destino.exists()
        if tipo_accion == TipoAccion.MOVER:
            assert not src.exists()
        else:
            assert src.exists()

    def test_rename_success(self, tmp_path: Path) -> None:
        src = tmp_path / "test.txt"
        src.write_text("hello")
        action = AccionRegla(tipo_accion=TipoAccion.RENOMBRAR, patron_renombre="{name}_backup{ext}")
        result = action.ejecutar(_archivo(src))
        assert result.estado == EstadoClasificacion.EXITO
        assert result.ruta_destino is not None
        assert result.ruta_destino.name == "test_backup.txt"
        assert not src.exists()

    def test_rename_no_double_extension(self, tmp_path: Path) -> None:
        src = tmp_path / "report.txt"
        src.write_text("hello")
        action = AccionRegla(tipo_accion=TipoAccion.RENOMBRAR, patron_renombre="{name}_backup{ext}")
        result = action.ejecutar(_archivo(src))
        assert result.estado == EstadoClasificacion.EXITO
        assert result.ruta_destino is not None
        assert result.ruta_destino.name == "report_backup.txt"
        assert result.ruta_destino.suffix == ".txt"

    def test_move_destination_exists(self, tmp_path: Path) -> None:
        src = tmp_path / "test.txt"
        src.write_text("hello")
        dest_dir = tmp_path / "destination"
        dest_dir.mkdir()
        (dest_dir / "test.txt").write_text("existing")
        action = AccionRegla(tipo_accion=TipoAccion.MOVER, carpeta_destino=str(dest_dir))
        result = action.ejecutar(_archivo(src))
        assert result.estado == EstadoClasificacion.OMITIDO

    def test_source_not_found(self, tmp_path: Path) -> None:
        src = tmp_path / "nonexistent.txt"
        action = AccionRegla(tipo_accion=TipoAccion.MOVER, carpeta_destino=str(tmp_path))
        result = action.ejecutar(_archivo(src))
        assert result.estado == EstadoClasificacion.ERROR

    def test_rollback_move(self, tmp_path: Path) -> None:
        src = tmp_path / "test.txt"
        src.write_text("hello")
        dest_dir = tmp_path / "destination"
        dest_dir.mkdir()
        dest = dest_dir / "test.txt"
        dest.write_text("hello")
        action = AccionRegla(tipo_accion=TipoAccion.MOVER, carpeta_destino=str(dest_dir))
        result = action.revertir(_archivo(dest), src)
        assert result.estado == EstadoClasificacion.EXITO
        assert src.exists()
        assert not dest.exists()

    def test_rollback_file_not_found(self, tmp_path: Path) -> None:
        src = tmp_path / "original.txt"
        dest = tmp_path / "nonexistent.txt"
        action = AccionRegla(tipo_accion=TipoAccion.MOVER, carpeta_destino=str(tmp_path))
        result = action.revertir(_archivo(dest), src)
        assert result.estado == EstadoClasificacion.ERROR

    @pytest.mark.parametrize("exists", [True, False])
    def test_check_conflict(self, tmp_path: Path, exists: bool) -> None:
        src = tmp_path / "test.txt"
        src.write_text("hello")
        dest_dir = tmp_path / "destination"
        dest_dir.mkdir()
        if exists:
            (dest_dir / "test.txt").write_text("existing")
        action = AccionRegla(tipo_accion=TipoAccion.MOVER, carpeta_destino=str(dest_dir))
        has_conflict = action.verificar_conflicto(_archivo(src))
        assert has_conflict is exists

    def test_build_dest_path_with_ext_template(self, tmp_path: Path) -> None:
        src = tmp_path / "notas.txt"
        src.write_text("hello")
        dest_dir = str(tmp_path / "Archivos {ext}")
        action = AccionRegla(tipo_accion=TipoAccion.MOVER, carpeta_destino=dest_dir)
        result = action.ejecutar(_archivo(src))
        assert result.estado == EstadoClasificacion.EXITO
        assert result.ruta_destino is not None
        assert "Archivos .txt" in str(result.ruta_destino.parent)
        assert result.ruta_destino.name == "notas.txt"

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
        src = tmp_path / filename
        src.write_text("data")
        dest_dir = str(tmp_path / template_str)
        action = AccionRegla(tipo_accion=TipoAccion.MOVER, carpeta_destino=dest_dir)
        result = action.ejecutar(_archivo(src))
        assert result.estado == EstadoClasificacion.EXITO
        assert result.ruta_destino is not None
        assert result.ruta_destino.parent == tmp_path / expected_folder

    def test_file_with_no_extension(self, tmp_path: Path) -> None:
        src = tmp_path / "README"
        src.write_text("hello")
        dest_dir = tmp_path / "destination"
        action = AccionRegla(tipo_accion=TipoAccion.MOVER, carpeta_destino=str(dest_dir))
        result = action.ejecutar(_archivo(src))
        assert result.estado == EstadoClasificacion.EXITO
        assert (dest_dir / "README").exists()

    def test_nested_directory_creation(self, tmp_path: Path) -> None:
        src = tmp_path / "doc.txt"
        src.write_text("hello")
        dest_dir = tmp_path / "a" / "b" / "c"
        action = AccionRegla(tipo_accion=TipoAccion.MOVER, carpeta_destino=str(dest_dir))
        result = action.ejecutar(_archivo(src))
        assert result.estado == EstadoClasificacion.EXITO
        assert (dest_dir / "doc.txt").exists()
        assert not src.exists()
