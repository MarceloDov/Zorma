# Plan de refactor SOLID — 8 fases

Basado en `docs/registro.md`. Versión ponytail: mínima abstracción, máxima simplificación.

---

## Fase 1: Definir puertos (Protocols) en `core/ports.py`

Crear `src/zorma/core/ports.py` con 4 Protocols estructurales (sin `@runtime_checkable`):

```python
from typing import Protocol
from pathlib import Path

class FileRepository(Protocol):
    def get_all_rules(self) -> list[Regla]: ...
    def get_rule_by_id(self, rule_id: str) -> Regla | None: ...
    def get_rules_by_group(self, group_id: str) -> list[Regla]: ...
    def save_rule(self, rule: Regla) -> None: ...
    def delete_rule(self, rule_id: str) -> None: ...
    def get_actions_for_rule(self, rule_id: str) -> list[AccionRegla]: ...
    def save_action(self, action: AccionRegla) -> None: ...
    def get_groups(self) -> list[GrupoRegla]: ...
    def save_group(self, group: GrupoRegla) -> None: ...
    def delete_group(self, group_id: str) -> None: ...

class UndoRedoStore(Protocol):
    def undo_push(self, entry: PilaDeshacer) -> None: ...
    def undo_pop(self) -> PilaDeshacer | None: ...
    def undo_peek(self) -> PilaDeshacer | None: ...
    def undo_size(self) -> int: ...
    def undo_clear(self) -> None: ...
    def undo_get_all(self) -> list[PilaDeshacer]: ...
    def undo_mark_reverted(self, entry_id: str) -> None: ...
    def undo_remove_by_id(self, entry_id: str) -> PilaDeshacer | None: ...
    def redo_push(self, entry: PilaDeshacer) -> None: ...
    def redo_pop(self) -> PilaDeshacer | None: ...
    def redo_clear(self) -> None: ...
    def redo_size(self) -> int: ...

class HistoryStore(Protocol):
    def add_history(self, result: ResultadoClasificacion) -> None: ...
    def get_history(self) -> list[ResultadoClasificacion]: ...

class FileWatcher(Protocol):
    def start(self, paths: list[Path], callback, excluded_patterns=None) -> None: ...
    def stop(self) -> None: ...
    def is_alive(self) -> bool: ...
    def update_filter(self, filter_config) -> None: ...
```

Solo la capa de abstracción. No se tocan implementaciones aún.

---

## Fase 2: Hacer que adapters implementen Protocols (DIP)

### Type annotations — `core/services/servicio_clasificacion.py`

```diff
- from ...adapters.persistence.zorma_repository import ZormaRepository
- from ...adapters.watcher.watchdog_watcher import WatchdogFileWatcher
+ from ..ports import FileRepository, HistoryStore, FileWatcher

  class ServicioClasificacion:
      def __init__(
          self,
-         watcher: WatchdogFileWatcher,
-         repo: ZormaRepository,
-         history: ZormaRepository,
+         watcher: FileWatcher,
+         repo: FileRepository,
+         history: HistoryStore,
      ) -> None:
```

### Type annotations — `core/services/gestor_deshacer.py`

```diff
- from ...adapters.persistence.zorma_repository import ZormaRepository
+ from ..ports import UndoRedoStore

  class GestorDeshacer:
-     def __init__(self, repo: ZormaRepository) -> None:
+     def __init__(self, store: UndoRedoStore) -> None:
```

### Runtime — `__main__.py`

Sigue igual (inyecta las mismas clases concretas). Los Protocols son estructurales, no hay que registrar nada. `duck-typing` funciona porque `ZormaRepository` tiene todos los métodos que `FileRepository`/`UndoRedoStore`/`HistoryStore` piden.

### Adaptadores existentes

- `ZormaRepository` ya implementa `FileRepository` + `UndoRedoStore` + `HistoryStore` (solo cambiar type hints)
- `WatchdogFileWatcher` ya implementa `FileWatcher`
- `PyQtNotificationAdapter` no se toca (nada en `core/` lo usa)

---

## Fase 3: Evaluadores en `core/evaluators.py` (OCP)

Un solo archivo, no un paquete:

```python
# core/evaluators.py
_EVALUATORS: dict[TipoCondicion, Callable[[Path, str], bool]] = {
    TipoCondicion.EXTENSION: _eval_extension,
    TipoCondicion.TAMANIO: _eval_size,
    TipoCondicion.FECHA: _eval_date,
    TipoCondicion.NOMBRE: _eval_name,
}

def evaluate(condition: TipoCondicion, file_path: Path, value: str) -> bool:
    fn = _EVALUATORS.get(condition)
    if fn is None:
        return False
    return fn(file_path, value)
```

