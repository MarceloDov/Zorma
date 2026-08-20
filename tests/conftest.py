from collections.abc import Generator
from pathlib import Path

import pytest

from zorma.core.models.enums import TipoCondicion
from zorma.core.models.regla import Regla


@pytest.fixture
def sample_rules() -> list[Regla]:
    return [
        Regla(nombre="Videos", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".mp4,.mkv,.avi"),
        Regla(nombre="Música", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".mp3,.flac,.wav"),
        Regla(nombre="Documentos", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".pdf,.doc,.docx,.txt"),
        Regla(nombre="Imágenes", tipo_condicion=TipoCondicion.EXTENSION, valor_condicion=".jpg,.jpeg,.png"),
        Regla(nombre="Grandes (>100MB)", tipo_condicion=TipoCondicion.TAMANIO, valor_condicion=">100 MB"),
        Regla(nombre="Antiguos (>30 days)", tipo_condicion=TipoCondicion.FECHA, valor_condicion=">30 days"),
        Regla(nombre="Recientes (<1 hour)", tipo_condicion=TipoCondicion.FECHA, valor_condicion="<1 hours"),
        Regla(nombre="Contiene 'reporte'", tipo_condicion=TipoCondicion.NOMBRE, valor_condicion="reporte"),
    ]


@pytest.fixture
def tmp_files(tmp_path: Path) -> Generator[dict[str, Path], None, None]:
    files = {}
    for name in ("video.mp4", "musica.mp3", "doc.pdf", "imagen.jpg", "reporte_final.xlsx", "comprimido.zip"):
        p = tmp_path / name
        p.write_text("test")
        files[name] = p
    yield files
