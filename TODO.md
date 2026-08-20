# TODO — Zorma v2.1

## Estado general

- [x] **Fase 1: Modelos** — Completado
- [x] **Fase 2: Servicios** — Completado
- [x] **Fase 3: UI + Tests** — Completado
- [x] **Migración de datos** — Completado (schema v4 → v5)
- [x] **Infraestructura** — Completado (`__init__.py`, `.pyc`, `.gitignore`)
- [x] **Bugs críticos** — Corregidos
- [x] **Dead code** — Eliminado

---

## Completado (historial)

### Fase 1: Modelos

- [x] `core/models/enums.py` — 7 enumeraciones
- [x] 11 modelos de dominio creados + `filter_config.py`

### Fase 2: Servicios

- [x] `servicio_clasificacion.py` — renombrado desde `WatcherService`
- [x] `gestor_deshacer.py` — renombrado desde `UndoManager`
- [x] Lógica migrada a modelos: `Regla.evaluar()`, `AccionRegla.ejecutar()`, `PilaDeshacer`
- [x] 3 adaptadores migrados a modelos españoles
- [x] 7 archivos viejos eliminados

### Fase 3: UI + Tests

- [x] 11 archivos UI migrados
- [x] 11 archivos test migrados

### Schema v5

- [x] `SCHEMA_VERSION = 5`, migración real v4→v5
- [x] Serialización de `id_registro`, `estado_serializado`, `aplicada`, `sobrescribir`

### Infraestructura

- [x] 8 `__init__.py` creados
- [x] `.pyc` limpiados, `.gitignore` verificado

### Bugs corregidos

- [x] `rules_view.py` — `rule.name` → `rule.nombre`
- [x] `dashboard_viewmodel.py` — `preview_all()` → `previsualizar_todos()`
- [x] `dashboard_viewmodel.py` — `classify()` → `clasificar()`
- [x] `history_view.py` — ahora lee de `ZormaRepository.get_history()` en vez de `history.jsonl`
- [x] `widgets.py` — signal `rules_requested` conectado via `DashboardView.navigate_requested`

### Dead code eliminado

- [x] `core/models/registro_movimiento.py` — nunca se usaba
- [x] `config/settings.py` — 5 constantes muertas (`APP_VERSION`, `AUTHOR`, `DEFAULT_OUTPUT_DIR`, `WATCHDOG_TIMEOUT`, `SCAN_TIMEOUT`, `LOGO_DIR`)
- [x] `pyproject.toml` — mypy override stale `zorma.ui.files.files_view`

### Tests

- [x] 156/162 pasan (6 fallos preexistentes en watchdog/watcher)

---

## Refactor SOLID (8 fases)

- [ ] **Fase 1**: Protocols en `core/ports.py` — `FileRepository`, `UndoRedoStore`, `HistoryStore`, `FileWatcher`
- [ ] **Fase 2**: Adapters implementan Protocols, core services cambian type hints (DIP)
- [ ] **Fase 3**: Evaluadores de Regla en `core/evaluators.py` (1 archivo, dict, OCP)
- [ ] **Fase 4**: Acciones en `core/actions.py` (1 archivo, dict, OCP)
- [ ] **Fase 5**: Extraer `ClassificationEngine` de `ServicioClasificacion` (SRP)
- [ ] **Fase 6**: `GestorDeshacer` usa `UndoRedoStore` (DIP)
- [ ] **Fase 7**: Partir `DashboardViewModel` → `AppSettingsManager` + `WorkersManager` + VM slim (SRP)
- [ ] **Fase 8**: Tests con mocks + cleanup CI (ruff, mypy, pytest)
