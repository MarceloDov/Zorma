# AGENTS.md

## 0. Jerarquía de reglas
Conflicto entre reglas se resuelve en este orden:
1. Seguridad y corrección.
2. Convenciones de este archivo.
3. Minimalismo (sección 5) — solo después de satisfacer 1 y 2.

## 1. Resumen del proyecto
Zorma: clasificador automático de archivos con GUI (PyQt6) para Windows. Monitorea carpetas con `watchdog` y mueve/copia/renombra archivos según reglas por extensión, tamaño, fecha o nombre. Uso personal/desktop, un solo usuario por instalación.

## 2. Stack técnico
- Lenguaje: Python >= 3.12 (target py312 en ruff/mypy).
- GUI: PyQt6 >= 6.6.0.
- Monitoreo de FS: watchdog >= 4.0.0.
- Gestor de paquetes: **uv** (no pip/poetry).
- Persistencia: JSON plano en `~/.zorma/zorma.json` (sin DB, sin ORM).
- Build de ejecutable: PyInstaller vía `zorma.spec` (ver sección 3).

## 3. Comandos de setup
```bash
# instalar (incluye dev: pytest, ruff, mypy, pyinstaller — es un extra "dev", no [tool.uv].dev-dependencies)
uv sync --all-extras

# correr tests
uv run pytest -q

# lint
uv run ruff check .

# type check (strict)
uv run mypy src/

# levantar la app
uv run python -m zorma

# generar el .exe (dist/zorma/zorma.exe)
uv run pyinstaller --noconfirm zorma.spec
```
`zorma.spec` apunta a `build_entry.py` (raíz), no a `src/zorma/__main__.py` directo — ese último usa imports relativos y falla como script suelto (`ImportError: attempted relative import`).

## 4. Estilo de código
- `from __future__ import annotations` al inicio de cada módulo.
- Tipado moderno: `X | None`, `list[X]`, `dict[X, Y]` — nunca `Optional`/`List`/`Dict` de `typing`.
- Modelos de dominio: `@dataclass` (no Pydantic — no hay validación de red/API que la justifique).
- **Nombres de dominio en español** (clases, campos, métodos): `Regla`, `Archivo`, `AccionRegla`, `ServicioClasificacion`. UI/PyQt (imports, nombres de objetos Qt) sí en inglés.
- Fechas: siempre `datetime.now(UTC)` (de `datetime import UTC`), nunca `timezone.utc`.
- Línea máx. 120 caracteres (`ruff: line-length = 120`).
- mypy strict en todo `src/`, con una excepción documentada: `ui.shared.toast` tiene `ignore_errors = true` en `pyproject.toml` — no es objetivo a "arreglar", es deliberado.
- `logging.getLogger(__name__)` en `core/`/`adapters/`. `ui/` no loguea — feedback al usuario va por `mostrar_aviso()` (`ui/shared/aviso.py`). Nunca `print`.

```python
@dataclass
class Regla:
    id: str = field(default_factory=lambda: uuid4().hex)
    tipo_condicion: TipoCondicion = TipoCondicion.EXTENSION
    valor_condicion: str = ""
    creado_en: datetime = field(default_factory=lambda: datetime.now(UTC))

    def evaluar(self, archivo: Archivo) -> bool: ...
```

## 5. Disciplina anti-sobreingeniería (Ponytail)
Antes de escribir código nuevo:
1. ¿Es necesario? (YAGNI) — si es especulativo, no.
2. ¿La stdlib ya lo resuelve? Úsala (ej. `operator`, no lambdas de comparación a mano).
   - Antes de crear un enum/tipo nuevo, revisar `core/models/enums.py` — `TipoAccion` y `TipoOperacion` existieron duplicados (mismos valores) hasta que se fusionaron; no repetir el patrón.
3. ¿Una dependencia ya instalada lo resuelve? Úsala. No agregar deps nuevas sin pedirlo.
4. ¿Se puede en una línea? Hazlo en una línea.
5. Solo entonces: mínimo código funcional.

No aplicar pereza en: validación de `zorma.json` al deserializar (es límite de confianza — el usuario puede editarlo o tener una versión vieja), manejo de errores que evita pérdida de archivos del usuario, y todo lo pedido explícitamente.

Lógica no trivial deja una verificación ejecutable mínima (`assert` o test en `tests/`).

## 6. Pruebas
Framework: `pytest` + `pytest-qt`. Ubicación: `tests/`, flat (no espeja `src/zorma/**` subcarpeta por subcarpeta) — algunos `test_*.py` conservan nombre de módulo pre-refactor (ej. `test_action_executor.py` prueba `accion_regla.py`); al crear un test nuevo, nombrarlo por el módulo actual que cubre. Mockear PyQt widgets pesados y `ZormaRepository` con `unittest.mock.create_autospec`, no instanciar Qt real salvo en `test_ui_*`.

## 7. QA — lo que corre en CI (`.github/workflows/ci.yml`)
En cada push/PR a `main`, sobre Python 3.12 y 3.13:
```bash
ruff check .
mypy src/
python -m pytest tests/ -v --tb=short
```
Si alguno falla, el PR no debe mergearse. No hay umbral de cobertura ni linter de complejidad configurado — no inventar uno; si hace falta, agregarlo a CI primero, documentarlo después.

## 8. Seguridad
- `~/.zorma/zorma.json` es editable por el usuario (o versión anterior de la app) — es frontera de confianza. Toda deserialización debe tolerar entradas corruptas (ver patrón `_deserialize_all` en `zorma_repository.py`), nunca crashear el arranque.
- Nunca commitear secretos/tokens (no aplica hoy: la app no llama APIs externas ni tiene credenciales).
- Rutas de destino de reglas de usuario (`carpeta_destino`) deben seguir validando path traversal (`".." in raw.parts`) antes de mover/copiar archivos — no relajar esa validación.

## 9. Commits y PR
Conventional Commits (`feat:`, `fix:`, `test:`, `refactor:`) con descripción en español, ej. `feat: agregar animación de navegación`. Rama: `feature/descripcion-corta` o `fix/descripcion-corta`. PR explica qué cambia y por qué.

## 10. Límites del agente (nunca tocar sin aprobación explícita)
- `.github/workflows/ci.yml`.
- Borrar o sobreescribir `~/.zorma/zorma.json` de un usuario real.
- Force-push, `git reset --hard`, o reescribir historia ya pusheada.
- Agregar una dependencia nueva a `pyproject.toml` sin que se haya pedido.

## 11. Mantenimiento
Tratar como código: corto, y crece solo cuando un agente falla repetido en algo concreto. Contexto del refactor a nombres en español (ya completado: métodos, clases y archivos) y la próxima fase (split SOLID de `InicioViewModel`, ports/`Protocol`) está en `docs/plan-refactor-solid.md` — leerlo antes de tocar `core/services/` o `ui/dashboard/` en algo estructural.
