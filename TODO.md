# TODO — Zorma

## ✅ Completado (verificado contra código actual)

### Bugs críticos arreglados
- [x] #1 Migración esquema — no hay `return` prematuro, cae a `load()`
- [x] #2 Windows multi-drive — usa `is_absolute()`, no `Path("/").resolve()`
- [x] #4 Observer restart — `Observer()` creado en `start()`, no en `__init__`
- [x] #5 Escritura atómica — `tempfile.mkstemp` + `os.replace` en ambos repos
- [x] #7 Historial persistido — `HistoryRepository` port + `history.jsonl`
- [x] #8 Settings persistidos — `_load_config()` / `_save_config()` en settings_view
- [x] #9 Sleep frágil — 0 llamadas a `time.sleep` en `src/`
- [x] #10 `{ext}` con punto — ambos métodos usan `file.suffix`
- [x] #11 `exclude_dirs` — usa `file_path.parent.parts`, no `file_path.parts`
- [x] #12 Undo COPY — usa `file.unlink()`, no `shutil.move`

### UX/UI implementados
- [x] #1.2 Feedback — barra indeterminada en scan, determinada en classify + label
- [x] #1.3 Conflictos — `PreviewDialog` con combo Sobrescribir/Omitir por fila
- [x] #1.5 Undo — confirmación `QMessageBox` + botón Redo + `redo_stack.json`
- [x] #7 Settings persistencia — `_load_settings()` / `_save_settings()` en dashboard_view

### Limpieza de código
- [x] Colores hardcodeados → tokens `COLORS` (`primary_pressed`, `card_disk`, settings_view, dashboard_view)
- [x] `rule_dialog.py` combos a español (Extensión, Tamaño, Fecha, Nombre, Mover, Copiar, Renombrar)

---

## 🔴 Críticos

- [x] #1.1 **OnboardingWidget bug** — `add_result()`/`clear()` movidas de `OnboardingWidget` a `TimelineFeed`. Dashboard ya llama correctamente `self._timeline.add_result()`
- [x] #3 **Thread safety** — `JsonHistoryRepository` ahora tiene `threading.RLock` en `add()` y `get_all()`
- [x] #6 **Excepción genérica** — ya captura `(OSError, ValueError, TypeError)` específicas + `logger.warning`. Safety net con `logger.exception` (no silencioso)
- [x] #10 **{ext} casing inconsistente** — `_apply_rename_pattern` ahora usa `file.suffix.lower()`, igual que `_build_dest_path`

---

## 🟡 UX / UI

- [x] #1.1b **Onboarding empty state** — bug del mismo #1.1 ya corregido: `add_result`/`clear` en `TimelineFeed`, `OnboardingWidget` intacto
- [x] #1.5b **Botón undo con contador** — `_update_undo_btn()` ahora muestra `"↩ Deshacer (N)"`
- [x] #2.2 **Light theme** — `_LIGHT_COLORS` (Catppuccin Latte), `set_theme()`, `build_qss()` dinámica. Toggle ☀/☾ en esquina superior derecha del content area. Persistencia en `app_config.json["theme"]`. Re-aplica QSS global al cambiar
- [x] #2.3 **Micro-animaciones** — fade opacity 150ms al navegar entre pestañas (`QGraphicsOpacityEffect` + `QPropertyAnimation`). Cards y sidebar tienen hover QSS con cambio de color/borde. Toast tiene entrada/salida animada
- [x] #3.3 **Toast apilable + cerrable** — `_active_toasts` class-level, offset Y por cantidad, botón ✕ para cerrar, `_reposition_all` al remover
- [x] #5.1 **Paginación historial** — carga en lotes de 100, botón "Cargar más… (N restantes)", oculta al final
- [x] #6.1 **Validación reglas** — valida formato `condition_value` (EXTENSION: lista no vacía, SIZE/DATE: regex, NAME: no vacío), carpeta destino obligatoria para MOVE/COPY, y patrón `rename_pattern` con `{name}`/`{ext}` para RENAME. Errores en `_error_label` múltiples líneas

### Tokens inconsistentes

