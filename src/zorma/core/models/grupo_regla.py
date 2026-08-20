from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


@dataclass
class GrupoRegla:
    id: str = field(default_factory=lambda: uuid4().hex)
    nombre: str = ""
    descripcion: str = ""
    prioridad: int = 0
    es_predeterminado: bool = False
    creado_en: datetime = field(default_factory=lambda: datetime.now(UTC))
