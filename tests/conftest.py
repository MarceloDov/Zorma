from pathlib import Path
from typing import Generator

import pytest

from zorma.core.models.rule import ConditionType, Rule


@pytest.fixture
def sample_rules() -> list[Rule]:
    return [
        Rule(name="Videos", condition_type=ConditionType.EXTENSION, condition_value=".mp4,.mkv,.avi"),
        Rule(name="Música", condition_type=ConditionType.EXTENSION, condition_value=".mp3,.flac,.wav"),
        Rule(name="Documentos", condition_type=ConditionType.EXTENSION, condition_value=".pdf,.doc,.docx,.txt"),
        Rule(name="Imágenes", condition_type=ConditionType.EXTENSION, condition_value=".jpg,.jpeg,.png"),
        Rule(name="Grandes (>100MB)", condition_type=ConditionType.SIZE, condition_value=">100 MB"),
        Rule(name="Antiguos (>30 days)", condition_type=ConditionType.DATE, condition_value=">30 days"),
        Rule(name="Recientes (<1 hour)", condition_type=ConditionType.DATE, condition_value="<1 hours"),
        Rule(name="Contiene 'reporte'", condition_type=ConditionType.NAME, condition_value="reporte"),
    ]


@pytest.fixture
def tmp_files(tmp_path: Path) -> Generator[dict[str, Path], None, None]:
    files = {}
    for name in ("video.mp4", "musica.mp3", "doc.pdf", "imagen.jpg", "reporte_final.xlsx", "comprimido.zip"):
        p = tmp_path / name
        p.write_text("test")
        files[name] = p
    yield files