- [x] #2.1a **history_view.py** — márgenes/fonts reemplazados con `SPACING`/`FONT_SIZES`
- [x] #2.1b **dashboard_view.py** — 3 `border-radius: 8px` → `BORDER_RADIUS['md']`
- [x] #2.1c **conflict_dialog.py** — `rgba(249, 226, 175, 0.1)` → `hex_to_rgba(COLORS['warning'], 0.1)`, `border-radius: 8px` → `BORDER_RADIUS['md']`. Nueva utilidad `hex_to_rgba()` en `styles.py`

### Idioma

- [x] #3.1 **Notificación de disco a español** — `"Espacio de disco bajo"` / `"Solo X GB restantes en la unidad Y"`

### Features faltantes

- [x] #1.6 **Accesibilidad** — `setAccessibleName` en: SidebarButton, Card, dashboard (folder/action/cancel/undo/redo), rules (add/delete), history (refresh/load-more), rule_dialog (name/condition/pattern/folder). ~20 controles con nombre accesible
- [x] #1.7 **Atajos de teclado** — `Ctrl+Z` (Undo), `Ctrl+Y` (Redo), `Ctrl+N` (Nueva Regla), `Ctrl+W` (Cerrar), `F5` (Refrescar Dashboard/Reglas), `Ctrl+1-4` (Navegación pestañas)
- [x] **Empty states enriquecidos** — nuevo widget `EmptyState` (icono + título + descripción + botón opcional) en `widgets.py`. TimelineFeed, HistoryView y RulesView lo usan con icono y CTA

---

## 🔵 Arquitectura / Deuda técnica

