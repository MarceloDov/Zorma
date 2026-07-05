from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from ...core.models.rule import ActionType, ConditionType, Rule, RuleAction, RuleGroup
from ...core.ports.rule_repository import RuleRepository

logger = logging.getLogger(__name__)


SCHEMA_VERSION = 4


class JsonRuleRepository(RuleRepository):
    """
    Repositorio de reglas que persiste la información en archivos JSON.
    """
    def __init__(self, data_dir: Path) -> None:
        """
        Inicializa el repositorio con el directorio de datos proporcionado.

        :param data_dir: Directorio donde se almacenan los archivos de reglas.
        """
        self._data_dir = data_dir
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._meta_file = data_dir / "meta.json"
        self._rules_file = data_dir / "rules.json"
        self._groups_file = data_dir / "rule_groups.json"
        self._actions_file = data_dir / "rule_actions.json"
        self._rules: dict[str, dict[str, Any]] = {}
        self._groups: dict[str, dict[str, Any]] = {}
        self._actions: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        """
        Carga las reglas, grupos y acciones desde los archivos JSON.
        """
        current_version = 0
        if self._meta_file.exists():
            try:
                meta = json.loads(self._meta_file.read_text())
                current_version = meta.get("schema_version", 0)
            except (json.JSONDecodeError, KeyError):
                pass

        if current_version < SCHEMA_VERSION:
            logger.info("Schema v%d < v%d — migrating rules", current_version, SCHEMA_VERSION)
            # Perform actual migration here if needed
            self._meta_file.write_text(json.dumps({"schema_version": SCHEMA_VERSION}))

        for fname, store in [
            (self._rules_file, self._rules),
            (self._groups_file, self._groups),
            (self._actions_file, self._actions),
        ]:
            if fname.exists():
                try:
                    data = json.loads(fname.read_text())
                    store.update({item["id"]: item for item in data})
                except (json.JSONDecodeError, KeyError):
                    store.clear()

    def _save(self, fname: Path, store: dict[str, dict[str, Any]]) -> None:
        """
        Guarda los datos del almacén especificado en un archivo JSON.

        :param fname: Ruta del archivo donde guardar.
        :param store: Diccionario con los datos a guardar.
        """
        fname.write_text(json.dumps(list(store.values()), indent=2, default=str))

    def _serialize_rule(self, r: Rule) -> dict[str, Any]:
        """
        Serializa un objeto Rule a un diccionario.

        :param r: Regla a serializar.
        :return: Diccionario con los datos de la regla.
        """
        return {
            "id": r.id,
            "group_id": r.group_id,
            "name": r.name,
            "enabled": r.enabled,
            "condition_type": r.condition_type.value,
            "condition_value": r.condition_value,
            "created_at": r.created_at.isoformat(),
            "updated_at": r.updated_at.isoformat(),
        }

    def _deserialize_rule(self, d: dict[str, Any]) -> Rule:
        """
        Deserializa un diccionario a un objeto Rule.

        :param d: Diccionario con los datos de la regla.
        :return: Objeto Rule deserializado.
        """
        return Rule(
            id=d["id"],
            group_id=d.get("group_id", ""),
            name=d.get("name", ""),
            enabled=d.get("enabled", True),
            condition_type=ConditionType(d.get("condition_type", "extension")),
            condition_value=d.get("condition_value", ""),
            created_at=datetime.fromisoformat(d["created_at"]) if "created_at" in d else datetime.now(),
            updated_at=datetime.fromisoformat(d["updated_at"]) if "updated_at" in d else datetime.now(),
        )

    def get_all(self) -> list[Rule]:
        """
        Obtiene todas las reglas almacenadas.

        :return: Lista de objetos Rule.
        """
        return [self._deserialize_rule(d) for d in self._rules.values()]

    def get_by_id(self, rule_id: str) -> Rule | None:
        """
        Obtiene una regla por su ID.

        :param rule_id: ID de la regla.
        :return: Objeto Rule o None si no existe.
        """
        d = self._rules.get(rule_id)
        return self._deserialize_rule(d) if d else None

    def get_by_group(self, group_id: str) -> list[Rule]:
        """
        Obtiene todas las reglas asociadas a un grupo.

        :param group_id: ID del grupo.
        :return: Lista de objetos Rule.
        """
        return [self._deserialize_rule(d) for d in self._rules.values() if d.get("group_id") == group_id]

    def save(self, rule: Rule) -> None:
        """
        Guarda o actualiza una regla.

        :param rule: Objeto Rule a guardar.
        """
        self._rules[rule.id] = self._serialize_rule(rule)
        self._save(self._rules_file, self._rules)

    def delete(self, rule_id: str) -> None:
        """
        Elimina una regla por su ID.

        :param rule_id: ID de la regla a eliminar.
        """
        self._rules.pop(rule_id, None)
        self._save(self._rules_file, self._rules)

    def get_groups(self) -> list[RuleGroup]:
        """
        Obtiene todos los grupos de reglas.

        :return: Lista de objetos RuleGroup.
        """
        return [self._deserialize_group(d) for d in self._groups.values()]

    def save_group(self, group: RuleGroup) -> None:
        """
        Guarda o actualiza un grupo de reglas.

        :param group: Objeto RuleGroup a guardar.
        """
        self._groups[group.id] = {
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "priority": group.priority,
            "is_default": group.is_default,
            "created_at": group.created_at.isoformat(),
            "updated_at": group.updated_at.isoformat(),
        }
        self._save(self._groups_file, self._groups)

    def _deserialize_group(self, d: dict[str, Any]) -> RuleGroup:
        """
        Deserializa un diccionario a un objeto RuleGroup.

        :param d: Diccionario con los datos del grupo.
        :return: Objeto RuleGroup deserializado.
        """
        return RuleGroup(
            id=d["id"],
            name=d.get("name", ""),
            description=d.get("description", ""),
            priority=d.get("priority", 0),
            is_default=d.get("is_default", False),
            created_at=datetime.fromisoformat(d["created_at"]) if "created_at" in d else datetime.now(),
            updated_at=datetime.fromisoformat(d["updated_at"]) if "updated_at" in d else datetime.now(),
        )

    def get_actions_for_rule(self, rule_id: str) -> list[RuleAction]:
        """
        Obtiene todas las acciones asociadas a una regla.

        :param rule_id: ID de la regla.
        :return: Lista de objetos RuleAction.
        """
        return [self._deserialize_action(d) for d in self._actions.values() if d.get("rule_id") == rule_id]

    def save_action(self, action: RuleAction) -> None:
        """
        Guarda o actualiza una acción.

        :param action: Objeto RuleAction a guardar.
        """
        self._actions[action.id] = {
            "id": action.id,
            "rule_id": action.rule_id,
            "action_type": action.action_type.value,
            "target_folder": action.target_folder,
            "copy_enabled": action.copy_enabled,
            "rename_pattern": action.rename_pattern,
            "created_at": action.created_at.isoformat(),
        }
        self._save(self._actions_file, self._actions)

    def _deserialize_action(self, d: dict[str, Any]) -> RuleAction:
        """
        Deserializa un diccionario a un objeto RuleAction.

        :param d: Diccionario con los datos de la acción.
        :return: Objeto RuleAction deserializado.
        """
        return RuleAction(
            id=d["id"],
            rule_id=d.get("rule_id", ""),
            action_type=ActionType(d["action_type"]),
            target_folder=d.get("target_folder", ""),
            copy_enabled=d.get("copy_enabled", False),
            rename_pattern=d.get("rename_pattern", ""),
            created_at=datetime.fromisoformat(d["created_at"]) if "created_at" in d else datetime.now(),
        )

    def create_default_rules(self) -> None:
        """
        Crea un conjunto de reglas por defecto.
        """
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
        self.save(rule)

        action = RuleAction(
            rule_id=rule.id,
            target_folder="Archivos {ext}",
        )
        self.save_action(action)

    def delete_group(self, group_id: str) -> None:
        """
        Elimina un grupo de reglas y todas sus reglas y acciones asociadas.

        :param group_id: ID del grupo a eliminar.
        """
        rules_in_group = self.get_by_group(group_id)
        for rule in rules_in_group:
            actions = self.get_actions_for_rule(rule.id)
            for action in actions:
                self._actions.pop(action.id, None)
            self._rules.pop(rule.id, None)
        self._groups.pop(group_id, None)
        self._save(self._rules_file, self._rules)
        self._save(self._actions_file, self._actions)
        self._save(self._groups_file, self._groups)

