from pathlib import Path

from zorma.core.models.filter_config import FilterConfig


class TestFilterConfig:
    """
    Clase de pruebas para `FilterConfig`.
    Verifica que las reglas de filtrado de archivos (extensiones, tamaños, archivos ocultos, directorios excluidos) se apliquen correctamente para determinar si un archivo debe ser procesado.
    """
    def test_no_filter_passes(self, tmp_path: Path) -> None:
        """
        Prueba que un archivo pase el filtro cuando no se aplican reglas de filtrado.
        Escenario: Un archivo .txt estándar con un filtro vacío debe ser aceptado.
        """
        f = tmp_path / "test.txt"
        f.write_text("hello")
        cfg = FilterConfig()
        assert cfg.matches(f) is True

    def test_include_extensions_pass(self, tmp_path: Path) -> None:
        """
        Prueba que un archivo pase el filtro si su extensión está incluida.
        Escenario: Se configura el filtro para incluir solo .txt, y un archivo con extensión .txt debe ser aceptado.
        """
        f = tmp_path / "test.txt"
        f.write_text("hello")
        cfg = FilterConfig(include_extensions=[".txt"])
        assert cfg.matches(f) is True

    def test_include_extensions_fail(self, tmp_path: Path) -> None:
        """
        Prueba que un archivo sea filtrado si su extensión no está incluida.
        Escenario: Se configura el filtro para incluir solo .txt, y un archivo con extensión .pdf debe ser filtrado.
        """
        f = tmp_path / "test.pdf"
        f.write_text("hello")
        cfg = FilterConfig(include_extensions=[".txt"])
        assert cfg.matches(f) is False

    def test_exclude_extensions(self, tmp_path: Path) -> None:
        """
        Prueba que un archivo sea filtrado si su extensión está explícitamente excluida.
        Escenario: Se configura el filtro para excluir .txt, y un archivo con extensión .txt debe ser filtrado.
        """
        f = tmp_path / "test.txt"
        f.write_text("hello")
        cfg = FilterConfig(exclude_extensions=[".txt"])
        assert cfg.matches(f) is False

    def test_exclude_not_matching(self, tmp_path: Path) -> None:
        """
        Prueba que un archivo pase el filtro si su extensión no coincide con ninguna exclusión.
        Escenario: Se configura el filtro para excluir .txt, y un archivo con extensión .pdf debe ser aceptado.
        """
        f = tmp_path / "test.pdf"
        f.write_text("hello")
        cfg = FilterConfig(exclude_extensions=[".txt"])
        assert cfg.matches(f) is True

    def test_hidden_file_excluded_by_default(self, tmp_path: Path) -> None:
        """
        Prueba que los archivos ocultos sean filtrados por defecto.
        Escenario: Un archivo cuyo nombre comienza con '.' debe ser filtrado si no se permite explícitamente.
        """
        f = tmp_path / ".hidden.txt"
        f.write_text("hello")
        cfg = FilterConfig()
        assert cfg.matches(f) is False

    def test_hidden_file_included(self, tmp_path: Path) -> None:
        """
        Prueba que un archivo oculto pase el filtro si se permite explícitamente.
        Escenario: Se habilita `include_hidden=True`, por lo que un archivo oculto debe ser aceptado.
        """
        f = tmp_path / ".hidden.txt"
        f.write_text("hello")
        cfg = FilterConfig(include_hidden=True)
        assert cfg.matches(f) is True

    def test_max_size(self, tmp_path: Path) -> None:
        """
        Prueba que un archivo sea filtrado si excede el tamaño máximo permitido.
        Escenario: Un archivo mayor que el `max_size` configurado debe ser filtrado.
        """
        f = tmp_path / "large.txt"
        f.write_text("x" * 1000)
        cfg = FilterConfig(max_size=500)
        assert cfg.matches(f) is False

    def test_min_size(self, tmp_path: Path) -> None:
        """
        Prueba que un archivo sea filtrado si es menor que el tamaño mínimo permitido.
        Escenario: Un archivo menor que el `min_size` configurado debe ser filtrado.
        """
        f = tmp_path / "small.txt"
        f.write_text("hi")
        cfg = FilterConfig(min_size=100)
        assert cfg.matches(f) is False

    def test_size_in_range(self, tmp_path: Path) -> None:
        """
        Prueba que un archivo pase el filtro si su tamaño está dentro del rango permitido.
        Escenario: Un archivo cuyo tamaño está entre `min_size` y `max_size` debe ser aceptado.
        """
        f = tmp_path / "medium.txt"
        f.write_text("x" * 200)
        cfg = FilterConfig(min_size=100, max_size=500)
        assert cfg.matches(f) is True

    def test_exclude_dirs(self, tmp_path: Path) -> None:
        """
        Prueba que un archivo dentro de un directorio excluido sea filtrado.
        Escenario: Se excluye el directorio 'node_modules', por lo que cualquier archivo en esa ruta debe ser filtrado.
        """
        d = tmp_path / "node_modules"
        d.mkdir()
        f = d / "test.txt"
        f.write_text("hello")
        cfg = FilterConfig(exclude_dirs=["node_modules"])
        assert cfg.matches(f) is False
