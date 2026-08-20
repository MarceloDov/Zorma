from __future__ import annotations

import json
import logging
import os
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

from ...core.models.accion_regla import AccionRegla
from ...core.models.enums import EstadoClasificacion, TipoAccion, TipoCondicion
from ...core.models.grupo_regla import GrupoRegla
from ...core.models.pila_deshacer import PilaDeshacer
from ...core.models.regla import Regla
from ...core.models.resultado_clasificacion import ResultadoClasificacion

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 5

T = TypeVar("T")


class ZormaRepository:
    def __init__(self, data_dir: Path, undo_limit: int = 1000) -> None:
        self._file = data_dir / "zorma.json"
        self._undo_limit = undo_limit
        self._data: dict[str, Any] = {}
        self._cargar()

    # ── persistence ──

    def _datos_predeterminados(self) -> dict[str, Any]:
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

    def _cargar(self) -> None:
        if not self._file.exists():
            self._data = self._datos_predeterminados()
            return
        try:
            raw = json.loads(self._file.read_text(encoding="utf-8"))
            self._data = {**self._datos_predeterminados(), **raw}
        except (json.JSONDecodeError, OSError):
            logger.exception("Failed to load %s, using defaults", self._file)
            self._data = self._datos_predeterminados()

    def _guardar(self) -> None:
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
    def _ahora() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _deserializar_todo(entries: list[dict[str, Any]], deserialize: Callable[[dict[str, Any]], T]) -> list[T]:
        result = []
        for entry in entries:
            try:
                result.append(deserialize(entry))
            except (KeyError, ValueError) as e:
                logger.warning("Malformed entry skipped: %s", e)
        return result

    # ── rules ──

    def obtener_todas_las_reglas(self) -> list[Regla]:
        return self._deserializar_todo(self._data["rules"], self._deserializar_regla)

    def obtener_regla_por_id(self, rule_id: str) -> Regla | None:
        for r in self._data["rules"]:
            if r["id"] == rule_id:
                try:
                    return self._deserializar_regla(r)
                except (KeyError, ValueError) as e:
                    logger.warning("Malformed rule %s: %s", rule_id, e)
                    return None
        return None

    def obtener_reglas_por_grupo(self, group_id: str) -> list[Regla]:
        rules = [r for r in self._data["rules"] if r.get("group_id") == group_id]
        return self._deserializar_todo(rules, self._deserializar_regla)

    def guardar_regla(self, rule: Regla) -> None:
        data = self._serializar_regla(rule)
        for i, r in enumerate(self._data["rules"]):
            if r["id"] == rule.id:
                self._data["rules"][i] = data
                break
        else:
            self._data["rules"].append(data)
        self._guardar()

    def eliminar_regla(self, rule_id: str) -> None:
        self._data["rules"] = [r for r in self._data["rules"] if r["id"] != rule_id]
        self._data["actions"] = [a for a in self._data["actions"] if a.get("rule_id") != rule_id]
        logger.debug("Deleted rule %s", rule_id)
        self._guardar()

    # ── groups ──

    def obtener_grupos(self) -> list[GrupoRegla]:
        return self._deserializar_todo(self._data["groups"], self._deserializar_grupo)

    def guardar_grupo(self, group: GrupoRegla) -> None:
        data = {
            "id": group.id,
            "name": group.nombre,
            "description": group.descripcion,
            "priority": group.prioridad,
            "is_default": group.es_predeterminado,
            "created_at": group.creado_en.isoformat() if isinstance(group.creado_en, datetime) else group.creado_en,
            "updated_at": self._ahora(),
        }
        for i, g in enumerate(self._data["groups"]):
            if g["id"] == group.id:
                self._data["groups"][i] = data
                break
        else:
            self._data["groups"].append(data)
        self._guardar()

    def eliminar_grupo(self, group_id: str) -> None:
        rule_ids = {r["id"] for r in self._data["rules"] if r.get("group_id") == group_id}
        self._data["groups"] = [g for g in self._data["groups"] if g["id"] != group_id]
        self._data["rules"] = [r for r in self._data["rules"] if r["id"] not in rule_ids]
        self._data["actions"] = [a for a in self._data["actions"] if a.get("rule_id") not in rule_ids]
        logger.debug("Deleted group %s", group_id)
        self._guardar()

    # ── actions ──

    def obtener_acciones_de_regla(self, rule_id: str) -> list[AccionRegla]:
        actions = [a for a in self._data["actions"] if a.get("rule_id") == rule_id]
        return self._deserializar_todo(actions, self._deserializar_accion)

    def guardar_accion(self, action: AccionRegla) -> None:
        data = {
            "id": action.id,
            "rule_id": action.id_regla,
            "action_type": action.tipo_accion.value,
            "target_folder": action.carpeta_destino,
            "rename_pattern": action.patron_renombre,
            "created_at": action.creado_en.isoformat() if isinstance(action.creado_en, datetime) else action.creado_en,
        }
        for i, a in enumerate(self._data["actions"]):
            if a["id"] == action.id:
                self._data["actions"][i] = data
                break
        else:
            self._data["actions"].append(data)
        self._guardar()

    def crear_reglas_predeterminadas(self) -> None:
        group = GrupoRegla(
            nombre="Clasificación Universal Automática",
            descripcion="Agrupa cualquier archivo seguro según su extensión",
            prioridad=1,
            es_predeterminado=True,
        )
        self.guardar_grupo(group)
        rule = Regla(
            id_grupo=group.id,
            nombre="Todas las extensiones",
            tipo_condicion=TipoCondicion.EXTENSION,
            valor_condicion="*",
        )
        self.guardar_regla(rule)
        action = AccionRegla(id_regla=rule.id, carpeta_destino="Archivos {ext}")
        self.guardar_accion(action)

    # ── undo / redo ──

    def _apilar_en_pila(self, stack_key: str, entry: PilaDeshacer) -> None:
        data = self._serializar_deshacer(entry)
        self._data[stack_key].append(data)
        if len(self._data[stack_key]) > self._undo_limit:
            self._data[stack_key].pop(0)
        logger.debug("Pushed to %s: %s", stack_key, entry.id)
        self._guardar()

    def _desapilar_de_pila(self, stack_key: str) -> PilaDeshacer | None:
        if not self._data[stack_key]:
            return None
        entry = self._deserializar_deshacer(self._data[stack_key].pop())
        logger.debug("Popped from %s: %s", stack_key, entry.id)
        self._guardar()
        return entry

    def _limpiar_pila(self, stack_key: str) -> None:
        self._data[stack_key].clear()
        self._guardar()

    def apilar_deshacer(self, entry: PilaDeshacer) -> None:
        self._apilar_en_pila("undo", entry)

    def desapilar_deshacer(self) -> PilaDeshacer | None:
        return self._desapilar_de_pila("undo")

    def ver_tope_deshacer(self) -> PilaDeshacer | None:
        return self._deserializar_deshacer(self._data["undo"][-1]) if self._data["undo"] else None

    def tamanio_deshacer(self) -> int:
        return len(self._data["undo"])

    def limpiar_deshacer(self) -> None:
        self._limpiar_pila("undo")

    def obtener_todo_deshacer(self) -> list[PilaDeshacer]:
        return [self._deserializar_deshacer(e) for e in reversed(self._data["undo"])]

    def marcar_deshacer_revertido(self, entry_id: str) -> None:
        for e in self._data["undo"]:
            if e["id"] == entry_id:
                e["reverted"] = True
                self._guardar()
                return

    def eliminar_deshacer_por_id(self, entry_id: str) -> PilaDeshacer | None:
        for i, e in enumerate(self._data["undo"]):
            if e["id"] == entry_id:
                removed = self._data["undo"].pop(i)
                self._guardar()
                return self._deserializar_deshacer(removed)
        return None

    def apilar_rehacer(self, entry: PilaDeshacer) -> None:
        self._apilar_en_pila("redo", entry)

    def desapilar_rehacer(self) -> PilaDeshacer | None:
        return self._desapilar_de_pila("redo")

    def limpiar_rehacer(self) -> None:
        self._limpiar_pila("redo")

    def tamanio_rehacer(self) -> int:
        return len(self._data["redo"])

    # ── history ──

    HISTORY_LIMIT = 10_000

    def agregar_historial(self, result: ResultadoClasificacion) -> None:
        self._data["history"].append(
            {
                "file_name": result.nombre_archivo,
                "source_path": str(result.ruta_origen) if result.ruta_origen else None,
                "destination_path": str(result.ruta_destino) if result.ruta_destino else None,
                "rule_name": result.regla_aplicada.nombre if result.regla_aplicada else None,
                "action_applied": result.accion_aplicada.tipo_accion.value if result.accion_aplicada else None,
                "status": result.estado.value,
                "error_message": result.mensaje_error,
                "timestamp": result.marca_tiempo.isoformat(),
                "applied": result.aplicada,
                "overwrite": result.sobrescribir,
            }
        )
        if len(self._data["history"]) > self.HISTORY_LIMIT:
            self._data["history"] = self._data["history"][-self.HISTORY_LIMIT :]
        self._guardar()

    def obtener_historial(self) -> list[ResultadoClasificacion]:
        results = []
        for entry in self._data["history"]:
            try:
                results.append(
                    ResultadoClasificacion(
                        nombre_archivo=entry.get("file_name", ""),
                        ruta_origen=Path(entry["source_path"]) if entry.get("source_path") else None,
                        ruta_destino=Path(entry["destination_path"]) if entry.get("destination_path") else None,
                        estado=EstadoClasificacion(entry["status"]),
                        mensaje_error=entry.get("error_message", ""),
                        marca_tiempo=datetime.fromisoformat(entry["timestamp"]),
                        aplicada=entry.get("applied", False),
                        sobrescribir=entry.get("overwrite", False),
                    )
                )
            except (KeyError, ValueError) as e:
                logger.warning("Malformed history entry: %s", e)
                continue
        return results

    # ── theme / config ──

    def obtener_tema(self) -> str:
        return str(self._data.get("theme", "dark"))

    def establecer_tema(self, theme: str) -> None:
        self._data["theme"] = theme
        self._guardar()

    # ── serialization ──

    def _serializar_regla(self, r: Regla) -> dict[str, Any]:
        return {
            "id": r.id,
            "group_id": r.id_grupo,
            "name": r.nombre,
            "enabled": r.habilitada,
            "priority": r.prioridad,
            "condition_type": r.tipo_condicion.value,
            "condition_value": r.valor_condicion,
            "created_at": r.creado_en.isoformat(),
        }

    def _deserializar_regla(self, d: dict[str, Any]) -> Regla:
        return Regla(
            id=d["id"],
            id_grupo=d.get("group_id", ""),
            nombre=d.get("name", ""),
            habilitada=d.get("enabled", True),
            prioridad=d.get("priority", 0),
            tipo_condicion=TipoCondicion(d.get("condition_type", "extension")),
            valor_condicion=d.get("condition_value", ""),
            creado_en=datetime.fromisoformat(d["created_at"]) if "created_at" in d else datetime.now(UTC),
        )

    def _deserializar_grupo(self, d: dict[str, Any]) -> GrupoRegla:
        return GrupoRegla(
            id=d["id"],
            nombre=d.get("name", ""),
            descripcion=d.get("description", ""),
            prioridad=d.get("priority", 0),
            es_predeterminado=d.get("is_default", False),
            creado_en=datetime.fromisoformat(d["created_at"]) if "created_at" in d else datetime.now(UTC),
        )

    def _deserializar_accion(self, d: dict[str, Any]) -> AccionRegla:
        return AccionRegla(
            id=d["id"],
            id_regla=d.get("rule_id", ""),
            tipo_accion=TipoAccion(d["action_type"]),
            carpeta_destino=d.get("target_folder", ""),
            patron_renombre=d.get("rename_pattern", ""),
            creado_en=datetime.fromisoformat(d["created_at"]) if "created_at" in d else datetime.now(UTC),
        )

    @staticmethod
    def _serializar_deshacer(entry: PilaDeshacer) -> dict[str, Any]:
        return {
            "id": entry.id,
            "source_path": str(entry._ruta_origen),
            "destination_path": str(entry._ruta_destino),
            "action_type": entry.tipo_operacion.value,
            "timestamp": entry.marca_tiempo.isoformat(),
            "reverted": entry.revertido,
        }

    @staticmethod
    def _deserializar_deshacer(d: dict[str, Any]) -> PilaDeshacer:
        entry = PilaDeshacer(
            id=d["id"],
            tipo_operacion=TipoAccion(d.get("action_type", TipoAccion.MOVER.value)),
            marca_tiempo=datetime.fromisoformat(d["timestamp"]) if "timestamp" in d else datetime.now(UTC),
            revertido=d.get("reverted", False),
        )
        entry._ruta_origen = Path(d.get("source_path", "."))
        entry._ruta_destino = Path(d.get("destination_path", "."))
        return entry
