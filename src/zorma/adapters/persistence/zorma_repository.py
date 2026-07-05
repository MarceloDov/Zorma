from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ...core.models.classification import ClassificationResult, ClassificationStatus
from ...core.models.rule import ActionType, ConditionType, Rule, RuleAction, RuleGroup
from ...core.models.undo_entry import UndoEntry

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 4


class ZormaRepository:
    def __init__(self, data_dir: Path, undo_limit: int = 1000) -> None:
        self._file = data_dir / "zorma.json"
        self._undo_limit = undo_limit
        self._data: dict[str, Any] = {}
        self._load()

    # ── persistence ──

    def _default_data(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "theme": "dark",
            "settings": {},
            "rules": [],
            "groups": [],
            "actions": [],
            "undo": [],
            "redo": [],
            "history": [],
        }

    def _load(self) -> None:
        if not self._file.exists():
            self._data = self._default_data()
            return
        try:
            raw = json.loads(self._file.read_text(encoding="utf-8"))
            if raw.get("schema_version", 0) < SCHEMA_VERSION:
                logger.info("Schema v%d < v%d — migrating", raw.get("schema_version", 0), SCHEMA_VERSION)
                raw["schema_version"] = SCHEMA_VERSION
            self._data = {**self._default_data(), **raw}
        except (json.JSONDecodeError, OSError):
            logger.exception("Failed to load %s, using defaults", self._file)
            self._data = self._default_data()

    def _save(self) -> None:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        tmp_fd, tmp_path = tempfile.mkstemp(dir=self._file.parent, suffix=".tmp", text=True)
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, default=str)
            os.replace(tmp_path, self._file)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            logger.exception("Failed to save %s", self._file)
            raise
        logger.debug("Saved to %s", self._file)

    # ── helpers ──

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    # ── rules ──

    def get_all_rules(self) -> list[Rule]:
        return sorted(
            (self._deserialize_rule(r) for r in self._data["rules"]),
            key=lambda r: r.priority,
        )

    def get_rule_by_id(self, rule_id: str) -> Rule | None:
        for r in self._data["rules"]:
            if r["id"] == rule_id:
                return self._deserialize_rule(r)
        return None

    def get_rules_by_group(self, group_id: str) -> list[Rule]:
        return [self._deserialize_rule(r) for r in self._data["rules"] if r.get("group_id") == group_id]

    def save_rule(self, rule: Rule) -> None:
        data = self._serialize_rule(rule)
        for i, r in enumerate(self._data["rules"]):
            if r["id"] == rule.id:
                self._data["rules"][i] = data
                break
        else:
            self._data["rules"].append(data)
        self._save()

    def delete_rule(self, rule_id: str) -> None:
        self._data["rules"] = [r for r in self._data["rules"] if r["id"] != rule_id]
        self._data["actions"] = [a for a in self._data["actions"] if a.get("rule_id") != rule_id]
        logger.debug("Deleted rule %s", rule_id)
        self._save()

    # ── groups ──

    def get_groups(self) -> list[RuleGroup]:
        return [self._deserialize_group(g) for g in self._data["groups"]]

    def save_group(self, group: RuleGroup) -> None:
        data = {
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "priority": group.priority,
            "is_default": group.is_default,
            "created_at": group.created_at.isoformat() if isinstance(group.created_at, datetime) else group.created_at,
            "updated_at": self._now(),
        }
        for i, g in enumerate(self._data["groups"]):
            if g["id"] == group.id:
                self._data["groups"][i] = data
                break
        else:
            self._data["groups"].append(data)
        self._save()

    def delete_group(self, group_id: str) -> None:
        rule_ids = {r["id"] for r in self._data["rules"] if r.get("group_id") == group_id}
        self._data["groups"] = [g for g in self._data["groups"] if g["id"] != group_id]
        self._data["rules"] = [r for r in self._data["rules"] if r["id"] not in rule_ids]
        self._data["actions"] = [a for a in self._data["actions"] if a.get("rule_id") not in rule_ids]
        logger.debug("Deleted group %s", group_id)
        self._save()

    # ── actions ──

    def get_actions_for_rule(self, rule_id: str) -> list[RuleAction]:
        return [self._deserialize_action(a) for a in self._data["actions"] if a.get("rule_id") == rule_id]

    def save_action(self, action: RuleAction) -> None:
        data = {
            "id": action.id,
            "rule_id": action.rule_id,
            "action_type": action.action_type.value,
            "target_folder": action.target_folder,
            "copy_enabled": action.copy_enabled,
            "rename_pattern": action.rename_pattern,
            "created_at": action.created_at.isoformat() if isinstance(action.created_at, datetime) else action.created_at,
        }
        for i, a in enumerate(self._data["actions"]):
            if a["id"] == action.id:
                self._data["actions"][i] = data
                break
        else:
            self._data["actions"].append(data)
        self._save()

    def create_default_rules(self) -> None:
        group = RuleGroup(
            name="Clasificación Universal Automática",
            description="Agrupa cualquier archivo seguro según su extensión",
            priority=1,
            is_default=True,
        )
        self.save_group(group)
        rule = Rule(
            group_id=group.id,
            name="Todas las extensiones",
            condition_type=ConditionType.EXTENSION,
            condition_value="*",
        )
        self.save_rule(rule)
        action = RuleAction(rule_id=rule.id, target_folder="Archivos {ext}")
        self.save_action(action)

    # ── undo / redo ──

    def _undo_push(self, stack_key: str, entry: UndoEntry) -> None:
        data = self._serialize_undo(entry)
        self._data[stack_key].append(data)
        if len(self._data[stack_key]) > self._undo_limit:
            self._data[stack_key].pop(0)
        logger.debug("Pushed to %s: %s", stack_key, entry.id)
        self._save()

    def _undo_pop(self, stack_key: str) -> UndoEntry | None:
        if not self._data[stack_key]:
            return None
        entry = self._deserialize_undo(self._data[stack_key].pop())
        logger.debug("Popped from %s: %s", stack_key, entry.id)
        self._save()
        return entry

    def _undo_clear(self, stack_key: str) -> None:
        self._data[stack_key].clear()
        self._save()

    def undo_push(self, entry: UndoEntry) -> None:
        self._undo_push("undo", entry)

    def undo_pop(self) -> UndoEntry | None:
        return self._undo_pop("undo")

    def undo_peek(self) -> UndoEntry | None:
        return self._deserialize_undo(self._data["undo"][-1]) if self._data["undo"] else None

    def undo_size(self) -> int:
        return len(self._data["undo"])

    def undo_clear(self) -> None:
        self._undo_clear("undo")

    def undo_get_all(self) -> list[UndoEntry]:
        return [self._deserialize_undo(e) for e in reversed(self._data["undo"])]

    def undo_mark_reverted(self, entry_id: str) -> None:
        for e in self._data["undo"]:
            if e["id"] == entry_id:
                e["reverted"] = True
                self._save()
                return

    def undo_remove_by_id(self, entry_id: str) -> UndoEntry | None:
        for i, e in enumerate(self._data["undo"]):
            if e["id"] == entry_id:
                removed = self._data["undo"].pop(i)
                self._save()
                return self._deserialize_undo(removed)
        return None

    def redo_push(self, entry: UndoEntry) -> None:
        self._undo_push("redo", entry)

    def redo_pop(self) -> UndoEntry | None:
        return self._undo_pop("redo")

    def redo_clear(self) -> None:
        self._undo_clear("redo")

    def redo_size(self) -> int:
        return len(self._data["redo"])

    # ── history ──

    HISTORY_LIMIT = 10_000

    def add_history(self, result: ClassificationResult) -> None:
        self._data["history"].append({
            "file_name": result.file_name,
            "source_path": str(result.source_path) if result.source_path else None,
            "destination_path": str(result.destination_path) if result.destination_path else None,
            "rule_name": result.rule_applied.name if result.rule_applied else None,
            "action_applied": result.action_applied.action_type.value if result.action_applied else None,
            "status": result.status.value,
            "error_message": result.error_message,
            "timestamp": result.timestamp.isoformat(),
        })
        if len(self._data["history"]) > self.HISTORY_LIMIT:
            self._data["history"] = self._data["history"][-self.HISTORY_LIMIT:]
        self._save()

    def get_history(self) -> list[ClassificationResult]:
        results = []
        for entry in self._data["history"]:
            try:
                results.append(ClassificationResult(
                    file_name=entry["file_name"],
                    source_path=Path(entry["source_path"]) if entry.get("source_path") else None,
                    status=ClassificationStatus(entry["status"]),
                    error_message=entry.get("error_message", ""),
                    timestamp=datetime.fromisoformat(entry["timestamp"]),
                ))
            except (KeyError, ValueError) as e:
                logger.warning("Malformed history entry: %s", e)
                continue
        return results

    # ── theme / config ──

    def get_theme(self) -> str:
        return str(self._data.get("theme", "dark"))

    def set_theme(self, theme: str) -> None:
        self._data["theme"] = theme
        self._save()

    # ── serialization ──

    def _serialize_rule(self, r: Rule) -> dict[str, Any]:
        return {
            "id": r.id,
            "group_id": r.group_id,
            "name": r.name,
            "enabled": r.enabled,
            "priority": r.priority,
            "condition_type": r.condition_type.value,
            "condition_value": r.condition_value,
            "created_at": r.created_at.isoformat(),
            "updated_at": r.updated_at.isoformat(),
        }

    def _deserialize_rule(self, d: dict[str, Any]) -> Rule:
        return Rule(
            id=d["id"],
            group_id=d.get("group_id", ""),
            name=d.get("name", ""),
            enabled=d.get("enabled", True),
            priority=d.get("priority", 0),
            condition_type=ConditionType(d.get("condition_type", "extension")),
            condition_value=d.get("condition_value", ""),
            created_at=datetime.fromisoformat(d["created_at"]) if "created_at" in d else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(d["updated_at"]) if "updated_at" in d else datetime.now(timezone.utc),
        )

    def _deserialize_group(self, d: dict[str, Any]) -> RuleGroup:
        return RuleGroup(
            id=d["id"],
            name=d.get("name", ""),
            description=d.get("description", ""),
            priority=d.get("priority", 0),
            is_default=d.get("is_default", False),
            created_at=datetime.fromisoformat(d["created_at"]) if "created_at" in d else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(d["updated_at"]) if "updated_at" in d else datetime.now(timezone.utc),
        )

    def _deserialize_action(self, d: dict[str, Any]) -> RuleAction:
        return RuleAction(
            id=d["id"],
            rule_id=d.get("rule_id", ""),
            action_type=ActionType(d["action_type"]),
            target_folder=d.get("target_folder", ""),
            copy_enabled=d.get("copy_enabled", False),
            rename_pattern=d.get("rename_pattern", ""),
            created_at=datetime.fromisoformat(d["created_at"]) if "created_at" in d else datetime.now(timezone.utc),
        )

    @staticmethod
    def _serialize_undo(entry: UndoEntry) -> dict[str, Any]:
        return {
            "id": entry.id,
            "file_name": entry.file_name,
            "source_path": str(entry.source_path),
            "destination_path": str(entry.destination_path),
            "action_type": entry.action_type.value,
            "rule_name": entry.rule_name,
            "timestamp": entry.timestamp.isoformat(),
            "reverted": entry.reverted,
        }

    @staticmethod
    def _deserialize_undo(d: dict[str, Any]) -> UndoEntry:
        return UndoEntry(
            id=d["id"],
            file_name=d.get("file_name", ""),
            source_path=Path(d.get("source_path", "")),
            destination_path=Path(d.get("destination_path", "")),
            action_type=ActionType(d.get("action_type", ActionType.MOVE.value)),
            rule_name=d.get("rule_name", ""),
            timestamp=datetime.fromisoformat(d["timestamp"]) if "timestamp" in d else datetime.now(timezone.utc),
            reverted=d.get("reverted", False),
        )