Las 4 funciones `_eval_*` se copian de `Regla` a `evaluators.py` tal cual (sin cambios de lógica).

```diff
# core/models/regla.py
- def evaluar(self, archivo: Archivo) -> bool:
-     if not self.habilitada:
-         return False
-     try:
-         evaluadores = {
-             TipoCondicion.EXTENSION: self._eval_extension,
-             TipoCondicion.TAMANIO: self._eval_size,
-             TipoCondicion.FECHA: self._eval_date,
-             TipoCondicion.NOMBRE: self._eval_name,
-         }
-         fn = evaluadores.get(self.tipo_condicion)
-         if fn is None:
-             return False
-         return fn(archivo._ruta_completa)
-     except (OSError, ValueError, TypeError) as e:
-         ...
+ def evaluar(self, archivo: Archivo) -> bool:
+     if not self.habilitada:
+         return False
+     return evaluate(self.tipo_condicion, archivo._ruta_completa, self.valor_condicion)
```

- `Regla` pierde los 4 métodos `_eval_extension`, `_eval_size`, `_eval_date`, `_eval_name`
- Nuevo `TipoCondicion` = agregar función al dict `_EVALUATORS`, sin tocar `Regla`

---

## Fase 4: Acciones en `core/actions.py` (OCP)

Un solo archivo:

```python
# core/actions.py
ActionFn = Callable[[AccionRegla, Archivo, bool], ResultadoClasificacion]

_ACTIONS: dict[TipoAccion, ActionFn] = {
    TipoAccion.MOVER: _exec_move,
    TipoAccion.COPIAR: _exec_copy,
    TipoAccion.RENOMBRAR: _exec_rename,
}

def execute(action: AccionRegla, archivo: Archivo, overwrite: bool = False) -> ResultadoClasificacion: ...
def check_conflict(action: AccionRegla, archivo: Archivo) -> bool: ...
def resolve_destination(action: AccionRegla, file: Path) -> Path: ...
```

- `AccionRegla.ejecutar()` → `actions.execute(self, archivo, overwrite)`
- `AccionRegla.verificar_conflicto()` → `actions.check_conflict(self, archivo)`
- Las funciones `_resolver_destino`, `_construir_ruta_destino`, `_aplicar_patron_renombre` se copian a `actions.py`
- `AccionRegla` queda como dataclass puro + métodos delgados que delegan
- Nuevo `TipoAccion` = agregar función al dict, sin tocar `AccionRegla`

---

## Fase 5: Extraer `ClassificationEngine` de `ServicioClasificacion` (SRP)

```python
# core/services/classification_engine.py
class ClassificationEngine:
    def __init__(self, repo: FileRepository) -> None: ...
    def find_action(self, file_path: Path) -> tuple[Regla, AccionRegla] | None: ...
    def classify(self, file_path: Path, overwrite: bool) -> ResultadoClasificacion: ...
    def preview(self, file_path: Path) -> ResultadoClasificacion: ...
```

`_find_action`, `_clasificar`, `previsualizar` se mueven de `ServicioClasificacion` a `ClassificationEngine`.

`_iter_files` se queda como función suelta en `servicio_clasificacion.py` (12 líneas, no merece clase).

```diff
# ServicioClasificacion (simplificado)
  class ServicioClasificacion:
      def __init__(
          self,
          watcher: FileWatcher,
          repo: FileRepository,
          history: HistoryStore,
+         engine: ClassificationEngine | None = None,
      ) -> None:
          self._watcher = watcher
          self._repo = repo
          self._history = history
+         self._engine = engine or ClassificationEngine(repo)
          ...
```

`ServicioClasificacion` se enfoca en orquestación: start/stop monitoring, event callbacks, history.

---

## Fase 6: `GestorDeshacer` usa `UndoRedoStore` (DIP)

```diff
  class GestorDeshacer:
-     def __init__(self, repo: ZormaRepository) -> None:
-         self._repo = repo
+     def __init__(self, store: UndoRedoStore) -> None:
+         self._store = store
```

- Todos los usos de `self._repo.undo_push(...)` → `self._store.undo_push(...)`
- Todos los usos de `self._repo.redo_push(...)` → `self._store.redo_push(...)`
- Sin import a `ZormaRepository`

---

## Fase 7: Partir `DashboardViewModel` en 3 clases (SRP)

### 7a. `AppSettingsManager` — solo I/O de `app_config.json`

```python
# ui/shared/app_settings.py
class AppSettingsManager:
    def __init__(self, data_dir: Path) -> None:
        self._file = data_dir / "app_config.json"

    def load(self) -> dict:
        if not self._file.exists():
            return {}
        try:
            return json.loads(self._file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def save(self, config: dict) -> None:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        self._file.write_text(json.dumps(config, indent=2, default=str), encoding="utf-8")
```