- [x] #14 **Prioridad de reglas** — campo `priority` en `Rule` (serializado/deserializado), `get_all()` ordenado por `priority` ascendente. Drag-to-reorder en tabla (`RulesTable` con `InternalMove`), `_on_rows_reordered` recalcula `rule.priority = row * 10` y persiste
- [x] #16 **Debounce** — `DebounceCallback` en `watchdog_watcher.py`: acumula eventos por `src_path` con `threading.Timer` (300ms), solo el último se entrega. Integrado en `WatchdogFileWatcher` con `flush_all()`
- [x] #21 **UI tests** — 54 tests nuevos (158 total): `test_ui_widgets.py` (20 tests: SidebarButton, Card, EmptyState, OnboardingWidget, TimelineRow, TimelineFeed), `test_ui_rules_view.py` (7 tests: RulesView table/empty/reorder), `test_rules_viewmodel.py` (14 tests: CRUD, reorder, signals), `test_dashboard_viewmodel.py` (13 tests: settings persistencia, watch path, estado). Requiere `pytest-qt>=4.0.0` + `QT_QPA_PLATFORM=offscreen` en CI
- [x] #22 **CI/CD** — `.github/workflows/ci.yml`: ubuntu-latest, Python 3.12/3.13, ruff check, mypy, pytest. PyQt6 system deps incluidos
- [x] #24 **ViewModels** — `DashboardViewModel` extrae estado/workers/settings/watcher/undo. `RulesViewModel` (nuevo `rules/rules_viewmodel.py`) extrae CRUD/reorder/deletion de reglas. `MainWindowViewModel` (nuevo `main_window_viewmodel.py`) extrae tema (load/toggle/persist). Vistas simplificadas: `DashboardView` 698→404, `RulesView` 299→224, `MainWindow` 440→415 líneas
- [x] #25 **Logging** — agregado a `ActionExecutor` (execute, rollback, check_conflict). `UndoManager` ya tenía logger.
- [x] #26 **Modelos en capa incorrecta** — `FilterConfig` movido a `core/models/filter_config.py`, `UndoEntry` movido a `core/models/undo_entry.py`. Imports actualizados en src/ y tests/
- [x] #27 **RuleRepository ISP** — `delete_action()` no agregado (YAGNI). Ningún caller lo necesita: `delete_rule`/`delete_group` ya cascade-deletean actions asociadas.
- [x] #28 **FileSystem abstraction** — RECHAZADO (YAGNI). `shutil` directo está bien, no necesita abstracción. Ver #37
- [x] #29 **Config muerta** — `BATCH_SIZE`/`BATCH_WINDOW` ya eliminados por #33. `create_default_rules()` es funcionalidad intencional (una regla default para UX out-of-box, no es config muerta).
- [x] #30 **Side-effects en modelos** — `FileEvent.size` eliminado (0 consumidores, I/O en property). `datetime.now()` → `datetime.now(timezone.utc)` en los 8 models fields + repository fallbacks + rule_evaluator. `fromtimestamp` también usa `tz=timezone.utc` para consistencia.
- [x] #31 **Hexagonal YAGNI** — 5 ABCs en `core/ports/` eliminados. `RuleRepository`/`UndoStack`/`HistoryRepository` → borrados (0 consumidores). `FileWatcher` fusionado en `WatchdogFileWatcher`, `NotificationService` fusionado en `PyQtNotificationAdapter`. `NotificationUrgency` movido a `core/models/`. 6 archivos + directorio eliminados (~330 líneas menos)
- [x] #32 **8 archivos de persistencia → 1 JSON** — fusionado en `zorma_repository.py`. Un solo `zorma.json`, 1 clase, 0 RLock. Eliminados `json_rule_repository.py`, `json_undo_stack.py`, `json_history_repository.py`, constantes muertas en settings.py (~530 líneas menos)
- [x] #33 **Constantes muertas en settings.py** — `BATCH_SIZE`, `BATCH_WINDOW`, `RAM_PASSIVE_LIMIT`, `RAM_ACTIVE_LIMIT`, `CPU_PASSIVE_LIMIT`, `RETRY_INTERVAL`, `RETRY_MAX_ATTEMPTS`. Cero referencias en el código
- [x] #34 **Inline MainWindowViewModel** — 65 líneas que solo persisten theme toggle. Movido a `main_window.py`
- [x] #35 **Limpiar __init__.py que solo re-exportan** — 7 archivos eliminados (core/models/, core/services/, adapters/persistence/, adapters/watcher/, ui/shared/, ui/rules/, ui/dashboard/). 2 directorios vacíos (ui/files/, ui/alerts/). 0 consumidores de re-exports
- [x] #36 **Filtrado duplicado en 3 lugares** — `Archivos ` safety filter movido de `ZormaEventHandler._dispatch()` a `FilterConfig.matches()`. Ahora todas las rutas de filtrado (eventos watchdog + escaneo inicial) comparten la misma lógica via `matches()`.
- [x] #37 **No crear abstracción FileSystem** — `shutil` directo está bien. El #28 propone over-engineering (YAGNI). Marcar como rechazado
- [x] #38 **Simplificar styles.py** — eliminados `btn_success` (19 lns), `btn_warning` (19 lns), `DARK_THEME` (1 ln). 0 consumidores. Generación dinámica de QSS mantenida (más simple que 2 archivos planos para theme switching)
- [x] #39 **Simplificar widgets.py** — RECHAZADO (YAGNI). SidebarButton tiene 1 consumidor prod + test; moverlo no ahorra líneas y complica imports. 6 clases en widgets.py son componentes legítimamente compartidos

---

## 🧪 Tests

- [x] #19 `test_watcher_service.py` — añadido `history = create_autospec(HistoryRepository)` en `setup_method`. Además se corrigió `_on_event` que no retornaba `result` para directorios. **104/104 tests, 0 failed, 0 errors**

---

## 📊 Referencia cruzada

| Origen | Items |
|--------|-------|
| Análisis bugs (doc 1) | #1-12, #14, #16, #19, #21-30 |
| Análisis UX/UI (doc 2) | #1.1-1.7, #2.1-2.7, #3.1-3.3, #4.1-4.3, #5.1-5.3, #6.1-6.3 |
| Ponytail audit | #31-39 |
| Verificados como aún vigentes | #1.1, #3, #6, #10 (casing), #1.5b, #2.2, #2.3, #3.3, #5.1, #6.1, #2.1a/b, #3.1, #1.6, #1.7, #14, #16, #21-39 |
