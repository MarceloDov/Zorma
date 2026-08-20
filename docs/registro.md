# Análisis SOLID — Zorma

## S - Single Responsibility (Responsabilidad Única) ⚠️

| Clase | Líneas | Problema |
|-------|--------|----------|
| `ServicioClasificacion` | 159 | Orquesta clasificación, maneja eventos de filesystem, hace scan inicial, itera archivos, busca acciones, clasifica, previsualiza |
| `ZormaRepository` | 379 | CRUD de reglas/grupos/acciones, pilas undo/redo, historial, tema, serialización, migración de schema, defaults |
| `DashboardViewModel` | 374 | Settings de UI, watcher, clasificación, workers, undo/redo, contadores, onboarding |
| `Regla` | 126 | Dataclass + 4 evaluadores internos (_eval_extension, _eval_size, _eval_date, _eval_name) |

### Correctas
`FilterConfig`, `PilaDeshacer`, `EventoArchivo`, `AccionRegla`, `RulesViewModel`, `ScanWorker`, `DebounceCallback`

## O - Open/Closed (Abierto/Cerrado) ⚠️

**`Regla.evaluar()`** — para agregar un nuevo tipo de condición (ej. `content-type`) hay que modificar:
1. Enum `TipoCondicion`
2. Dict interno en `evaluar()`
3. Nuevo método `_eval_*` en `Regla`

**`AccionRegla._resolver_destino()`** — nuevo `TipoAccion` requiere modificar el if/elif.

**✅** La arquitectura hexagonal es OCP-friendly en los adapters.

## L - Liskov Substitution ✅

Sin problemas. Herencia superficial:
- `Archivo(Nombre, Extension)` — dataclasses simples
- `ZormaEventHandler(PatternMatchingEventHandler)` — override correcto
- `ScanWorker/ClassifyWorker(QThread)` — subclases limpias
- Widgets Qt estándar

## I - Interface Segregation (Segregación de Interfaces) ⚠️

No hay interfaces/Protocols/ABCs en todo el código.

| Dependencia | Usa la clase completa pero necesita solo |
|-------------|-------------------------------------------|
| `RulesViewModel` → `ZormaRepository` | 5/20 métodos |
| `GestorDeshacer` → `ZormaRepository` | Solo undo/redo |
| `ServicioClasificacion` → `WatchdogFileWatcher` | Clase concreta, sin abstracción |

## D - Dependency Inversion (Inversión de Dependencias) ❌

El core depende de adapters, violando la arquitectura hexagonal:

```
core/services/servicio_clasificacion.py:7
  → from ...adapters.persistence.zorma_repository import ZormaRepository

core/services/servicio_clasificacion.py:16
  → from ...adapters.watcher.watchdog_watcher import WatchdogFileWatcher

core/services/gestor_deshacer.py:8
  → from ...adapters.persistence.zorma_repository import ZormaRepository
```

Las abstracciones (`Protocol`) deberían vivir en `core/` y los adapters implementarlas.

## Resumen

| Principio | Estado |
|-----------|--------|
| **S** SRP | ⚠️ Varias clases con múltiples responsabilidades |
| **O** OCP | ⚠️ Strategy parcial, pero agregar condiciones requiere modificar `Regla` |
| **L** LSP | ✅ Correcto |
| **I** ISP | ⚠️ Sin interfaces/Protocols; dependencias de clases concretas grandes |
| **D** DIP | ❌ Core importa adapters; falta abstracción |

## Prioridades de mejora

1. **DIP**: Definir `Protocol` en `core/` para `Repository`, `FileWatcher`, `NotificationAdapter`
2. **OCP/SRP en Regla**: Extraer evaluadores a clases separadas con interfaz común
3. **SRP en ServicioClasificacion**: Separar escaneo, clasificación y manejo de eventos
4. **ISP**: Segmentar `ZormaRepository` en interfaces más pequeñas