Sin Qt, sin señales. Pura lectura/escritura JSON.

### 7b. `WorkersManager` — workers + watcher

```python
# ui/dashboard/workers_manager.py

# ScanWorker y ClassifyWorker dejan de ser clases anidadas,
# pasan a ser clases independientes en este mismo módulo.

class WorkersManager(QObject):
    classifying_changed = pyqtSignal(bool)
    progress_changed = pyqtSignal(int, int)
    status_text = pyqtSignal(str, str)
    scan_finished_for_preview = pyqtSignal(list)
    file_done = pyqtSignal(object)
    classify_finished = pyqtSignal(int, int)
    watcher_status = pyqtSignal(str, str)
    show_toast = pyqtSignal(str, str)

    def __init__(self, watcher_service: ServicioClasificacion, parent=None):
        super().__init__(parent)
        self._watcher_service = watcher_service
        self._scan_worker: ScanWorker | None = None
        self._classify_worker: ClassifyWorker | None = None
        self._watcher_running = False

    def run_scan(self, paths: list[Path]) -> None: ...
    def start_classify(self, results: list[ResultadoClasificacion]) -> None: ...
    def cancel(self) -> None: ...
    def start_watcher(self, paths: list[Path]) -> None: ...
    def stop_watcher(self) -> None: ...
    def load_history(self) -> list[ResultadoClasificacion]: ...
```

### 7c. `DashboardViewModel` — coordinación + estado UI

```python
class DashboardViewModel(QObject):
    # 11 señales públicas (la View no cambia su conexión)
    watch_path_changed = pyqtSignal(object)
    classifying_changed = pyqtSignal(bool)
    counters_changed = pyqtSignal(int, int)
    undo_redo_changed = pyqtSignal(bool, bool)
    onboarding_changed = pyqtSignal(bool)
    progress_changed = pyqtSignal(int, int)
    status_text = pyqtSignal(str, str)
    result_added = pyqtSignal(object)
    watcher_status = pyqtSignal(str, str)
    show_toast = pyqtSignal(str, str)
    scan_finished_for_preview = pyqtSignal(list)

    def __init__(self, data_dir: Path, repo, gestor_deshacer, parent=None):
        self._settings = AppSettingsManager(data_dir)
        self._workers: WorkersManager | None = None
        self._gestor_deshacer = gestor_deshacer
        self._watch_path: Path | None = None
        self._total_classified = 0
        self._total_errors = 0
        self._auto_classify = False
        self._load_settings()
        self._wire_workers_signals()
```

El VM conecta las señales de `WorkersManager` internamente y las re-emite como propias. La View sigue conectada solo al VM.

### Diagrama de flujo post-refactor

```
View ──conecta──► DashboardViewModel (11 señales)
                       │
                       ├──► AppSettingsManager (I/O puro, sin Qt)
                       │
                       ├──► WorkersManager (QObject, 8 señales)
                       │       ├── ScanWorker
                       │       └── ClassifyWorker
                       │
                       └──► GestorDeshacer
                               └── UndoRedoStore (Protocol)
```

---

## Fase 8: Tests + cleanup CI

### Tests nuevos

| Test | Qué prueba |
|------|------------|
| `test_classification_engine.py` | `ClassificationEngine` con un `FileRepository` mock |
| `test_app_settings.py` | `AppSettingsManager` load/save con archivo temporal |
| `test_workers_manager.py` | Workers con `ServicioClasificacion` mockeado |

### Tests existentes que deben seguir pasando

| Archivo | Clase | Notas |
|---------|-------|-------|
| `test_rule_evaluator.py` | `TestRuleEvaluator` | La lógica se movió a `evaluators.py` pero `Regla.evaluar()` delega — debe pasar igual |
| `test_action_executor.py` | `TestActionExecutor` | La lógica se movió a `actions.py` pero `AccionRegla.ejecutar()` delega |
| `test_gestor_deshacer.py` | `TestGestorDeshacer` | Cambió el constructor pero el comportamiento es el mismo |
| `test_json_rule_repository.py` | `TestZormaRepository` | Sin cambios |
| `test_watcher_service.py` | `TestWatcherService` | `ServicioClasificacion` recibe `ClassificationEngine` internamente |
| `test_dashboard_viewmodel.py` | `TestDashboardViewModel` | VM delega en `WorkersManager` y `AppSettingsManager` |
| `test_rules_viewmodel.py` | `TestRulesViewModel` | Sin cambios |

### CI

```bash
ruff check src/
mypy src/
pytest tests/ -v --tb=short
```

### Post-refactor

Actualizar `docs/registro.md` con el estado final post-refactor.
