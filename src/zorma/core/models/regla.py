from __future__ import annotations

import fnmatch
import logging
import operator
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

from .enums import TipoCondicion

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from .archivo import Archivo

logger = logging.getLogger(__name__)


@dataclass
class Regla:
    _SIZE_RE = re.compile(r"(<=?|>=?|==?)\s*(\d+)\s*(KB|MB|GB)?", re.IGNORECASE)
    _DATE_RE = re.compile(
        r"(<|>|==?)\s*(\d+)\s*(days|hours|minutes|días|dias|horas|hora|minutos|minuto)?", re.IGNORECASE
    )
    _SIZE_MULTIPLIERS = {"KB": 1024, "MB": 1024**2, "GB": 1024**3}
    MATCH_ALL_EXTENSIONS = "*"

    id: str = field(default_factory=lambda: uuid4().hex)
    id_grupo: str = ""
    nombre: str = ""
    habilitada: bool = True
    prioridad: int = 0
    tipo_condicion: TipoCondicion = TipoCondicion.EXTENSION
    valor_condicion: str = ""
    creado_en: datetime = field(default_factory=lambda: datetime.now(UTC))

    def evaluar(self, archivo: Archivo) -> bool:
        if not self.habilitada:
            return False
        try:
            evaluadores = {
                TipoCondicion.EXTENSION: self._eval_extension,
                TipoCondicion.TAMANIO: self._eval_size,
                TipoCondicion.FECHA: self._eval_date,
                TipoCondicion.NOMBRE: self._eval_name,
            }
            fn = evaluadores.get(self.tipo_condicion)
            if fn is None:
                return False
            return fn(archivo._ruta_completa)
        except (OSError, ValueError, TypeError) as e:
            logger.warning("Error evaluando regla %s en %s: %s", self.id, archivo._ruta_completa, e)
            return False

    def obtener_descripcion(self) -> str:
        return f"{self.nombre} ({self.tipo_condicion.value}: {self.valor_condicion})"

    def _eval_extension(self, file: Path) -> bool:
        value = self.valor_condicion
        exts = [e.strip().lower().lstrip(".") for e in value.split(",")]
        if self.MATCH_ALL_EXTENSIONS in exts:
            if not file.suffix or file.name.startswith("."):
                return False
            ignored_system_exts = {"ini", "sys", "dll", "pem", "rdp", "tmp", "crdownload", "part", "lnk"}
            return file.suffix[1:].lower() not in ignored_system_exts
        file_ext = file.suffix.lower().lstrip(".")
        return file_ext in exts

    def _eval_size(self, file: Path) -> bool:
        value = self.valor_condicion
        match = self._SIZE_RE.match(value.strip())
        if not match:
            return False
        op, amount, unit = match.groups()
        file_size = file.stat().st_size
        threshold = int(amount)
        if unit:
            threshold *= self._SIZE_MULTIPLIERS.get(unit.upper(), 1)
        ops: dict[str, Callable[[int, int], bool]] = {
            "<": operator.lt,
            "<=": operator.le,
            ">": operator.gt,
            ">=": operator.ge,
            "==": operator.eq,
        }
        fn = ops.get(op)
        if fn is None:
            return False
        return fn(file_size, threshold)

    def _eval_date(self, file: Path) -> bool:
        value = self.valor_condicion
        match = self._DATE_RE.match(value.strip())
        if not match:
            return False
        op, amount, unit = match.groups()
        if unit is None:
            unit = "days"
        delta_map = {
            "days": "days",
            "días": "days",
            "dias": "days",
            "hours": "hours",
            "horas": "hours",
            "hora": "hours",
            "minutes": "minutes",
            "minutos": "minutes",
            "minuto": "minutes",
        }
        kw = {delta_map.get(unit.lower(), "days"): int(amount)}
        cutoff = datetime.now(UTC) - timedelta(**kw)

        try:
            file_mtime = datetime.fromtimestamp(file.stat().st_mtime, tz=UTC)
        except OSError:
            return False
        date_ops: dict[str, Callable[[datetime, datetime], bool]] = {
            "<": lambda mtime, cut: mtime > cut,
            ">": lambda mtime, cut: mtime < cut,
            "==": lambda mtime, cut: abs((mtime - cut).total_seconds()) < 60,
        }
        fn = date_ops.get(op)
        if fn is None:
            return False
        return fn(file_mtime, cutoff)

    def _eval_name(self, file: Path) -> bool:
        value = self.valor_condicion
        name = file.stem
        if "*" in value or "?" in value:
            return fnmatch.fnmatch(name, value)
        return value.lower() in name.lower()
