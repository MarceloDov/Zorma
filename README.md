# Zorma

Clasificador automático de archivos con interfaz gráfica (PyQt6) y monitorización en tiempo real vía watchdog.

## Características

- **Monitor en segundo plano** — observa carpetas y clasifica archivos automáticamente al crearse.
- **Reglas por extensión** — cada extensión de archivo se mueve a su propia carpeta (ej. `~/Zorma/Archivos txt`).
- **Interfaz gráfica** — dashboard, vista de reglas, historial de clasificación, vista previa y resolución de conflictos.
- **Tema oscuro** — paleta inspirada en Catppuccin.
- **Deshacer** — permite revertir clasificaciones.

## Requisitos

- Python >= 3.12
- PyQt6 >= 6.6.0
- watchdog >= 4.0.0

## Instalación

```bash
git clone <repo-url>
cd zorma
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\Activate.ps1  # Windows
pip install -e .
```

Para desarrollo:

```bash
pip install -e ".[dev]"
```

## Uso

```bash
zorma
```

## Estructura

```text
src/zorma/
├── __main__.py        # Punto de entrada
├── core/              # Lógica de dominio: servicios, modelos, puertos
├── adapters/          # Implementaciones concretas (persistencia, watchdog)
├── ui/                # Interfaz gráfica (PyQt6)
└── config/            # Configuración global
```

## Tests

```bash
pytest tests/ -v
```

## Licencia

MIT
