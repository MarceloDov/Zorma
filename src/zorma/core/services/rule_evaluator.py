from __future__ import annotations

import fnmatch
import re
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

from ..models.rule import ConditionType, Rule


class RuleEvaluator:
    MATCH_ALL_EXTENSIONS = "*"
    _SIZE_RE = re.compile(r"(<=?|>=?|==?)\s*(\d+)\s*(KB|MB|GB)?", re.IGNORECASE)
    _DATE_RE = re.compile(r"(<|>|==?)\s*(\d+)\s*(days|hours|minutes)?", re.IGNORECASE)
    _SIZE_MULTIPLIERS = {"KB": 1024, "MB": 1024**2, "GB": 1024**3}

    def evaluate(self, file: Path, rule: Rule) -> bool:
        if not rule.enabled:
            return False
        try:
            evaluator = {
                ConditionType.EXTENSION: self._eval_extension,
                ConditionType.SIZE: self._eval_size,
                ConditionType.DATE: self._eval_date,
                ConditionType.NAME: self._eval_name,
            }
            fn = evaluator.get(rule.condition_type)
            if fn is None:
                return False
            return fn(file, rule.condition_value)
        except Exception:
            return False

    def evaluate_all(self, file: Path, rules: list[Rule]) -> list[Rule]:
        matched: list[Rule] = []
        for rule in rules:
            if self.evaluate(file, rule):
                matched.append(rule)
        return matched

    def _eval_extension(self, file: Path, value: str) -> bool:
        exts = [e.strip().lower().lstrip('.') for e in value.split(",")]
        if self.MATCH_ALL_EXTENSIONS in exts:
            if not file.suffix or file.name.startswith('.'):
                return False
            ignored_system_exts = {'ini', 'sys', 'dll', 'pem', 'rdp', 'tmp', 'crdownload', 'part', 'lnk'}
            if file.suffix[1:].lower() in ignored_system_exts:
                return False
            return True
        file_ext = file.suffix.lower().lstrip('.')
        return file_ext in exts

    def _eval_size(self, file: Path, value: str) -> bool:
        match = self._SIZE_RE.match(value.strip())
        if not match:
            return False
        op, amount, unit = match.groups()
        file_size = file.stat().st_size
        threshold = int(amount)
        if unit:
            threshold *= self._SIZE_MULTIPLIERS.get(unit.upper(), 1)
        ops: dict[str, Callable[[int, int], bool]] = {
            "<": lambda f, t: f < t,
            "<=": lambda f, t: f <= t,
            ">": lambda f, t: f > t,
            ">=": lambda f, t: f >= t,
            "==": lambda f, t: f == t,
        }
        fn = ops.get(op)
        if fn is None:
            return False
        return fn(file_size, threshold)

    def _eval_date(self, file: Path, value: str) -> bool:
        match = self._DATE_RE.match(value.strip())
        if not match:
            return False
        op, amount, unit = match.groups()
        delta_map = {"days": "days", "hours": "hours", "minutes": "minutes"}
        kw = {delta_map.get(unit.lower(), "days"): int(amount)}
        cutoff = datetime.now() - timedelta(**kw)

        try:
            file_mtime = datetime.fromtimestamp(file.stat().st_mtime)
        except OSError:
            return False
        # "<1 days" means age < 1 day → file_mtime > cutoff (more recent)
        # ">30 days" means age > 30 days → file_mtime < cutoff (older)
        date_ops: dict[str, Callable[[datetime, datetime], bool]] = {
            "<": lambda mtime, cut: mtime > cut,
            ">": lambda mtime, cut: mtime < cut,
            "==": lambda mtime, cut: abs((mtime - cut).total_seconds()) < 60,
        }
        fn = date_ops.get(op)
        if fn is None:
            return False
        return fn(file_mtime, cutoff)

    def _eval_name(self, file: Path, value: str) -> bool:
        name = file.stem
        if "*" in value or "?" in value:
            return fnmatch.fnmatch(name, value)
        return value.lower() in name.lower()
