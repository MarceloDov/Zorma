from __future__ import annotations

import shutil
from pathlib import Path

from ..models.classification import ClassificationResult, ClassificationStatus
from ..models.rule import ActionType, RuleAction


class ActionExecutor:
    """Ejecuta las acciones definidas en las reglas sobre archivos específicos."""

    def execute(self, action: RuleAction, file: Path) -> ClassificationResult:
        """Ejecuta una acción sobre el archivo dado y retorna el resultado."""
        result = ClassificationResult(
            file_name=file.name,
            source_path=file,
        )
        try:
            if not file.exists():
                return self._error(result, f"Source file not found: {file}")

            dest = self._resolve_destination(action, file)
            if dest.exists():
                return self._skipped(result, f"Destination exists: {dest}")

            if action.action_type in (ActionType.MOVE, ActionType.COPY):
                dest.parent.mkdir(parents=True, exist_ok=True)
                if action.action_type == ActionType.MOVE:
                    shutil.move(str(file), str(dest))
                else:
                    shutil.copy2(str(file), str(dest))
            else:
                file.rename(dest)

            result.destination_path = dest
            result.status = ClassificationStatus.SUCCESS

        except PermissionError as e:
            result.status = ClassificationStatus.ERROR
            result.error_message = f"PERMISSION_DENIED: {e}"
        except OSError as e:
            if e.errno == 28:
                result.status = ClassificationStatus.ERROR
                result.error_message = f"DISK_FULL: {e}"
            else:
                result.status = ClassificationStatus.ERROR
                result.error_message = f"OS_ERROR: {e}"
        return result

    def rollback(self, action: RuleAction, file: Path, original: Path) -> ClassificationResult:
        """Revierte una acción realizada sobre un archivo."""
        result = ClassificationResult(
            file_name=file.name,
            source_path=original,
        )
        try:
            if not file.exists():
                return self._error(result, f"File to rollback not found: {file}")
            dst = original
            if action.action_type in (ActionType.MOVE, ActionType.COPY):
                shutil.move(str(file), str(dst))
            elif action.action_type == ActionType.RENAME:
                file.rename(dst)
            result.destination_path = dst
            result.status = ClassificationStatus.SUCCESS
        except OSError as e:
            result.status = ClassificationStatus.ERROR
            result.error_message = str(e)
        return result

    def check_conflict(self, action: RuleAction, file: Path) -> tuple[bool, Path]:
        """Verifica si existe un conflicto de destino para una acción."""
        dest = self._resolve_destination(action, file)
        return dest.exists(), dest

    def _resolve_destination(self, action: RuleAction, file: Path) -> Path:
        """Resuelve la ruta de destino basándose en la acción y el archivo."""
        if action.action_type == ActionType.RENAME:
            new_name = self._apply_rename_pattern(action, file)
            return file.parent / new_name
        return self._build_dest_path(action, file)

    @staticmethod
    def _error(result: ClassificationResult, message: str) -> ClassificationResult:
        """Registra un error en el resultado."""
        result.status = ClassificationStatus.ERROR
        result.error_message = message
        return result

    @staticmethod
    def _skipped(result: ClassificationResult, message: str) -> ClassificationResult:
        """Marca un resultado como omitido."""
        result.status = ClassificationStatus.SKIPPED
        result.error_message = message
        return result

    def _build_dest_path(self, action: RuleAction, file: Path) -> Path:
        """Construye y valida la ruta de destino, previniendo ataques de path traversal."""
        target_str = action.target_folder
        if not target_str:
            raise ValueError("Target folder cannot be empty")

        ext_no_dot = file.suffix[1:].lower() if file.suffix else "varios"
        target_str = target_str.replace("{ext}", ext_no_dot)
        raw = Path(target_str)

        # Validaciones de seguridad de ruta
        if ".." in raw.parts:
            raise ValueError(f"Path traversal detected in target folder: {target_str}")

        if raw.is_absolute():
            target = raw.resolve()
        else:
            target = (file.parent / raw).resolve()

        # Validación final: la ruta debe ser absoluta
        if not target.is_absolute():
             raise ValueError("Invalid target path: must be absolute")

        return target / file.name

    def _apply_rename_pattern(self, action: RuleAction, file: Path) -> str:
        """Aplica el patrón de renombrado configurado en la regla."""
        pattern = action.rename_pattern or file.stem
        new_name = pattern.replace("{name}", file.stem).replace("{ext}", file.suffix)
        if not new_name.endswith(file.suffix):
            new_name = f"{new_name}{file.suffix}"
        return new_name
