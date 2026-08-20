from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class FilterConfig:
    include_extensions: set[str] | None = None
    exclude_extensions: set[str] | None = None
    max_size: int | None = None
    min_size: int | None = None
    include_hidden: bool = False
    exclude_dirs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.include_extensions is not None:
            self.include_extensions = set(self.include_extensions)
        if self.exclude_extensions is not None:
            self.exclude_extensions = set(self.exclude_extensions)

    def coincide(self, file_path: Path) -> bool:
        if not self.include_hidden and file_path.name.startswith("."):
            return False
        suffix = file_path.suffix.lower()
        if self.include_extensions is not None and suffix not in self.include_extensions:
            return False
        if self.exclude_extensions is not None and suffix in self.exclude_extensions:
            return False
        if self.min_size is not None or self.max_size is not None:
            try:
                sz = file_path.stat().st_size
                if self.min_size is not None and sz < self.min_size:
                    return False
                if self.max_size is not None and sz > self.max_size:
                    return False
            except OSError:
                return False
        if self.exclude_dirs:
            exclude_dirs_lower = [d.lower() for d in self.exclude_dirs]
            for part in file_path.parent.parts:
                if part.lower() in exclude_dirs_lower:
                    return False
        # ponytail: hardcoded safety filter for Windows system dirs shared by all call sites
        return not any(part.startswith("Archivos ") for part in file_path.parts)
